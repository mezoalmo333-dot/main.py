# -*- coding: utf-8 -*-
"""
Telegram Top-Up Bot
------------------------
Production service-credit top-up bot.

Flow:
1) User presses "تعبئة رصيد"
2) Bot asks for amount
3) Bot shows a configured payment number
4) User sends transfer screenshot + sender number
5) Admin receives a review card with:
   - requested amount
   - sender number
   - screenshot
   - Confirm / Reject buttons
6) Confirm adds virtual service credits.
7) Reject closes the request.

No real-money betting, wagering, withdrawal, or gambling logic is included.
"""

import json
import logging
import os
import uuid
from html import escape
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    MessageEntity,
    CopyTextButton,
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    PreCheckoutQueryHandler,
    filters,
)
from telegram.error import BadRequest

BOT_TOKEN = "8970655864:AAGSOMZlNoAENKiyfskVob51MSFEwKIrg2k"
OWNER_ID = 8037399518

# Vodafone Cash number displayed to users for payment.
VODAFONE_CASH_NUMBER = "01205995761"

DB_FILE = Path("topup_db.json")
MIN_TOPUP = 150
MAX_TOPUP = 100000

# Telegram Stars: 1 Star = 1 service-credit unit.
STARS_PER_CREDIT = 3

ASK_AMOUNT, ASK_SENDER, ASK_RECEIPT = range(3)
ADMIN_CASH, ADMIN_IMAGE, ADMIN_BROADCAST_CONTENT, ADMIN_BROADCAST_BUTTONS, ADMIN_ADD, ADMIN_FUNDS = range(10, 16)

DEFAULT_DB = {
    "users": {},
    "requests": {},
    "blocked_users": {},
    "admins": [OWNER_ID],
    "settings": {
        "cash_number": VODAFONE_CASH_NUMBER,
        "images": {},
    },
}


def save_db(data):
    tmp = DB_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DB_FILE)


def load_db():
    if not DB_FILE.exists():
        data = DEFAULT_DB.copy()
        data["users"] = {}
        data["requests"] = {}
        data["blocked_users"] = {}
        data["admins"] = [OWNER_ID]
        data["settings"] = {"cash_number": VODAFONE_CASH_NUMBER, "images": {}}
        save_db(data)
        return data

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("users", {})
        data.setdefault("requests", {})
        data.setdefault("blocked_users", {})
        data.setdefault("admins", [OWNER_ID])
        if OWNER_ID not in data["admins"]:
            data["admins"].insert(0, OWNER_ID)
        data.setdefault("settings", {})
        data["settings"].setdefault("cash_number", VODAFONE_CASH_NUMBER)
        data["settings"].setdefault("images", {})
        return data
    except Exception:
        data = {"users": {}, "requests": {}, "blocked_users": {}, "admins": [OWNER_ID], "settings": {"cash_number": VODAFONE_CASH_NUMBER, "images": {}}}
        save_db(data)
        return data


db = load_db()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("topup_bot")


def get_cash_number():
    return str(db.get("settings", {}).get("cash_number") or VODAFONE_CASH_NUMBER)


def get_section_image(section):
    return db.get("settings", {}).get("images", {}).get(section)


def set_section_image(section, file_id):
    db.setdefault("settings", {}).setdefault("images", {})[section] = file_id
    save_db(db)


def remove_section_image(section):
    db.setdefault("settings", {}).setdefault("images", {}).pop(section, None)
    save_db(db)


SECTION_NAMES = {
    "welcome": "الترحيب",
    "topup": "تعبئة رصيد",
    "balance": "رصيدي",
    "howto": "طريقة الاستخدام",
    "cash": "تعبئة بالكاش",
    "stars": "تعبئة بالنجوم",
    "transfer": "بيانات التحويل",
}


def get_user(user_id, first_name="", username=""):
    key = str(user_id)
    if key not in db["users"]:
        db["users"][key] = {
            "id": user_id,
            "first_name": first_name or "",
            "username": username or "",
            "credits": 0,
        }
    else:
        db["users"][key]["first_name"] = first_name or db["users"][key].get("first_name", "")
        db["users"][key]["username"] = username or db["users"][key].get("username", "")
    return db["users"][key]


def bold_quote(text):
    return f"<blockquote><b>{text}</b></blockquote>"


def tg_emoji(emoji_id, fallback="⭐"):
    """Telegram HTML custom emoji tag."""
    return f'<tg-emoji emoji-id="{escape(str(emoji_id), quote=True)}">{escape(fallback)}</tg-emoji>'


def user_link_html(user):
    name = escape(user.full_name or user.first_name or "المستخدم")
    if user.username:
        href = f"https://t.me/{escape(user.username, quote=True)}"
    else:
        href = f"tg://user?id={user.id}"
    return f'<a href="{href}">{name}</a>'


def utf16_offset(text, char_index):
    return len(text[:char_index].encode("utf-16-le")) // 2


def custom_quote(text, emoji_positions=None):
    emoji_positions = emoji_positions or []
    total_len = len(text.encode("utf-16-le")) // 2
    entities = [
        MessageEntity(MessageEntity.BLOCKQUOTE, 0, total_len),
        MessageEntity(MessageEntity.BOLD, 0, total_len),
    ]
    emoji_len = len("⭐".encode("utf-16-le")) // 2
    for pos, emoji_id in emoji_positions:
        entity_pos = utf16_offset(text, pos)
        entities.append(MessageEntity(MessageEntity.CUSTOM_EMOJI, entity_pos, emoji_len, custom_emoji_id=str(emoji_id)))
    return text, entities


def is_blocked(user_id):
    return bool(db.get("blocked_users", {}).get(str(user_id)))


def block_user(user_id):
    db.setdefault("blocked_users", {})[str(user_id)] = True
    save_db(db)


def is_admin(user_id):
    try:
        return int(user_id) in {int(x) for x in db.get("admins", [OWNER_ID])}
    except Exception:
        return int(user_id) == OWNER_ID


def add_admin(user_id):
    db.setdefault("admins", [])
    uid = int(user_id)
    if uid not in [int(x) for x in db["admins"]]:
        db["admins"].append(uid)
        save_db(db)
        return True
    return False


def styled_button(text, callback_data, style="primary", custom_emoji_id=None):
    kwargs = {
        "text": text,
        "callback_data": callback_data,
        "style": style,
    }
    if custom_emoji_id:
        kwargs["icon_custom_emoji_id"] = str(custom_emoji_id)
    return InlineKeyboardButton(**kwargs)


def plain_main_keyboard():
    return InlineKeyboardMarkup([
        [
            styled_button("تعبئة رصيد", "topup", "primary"),
            styled_button("رصيدي", "balance", "primary"),
        ],
        [
            styled_button("طريقة الاستخدام", "howto", "primary"),
        ],
        [
            styled_button("تواصل معا الدعم الفني", "support", "primary"),
        ],
    ])


def main_keyboard(user_id=None):
    rows = [
        [styled_button("استثمار الآن", "investment_now", "success", "5974217466270716579")],
        [styled_button("تعبئة رصيد", "topup", "primary", "5206607081334906820"), styled_button("رصيدي", "balance", "primary", "5231200819986047254")],
        [styled_button("طريقة الاستخدام", "howto", "primary", "5382357040008021292")],
        [InlineKeyboardButton("تواصل معا الدعم الفني", url="https://t.me/Hind_EiD1", style="primary", icon_custom_emoji_id="5395695537687123235")],
    ]
    if user_id is not None and is_admin(user_id):
        rows.append([InlineKeyboardButton("لوحة الأدمن", callback_data="admin", style="primary")])
    return InlineKeyboardMarkup(rows)


def plain_payment_keyboard():
    return InlineKeyboardMarkup([
        [styled_button("⭐ نجوم", "stars_topup", "success")],
        [styled_button("💵 فودافون كاش", "cash_topup", "danger")],
        [styled_button("إلغاء", "cancel_topup", "danger")],
    ])


def payment_keyboard():
    return InlineKeyboardMarkup([
        [styled_button("نجوم", "stars_topup", "success", "6298369007560951386")],
        [styled_button("فودافون كاش", "cash_topup", "danger", "5870611245794595990")],
        [styled_button("إلغاء", "cancel_topup", "danger")],
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "رجوع",
                callback_data="back_main",
                style="danger",
                icon_custom_emoji_id="5260293700088511294",
            )
        ]
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("الصور", callback_data="admin_images", icon_custom_emoji_id="5931629923478278721"), InlineKeyboardButton("إذاعة", callback_data="admin_broadcast", icon_custom_emoji_id="5462943653116792628")],
        [InlineKeyboardButton("إضافة أدمن", callback_data="admin_add", style="primary"), InlineKeyboardButton("إضافة فلوس", callback_data="admin_funds", style="primary")],
        [InlineKeyboardButton("المستخدمين", callback_data="admin_users", style="primary"), InlineKeyboardButton("المحظورين", callback_data="admin_blocked", style="danger")],
        [InlineKeyboardButton("تغيير رقم الكاش", callback_data="admin_cash", style="primary")],
        [InlineKeyboardButton("إغلاق", callback_data="admin_close", style="danger")],
    ])


def admin_images_keyboard():
    rows = []
    for key, title in SECTION_NAMES.items():
        rows.append([
            InlineKeyboardButton(
                title,
                callback_data=f"admin_img:{key}",
                icon_custom_emoji_id="5931629923478278721",
            ),
            InlineKeyboardButton(
                "حذف",
                callback_data=f"admin_delimg:{key}",
                style="danger",
                icon_custom_emoji_id="5931476386987380989",
            ),
        ])
    rows.append([
        InlineKeyboardButton(
            "رجوع",
            callback_data="admin_back",
            style="danger",
        )
    ])
    return InlineKeyboardMarkup(rows)


def broadcast_buttons_keyboard(buttons):
    if not buttons:
        return None
    rows = []
    for item in buttons:
        btn = InlineKeyboardButton(
            item["text"],
            url=item["url"],
            **({"icon_custom_emoji_id": item["emoji_id"]} if item.get("emoji_id") else {}),
        )
        # Two buttons per row by default. This supports well over 10 buttons.
        if not rows or len(rows[-1]) >= 2:
            rows.append([btn])
        else:
            rows[-1].append(btn)
    return InlineKeyboardMarkup(rows)


def parse_broadcast_buttons(text):
    """
    Each non-empty line:
      Button text | https://example.com | optional_custom_emoji_id

    Empty lines create a new row.
    A blank line is therefore optional; buttons are normally paired two per row.
    """
    buttons = []
    errors = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = [x.strip() for x in line.split("|")]
        if len(parts) < 2:
            errors.append(line)
            continue
        label, url = parts[0], parts[1]
        emoji_id = parts[2] if len(parts) >= 3 and parts[2] else None
        if not label or not url.startswith(("http://", "https://", "tg://")):
            errors.append(line)
            continue
        if emoji_id and not emoji_id.isdigit():
            errors.append(line)
            continue
        buttons.append({
            "text": label,
            "url": url,
            "emoji_id": emoji_id,
        })
    return buttons, errors



def cancel_keyboard():
    return InlineKeyboardMarkup([
        [styled_button("إلغاء", "cancel_topup", "danger")],
    ])


def cash_number_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "نسخ رقم التحويل",
                copy_text=CopyTextButton(get_cash_number()),
                style="primary",
            )
        ],
        [styled_button("إلغاء", "cancel_topup", "danger")],
    ])



async def investment_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if u and is_blocked(u.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.", show_alert=True)
        return

    q = update.callback_query
    await q.answer()
    text = bold_quote(
        "قسم الاستثمار\n\n"
        "يمكنك الدخول إلى قسم الاستثمار بعد تجهيز رصيدك.\n"
        "ملاحظة: لا توجد أرباح مضمونة، وأي عائد يعتمد على شروط الخدمة الفعلية."
    )
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
        [styled_button("تعبئة رصيد", "topup", "primary", "5206607081334906820")],
        [styled_button("رجوع", "back_main", "danger", "5260293700088511294")],
    ]))


async def how_to_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if u and is_blocked(u.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.", show_alert=True)
        return

    text = (
        "بـص يـا روحي أول حاجة اعمل إيداع عبر كاش مصري أو نجوم، "
        "بعد كدة بيظهرلك لوحـة استثمار مضمونة بتقدر تستثمر فلوسك بشكل مجاني، "
        "ولو واجهتك أي مشكلة في الإيداع أو خسرت بيتم تعويضك تلقائي، "
        "يعني كسبان كسبان."
    )
    msg = bold_quote(f"{text} {tg_emoji('5382357040008021292', '⭐')}")
    q = update.callback_query
    if q:
        await q.answer()
        photo = get_section_image("howto")
        if photo:
            try:
                await q.message.delete()
            except Exception:
                pass
            await context.bot.send_photo(
                chat_id=q.message.chat_id,
                photo=photo,
                caption=msg,
                parse_mode="HTML",
                reply_markup=back_keyboard(),
            )
        else:
            await q.edit_message_text(
                msg,
                parse_mode="HTML",
                reply_markup=back_keyboard(),
            )
    else:
        await update.message.reply_text(
            msg,
            parse_mode="HTML",
            reply_markup=back_keyboard(),
        )


async def support_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(
        bold_quote("تواصل معا الدعم الفني | @Hind_EiD1"),
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        bold_quote("القائمة الرئيسية"),
        parse_mode="HTML",
        reply_markup=main_keyboard(update.effective_user.id),
    )


async def admin_add_start(update, context):
    q=update.callback_query
    if q.from_user.id != OWNER_ID:
        await q.answer("المالك فقط يستطيع إضافة أدمن.", show_alert=True); return ConversationHandler.END
    await q.answer(); await q.edit_message_text(bold_quote("أرسل ID المستخدم الذي تريد إضافته كأدمن."), parse_mode="HTML", reply_markup=back_keyboard()); return ADMIN_ADD

async def admin_add_save(update, context):
    if update.effective_user.id != OWNER_ID: return ConversationHandler.END
    try: uid=int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(bold_quote("أرسل Telegram ID رقمي فقط."), parse_mode="HTML"); return ADMIN_ADD
    ok=add_admin(uid)
    await update.message.reply_text(bold_quote(("تمت إضافة الأدمن." if ok else "المستخدم أدمن بالفعل.")+f"\n\nID: {uid}"), parse_mode="HTML", reply_markup=admin_keyboard()); return ConversationHandler.END

async def admin_funds_start(update, context):
    q=update.callback_query
    if not is_admin(q.from_user.id): await q.answer("غير مصرح.", show_alert=True); return ConversationHandler.END
    await q.answer(); await q.edit_message_text(bold_quote("إضافة فلوس لمستخدم\n\nأرسل بالشكل:\nID المبلغ\n\nمثال: 123456789 500"), parse_mode="HTML", reply_markup=back_keyboard()); return ADMIN_FUNDS

async def admin_funds_save(update, context):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    parts=(update.message.text or "").strip().split()
    if len(parts)!=2:
        await update.message.reply_text(bold_quote("الصيغة: ID المبلغ"), parse_mode="HTML"); return ADMIN_FUNDS
    try: uid=int(parts[0]); amount=int(parts[1])
    except ValueError:
        await update.message.reply_text(bold_quote("الـID والمبلغ لازم يكونوا أرقام."), parse_mode="HTML"); return ADMIN_FUNDS
    if amount<=0:
        await update.message.reply_text(bold_quote("المبلغ يجب أن يكون أكبر من صفر."), parse_mode="HTML"); return ADMIN_FUNDS
    user=get_user(uid); user["credits"]=int(user.get("credits",0))+amount; save_db(db)
    await update.message.reply_text(bold_quote(f"تمت إضافة {amount} جنيه للمستخدم.\n\nID: {uid}\nرصيده الجديد: {user['credits']} جنيه"), parse_mode="HTML", reply_markup=admin_keyboard())
    try: await context.bot.send_message(uid,bold_quote(f"تمت إضافة {amount} جنيه إلى رصيدك.\n\nرصيدك الحالي: {user['credits']} جنيه"),parse_mode="HTML")
    except Exception: pass
    return ConversationHandler.END

async def admin_users(update, context):
    q=update.callback_query
    if not is_admin(q.from_user.id): await q.answer("غير مصرح.", show_alert=True); return
    await q.answer(); users=list(db.get("users",{}).values())
    lines=[]
    for u in users[-50:]: lines.append(f"• {u.get('first_name') or 'بدون اسم'} | @{u.get('username')}\nID: {u['id']} | الرصيد: {u.get('credits',0)} جنيه | {'🚫 محظور' if is_blocked(u['id']) else '✅ نشط'}")
    text="المستخدمون:\n\n"+"\n\n".join(lines) if lines else "لا يوجد مستخدمون مسجلون."
    await q.edit_message_text(bold_quote(text[:4000]),parse_mode="HTML",reply_markup=back_keyboard())

async def admin_blocked(update, context):
    q=update.callback_query
    if not is_admin(q.from_user.id): await q.answer("غير مصرح.", show_alert=True); return
    await q.answer(); ids=list(db.get("blocked_users",{}).keys())
    text="المستخدمون المحظورون:\n\n"+"\n\n".join(f"• ID: {uid}" for uid in ids) if ids else "لا يوجد مستخدمون محظورون."
    await q.edit_message_text(bold_quote(text[:4000]),parse_mode="HTML",reply_markup=back_keyboard())


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer("غير مصرح.", show_alert=True)
        else:
            await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END

    text = bold_quote(
        f"لوحة الأدمن\n\n"
        f"رقم الكاش الحالي: {get_cash_number()}\n"
        f"عدد المستخدمين: {len(db['users'])}\n"
        f"الصور المضافة: {len(db.get('settings', {}).get('images', {}))}"
    )
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=admin_keyboard())
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=admin_keyboard())
    return ConversationHandler.END


async def admin_change_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.callback_query.answer("غير مصرح.", show_alert=True)
        return ConversationHandler.END
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        bold_quote("أرسل رقم الكاش الجديد الآن."),
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )
    return ADMIN_CASH


async def admin_save_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END
    number = update.message.text.strip().replace(" ", "").replace("-", "")
    if not number.isdigit() or len(number) < 8 or len(number) > 20:
        await update.message.reply_text(
            bold_quote("رقم الكاش غير صحيح. أرسله أرقام فقط."),
            parse_mode="HTML",
        )
        return ADMIN_CASH

    db.setdefault("settings", {})["cash_number"] = number
    save_db(db)
    await update.message.reply_text(
        bold_quote(f"تم تغيير رقم الكاش إلى: {number}"),
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )
    return ConversationHandler.END


async def admin_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.callback_query.answer("غير مصرح.", show_alert=True)
        return ConversationHandler.END
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        bold_quote("اختر القسم الذي تريد إضافة أو تغيير صورته."),
        parse_mode="HTML",
        reply_markup=admin_images_keyboard(),
    )
    return ConversationHandler.END


async def admin_select_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.callback_query.answer("غير مصرح.", show_alert=True)
        return ConversationHandler.END
    q = update.callback_query
    section = q.data.split(":", 1)[1]
    context.user_data["admin_image_section"] = section
    await q.answer()
    await q.edit_message_text(
        bold_quote(f"أرسل الآن صورة قسم: {SECTION_NAMES.get(section, section)}"),
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )
    return ADMIN_IMAGE


async def admin_receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END
    if not update.message.photo:
        await update.message.reply_text(
            bold_quote("أرسل صورة فقط."),
            parse_mode="HTML",
        )
        return ADMIN_IMAGE

    section = context.user_data.get("admin_image_section")
    if section not in SECTION_NAMES:
        await update.message.reply_text("اختر القسم من لوحة الصور أولاً.")
        return ConversationHandler.END

    file_id = update.message.photo[-1].file_id
    set_section_image(section, file_id)
    context.user_data.pop("admin_image_section", None)

    await update.message.reply_text(
        bold_quote(f"تم حفظ صورة قسم: {SECTION_NAMES[section]}"),
        parse_mode="HTML",
        reply_markup=admin_images_keyboard(),
    )
    return ConversationHandler.END


async def admin_delete_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.callback_query.answer("غير مصرح.", show_alert=True)
        return
    q = update.callback_query
    section = q.data.split(":", 1)[1]
    remove_section_image(section)
    await q.answer("تم حذف الصورة.")
    await q.edit_message_text(
        bold_quote(f"تم حذف صورة قسم: {SECTION_NAMES.get(section, section)}"),
        parse_mode="HTML",
        reply_markup=admin_images_keyboard(),
    )
    return ConversationHandler.END


async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        bold_quote("لوحة الأدمن"),
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


async def admin_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        bold_quote("تم إغلاق لوحة الأدمن."),
        parse_mode="HTML",
        reply_markup=main_keyboard(update.effective_user.id),
    )



async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.callback_query.answer("غير مصرح.", show_alert=True)
        return ConversationHandler.END

    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        bold_quote(
            "إذاعة جديدة\n\n"
            "أرسل الآن الرسالة التي تريد إذاعتها.\n"
            "يدعم النص، الصور، الفيديو، الملفات، الملصقات، الإيموجي المميز والنصوص والروابط."
        ),
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )
    return ADMIN_BROADCAST_CONTENT


async def admin_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END

    # Save the exact source chat/message. copy_message preserves media,
    # formatting, links and custom emoji entities.
    context.user_data["broadcast_source_chat"] = update.effective_chat.id
    context.user_data["broadcast_source_message"] = update.message.message_id

    await update.message.reply_text(
        bold_quote(
            "تم استلام الرسالة.\n\n"
            "أرسل أزرار الروابط الآن، زر في كل سطر بالشكل:\n"
            "اسم الزر | https://example.com | emoji_id\n\n"
            "يمكنك إرسال أكثر من 10 أزرار.\n"
            "إذا لا تريد أزرار، اكتب: بدون"
        ),
        parse_mode="HTML",
    )
    return ADMIN_BROADCAST_BUTTONS


async def admin_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END

    raw = (update.message.text or "").strip()
    buttons = []
    errors = []

    if raw and raw not in {"بدون", "لا", "none", "-"}:
        buttons, errors = parse_broadcast_buttons(raw)
        if errors:
            await update.message.reply_text(
                bold_quote(
                    "فيه أسطر غير صحيحة.\n\n"
                    "الصيغة الصحيحة:\n"
                    "اسم الزر | https://example.com | emoji_id\n\n"
                    + "\n".join(errors[:10])
                ),
                parse_mode="HTML",
            )
            return ADMIN_BROADCAST_BUTTONS

    if len(buttons) > 100:
        await update.message.reply_text(
            bold_quote("الحد الأقصى 100 زر في الإذاعة الواحدة."),
            parse_mode="HTML",
        )
        return ADMIN_BROADCAST_BUTTONS

    source_chat = context.user_data.get("broadcast_source_chat")
    source_message = context.user_data.get("broadcast_source_message")
    if not source_chat or not source_message:
        await update.message.reply_text(
            bold_quote("انتهت جلسة الإذاعة. اضغط إذاعة مرة أخرى."),
            parse_mode="HTML",
        )
        return ConversationHandler.END

    markup = broadcast_buttons_keyboard(buttons)
    users = list(db.get("users", {}).values())
    sent = 0
    failed = 0
    blocked = 0

    await update.message.reply_text(
        bold_quote(f"بدأت الإذاعة إلى {len(users)} مستخدم..."),
        parse_mode="HTML",
    )

    for user in users:
        uid = int(user["id"])
        if is_blocked(uid):
            blocked += 1
            continue
        try:
            await context.bot.copy_message(
                chat_id=uid,
                from_chat_id=source_chat,
                message_id=source_message,
                reply_markup=markup,
            )
            sent += 1
        except Exception as exc:
            failed += 1
            logger.warning("Broadcast failed for %s: %s", uid, exc)

    context.user_data.pop("broadcast_source_chat", None)
    context.user_data.pop("broadcast_source_message", None)

    await update.message.reply_text(
        bold_quote(
            "تم انتهاء الإذاعة.\n\n"
            f"تم الإرسال: {sent}\n"
            f"فشل: {failed}\n"
            f"محظورون تم تخطيهم: {blocked}"
        ),
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )
    return ConversationHandler.END



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not u or not update.message:
        return

    if is_blocked(u.id):
        await update.message.reply_text(
            bold_quote("تم حظرك من البوت بسبب You can transfer"),
            parse_mode="HTML",
        )
        return

    get_user(u.id, u.first_name, u.username)
    save_db(db)

    linked_name = user_link_html(u)
    welcome = (
        f"مـرحـبـا بـك يـ {linked_name} فـي بـوت اربـاح اسـتـثـمـار "
        f"{tg_emoji('5409048419211682843')}\n\n"
        f"عـلـيـك الـشـحـن اولا {tg_emoji('5206607081334906820')}\n\n"
        f"عـدد مسـتخـدميـن البوت [{len(db['users'])}]"
    )

    welcome_photo = get_section_image("welcome")
    try:
        if welcome_photo:
            await update.message.reply_photo(
                photo=welcome_photo,
                caption=bold_quote(welcome),
                parse_mode="HTML",
                reply_markup=main_keyboard(update.effective_user.id),
            )
        else:
            await update.message.reply_text(
                bold_quote(welcome),
                parse_mode="HTML",
                reply_markup=main_keyboard(update.effective_user.id),
            )
    except BadRequest as exc:
        logger.warning("Welcome custom emoji/button rejected: %s", exc)
        # Fallback still keeps the person's name clickable.
        safe_welcome = (
            f"مـرحـبـا بـك يـ {linked_name} فـي بـوت اربـاح اسـتـثـمـار ⭐\n\n"
            f"عـلـيـك الـشـحـن اولا ⭐\n\n"
            f"عـدد مسـتخـدميـن البوت [{len(db['users'])}]"
        )
        await update.message.reply_text(
            bold_quote(safe_welcome),
            parse_mode="HTML",
            reply_markup=plain_main_keyboard(),
        )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not u:
        return
    if is_blocked(u.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.", show_alert=True)
        return

    user = get_user(u.id, u.first_name, u.username)
    msg = bold_quote(
        f"رصـيـدك هـو {user['credits']} جنيه {tg_emoji('5251203410396458957')}"
    )

    if update.callback_query:
        q = update.callback_query
        await q.answer()
        try:
            photo = get_section_image("balance")
            if photo:
                try:
                    await q.message.delete()
                except Exception:
                    pass
                await context.bot.send_photo(
                    chat_id=q.message.chat_id,
                    photo=photo,
                    caption=msg,
                    parse_mode="HTML",
                    reply_markup=main_keyboard(update.effective_user.id),
                )
            else:
                await q.edit_message_text(
                    msg,
                    parse_mode="HTML",
                    reply_markup=main_keyboard(update.effective_user.id),
                )
        except BadRequest as exc:
            logger.warning("Balance custom emoji/button rejected: %s", exc)
            await q.edit_message_text(
                msg.replace(tg_emoji('5251203410396458957'), "⭐"),
                parse_mode="HTML",
                reply_markup=plain_main_keyboard(),
            )
    else:
        try:
            await update.message.reply_text(
                msg,
                parse_mode="HTML",
                reply_markup=main_keyboard(update.effective_user.id),
            )
        except BadRequest as exc:
            logger.warning("Balance custom emoji/button rejected: %s", exc)
            await update.message.reply_text(
                msg.replace(tg_emoji('5251203410396458957'), "⭐"),
                parse_mode="HTML",
                reply_markup=plain_main_keyboard(),
            )


async def topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_check=update.effective_user
    if u_check and is_blocked(u_check.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.",show_alert=True)
        elif update.message:
            await update.message.reply_text(bold_quote("تم حظرك من البوت بسبب You can transfer ⭐"),parse_mode="HTML")
        return

    query = update.callback_query
    await query.answer()
    context.user_data.pop("topup", None)
    context.user_data.pop("stars_mode", None)

    keyboard = payment_keyboard()
    topup_msg = bold_quote("💰 تعبئة رصيد\n\nاختر طريقة الدفع.")
    topup_photo = get_section_image("topup")
    if topup_photo:
        try:
            await query.message.delete()
        except Exception:
            pass
        try:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=topup_photo,
                caption=topup_msg,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except BadRequest as exc:
            logger.warning("Topup image/custom button rejected: %s", exc)
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=topup_photo,
                caption=topup_msg,
                parse_mode="HTML",
                reply_markup=plain_payment_keyboard(),
            )
        return ConversationHandler.END

    try:
        await query.edit_message_text(
            topup_msg,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except BadRequest as exc:
        logger.warning("Payment custom emoji buttons rejected: %s", exc)
        await query.edit_message_text(
            bold_quote("💰 تعبئة رصيد\n\nاختر طريقة الدفع."),
            parse_mode="HTML",
            reply_markup=plain_payment_keyboard(),
        )


async def cash_topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_check=update.effective_user
    if u_check and is_blocked(u_check.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.",show_alert=True)
        elif update.message:
            await update.message.reply_text(bold_quote("تم حظرك من البوت بسبب You can transfer ⭐"),parse_mode="HTML")
        return

    query = update.callback_query
    await query.answer()
    context.user_data.pop("topup", None)
    context.user_data.pop("stars_mode", None)

    cash_title = tg_emoji("5870611245794595990", "💵")
    cash_msg = bold_quote(
        f"{cash_title} تعبئة بالكاش\n\n"
        f"الحد الأدنى: {MIN_TOPUP}\n"
        f"الحد الأقصى: {MAX_TOPUP}\n\n"
        "اكتب قيمة الرصيد الذي تريد إضافته."
    )
    cash_photo = get_section_image("cash")
    if cash_photo:
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=cash_photo,
            caption=cash_msg,
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
    else:
        await query.edit_message_text(
            cash_msg,
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
    return ASK_AMOUNT


async def stars_topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_check=update.effective_user
    if u_check and is_blocked(u_check.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.",show_alert=True)
        elif update.message:
            await update.message.reply_text(bold_quote("تم حظرك من البوت بسبب You can transfer ⭐"),parse_mode="HTML")
        return

    query = update.callback_query
    await query.answer()
    context.user_data.pop("topup", None)
    context.user_data["stars_mode"] = True

    stars_msg = bold_quote(
        "⭐ تعبئة بالنجوم\n\n"
        f"كل {STARS_PER_CREDIT} نجوم = 1 جنيه.\n"
        f"الحد الأدنى: {MIN_TOPUP}\n"
        f"الحد الأقصى: {MAX_TOPUP}\n\n"
        "اكتب قيمة الرصيد الذي تريد إضافته."
    )
    stars_photo = get_section_image("stars")
    if stars_photo:
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=stars_photo,
            caption=stars_msg,
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
    else:
        await query.edit_message_text(
            stars_msg,
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
    return ASK_AMOUNT


async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_check=update.effective_user
    if u_check and is_blocked(u_check.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.",show_alert=True)
        elif update.message:
            await update.message.reply_text(bold_quote("تم حظرك من البوت بسبب You can transfer ⭐"),parse_mode="HTML")
        return

    raw = update.message.text.strip().replace(",", "")

    try:
        amount = int(raw)
    except ValueError:
        await update.message.reply_text(
            bold_quote("اكتب المبلغ كرقم صحيح فقط."),
            parse_mode="HTML",
        )
        return ASK_AMOUNT

    if not MIN_TOPUP <= amount <= MAX_TOPUP:
        await update.message.reply_text(
            bold_quote(f"المبلغ يجب أن يكون بين {MIN_TOPUP} و {MAX_TOPUP}."),
            parse_mode="HTML",
        )
        return ASK_AMOUNT

    if context.user_data.get("stars_mode"):
        user = update.effective_user
        stars = amount * STARS_PER_CREDIT
        payload = f"topup:{user.id}:{uuid.uuid4().hex}"

        db["requests"][payload] = {
            "id": payload,
            "user_id": user.id,
            "name": user.full_name,
            "username": user.username or "",
            "amount": amount,
            "stars": stars,
            "status": "pending_stars",
        }
        save_db(db)

        try:
            await context.bot.send_invoice(
                chat_id=user.id,
                title="تعبئة رصيد",
                description=f"إضافة {amount} وحدة رصيد إلى حسابك.",
                payload=payload,
                currency="XTR",
                prices=[LabeledPrice("رصيد الخدمة", stars)],
            )
        except Exception:
            db["requests"].pop(payload, None)
            save_db(db)
            logger.exception("Could not create Stars invoice")
            await update.message.reply_text(
                bold_quote("تعذر إنشاء فاتورة النجوم حاليًا. حاول مرة أخرى."),
                parse_mode="HTML",
                reply_markup=plain_main_keyboard(),
            )
            context.user_data.pop("stars_mode", None)
            return ConversationHandler.END

        await update.message.reply_text(
            bold_quote(
                "⭐ تم إنشاء فاتورة الدفع.\n\n"
                f"المطلوب: {stars} نجمة (كل 3 نجوم = 1 جنيه).\n"
                "بعد إتمام الدفع سيتم إضافة الرصيد تلقائيًا."
            ),
            parse_mode="HTML",
            reply_markup=plain_main_keyboard(),
        )
        context.user_data.pop("stars_mode", None)
        return ConversationHandler.END

    context.user_data["topup"] = {"amount": amount}

    transfer_title = tg_emoji("5451882707875276247", "📱")
    transfer_msg = bold_quote(
        f"{transfer_title} بيانات التحويل\n\n"
        f"حوّل المبلغ المحدد إلى الرقم:\n{get_cash_number()}\n\n"
        f"المبلغ المطلوب: {amount} جنيه\n\n"
        "بعد التحويل أرسل رقم الهاتف الذي تم التحويل منه."
    )
    transfer_photo = get_section_image("transfer")
    try:
        if transfer_photo:
            await update.message.reply_photo(
                photo=transfer_photo,
                caption=transfer_msg,
                parse_mode="HTML",
                reply_markup=cash_number_keyboard(),
            )
        else:
            await update.message.reply_text(
                transfer_msg,
                parse_mode="HTML",
                reply_markup=cash_number_keyboard(),
            )
    except BadRequest as exc:
        logger.warning("Transfer custom emoji rejected: %s", exc)
        fallback_msg = bold_quote(
            f"📱 بيانات التحويل\n\n"
            f"حوّل المبلغ المحدد إلى الرقم:\n{get_cash_number()}\n\n"
            f"المبلغ المطلوب: {amount} جنيه\n\n"
            "بعد التحويل أرسل رقم الهاتف الذي تم التحويل منه."
        )
        if transfer_photo:
            await update.message.reply_photo(
                photo=transfer_photo,
                caption=fallback_msg,
                parse_mode="HTML",
                reply_markup=cash_number_keyboard(),
            )
        else:
            await update.message.reply_text(
                fallback_msg,
                parse_mode="HTML",
                reply_markup=cash_number_keyboard(),
            )
    return ASK_SENDER


async def receive_sender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_check=update.effective_user
    if u_check and is_blocked(u_check.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.",show_alert=True)
        elif update.message:
            await update.message.reply_text(bold_quote("تم حظرك من البوت بسبب You can transfer ⭐"),parse_mode="HTML")
        return

    sender = update.message.text.strip().replace(" ", "")

    if not sender.isdigit() or len(sender) < 10 or len(sender) > 15:
        await update.message.reply_text(
            bold_quote("رقم الهاتف غير صحيح. أرسل رقم الهاتف الذي تم التحويل منه."),
            parse_mode="HTML",
        )
        return ASK_SENDER

    context.user_data["topup"]["sender"] = sender

    await update.message.reply_text(
        bold_quote(
            "📸 الآن أرسل صورة إيصال التحويل.\n\n"
            "يفضل أن تكون الصورة واضحة ويظهر فيها المبلغ ورقم العملية."
        ),
        parse_mode="HTML",
    )
    return ASK_RECEIPT


async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_check=update.effective_user
    if u_check and is_blocked(u_check.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.",show_alert=True)
        elif update.message:
            await update.message.reply_text(bold_quote("تم حظرك من البوت بسبب You can transfer ⭐"),parse_mode="HTML")
        return

    if not update.message.photo:
        await update.message.reply_text(
            bold_quote("أرسل صورة إيصال التحويل كصورة، ثم أعد المحاولة."),
            parse_mode="HTML",
        )
        return ASK_RECEIPT

    u = update.effective_user
    topup = context.user_data.get("topup")

    if not topup:
        await update.message.reply_text(
            bold_quote("انتهت جلسة الطلب. اضغط تعبئة رصيد مرة أخرى."),
            parse_mode="HTML",
        )
        return ConversationHandler.END

    request_id = uuid.uuid4().hex[:10].upper()
    photo_id = update.message.photo[-1].file_id

    db["requests"][request_id] = {
        "id": request_id,
        "user_id": u.id,
        "name": u.full_name,
        "username": u.username or "",
        "amount": topup["amount"],
        "sender": topup["sender"],
        "photo_id": photo_id,
        "status": "pending",
    }
    save_db(db)

    admin_keyboard = InlineKeyboardMarkup([
        [
            styled_button(
                "تأكيد",
                f"approve:{request_id}",
                "success",
            ),
            styled_button(
                "رفض",
                f"reject:{request_id}",
                "danger",
            ),
        ]
    ])

    admin_text = (
        "<blockquote><b>"
        "🔔 طلب تعبئة جديد\n\n"
        f"الطلب: {request_id}\n"
        f"المستخدم: {u.full_name}\n"
        f"ID: {u.id}\n"
        f"المبلغ: {topup['amount']} جنيه\n"
        f"رقم المرسل: {topup['sender']}\n\n"
        "راجع الإيصال ثم اختر الإجراء."
        "</b></blockquote>"
    )

    try:
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=photo_id,
            caption=admin_text,
            parse_mode="HTML",
            reply_markup=admin_keyboard,
        )
    except Exception:
        logger.exception("Could not send request to admin")

    await update.message.reply_text(
        bold_quote(
            "✅ تم إرسال طلبك للمراجعة.\n\n"
            f"رقم الطلب: {request_id}\n"
            "سيتم تحديث الرصيد بعد مراجعة الأدمن."
        ),
        parse_mode="HTML",
        reply_markup=plain_main_keyboard(),
    )

    context.user_data.pop("topup", None)
    return ConversationHandler.END


async def approve_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != OWNER_ID:
        await query.answer("غير مصرح.", show_alert=True)
        return

    request_id = query.data.split(":", 1)[1]
    request = db["requests"].get(request_id)

    if not request:
        await query.answer("الطلب غير موجود.", show_alert=True)
        return

    if request["status"] != "pending":
        await query.answer("تمت معالجة الطلب مسبقاً.", show_alert=True)
        return

    request["status"] = "approved"

    user = get_user(request["user_id"])
    user["credits"] += int(request["amount"])
    save_db(db)

    await query.answer("تم التأكيد.")

    try:
        await context.bot.send_message(
            request["user_id"],
            bold_quote(
                "✅ تم تأكيد طلب التعبئة.\n\n"
                f"الطلب: {request_id}\n"
                f"المضاف: {request['amount']} جنيه\n"
                f"رصيدك: {user['credits']} جنيه"
            ),
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Could not notify user")

    await query.edit_message_caption(
        caption=(
            "<blockquote><b>"
            f"✅ تم تأكيد الطلب {request_id}\n\n"
            f"المبلغ: {request['amount']} جنيه\n"
            f"رقم المرسل: {request['sender']}"
            "</b></blockquote>"
        ),
        parse_mode="HTML",
        reply_markup=None,
    )


async def reject_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != OWNER_ID:
        await query.answer("غير مصرح.", show_alert=True)
        return

    request_id = query.data.split(":", 1)[1]
    request = db["requests"].get(request_id)

    if not request:
        await query.answer("الطلب غير موجود.", show_alert=True)
        return

    if request["status"] != "pending":
        await query.answer("تمت معالجة الطلب مسبقاً.", show_alert=True)
        return

    request["status"] = "rejected"
    block_user(request["user_id"])
    await query.answer("تم الرفض والحظر.")

    try:
        reject_text="تم حظرك من البوت بسبب You can transfer ⭐"
        reject_text,reject_entities=custom_quote(
            reject_text,
            [(reject_text.find("⭐"),"5411225014148014586")],
        )
        try:
            await context.bot.send_message(
                request["user_id"],
                reject_text,
                entities=reject_entities,
            )
        except BadRequest:
            await context.bot.send_message(
                request["user_id"],
                bold_quote("تم حظرك من البوت بسبب You can transfer"),
                parse_mode="HTML",
            )
    except Exception:
        logger.exception("Could not notify user")

    await query.edit_message_caption(
        caption=(
            "<blockquote><b>"
            f"❌ تم رفض الطلب {request_id}\n\n"
            f"المبلغ: {request['amount']} جنيه\n"
            f"رقم المرسل: {request['sender']}"
            "</b></blockquote>"
        ),
        parse_mode="HTML",
        reply_markup=None,
    )


async def cancel_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("topup", None)
    await query.edit_message_text(
        bold_quote("تم إلغاء طلب التعبئة."),
        parse_mode="HTML",
        reply_markup=plain_main_keyboard(),
    )
    return ConversationHandler.END


async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_check=update.effective_user
    if u_check and is_blocked(u_check.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.",show_alert=True)
        elif update.message:
            await update.message.reply_text(bold_quote("تم حظرك من البوت بسبب You can transfer ⭐"),parse_mode="HTML")
        return

    query = update.pre_checkout_query
    request = db["requests"].get(query.invoice_payload)

    if not request or request.get("status") != "pending_stars":
        await query.answer(ok=False, error_message="الفاتورة غير صالحة أو منتهية.")
        return

    if request.get("user_id") != query.from_user.id:
        await query.answer(ok=False, error_message="هذه الفاتورة ليست لحسابك.")
        return

    if int(query.total_amount) != int(request["stars"]):
        await query.answer(ok=False, error_message="قيمة الفاتورة غير صحيحة.")
        return

    await query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_check=update.effective_user
    if u_check and is_blocked(u_check.id):
        if update.callback_query:
            await update.callback_query.answer("أنت محظور من البوت.",show_alert=True)
        elif update.message:
            await update.message.reply_text(bold_quote("تم حظرك من البوت بسبب You can transfer ⭐"),parse_mode="HTML")
        return

    message = update.message
    payment = message.successful_payment
    request = db["requests"].get(payment.invoice_payload)

    if not request:
        logger.error("Unknown successful payment payload: %s", payment.invoice_payload)
        return

    if request.get("status") == "approved_stars":
        return

    if request.get("status") != "pending_stars":
        return

    if request.get("user_id") != message.from_user.id:
        logger.error("Payment user mismatch")
        return

    if int(payment.total_amount) != int(request["stars"]):
        logger.error("Payment amount mismatch")
        return

    user = get_user(
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.username,
    )
    user["credits"] += int(request["amount"])

    request["status"] = "approved_stars"
    request["charge_id"] = payment.telegram_payment_charge_id
    request["paid_stars"] = int(payment.total_amount)
    save_db(db)

    await message.reply_text(
        bold_quote(
            "⭐ تم الدفع بنجاح.\n\n"
            f"المضاف: {request['amount']} وحدة رصيد\n"
            f"المدفوع: {request['stars']} نجمة\n"
            f"رصيدك الآن: {user['credits']} وحدة"
        ),
        parse_mode="HTML",
        reply_markup=plain_main_keyboard(),
    )

    try:
        await context.bot.send_message(
            OWNER_ID,
            bold_quote(
                "⭐ تعبئة نجوم تلقائية جديدة.\n\n"
                f"المستخدم: {message.from_user.full_name}\n"
                f"ID: {message.from_user.id}\n"
                f"الرصيد المضاف: {request['amount']} وحدة\n"
                f"النجوم: {request['stars']}\n"
                f"Charge ID: {payment.telegram_payment_charge_id}"
            ),
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Could not notify owner about Stars payment")


async def monitor_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user or is_admin(update.effective_user.id) or is_blocked(update.effective_user.id): return
    u=update.effective_user; get_user(u.id,u.first_name,u.username); save_db(db)
    header=bold_quote(f"رسالة جديدة من المستخدم\n\nالاسم: {u.full_name}\nاليوزر: @{u.username if u.username else 'بدون يوزرنيم'}\nID: {u.id}")
    for aid in db.get("admins",[OWNER_ID]):
        try:
            await context.bot.send_message(int(aid),header,parse_mode="HTML")
            await context.bot.copy_message(int(aid),update.effective_chat.id,update.message.message_id)
        except Exception: logger.warning("Could not forward message to admin %s",aid)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled exception", exc_info=context.error)


def build_app():
    if not BOT_TOKEN or BOT_TOKEN == "PUT_BOT_TOKEN_HERE":
        raise RuntimeError("ضع BOT_TOKEN داخل الملف أولاً.")

    app = Application.builder().token(BOT_TOKEN).build()

    conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(topup_start, pattern=r"^topup$"),
            CallbackQueryHandler(cash_topup_start, pattern=r"^cash_topup$"),
            CallbackQueryHandler(stars_topup_start, pattern=r"^stars_topup$"),
        ],
        states={
            ASK_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)
            ],
            ASK_SENDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sender)
            ],
            ASK_RECEIPT: [
                MessageHandler(filters.PHOTO, receive_receipt)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_topup, pattern=r"^cancel_topup$")
        ],
        allow_reentry=True,
    )

    admin_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_panel),
            CallbackQueryHandler(admin_panel, pattern=r"^admin$"),
            CallbackQueryHandler(admin_change_cash, pattern=r"^admin_cash$"),
            CallbackQueryHandler(admin_select_image, pattern=r"^admin_img:[a-z]+$"),
            CallbackQueryHandler(admin_broadcast_start, pattern=r"^admin_broadcast$"),
            CallbackQueryHandler(admin_add_start, pattern=r"^admin_add$"),
            CallbackQueryHandler(admin_funds_start, pattern=r"^admin_funds$"),
        ],
        states={
            ADMIN_CASH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_save_cash)
            ],
            ADMIN_IMAGE: [
                MessageHandler(filters.PHOTO, admin_receive_image)
            ],
            ADMIN_BROADCAST_CONTENT: [
                MessageHandler(~filters.COMMAND, admin_broadcast_content)
            ],
            ADMIN_BROADCAST_BUTTONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_send)
            ],
            ADMIN_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_save)],
            ADMIN_FUNDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_funds_save)],
        },
        fallbacks=[
            CallbackQueryHandler(back_main, pattern=r"^back_main$")
        ],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(admin_conversation)
    app.add_handler(conversation)

    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment)
    )

    app.add_handler(CallbackQueryHandler(investment_now, pattern=r"^investment_now$"))
    app.add_handler(CallbackQueryHandler(how_to_use, pattern=r"^howto$"))
    app.add_handler(CallbackQueryHandler(support_button, pattern=r"^support$"))
    app.add_handler(CallbackQueryHandler(back_main, pattern=r"^back_main$"))
    app.add_handler(CallbackQueryHandler(admin_images, pattern=r"^admin_images$"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern=r"^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_blocked, pattern=r"^admin_blocked$"))
    app.add_handler(CallbackQueryHandler(admin_delete_image, pattern=r"^admin_delimg:[a-z]+$"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern=r"^admin_back$"))
    app.add_handler(CallbackQueryHandler(admin_close, pattern=r"^admin_close$"))

    app.add_handler(
        CallbackQueryHandler(
            approve_request,
            pattern=r"^approve:[A-Z0-9]+$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            reject_request,
            pattern=r"^reject:[A-Z0-9]+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            cancel_topup,
            pattern=r"^cancel_topup$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            balance,
            pattern=r"^balance$",
        )
    )

    app.add_error_handler(error_handler)
    return app


if __name__ == "__main__":
    application = build_app()
    print("Top-up bot started (production mode).")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
