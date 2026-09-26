# -*- coding: utf-8 -*-
"""
MaX VIP Subscription Bot
Pydroid 3 / Python 3.10+
"""

import asyncio
import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = "8746223128:AAGyRjSb8I8pxL1TPKKvuTsSw_Wrzlg_7Cs"
OWNER_ID = 8037399518

SUBSCRIPTION_STARS = 50
SUBSCRIPTION_DAYS = 30
SUBSCRIPTION_SECONDS = 30 * 24 * 60 * 60

DATABASE_FILE = "max_vip_bot_db.json"

ALL_VIDEOS_URL = "https://t.me/mediation_King"
DEFAULT_REQUIRED_CHANNEL = "https://t.me/mediation_King"

BOT_TITLE = "MaX VIP"

WELCOME_TEXT =(
    "Welcome to MaX VIP\n\n"
    "اشترك  ⭐ شهريًا لفتح جميع المميزات.\n"
    "بعد نجاح الدفع سيتم فتح الأقسام المتاحة لك."
)

PAYMENT_TEXT = (
    "https://t.me/mediation_King"
    "الاشتراك الشهري\n\n"
    "السعر: 50 ⭐\n"
    "المدة: 30 يوم\n\n"
    "بعد الدفع الناجح سيتم فتح جميع مميزات العضوية."
)

NO_ACCESS_TEXT = (
    "لا يمكنك استخدام هذا القسم الآن.\n\n"
    "يجب أن يكون اشتراكك فعالًا."
)

REQUIRED_CHANNEL_TEXT = (
    "قبل استخدام البوت، يجب الاشتراك في القناة المطلوبة ثم الضغط على تحقق."
)

# ============================================================
# GROUP AUTO-REPLY
# ============================================================

GROUP_REPLY_MESSAGES = [
    "تعال خاص ضروري 🫦🔥",
    "ابعت بف هقولك",
    "تعال فكيت البلوك",
    "يارجال بقولك مولعة 🔥🫦",
    "متيجي خاص تحلبني",
    "ابعتلي خاص ثانيه",
    "تعال هقولك حاجه خاص",
    "بقولك اي في فديوهات خاص تعال",
    "متيجي خاص يخول بقولك",
    "بتعرف تنيك؟",
    "تعال امصلك ابعت خاص",
    "ضيفتك ضيف وابعت خاص",
]

# نطاق الحروف العربية + الإنجليزية
LETTERS_PATTERN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF"
    r"A-Za-z"
    r"]"
)

# ============================================================
# CUSTOM EMOJI IDs
# ============================================================

EMOJI_ADMIN = "5972226216353074147"
EMOJI_ADD_VIDEO = "5974563533260590445"
EMOJI_DELETE = "5976383044615934151"
EMOJI_SUBSCRIBE = "5891131044756723016"

EMOJI_CLOTHES = "5906597204809749180"
EMOJI_ALL_VIDEOS = "5909008794586715815"
EMOJI_CHECK_SUB = "5260416304224936047"
EMOJI_HOME = "5257963315258204021"

EMOJI_FACES = [
    "5909242019900823049",
    "5908867262529409910",
    "5906536933533684298",
    "5891131044756723016",
    "5906794932219154887",
]

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("max_vip_bot")

# ============================================================
# DATABASE
# ============================================================

DEFAULT_CATEGORIES = [
    {"id": "fire", "name": "مقاطع ناررر", "videos": [], "children": [], "style": {"color": "primary", "emoji_id": "", "url": ""}},
    {"id": "kids_fire", "name": "اطفال نارية", "videos": [], "children": [], "style": {"color": "primary", "emoji_id": "", "url": ""}},
    {"id": "massage", "name": "تدليك", "videos": [], "children": [], "style": {"color": "primary", "emoji_id": "", "url": ""}},
    {"id": "clothes", "name": "ملابس", "videos": [], "children": [], "style": {"color": "primary", "emoji_id": "", "url": ""}},
    {"id": "leaks", "name": "تسريبات", "videos": [], "children": [], "style": {"color": "primary", "emoji_id": "", "url": ""}},
    {"id": "dallal", "name": "الدلع", "videos": [], "children": [], "style": {"color": "primary", "emoji_id": "", "url": ""}},
    {"id": "fun", "name": "المتعة", "videos": [], "children": [], "style": {"color": "primary", "emoji_id": "", "url": ""}},
]

DEFAULT_DB = {
    "users": {},
    "admins": [],
    "required_channels": [DEFAULT_REQUIRED_CHANNEL],
    "categories": DEFAULT_CATEGORIES,
    "settings": {
        "welcome_text": WELCOME_TEXT,
        "payment_text": PAYMENT_TEXT,
        "no_access_text": NO_ACCESS_TEXT,
        "bot_title": BOT_TITLE,
        "subscription_stars": 50,
    },
    "broadcast": {
        "running": False,
    },
    "keyword_replies": [],
}

DB: Dict[str, Any] = {}


def normalize_category(category: Dict[str, Any]) -> Dict[str, Any]:
    category.setdefault("videos", [])
    category.setdefault("children", [])
    category.setdefault("style", {"color": "primary", "emoji_id": "", "url": ""})
    category["style"].setdefault("color", "primary")
    category["style"].setdefault("emoji_id", "")
    category["style"].setdefault("url", "")

    for child in category["children"]:
        normalize_category(child)

    return category


def save_db(db: Dict[str, Any]) -> None:
    tmp = DATABASE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATABASE_FILE)


def load_db() -> Dict[str, Any]:
    path = Path(DATABASE_FILE)
    if not path.exists():
        save_db(DEFAULT_DB)
        return json.loads(json.dumps(DEFAULT_DB, ensure_ascii=False))

    try:
        with path.open("r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        logger.exception("Database could not be read. Recreating database.")
        db = json.loads(json.dumps(DEFAULT_DB, ensure_ascii=False))
        save_db(db)
        return db

    changed = False

    for key, value in DEFAULT_DB.items():
        if key not in db:
            db[key] = json.loads(json.dumps(value, ensure_ascii=False))
            changed = True

    if OWNER_ID not in db["admins"]:
        db["admins"].append(OWNER_ID)
        changed = True

    db.setdefault("keyword_replies", [])

    db.setdefault("settings", {})
    if "subscription_stars" not in db["settings"]:
        db["settings"]["subscription_stars"] = SUBSCRIPTION_STARS
        changed = True

    if not db.get("required_channels"):
        db["required_channels"] = [DEFAULT_REQUIRED_CHANNEL]
        changed = True

    for item in db.get("categories", []):
        normalize_category(item)

    if changed:
        save_db(db)

    return db


# ============================================================
# HELPERS
# ============================================================


def get_subscription_stars() -> int:
    try:
        value = int(DB.get("settings", {}).get("subscription_stars", SUBSCRIPTION_STARS))
        return max(1, value)
    except (TypeError, ValueError):
        return SUBSCRIPTION_STARS


def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in DB.get("admins", [])


def colored_button(
    text: str,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
    style: str = "primary",
    emoji_id: Optional[str] = None,
) -> InlineKeyboardButton:
    kwargs: Dict[str, Any] = {"text": text}

    if callback_data:
        kwargs["callback_data"] = callback_data

    if url:
        kwargs["url"] = url

    if style in ("primary", "success", "danger"):
        kwargs["style"] = style

    if emoji_id:
        kwargs["icon_custom_emoji_id"] = emoji_id

    return InlineKeyboardButton(**kwargs)


def chunk_rows(buttons: List[InlineKeyboardButton], per_row: int = 2) -> List[List[InlineKeyboardButton]]:
    rows = []
    for i in range(0, len(buttons), per_row):
        rows.append(buttons[i:i + per_row])
    return rows


def ensure_user(user) -> Dict[str, Any]:
    uid = str(user.id)

    if uid not in DB["users"]:
        DB["users"][uid] = {
            "id": user.id,
            "username": user.username or "",
            "name": user.full_name or "",
            "joined_at": int(time.time()),
            "subscription_until": 0,
            "payment_charge_id": "",
            "is_subscribed": False,
            "blocked": False,
        }
    else:
        DB["users"][uid]["username"] = user.username or DB["users"][uid].get("username", "")
        DB["users"][uid]["name"] = user.full_name or DB["users"][uid].get("name", "")

    save_db(DB)
    return DB["users"][uid]


def subscription_active(user_id: int) -> bool:
    user = DB["users"].get(str(user_id))
    if not user:
        return False

    until = int(user.get("subscription_until", 0))
    active = until > int(time.time())

    if user.get("is_subscribed") != active:
        user["is_subscribed"] = active
        save_db(DB)

    return active


def subscription_remaining(user_id: int) -> str:
    user = DB["users"].get(str(user_id))
    if not user:
        return "غير مشترك"

    until = int(user.get("subscription_until", 0))
    remaining = until - int(time.time())

    if remaining <= 0:
        return "منتهي"

    days = remaining // 86400
    hours = (remaining % 86400) // 3600
    minutes = (remaining % 3600) // 60

    return f"{days} يوم، {hours} ساعة، {minutes} دقيقة"


def find_nested_category(category_id: str, categories=None):
    if categories is None:
        categories = DB.get("categories", [])

    for category in categories:
        if category.get("id") == category_id:
            return category

        found = find_nested_category(category_id, category.get("children", []))
        if found:
            return found

    return None


def get_category(category_id: str) -> Optional[Dict[str, Any]]:
    return find_nested_category(category_id)


def make_category_id(name: str) -> str:
    base = "cat_" + str(abs(hash(name)))[:8]
    candidate = base
    counter = 1

    while get_category(candidate):
        candidate = f"{base}_{counter}"
        counter += 1

    return candidate


async def safe_answer_callback(query, text: Optional[str] = None, show_alert: bool = False) -> None:
    try:
        await query.answer(text=text, show_alert=show_alert)
    except Exception:
        pass


async def user_required_channels_joined(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    channels = DB.get("required_channels", [])
    if not channels:
        return True

    for channel in channels:
        channel = str(channel).strip()
        if not channel:
            continue
        if channel.startswith("https://t.me/+"):
            continue

        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            status = member.status
            if status in ("left", "kicked"):
                return False
        except Exception as exc:
            logger.warning("Required channel check failed for %s / %s: %s", channel, user_id, exc)
            continue

    return True


async def ensure_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False

    record = ensure_user(user)
    if record.get("blocked"):
        return False

    if is_admin(user.id):
        return True

    joined = await user_required_channels_joined(context, user.id)
    if not joined:
        if update.callback_query:
            await safe_answer_callback(update.callback_query, "اشترك أولًا في القنوات المطلوبة.", True)
            await send_required_channels(update, context)
        else:
            await send_required_channels(update, context)
        return False

    if not subscription_active(user.id):
        if update.callback_query:
            await safe_answer_callback(update.callback_query, "الاشتراك غير فعال.", True)
            await send_subscription_page(update, context)
        else:
            await send_subscription_page(update, context)
        return False

    return True


def all_categories(categories=None):
    if categories is None:
        categories = DB.get("categories", [])

    result = []
    for category in categories:
        result.append(category)
        result.extend(all_categories(category.get("children", [])))
    return result


def make_button(
    text: str,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
    category: Optional[Dict[str, Any]] = None,
    default_emoji: Optional[str] = None,
) -> InlineKeyboardButton:
    kwargs: Dict[str, Any] = {"text": text}

    if callback_data:
        kwargs["callback_data"] = callback_data

    if url:
        kwargs["url"] = url

    color = "primary"
    emoji_id = default_emoji or ""

    if category:
        style = category.get("style", {}) or {}
        c = style.get("color", "primary")
        if c in ("primary", "success", "danger"):
            color = c
        custom_emoji = str(style.get("emoji_id", "")).strip()
        if custom_emoji:
            emoji_id = custom_emoji

    kwargs["style"] = color

    if emoji_id:
        kwargs["icon_custom_emoji_id"] = emoji_id

    return InlineKeyboardButton(**kwargs)


def get_default_emoji_for_category(category_id: str, idx: int) -> str:
    if category_id == "clothes":
        return EMOJI_CLOTHES
    return EMOJI_FACES[idx % len(EMOJI_FACES)]


def nested_category_keyboard(category: Dict[str, Any]) -> InlineKeyboardMarkup:
    buttons: List[InlineKeyboardButton] = []

    for child in category.get("children", []):
        normalize_category(child)
        child_url = child.get("style", {}).get("url", "").strip()

        if child_url:
            button = make_button(child.get("name", "قسم"), url=child_url, category=child)
        else:
            button = make_button(child.get("name", "قسم"), callback_data=f"cat:{child.get('id')}", category=child)

        buttons.append(button)

    videos = category.get("videos", [])

    for index, _ in enumerate(videos, start=1):
        color = category.get("style", {}).get("color", "primary")
        if color not in ("primary", "success", "danger"):
            color = "primary"

        emoji_id = category.get("style", {}).get("emoji_id", "") or None

        kwargs = {
            "text": f"فيديو {index}",
            "callback_data": f"video:{category['id']}:{index-1}",
            "style": color,
        }
        if emoji_id:
            kwargs["icon_custom_emoji_id"] = emoji_id

        buttons.append(InlineKeyboardButton(**kwargs))

    if not buttons:
        buttons.append(colored_button("لا توجد عناصر حاليًا", callback_data="noop", style="primary"))

    rows = chunk_rows(buttons, per_row=2)
    rows.append([colored_button("رجوع", callback_data="home", style="danger", emoji_id=EMOJI_HOME)])

    return InlineKeyboardMarkup(rows)


def format_category_text(category: Dict[str, Any]) -> str:
    count = len(category.get("videos", []))
    return f"{category.get('name', 'قسم')} \n\nعدد الفيديوهات: {count}"


def category_keyboard(category: Dict[str, Any]) -> InlineKeyboardMarkup:
    normalize_category(category)
    return nested_category_keyboard(category)


def home_keyboard() -> InlineKeyboardMarkup:
    buttons: List[InlineKeyboardButton] = []

    for idx, category in enumerate(DB.get("categories", [])):
        normalize_category(category)
        default_emoji = get_default_emoji_for_category(category.get("id", ""), idx)

        child_url = category.get("style", {}).get("url", "").strip()

        if child_url:
            button = make_button(
                category.get("name", "قسم"),
                url=child_url,
                category=category,
                default_emoji=default_emoji,
            )
        else:
            button = make_button(
                category.get("name", "قسم"),
                callback_data=f"cat:{category.get('id')}",
                category=category,
                default_emoji=default_emoji,
            )

        buttons.append(button)

    rows = chunk_rows(buttons, per_row=2)

    rows.append([colored_button("جميع الفيديوهات", url=ALL_VIDEOS_URL, style="success", emoji_id=EMOJI_ALL_VIDEOS)])
    rows.append([colored_button("حالة الاشتراك", callback_data="subscription_status", style="primary", emoji_id=EMOJI_FACES[1])])

    return InlineKeyboardMarkup(rows)


def keyword_replies_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for index, item in enumerate(DB.get("keyword_replies", [])):
        reply_value = str(item.get("response", item.get("keyword", "")))[:18]
        buttons.append(colored_button(f"حذف: {reply_value}", callback_data=f"admin_kw_del:{index}", style="danger", emoji_id=EMOJI_DELETE))
    rows = chunk_rows(buttons, per_row=2) if buttons else []
    rows.append([colored_button("إضافة رد بكلمة", callback_data="admin_kw_add", style="primary", emoji_id=EMOJI_ADMIN)])
    rows.append([colored_button("رجوع", callback_data="admin_panel", style="danger", emoji_id=EMOJI_HOME)])
    return InlineKeyboardMarkup(rows)


def admin_keyboard() -> InlineKeyboardMarkup:
    e = EMOJI_ADMIN
    av = EMOJI_ADD_VIDEO
    d = EMOJI_DELETE
    buttons = [
        colored_button("إضافة فيديو", callback_data="admin_add_video", style="success", emoji_id=av),
        colored_button("الأقسام", callback_data="admin_categories", style="primary", emoji_id=e),
        colored_button("الاشتراك الإجباري", callback_data="admin_required", style="primary", emoji_id=e),
        colored_button("تفعيل اشتراك", callback_data="admin_activate", style="primary", emoji_id=e),
        colored_button("سعر الاشتراك", callback_data="admin_price", style="primary", emoji_id=e),
        colored_button("الإذاعة", callback_data="admin_broadcast", style="success", emoji_id=e),
        colored_button("المستخدمون", callback_data="admin_users", style="primary", emoji_id=e),
        colored_button("إدارة الأدمن", callback_data="admin_admins", style="primary", emoji_id=e),
        colored_button("النصوص", callback_data="admin_texts", style="primary", emoji_id=e),
        colored_button("ردود الكلمات", callback_data="admin_keywords", style="primary", emoji_id=e),
        colored_button("إحصائيات", callback_data="admin_stats", style="primary", emoji_id=e),
    ]

    rows = chunk_rows(buttons, per_row=2)
    rows.append([colored_button("الرئيسية", callback_data="home", style="danger", emoji_id=EMOJI_HOME)])

    return InlineKeyboardMarkup(rows)


def required_channels_keyboard() -> InlineKeyboardMarkup:
    buttons: List[InlineKeyboardButton] = []

    for index, channel in enumerate(DB.get("required_channels", [])):
        display = str(channel)
        if len(display) > 20:
            display = display[:17] + "..."

        buttons.append(
            colored_button(
                f"حذف: {display}",
                callback_data=f"admin_req_del:{index}",
                style="danger",
                emoji_id=EMOJI_DELETE,
            )
        )

    rows = chunk_rows(buttons, per_row=2) if buttons else []

    rows.append([colored_button("إضافة قناة", callback_data="admin_req_add", style="success", emoji_id=EMOJI_ADMIN)])
    rows.append([colored_button("رجوع", callback_data="admin_panel", style="danger", emoji_id=EMOJI_ADMIN)])

    return InlineKeyboardMarkup(rows)


def categories_admin_keyboard() -> InlineKeyboardMarkup:
    buttons: List[InlineKeyboardButton] = []

    for category in DB.get("categories", []):
        buttons.append(
            colored_button(
                f"إدارة: {category.get('name')}",
                callback_data=f"admin_cat:{category.get('id')}",
                style="primary",
                emoji_id=EMOJI_ADMIN,
            )
        )

    rows = chunk_rows(buttons, per_row=2) if buttons else []

    rows.append([colored_button("إضافة قسم", callback_data="admin_cat_add", style="success", emoji_id=EMOJI_ADMIN)])
    rows.append([colored_button("رجوع", callback_data="admin_panel", style="danger", emoji_id=EMOJI_ADMIN)])

    return InlineKeyboardMarkup(rows)


def category_admin_keyboard(category_id: str) -> InlineKeyboardMarkup:
    e = EMOJI_ADMIN
    av = EMOJI_ADD_VIDEO
    d = EMOJI_DELETE
    buttons = [
        colored_button("إضافة فيديو", callback_data=f"admin_video_add:{category_id}", style="success", emoji_id=av),
        colored_button("إضافة زر داخل هذا الزر", callback_data=f"admin_child_add:{category_id}", style="success", emoji_id=e),
        colored_button("تعديل اسم الزر", callback_data=f"admin_cat_name:{category_id}", style="primary", emoji_id=e),
        colored_button("تعديل لون الزر", callback_data=f"admin_cat_color:{category_id}", style="primary", emoji_id=e),
        colored_button("تعديل إيموجي الزر", callback_data=f"admin_cat_emoji:{category_id}", style="primary", emoji_id=e),
        colored_button("إضافة/تعديل رابط", callback_data=f"admin_cat_url:{category_id}", style="primary", emoji_id=e),
        colored_button("إدارة الأزرار الداخلية", callback_data=f"admin_children:{category_id}", style="primary", emoji_id=e),
        colored_button("حذف آخر فيديو", callback_data=f"admin_video_del_last:{category_id}", style="danger", emoji_id=d),
        colored_button("حذف الزر", callback_data=f"admin_cat_del:{category_id}", style="danger", emoji_id=d),
    ]

    rows = chunk_rows(buttons, per_row=2)
    rows.append([colored_button("رجوع", callback_data="admin_categories", style="danger", emoji_id=e)])

    return InlineKeyboardMarkup(rows)


def admin_texts_keyboard() -> InlineKeyboardMarkup:
    e = EMOJI_ADMIN
    buttons = [
        colored_button("تغيير رسالة الترحيب", callback_data="admin_text_welcome", style="primary", emoji_id=e),
        colored_button("تغيير رسالة الدفع", callback_data="admin_text_payment", style="primary", emoji_id=e),
        colored_button("تغيير رسالة عدم الوصول", callback_data="admin_text_noaccess", style="primary", emoji_id=e),
    ]

    rows = chunk_rows(buttons, per_row=2)
    rows.append([colored_button("رجوع", callback_data="admin_panel", style="danger", emoji_id=e)])

    return InlineKeyboardMarkup(rows)


def subscription_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                colored_button(f"اشترك الآن — {get_subscription_stars()}", callback_data="buy_subscription", style="success", emoji_id=EMOJI_SUBSCRIBE),
                colored_button("تحقق", callback_data="subscription_status", style="primary", emoji_id=EMOJI_CHECK_SUB),
            ]
        ]
    )


async def send_required_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = []

    for channel in DB.get("required_channels", []):
        channel = str(channel)

        if channel.startswith("http://") or channel.startswith("https://"):
            rows.append([colored_button("الاشتراك في القناة", url=channel, style="primary", emoji_id=EMOJI_ADMIN)])
        elif channel.startswith("@"):
            rows.append([colored_button("فتح القناة", url=f"https://t.me/{channel[1:]}", style="primary", emoji_id=EMOJI_ADMIN)])

    rows.append([colored_button("تحقق من الاشتراك", callback_data="check_required", style="success", emoji_id=EMOJI_CHECK_SUB)])

    markup = InlineKeyboardMarkup(rows)
    text = REQUIRED_CHANNEL_TEXT

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
            return
        except Exception:
            pass

    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=markup)


async def send_subscription_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = DB["settings"].get("payment_text", PAYMENT_TEXT)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=subscription_keyboard())
            return
        except Exception:
            pass

    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=subscription_keyboard())


async def send_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        ensure_user(user)

    text = DB["settings"].get("welcome_text", WELCOME_TEXT)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=home_keyboard())
            return
        except Exception:
            pass

    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=home_keyboard())


# ============================================================
# START
# ============================================================


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message:
        return

    # إذا كان في جروب، لا يرد
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        return

    user = ensure_user(update.effective_user)

    if user.get("blocked"):
        await update.effective_message.reply_text("تم منع حسابك من استخدام البوت.")
        return

    if is_admin(update.effective_user.id):
        await send_home(update, context)
        return

    joined = await user_required_channels_joined(context, update.effective_user.id)
    if not joined:
        await send_required_channels(update, context)
        return

    if not subscription_active(update.effective_user.id):
        await send_subscription_page(update, context)
        return

    await send_home(update, context)


# ============================================================
# PAYMENT
# ============================================================


async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await safe_answer_callback(query)

    if not await user_required_channels_joined(context, user.id):
        await send_required_channels(update, context)
        return

    payload = f"vip_monthly:{user.id}:{int(time.time())}"

    try:
        await context.bot.send_invoice(
            chat_id=user.id,
            title="MaX VIP — اشتراك شهري",
            description="اشتراك شهري يفتح جميع مميزات MaX VIP.",
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label="اشتراك شهري", amount=get_subscription_stars())],
        )
    except Exception as exc:
        logger.exception("Invoice error: %s", exc)
        await context.bot.send_message(
            chat_id=user.id,
            text="تعذر إنشاء فاتورة الاشتراك الآن، حاول لاحقًا.",
        )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if not query:
        return

    if not query.invoice_payload.startswith("vip_monthly:"):
        await query.answer(ok=False, error_message="الفاتورة غير صالحة.")
        return

    try:
        await query.answer(ok=True)
    except Exception:
        logger.exception("Pre-checkout answer failed.")


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if not message or not user or not message.successful_payment:
        return

    payment = message.successful_payment

    if payment.currency != "XTR":
        await message.reply_text("تم استلام عملية دفع بعملة غير متوقعة.")
        return

    if payment.total_amount != get_subscription_stars():
        await message.reply_text("قيمة الاشتراك غير مطابقة.")
        return

    expiration = payment.subscription_expiration_date

    if expiration:
        subscription_until = int(expiration)
    else:
        subscription_until = int(time.time()) + SUBSCRIPTION_SECONDS

    record = ensure_user(user)
    record["subscription_until"] = subscription_until
    record["is_subscribed"] = True
    record["payment_charge_id"] = payment.telegram_payment_charge_id
    save_db(DB)

    await message.reply_text(
        "تم تفعيل اشتراكك بنجاح\n\n"
        f"السعر: {SUBSCRIPTION_STARS} نجمة\n"
        f"المدة: {SUBSCRIPTION_DAYS} يوم\n\n"
        "يمكنك الآن فتح جميع الأقسام.",
        reply_markup=home_keyboard(),
    )


# ============================================================
# GROUP AUTO-REPLY HANDLER
# ============================================================


async def group_auto_reply_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """يرد على كل رسالة في الجروب باستخدام رد عشوائي من الردود المضافة في لوحة الأدمن."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or not user:
        return

    # لا يرد على رسائل البوتات
    if user.is_bot:
        return

    # يرد على جميع رسائل المستخدمين في الجروب، بدون اشتراط حروف عربية أو إنجليزية.
    # يتم تجاهل رسائل البوتات فقط حتى لا يدخل البوت في حلقة ردود.
    configured_replies = [
        str(item.get("response", item.get("keyword", ""))).strip()
        for item in DB.get("keyword_replies", [])
        if str(item.get("response", item.get("keyword", ""))).strip()
    ]
    reply_text = random.choice(configured_replies or GROUP_REPLY_MESSAGES)

    try:
        await message.reply_text(
            reply_text,
            reply_to_message_id=message.message_id,
        )
    except Exception as exc:
        logger.warning("Group auto-reply failed: %s", exc)


# ============================================================
# USER CALLBACKS
# ============================================================


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    ensure_user(user)
    data = query.data or ""

    if data == "noop":
        await safe_answer_callback(query)
        return

    if data == "home":
        await safe_answer_callback(query)
        if await ensure_access(update, context):
            await send_home(update, context)
        return

    if data == "check_required":
        joined = await user_required_channels_joined(context, user.id)

        if not joined:
            await safe_answer_callback(query, "لم يتم التحقق من الاشتراك.", True)
            await send_required_channels(update, context)
            return

        await safe_answer_callback(query, "تم التحقق.")

        if is_admin(user.id) or subscription_active(user.id):
            await send_home(update, context)
        else:
            await send_subscription_page(update, context)
        return

    if data == "buy_subscription":
        await buy_subscription(update, context)
        return

    if data == "subscription_status":
        await safe_answer_callback(query)

        if is_admin(user.id):
            text = "أنت أدمن/مالك البوت — لديك صلاحية كاملة بدون اشتراك."
            markup = InlineKeyboardMarkup([[colored_button("الرئيسية", callback_data="home", style="primary", emoji_id=EMOJI_HOME)]])
            try:
                await query.edit_message_text(text, reply_markup=markup)
            except Exception:
                pass
            return

        active = subscription_active(user.id)

        if active:
            text = (
                "حالة الاشتراك: فعال\n\n"
                f"المتبقي: {subscription_remaining(user.id)}\n"
                f"السعر: {get_subscription_stars()} نجمة"
            )
            markup = InlineKeyboardMarkup([[colored_button("الرئيسية", callback_data="home", style="primary", emoji_id=EMOJI_HOME)]])
        else:
            text = "حالة الاشتراك: غير فعال\n\nاشترك لفتح جميع المميزات."
            markup = subscription_keyboard()

        try:
            await query.edit_message_text(text, reply_markup=markup)
        except Exception:
            pass
        return

    if data.startswith("cat:"):
        if not await ensure_access(update, context):
            return

        category_id = data.split(":", 1)[1]
        category = get_category(category_id)

        if not category:
            await safe_answer_callback(query, "القسم غير موجود.", True)
            return

        await safe_answer_callback(query)
        try:
            await query.edit_message_text(format_category_text(category), reply_markup=category_keyboard(category))
        except Exception:
            pass
        return

    if data.startswith("video:"):
        if not await ensure_access(update, context):
            return

        parts = data.split(":")
        if len(parts) != 3:
            return

        category_id = parts[1]
        try:
            index = int(parts[2])
        except ValueError:
            return

        category = get_category(category_id)
        if not category:
            await safe_answer_callback(query, "القسم غير موجود.", True)
            return

        videos = category.get("videos", [])
        if index < 0 or index >= len(videos):
            await safe_answer_callback(query, "الفيديو غير موجود.", True)
            return

        await safe_answer_callback(query)
        video = videos[index]

        try:
            await context.bot.copy_message(
                chat_id=user.id,
                from_chat_id=video["from_chat_id"],
                message_id=video["message_id"],
            )
        except Exception as exc:
            logger.exception("Could not send video: %s", exc)
            await context.bot.send_message(chat_id=user.id, text="تعذر إرسال الفيديو.")
        return

    if data == "admin_panel":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query)
        await show_admin_panel(update, context)
        return

    if data == "admin_categories":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query)
        try:
            await query.edit_message_text("إدارة الأقسام:", reply_markup=categories_admin_keyboard())
        except Exception:
            pass
        return

    if data.startswith("admin_cat:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return

        category_id = data.split(":", 1)[1]
        category = get_category(category_id)

        if not category:
            await safe_answer_callback(query, "القسم غير موجود.", True)
            return

        await safe_answer_callback(query)
        try:
            await query.edit_message_text(format_category_text(category), reply_markup=category_admin_keyboard(category_id))
        except Exception:
            pass
        return

    if data == "admin_cat_add":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        context.user_data["admin_state"] = "add_category"
        await safe_answer_callback(query)
        try:
            await query.edit_message_text("أرسل الآن اسم القسم الجديد في رسالة واحدة.\n\nللإلغاء: /cancel")
        except Exception:
            pass
        return

    if data.startswith("admin_cat_del:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return

        category_id = data.split(":", 1)[1]
        category = get_category(category_id)

        if category:
            def remove_nested(items):
                kept = []
                for item in items:
                    if item.get("id") == category_id:
                        continue
                    item["children"] = remove_nested(item.get("children", []))
                    kept.append(item)
                return kept

            DB["categories"] = remove_nested(DB.get("categories", []))
            save_db(DB)

        await safe_answer_callback(query, "تم حذف القسم.")
        try:
            await query.edit_message_text("إدارة الأقسام:", reply_markup=categories_admin_keyboard())
        except Exception:
            pass
        return

    if data == "admin_add_video":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query)
        try:
            await query.edit_message_text("اختر القسم الذي تريد إضافة الفيديو إليه:", reply_markup=categories_admin_keyboard())
        except Exception:
            pass
        return

    if data.startswith("admin_video_add:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return

        category_id = data.split(":", 1)[1]
        if not get_category(category_id):
            await safe_answer_callback(query, "القسم غير موجود.", True)
            return

        context.user_data["admin_state"] = "add_video"
        context.user_data["admin_category_id"] = category_id
        await safe_answer_callback(query)
        try:
            await query.edit_message_text("أرسل الفيديو الآن.\n\nيمكنك إرسال فيديو أو Document فيديو.\n\nللإلغاء: /cancel")
        except Exception:
            pass
        return

    if data.startswith("admin_video_del_last:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return

        category_id = data.split(":", 1)[1]
        category = get_category(category_id)

        if category and category.get("videos"):
            category["videos"].pop()
            save_db(DB)
            await safe_answer_callback(query, "تم حذف آخر فيديو.")
        else:
            await safe_answer_callback(query, "لا توجد فيديوهات.", True)
        return

    if data == "admin_activate":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        context.user_data["admin_state"] = "activate_subscription"
        await safe_answer_callback(query)
        await query.edit_message_text(
            "أرسل ID المستخدم أو @username لتفعيل اشتراك لمدة 30 يومًا.\\n\\n"
            "مثال: 123456789 أو @username\\nللإلغاء: /cancel"
        )
        return

    if data == "admin_price":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        context.user_data["admin_state"] = "change_price"
        await safe_answer_callback(query)
        await query.edit_message_text(
            f"السعر الحالي: {get_subscription_stars()} نجمة\\n\\n"
            "أرسل السعر الجديد بالأرقام فقط.\\n"
            "مثال: 50\\nللإلغاء: /cancel"
        )
        return

    if data == "admin_required":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query)
        text = (
            "الاشتراك الإجباري\n\n"
            "يمكنك إضافة @username أو chat_id للقناة/المجموعة.\n"
            "يمكن أيضًا حفظ رابط t.me كزر، لكن التحقق الآلي يحتاج معرّف chat قابلًا للفحص."
        )
        try:
            await query.edit_message_text(text, reply_markup=required_channels_keyboard())
        except Exception:
            pass
        return

    if data == "admin_req_add":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        context.user_data["admin_state"] = "add_required"
        await safe_answer_callback(query)
        try:
            await query.edit_message_text(
                "أرسل الآن @username أو chat_id للقناة المطلوبة.\n\nمثال:\n@kon_ze_athar\n\nللإلغاء: /cancel"
            )
        except Exception:
            pass
        return

    if data.startswith("admin_req_del:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return

        try:
            index = int(data.split(":", 1)[1])
        except ValueError:
            return

        channels = DB.get("required_channels", [])
        if 0 <= index < len(channels):
            channels.pop(index)
            save_db(DB)

        await safe_answer_callback(query, "تم الحذف.")
        try:
            await query.edit_message_text("الاشتراك الإجباري:", reply_markup=required_channels_keyboard())
        except Exception:
            pass
        return

    if data.startswith("admin_child_add:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return

        parent_id = data.split(":", 1)[1]
        if not get_category(parent_id):
            await safe_answer_callback(query, "القسم غير موجود.", True)
            return

        context.user_data["admin_state"] = "add_child"
        context.user_data["admin_parent_id"] = parent_id
        await safe_answer_callback(query)
        try:
            await query.edit_message_text(
                "أرسل بيانات الزر الداخلي بهذا الشكل:\n\nاسم الزر | الرابط\n\nمثال:\nمحتوى خاص | https://t.me/example\n\nللإلغاء: /cancel"
            )
        except Exception:
            pass
        return

    if data.startswith("admin_cat_name:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        category_id = data.split(":", 1)[1]
        if not get_category(category_id):
            await safe_answer_callback(query, "القسم غير موجود.", True)
            return
        context.user_data["admin_state"] = "edit_cat_name"
        context.user_data["admin_category_id"] = category_id
        await safe_answer_callback(query)
        try:
            await query.edit_message_text("أرسل الاسم الجديد للزر.\n\nللإلغاء: /cancel")
        except Exception:
            pass
        return

    if data.startswith("admin_cat_color:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        category_id = data.split(":", 1)[1]
        if not get_category(category_id):
            await safe_answer_callback(query, "القسم غير موجود.", True)
            return
        context.user_data["admin_state"] = "edit_cat_color"
        context.user_data["admin_category_id"] = category_id
        await safe_answer_callback(query)
        try:
            await query.edit_message_text(
                "أرسل لون الزر:\n\nprimary = أزرق\nsuccess = أخضر\ndanger = أحمر\n\nللإلغاء: /cancel"
            )
        except Exception:
            pass
        return

    if data.startswith("admin_cat_emoji:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        category_id = data.split(":", 1)[1]
        if not get_category(category_id):
            await safe_answer_callback(query, "القسم غير موجود.", True)
            return
        context.user_data["admin_state"] = "edit_cat_emoji"
        context.user_data["admin_category_id"] = category_id
        await safe_answer_callback(query)
        try:
            await query.edit_message_text(
                "أرسل الآن Custom Emoji واحد فقط.\n\nسيتم التقاط الـ custom emoji من الرسالة تلقائيًا.\nللإزالة أرسل: حذف\n\nللإلغاء: /cancel"
            )
        except Exception:
            pass
        return

    if data.startswith("admin_cat_url:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        category_id = data.split(":", 1)[1]
        if not get_category(category_id):
            await safe_answer_callback(query, "القسم غير موجود.", True)
            return
        context.user_data["admin_state"] = "edit_cat_url"
        context.user_data["admin_category_id"] = category_id
        await safe_answer_callback(query)
        try:
            await query.edit_message_text(
                "أرسل رابط الزر.\n\nمثال:\nhttps://t.me/example\n\nللإزالة أرسل: حذف\nللإلغاء: /cancel"
            )
        except Exception:
            pass
        return

    if data.startswith("admin_children:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return

        category_id = data.split(":", 1)[1]
        category = get_category(category_id)

        if not category:
            await safe_answer_callback(query, "القسم غير موجود.", True)
            return

        normalize_category(category)
        await safe_answer_callback(query)

        buttons: List[InlineKeyboardButton] = []
        for child in category.get("children", []):
            buttons.append(
                colored_button(
                    f"حذف: {child.get('name', 'زر')}",
                    callback_data=f"admin_child_del:{category_id}:{child.get('id')}",
                    style="danger",
                    emoji_id=EMOJI_DELETE,
                )
            )

        rows = chunk_rows(buttons, per_row=2) if buttons else []
        rows.append([colored_button("إضافة زر داخل هذا الزر", callback_data=f"admin_child_add:{category_id}", style="success", emoji_id=EMOJI_ADMIN)])
        rows.append([colored_button("رجوع", callback_data=f"admin_cat:{category_id}", style="danger", emoji_id=EMOJI_ADMIN)])

        try:
            await query.edit_message_text("الأزرار الداخلية:", reply_markup=InlineKeyboardMarkup(rows))
        except Exception:
            pass
        return

    if data.startswith("admin_child_del:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return

        parts = data.split(":", 2)
        if len(parts) != 3:
            return

        parent_id = parts[1]
        child_id = parts[2]
        parent = get_category(parent_id)

        if parent:
            parent["children"] = [child for child in parent.get("children", []) if child.get("id") != child_id]
            save_db(DB)

        await safe_answer_callback(query, "تم حذف الزر الداخلي.")
        try:
            await query.edit_message_text("تم حذف الزر الداخلي.", reply_markup=category_admin_keyboard(parent_id))
        except Exception:
            pass
        return

    if data == "admin_broadcast":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        context.user_data["admin_state"] = "broadcast"
        await safe_answer_callback(query)
        try:
            await query.edit_message_text(
                "أرسل الرسالة التي تريد إذاعتها الآن.\n\nسيتم نسخ الرسالة إلى المستخدمين المسجلين.\n\nللإلغاء: /cancel"
            )
        except Exception:
            pass
        return

    if data == "admin_users":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query)

        total = len(DB.get("users", {}))
        active = sum(1 for uid in DB.get("users", {}) if subscription_active(int(uid)))

        text = (
            "إحصائيات المستخدمين\n\n"
            f"إجمالي المستخدمين: {total}\n"
            f"الاشتراكات النشطة: {active}\n"
            f"الأقسام: {len(DB.get('categories', []))}"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[colored_button("رجوع", callback_data="admin_panel", style="danger", emoji_id=EMOJI_ADMIN)]]),
            )
        except Exception:
            pass
        return

    if data == "admin_stats":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query)

        total_videos = sum(len(c.get("videos", [])) for c in DB.get("categories", []))
        active = sum(1 for uid in DB.get("users", {}) if subscription_active(int(uid)))

        text = (
            "إحصائيات MaX VIP\n\n"
            f"المستخدمون: {len(DB.get('users', {}))}\n"
            f"المشتركون النشطون: {active}\n"
            f"الأقسام: {len(DB.get('categories', []))}\n"
            f"الفيديوهات: {total_videos}\n"
            f"سعر الاشتراك: {SUBSCRIPTION_STARS} نجمة\n"
            f"مدة الاشتراك: {SUBSCRIPTION_DAYS} يوم"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[colored_button("رجوع", callback_data="admin_panel", style="danger", emoji_id=EMOJI_ADMIN)]]),
            )
        except Exception:
            pass
        return

    if data == "admin_admins":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query)

        text = (
            "إدارة الأدمن\n\n"
            f"Owner ID: {OWNER_ID}\n"
            f"عدد الأدمن: {len(DB.get('admins', []))}\n\n"
            "استخدم الأوامر:\n/addadmin ID\n/deladmin ID"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[colored_button("رجوع", callback_data="admin_panel", style="danger", emoji_id=EMOJI_ADMIN)]]),
            )
        except Exception:
            pass
        return

    if data == "admin_keywords":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query)
        text = "إدارة ردود الجروبات\n\nأضف كلمة أو عبارة أو جملة، وسيستخدمها البوت كرد عشوائي على أي رسالة تصل داخل الجروب."
        await query.edit_message_text(text, reply_markup=keyword_replies_keyboard())
        return

    if data == "admin_kw_add":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        context.user_data["admin_state"] = "add_keyword"
        await safe_answer_callback(query)
        await query.edit_message_text("أرسل الكلمة أو الجملة التي تريد أن يرد بها البوت على أي رسالة في الجروب.\n\nمثال:\nيا هلا بالجميع\n\nللإلغاء: /cancel")
        return

    if data.startswith("admin_kw_del:"):
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        try:
            index = int(data.split(":", 1)[1])
            DB.get("keyword_replies", []).pop(index)
            save_db(DB)
            await safe_answer_callback(query, "تم حذف الرد.")
        except (ValueError, IndexError):
            await safe_answer_callback(query, "الرد غير موجود.", True)
        await query.edit_message_text("إدارة الردود بالكلمات", reply_markup=keyword_replies_keyboard())
        return

    if data == "admin_texts":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query)
        try:
            await query.edit_message_text("تعديل نصوص البوت:", reply_markup=admin_texts_keyboard())
        except Exception:
            pass
        return

    if data == "admin_text_welcome":
        if not is_admin(user.id):
            return
        context.user_data["admin_state"] = "text_welcome"
        await safe_answer_callback(query)
        try:
            await query.edit_message_text("أرسل رسالة الترحيب الجديدة.\n\nللإلغاء: /cancel")
        except Exception:
            pass
        return

    if data == "admin_text_payment":
        if not is_admin(user.id):
            return
        context.user_data["admin_state"] = "text_payment"
        await safe_answer_callback(query)
        try:
            await query.edit_message_text("أرسل رسالة الدفع الجديدة.\n\nللإلغاء: /cancel")
        except Exception:
            pass
        return

    if data == "admin_text_noaccess":
        if not is_admin(user.id):
            return
        context.user_data["admin_state"] = "text_noaccess"
        await safe_answer_callback(query)
        try:
            await query.edit_message_text("أرسل رسالة عدم الوصول الجديدة.\n\nللإلغاء: /cancel")
        except Exception:
            pass
        return


# ============================================================
# ADMIN PANEL
# ============================================================


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not is_admin(update.effective_user.id):
        return

    text = (
        "لوحة تحكم MaX VIP\n\n"
        "من هنا يمكنك إدارة الأقسام والفيديوهات والاشتراك الإجباري "
        "والإذاعة والمستخدمين والنصوص."
    )

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=admin_keyboard())
            return
        except Exception:
            pass

    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=admin_keyboard())


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return

    # لا يعمل في الجروبات
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        return

    ensure_user(update.effective_user)

    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("غير مصرح.")
        return

    await show_admin_panel(update, context)


# ============================================================
# ADMIN TEXT / VIDEO / BROADCAST INPUT
# ============================================================


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        return

    context.user_data.pop("admin_state", None)
    context.user_data.pop("admin_category_id", None)

    if update.effective_message:
        await update.effective_message.reply_text(
            "تم إلغاء العملية.",
            reply_markup=admin_keyboard() if update.effective_user and is_admin(update.effective_user.id) else None,
        )


async def admin_add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not is_admin(update.effective_user.id):
        return

    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        return

    if not context.args:
        await update.effective_message.reply_text("الاستخدام:\n/addadmin 123456789")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("ID غير صحيح.")
        return

    if user_id not in DB["admins"]:
        DB["admins"].append(user_id)
        save_db(DB)

    await update.effective_message.reply_text(f"تمت إضافة الأدمن: {user_id}")


async def admin_del_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not is_admin(update.effective_user.id):
        return

    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        return

    if not context.args:
        await update.effective_message.reply_text("الاستخدام:\n/deladmin 123456789")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("ID غير صحيح.")
        return

    if user_id == OWNER_ID:
        await update.effective_message.reply_text("لا يمكن حذف Owner.")
        return

    if user_id in DB["admins"]:
        DB["admins"].remove(user_id)
        save_db(DB)

    await update.effective_message.reply_text(f"تم حذف الأدمن: {user_id}")


def make_button_child_id(parent: Dict[str, Any]) -> str:
    base = "child_" + str(abs(hash((parent.get("id"), time.time_ns()))))[:10]
    used = {c.get("id") for c in parent.get("children", [])}
    candidate = base
    counter = 1

    while candidate in used:
        candidate = f"{base}_{counter}"
        counter += 1

    return candidate


def extract_custom_emoji_id(message) -> str:
    entities = []

    if getattr(message, "entities", None):
        entities.extend(message.entities)

    if getattr(message, "caption_entities", None):
        entities.extend(message.caption_entities)

    for entity in entities:
        if getattr(entity, "type", "") == "custom_emoji":
            custom_id = getattr(entity, "custom_emoji_id", None)
            if custom_id:
                return str(custom_id)

    return ""


async def admin_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    if not is_admin(user.id):
        return

    state = context.user_data.get("admin_state")

    if not state:
        return

    if state == "add_keyword":
        response = (message.text or "").strip()
        if not response:
            await message.reply_text("أرسل الكلمة أو الجملة التي تريد أن يرد بها البوت.")
            return
        if len(response) > 4000:
            await message.reply_text("الرد بحد أقصى 4000 حرف.")
            return
        DB.setdefault("keyword_replies", []).append({"keyword": response, "response": response})
        save_db(DB)
        context.user_data.pop("admin_state", None)
        await message.reply_text("تمت إضافة الرد بنجاح، وسيستخدمه البوت على أي رسالة في الجروب.", reply_markup=keyword_replies_keyboard())
        return

    if state == "add_category":
        if not message.text:
            await message.reply_text("أرسل اسم القسم كنص.")
            return

        name = message.text.strip()
        if len(name) < 1 or len(name) > 50:
            await message.reply_text("اسم القسم يجب أن يكون بين 1 و50 حرفًا.")
            return

        category = {"id": make_category_id(name), "name": name, "videos": [], "children": [], "style": {"color": "primary", "emoji_id": "", "url": ""}}
        DB["categories"].append(category)
        save_db(DB)

        context.user_data.pop("admin_state", None)
        await message.reply_text(f"تم إنشاء القسم: {name}", reply_markup=admin_keyboard())
        return

    if state == "add_video":
        category_id = context.user_data.get("admin_category_id")
        category = get_category(category_id)

        if not category:
            context.user_data.pop("admin_state", None)
            context.user_data.pop("admin_category_id", None)
            await message.reply_text("القسم غير موجود.")
            return

        if message.video or message.document or message.animation:
            category["videos"].append(
                {
                    "from_chat_id": update.effective_chat.id,
                    "message_id": message.message_id,
                    "kind": "video" if message.video else "document" if message.document else "animation",
                    "added_at": int(time.time()),
                }
            )
            save_db(DB)
            await message.reply_text(
                f"تمت إضافة الفيديو إلى قسم: {category['name']}\n"
                f"إجمالي الفيديوهات: {len(category['videos'])}"
            )
            return

        await message.reply_text("أرسل فيديو أو ملف فيديو أو GIF فقط.")
        return

    if state == "add_child":
        parent_id = context.user_data.get("admin_parent_id")
        parent = get_category(parent_id)

        if not parent:
            context.user_data.pop("admin_state", None)
            context.user_data.pop("admin_parent_id", None)
            await message.reply_text("القسم الأب غير موجود.")
            return

        if not message.text:
            await message.reply_text("أرسل: اسم الزر | الرابط\nأو اسم الزر فقط لزر داخلي يفتح قسمًا.")
            return

        raw = message.text.strip()
        parts = raw.split("|", 1)
        name = parts[0].strip()
        url = parts[1].strip() if len(parts) == 2 else ""

        if not name:
            await message.reply_text("اسم الزر مطلوب.")
            return

        if url and not (url.startswith("https://") or url.startswith("http://") or url.startswith("tg://")):
            await message.reply_text("الرابط يجب أن يبدأ بـ https:// أو http:// أو tg://")
            return

        normalize_category(parent)

        child = {
            "id": make_button_child_id(parent),
            "name": name,
            "videos": [],
            "children": [],
            "style": {"color": "primary", "emoji_id": "", "url": url},
        }
        parent["children"].append(child)
        save_db(DB)

        context.user_data.pop("admin_state", None)
        context.user_data.pop("admin_parent_id", None)
        await message.reply_text(f"تمت إضافة الزر الداخلي: {name}", reply_markup=category_admin_keyboard(parent_id))
        return

    if state == "edit_cat_name":
        category_id = context.user_data.get("admin_category_id")
        category = get_category(category_id)
        if not category:
            await message.reply_text("القسم غير موجود.")
            return
        if not message.text:
            await message.reply_text("أرسل الاسم الجديد كنص.")
            return

        new_name = message.text.strip()
        if not new_name:
            await message.reply_text("الاسم لا يمكن أن يكون فارغًا.")
            return

        category["name"] = new_name
        save_db(DB)
        context.user_data.pop("admin_state", None)
        context.user_data.pop("admin_category_id", None)
        await message.reply_text(f"تم تغيير الاسم إلى: {new_name}", reply_markup=category_admin_keyboard(category_id))
        return

    if state == "edit_cat_color":
        category_id = context.user_data.get("admin_category_id")
        category = get_category(category_id)
        if not category:
            await message.reply_text("القسم غير موجود.")
            return
        if not message.text:
            await message.reply_text("أرسل primary أو success أو danger.")
            return

        color = message.text.strip().lower()
        if color not in ("primary", "success", "danger"):
            await message.reply_text("الاختيارات المتاحة فقط:\nprimary\nsuccess\ndanger")
            return

        normalize_category(category)
        category["style"]["color"] = color
        save_db(DB)
        context.user_data.pop("admin_state", None)
        context.user_data.pop("admin_category_id", None)
        await message.reply_text(f"تم تغيير لون الزر إلى: {color}", reply_markup=category_admin_keyboard(category_id))
        return

    if state == "edit_cat_emoji":
        category_id = context.user_data.get("admin_category_id")
        category = get_category(category_id)
        if not category:
            await message.reply_text("القسم غير موجود.")
            return

        normalize_category(category)

        if message.text and message.text.strip() == "حذف":
            category["style"]["emoji_id"] = ""
            save_db(DB)
            context.user_data.pop("admin_state", None)
            context.user_data.pop("admin_category_id", None)
            await message.reply_text("تم حذف Custom Emoji من الزر.", reply_markup=category_admin_keyboard(category_id))
            return

        emoji_id = extract_custom_emoji_id(message)
        if not emoji_id:
            await message.reply_text("لم أجد Custom Emoji في الرسالة.\nأرسل Custom Emoji واحدًا.")
            return

        category["style"]["emoji_id"] = emoji_id
        save_db(DB)
        context.user_data.pop("admin_state", None)
        context.user_data.pop("admin_category_id", None)
        await message.reply_text("تم حفظ Custom Emoji للزر.", reply_markup=category_admin_keyboard(category_id))
        return

    if state == "edit_cat_url":
        category_id = context.user_data.get("admin_category_id")
        category = get_category(category_id)
        if not category:
            await message.reply_text("القسم غير موجود.")
            return

        normalize_category(category)

        if message.text and message.text.strip() == "حذف":
            category["style"]["url"] = ""
            save_db(DB)
            context.user_data.pop("admin_state", None)
            context.user_data.pop("admin_category_id", None)
            await message.reply_text("تم حذف الرابط من الزر.", reply_markup=category_admin_keyboard(category_id))
            return

        if not message.text:
            await message.reply_text("أرسل رابطًا.")
            return

        url = message.text.strip()
        if not (url.startswith("https://") or url.startswith("http://") or url.startswith("tg://")):
            await message.reply_text("الرابط يجب أن يبدأ بـ https:// أو http:// أو tg://")
            return

        category["style"]["url"] = url
        save_db(DB)
        context.user_data.pop("admin_state", None)
        context.user_data.pop("admin_category_id", None)
        await message.reply_text("تم حفظ الرابط.", reply_markup=category_admin_keyboard(category_id))
        return

    if state == "change_price":
        if not message.text:
            await message.reply_text("أرسل السعر بالأرقام فقط.")
            return
        try:
            new_price = int(message.text.strip())
        except ValueError:
            await message.reply_text("السعر يجب أن يكون رقمًا صحيحًا.")
            return
        if not 1 <= new_price <= 100000:
            await message.reply_text("السعر يجب أن يكون بين 1 و100000 نجمة.")
            return
        DB.setdefault("settings", {})["subscription_stars"] = new_price
        save_db(DB)
        context.user_data.pop("admin_state", None)
        await message.reply_text(
            f"تم تغيير سعر الاشتراك إلى {new_price} نجمة.",
            reply_markup=admin_keyboard(),
        )
        return

    if state == "activate_subscription":
        if not message.text:
            await message.reply_text("أرسل ID أو @username.")
            return

        target = message.text.strip()
        target_record = None

        if target.isdigit():
            target_record = DB.get("users", {}).get(target)
        else:
            username = target.lstrip("@").lower()
            for record in DB.get("users", {}).values():
                if str(record.get("username", "")).lstrip("@").lower() == username:
                    target_record = record
                    break

        if not target_record:
            context.user_data.pop("admin_state", None)
            await message.reply_text(
                "لم أجد هذا المستخدم في قاعدة بيانات البوت.\\n"
                "يجب أن يكون قد بدأ البوت من قبل، ثم أرسل ID أو username الصحيح.",
                reply_markup=admin_keyboard(),
            )
            return

        target_id = int(target_record["id"])
        current_until = int(target_record.get("subscription_until", 0))
        start_from = max(current_until, int(time.time()))
        target_record["subscription_until"] = start_from + SUBSCRIPTION_SECONDS
        target_record["is_subscribed"] = True
        target_record["manual_subscription"] = True
        save_db(DB)
        context.user_data.pop("admin_state", None)

        await message.reply_text(
            f"تم تفعيل الاشتراك بنجاح.\\n\\n"
            f"المستخدم: {target_record.get('name', '')}\\n"
            f"ID: {target_id}\\n"
            f"المدة المضافة: {SUBSCRIPTION_DAYS} يوم",
            reply_markup=admin_keyboard(),
        )
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="تم تفعيل اشتراكك يدويًا من الإدارة لمدة 30 يومًا.\\nيمكنك الآن استخدام جميع المميزات.",
                reply_markup=home_keyboard(),
            )
        except Exception as exc:
            logger.warning("Could not notify manually activated user %s: %s", target_id, exc)
        return

    if state == "add_required":
        if not message.text:
            await message.reply_text("أرسل @username أو chat_id أو رابط t.me.")
            return

        value = message.text.strip()
        if value not in DB["required_channels"]:
            DB["required_channels"].append(value)
            save_db(DB)

        context.user_data.pop("admin_state", None)
        await message.reply_text(f"تمت إضافة الاشتراك الإجباري:\n{value}", reply_markup=admin_keyboard())
        return

    if state == "text_welcome":
        if not message.text:
            await message.reply_text("أرسل النص.")
            return
        DB["settings"]["welcome_text"] = message.text
        save_db(DB)
        context.user_data.pop("admin_state", None)
        await message.reply_text("تم تغيير رسالة الترحيب.", reply_markup=admin_keyboard())
        return

    if state == "text_payment":
        if not message.text:
            await message.reply_text("أرسل النص.")
            return
        DB["settings"]["payment_text"] = message.text
        save_db(DB)
        context.user_data.pop("admin_state", None)
        await message.reply_text("تم تغيير رسالة الدفع.", reply_markup=admin_keyboard())
        return

    if state == "text_noaccess":
        if not message.text:
            await message.reply_text("أرسل النص.")
            return
        DB["settings"]["no_access_text"] = message.text
        save_db(DB)
        context.user_data.pop("admin_state", None)
        await message.reply_text("تم تغيير رسالة عدم الوصول.", reply_markup=admin_keyboard())
        return

    if state == "broadcast":
        context.user_data.pop("admin_state", None)
        users = list(DB.get("users", {}).values())
        sent = 0
        failed = 0

        await message.reply_text(f"بدأت الإذاعة إلى {len(users)} مستخدم.")

        for record in users:
            target_id = record.get("id")
            if not target_id or record.get("blocked"):
                continue

            try:
                await context.bot.copy_message(
                    chat_id=target_id,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id,
                )
                sent += 1
            except Exception as exc:
                failed += 1
                logger.warning("Broadcast failed for %s: %s", target_id, exc)

            await asyncio.sleep(0.05)

        await message.reply_text(
            f"انتهت الإذاعة.\n\nتم الإرسال: {sent}\nفشل: {failed}",
            reply_markup=admin_keyboard(),
        )
        return


# ============================================================
# MESSAGE FALLBACK
# ============================================================


async def normal_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message:
        return

    chat_type = update.effective_chat.type if update.effective_chat else "private"

    # في الجروبات — تجاهل (المعالج الخاص بالجروبات يتكفل)
    if chat_type in ("group", "supergroup"):
        return

    # في الخاص فقط
    if chat_type != "private":
        return

    user = update.effective_user
    ensure_user(user)

    if is_admin(user.id) and context.user_data.get("admin_state"):
        await admin_input_handler(update, context)
        return

    if is_admin(user.id):
        await send_home(update, context)
        return

    joined = await user_required_channels_joined(context, user.id)
    if not joined:
        await send_required_channels(update, context)
        return

    if not subscription_active(user.id):
        await send_subscription_page(update, context)
        return

    await send_home(update, context)


# ============================================================
# ERROR HANDLER
# ============================================================


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception while processing update:", exc_info=context.error)


# ============================================================
# STARTUP
# ============================================================


async def post_init(application: Application) -> None:
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        logger.exception("Could not delete webhook.")

    try:
        me = await application.bot.get_me()
        logger.info("Bot started: @%s (%s)", me.username, me.id)
    except Exception:
        logger.exception("Could not fetch bot info.")


def validate_config() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("ضع توكن البوت داخل BOT_TOKEN في أعلى الملف.")

    if not isinstance(OWNER_ID, int) or OWNER_ID <= 0:
        raise RuntimeError("ضع Telegram numeric ID الصحيح داخل OWNER_ID.")


def build_application() -> Application:
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("addadmin", admin_add_admin_command))
    application.add_handler(CommandHandler("deladmin", admin_del_admin_command))

    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    # ✅ معالج الجروبات — يعمل قبل باقي الـ handlers
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL,
            group_auto_reply_handler,
        ),
        group=-1,
    )

    application.add_handler(CallbackQueryHandler(callback_handler))

    # في الخاص فقط
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.ALL & ~filters.COMMAND,
            normal_message_handler,
        )
    )

    application.add_error_handler(error_handler)

    return application


def main() -> None:
    validate_config()

    global DB
    DB = load_db()

    application = build_application()

    logger.info("Starting MaX VIP bot...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
