# -*- coding: utf-8 -*-
"""
MaX VIP Subscription Bot
Pydroid 3 / Python 3.10+
"""

import asyncio
import html
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
    InputFile,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
)
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ChatMemberHandler,
    PreCheckoutQueryHandler,
    filters,
)

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = "8719852365:AAFaCMsqCXLzSFMANqKgZp02PQPzpDVtug4"
OWNER_ID = 8037399518

SUBSCRIPTION_STARS = 50
SUBSCRIPTION_DAYS = 30
REFERRAL_POINTS_PER_INVITE = 1
POINTS_REQUIRED_PER_SECTION = 5
VIP_SECTION_ID = "vip"
EMOJI_INVITE_LINK = "🔗"
EMOJI_REFERRAL_NOTICE = "🎁"
SUBSCRIPTION_SECONDS = 30 * 24 * 60 * 60

# Persistent data directory.
# Railway Volume is mounted at /data. When /data is available and writable,
# all bot database data is stored there so it survives restarts/redeploys.
# Outside Railway (for example Pydroid), it falls back to ./bot_data.
VOLUME_ROOT = Path("/data")
if VOLUME_ROOT.exists() and os.access(VOLUME_ROOT, os.W_OK):
    DATA_DIR = VOLUME_ROOT / "bot_data"
else:
    DATA_DIR = Path("bot_data")

DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_FILE = str(DATA_DIR / "max_vip_bot_db.json")
LEGACY_DATABASE_FILE = Path("max_vip_bot_db.json")

ALL_VIDEOS_URL = "https://t.me/mediation_King"
DEFAULT_REQUIRED_CHANNEL = "https://t.me/mediation_King"
SECOND_REQUIRED_CHANNEL = "https://t.me/Bbeemmsn"
REQUIRED_CHANNEL_ID = "-1003390584761"
REQUIRED_CHANNEL_INVITE_URL = "https://t.me/+7lFrm3Ae5yliZDg0"
REQUIRED_CHANNELS = ["@mediation_King", "@Bbeemmsn"]

BOT_TITLE = "مملكة الدلع الحصري"
BOT_USERNAME = "TteeRMBoT"
ADD_TO_GROUP_URL = f"https://t.me/{BOT_USERNAME}?startgroup=true"

WELCOME_TEXT = (
    "︙ نورت يـ {name} في بوت مقاطع 🤤🔥\n"
    "︙ اجمع 5 نقاط من رابط الدعوة لفتح الأقسام\n"
    "︙ قسم VIP متاح بالنجوم ⭐\n\n"
    "اختار من الأزرار بالأسفل."
)

PAYMENT_TEXT = (
    "︙ نورت يـ {name} في بوت مقاطع 🤤🔥\n"
    "︙ اجمع 5 نقاط من رابط الدعوة لفتح الأقسام\n"
    "︙ قسم VIP متاح بالنجوم ⭐\n\n"
    "استخدم رابط الدعوة للحصول على النقاط."
)

NO_ACCESS_TEXT = (
    "لا يمكنك استخدام هذا القسم الآن.\n\n"
    "يجب أن يكون اشتراكك فعالًا."
)

REQUIRED_CHANNEL_TEXT = (
    "اشترك في القناة الأولى والقناة الثانية، ثم اضغط تحقق من الاشتراك."
)

# ============================================================
# GROUP AUTO-REPLY
# ============================================================

GROUP_REPLY_MESSAGES = [
    "لو عايز تعرف النظام، مستنيك خاص 💕",
    "تعالى خاص وهقولك كل التفاصيل ❤️",
    "لو محتاج تعرف التفاصيل ابعتلي خاص 💕",
    "تعالى خاص يا صاحبي ❤️",
    "لو حابب تعرف أكتر، الخاص مفتوح 💕",
    "كل التفاصيل موجودة في الخاص ❤️",
    "ابعتلي خاص وهقولك النظام بالكامل 💕",
    "اللي عايز يعرف التفاصيل يتفضل خاص ❤️",
]

# روابط الاشتراك الإجباري التي تظهر في الجروبات
GROUP_REQUIRED_TEXT = (
    "لاستخدام البوت داخل الجروب، لازم تشترك في القناتين أولًا.\n\n"
    "بعد الاشتراك ابعت أي رسالة مرة ثانية وسيتم التحقق تلقائيًا."
)

# نطاق الحروف العربية + الإنجليزية
LETTERS_PATTERN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF"
    r"A-Za-z"
    r"]"
)

# ============================================================
# CUSTOM EMOJI IDs
# ============================================================

EMOJI_ADMIN = "⚙️"
EMOJI_ADD_VIDEO = "➕"
EMOJI_DELETE = "🗑️"
EMOJI_SUBSCRIBE = "⭐"

EMOJI_CLOTHES = "👕"
EMOJI_ALL_VIDEOS = "🎬"
EMOJI_CHECK_SUB = "✅"
EMOJI_HOME = "🏠"

EMOJI_FACES = [
    "😀",
    "😎",
    "😂",
    "😍",
    "🥰",
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
    "required_channels": [DEFAULT_REQUIRED_CHANNEL, REQUIRED_CHANNEL_ID],
    "categories": DEFAULT_CATEGORIES,
    "settings": {
        "welcome_text": WELCOME_TEXT,
        "payment_text": PAYMENT_TEXT,
        "no_access_text": NO_ACCESS_TEXT,
        "bot_title": BOT_TITLE,
        "subscription_stars": 50,
        "all_videos_url": ALL_VIDEOS_URL,
        "join_groups_required": 5,
        "member_join_notice": True,
        "points_per_referral": 1,
        "points_required_per_section": 5,
        "vip_stars": 50,
        "referral_code": "5141092083993412661",
        "group_welcome_photo": "",
    },
    "broadcast": {
        "running": False,
    },
    "keyword_replies": [],
    "group_protection": {},
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


EMOJI_ID_TO_UNICODE = {
    "5141092083993412661": "🔗",
    "5775979900649347911": "🎁",
    "5972226216353074147": "⚙️",
    "5974563533260590445": "➕",
    "5976383044615934151": "🗑️",
    "5891131044756723016": "⭐",
    "5906597204809749180": "👕",
    "5909008794586715815": "🎬",
    "5260416304224936047": "✅",
    "5257963315258204021": "🏠",
    "5909242019900823049": "😀",
    "5908867262529409910": "😎",
    "5906536933533684298": "😂",
    "5906794932219154887": "🥰",
    "5206607081334906820": "🔒",
    "5870734657384877785": "🛡️",
    "5260293700088511294": "🔒",
}

def migrate_emoji_ids(value):
    if isinstance(value, dict):
        for k, v in list(value.items()):
            value[k] = migrate_emoji_ids(v)
        return value
    if isinstance(value, list):
        return [migrate_emoji_ids(v) for v in value]
    if isinstance(value, str):
        return EMOJI_ID_TO_UNICODE.get(value, value)
    return value


def load_db() -> Dict[str, Any]:
    path = Path(DATABASE_FILE)

    # First run after attaching the Railway Volume: if the old database is
    # still available in the previous local path, copy it into the persistent
    # Volume before creating a new empty database.
    if not path.exists() and LEGACY_DATABASE_FILE.exists() and LEGACY_DATABASE_FILE.resolve() != path.resolve():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(LEGACY_DATABASE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
            logger.info("Migrated legacy database to persistent path: %s", path)
        except Exception:
            logger.exception("Could not migrate legacy database to persistent path.")

    if not path.exists():
        save_db(DEFAULT_DB)
        return json.loads(json.dumps(DEFAULT_DB, ensure_ascii=False))

    try:
        with path.open("r", encoding="utf-8") as f:
            db = json.load(f)
        db = migrate_emoji_ids(db)
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
    if "all_videos_url" not in db["settings"]:
        db["settings"]["all_videos_url"] = ALL_VIDEOS_URL
        changed = True
    if "join_groups_required" not in db["settings"]:
        db["settings"]["join_groups_required"] = 5
        changed = True
    if "member_join_notice" not in db["settings"]:
        db["settings"]["member_join_notice"] = True
        changed = True
    for _key, _default in (("points_per_referral", 1), ("points_required_per_section", 5), ("vip_stars", 50), ("referral_code", "5141092083993412661"), ("group_welcome_photo", "")):
        if _key not in db["settings"]:
            db["settings"][_key] = _default
            changed = True

    # الاشتراك الإجباري الثابت: القناتان المطلوبتان في الخاص والجروبات.
    required_only = list(REQUIRED_CHANNELS)
    if db.get("required_channels") != required_only:
        db["required_channels"] = required_only
        changed = True

    for item in db.get("categories", []):
        normalize_category(item)

    if not any(str(item.get("id")) == VIP_SECTION_ID for item in db.get("categories", [])):
        db["categories"].insert(0, {"id": VIP_SECTION_ID, "name": "VIP ⭐", "videos": [], "children": [], "style": {"color": "success", "emoji_id": EMOJI_SUBSCRIBE, "url": ""}})
        changed = True

    for _record in db.get("users", {}).values():
        _record.setdefault("points", 0)
        _record.setdefault("referrals", 0)
        _record.setdefault("referred_by", 0)

    if changed:
        save_db(db)

    return db


# ============================================================
# HELPERS
# ============================================================


def get_subscription_stars() -> int:
    try:
        value = int(DB.get("settings", {}).get("vip_stars", DB.get("settings", {}).get("subscription_stars", SUBSCRIPTION_STARS)))
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
        kwargs["text"] = f"{emoji_id} {kwargs['text']}"

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
            "points": 0,
            "referrals": 0,
            "referred_by": 0,
        }
    else:
        DB["users"][uid]["username"] = user.username or DB["users"][uid].get("username", "")
        DB["users"][uid]["name"] = user.full_name or DB["users"][uid].get("name", "")

    save_db(DB)
    return DB["users"][uid]


def get_user_points(user_id: int) -> int:
    record = DB.get("users", {}).get(str(user_id), {})
    return max(0, int(record.get("points", 0)))


def referral_link(user_id: int) -> str:
    return f"https://t.me/{BOT_USERNAME}?start=ref_{int(user_id)}"


def add_referral(referrer_id: int, referred_user) -> bool:
    if referrer_id <= 0 or referrer_id == referred_user.id:
        return False
    referrer = DB.get("users", {}).get(str(referrer_id))
    referred = DB.get("users", {}).get(str(referred_user.id))
    if not referrer or not referred:
        return False
    if referred.get("referred_by"):
        return False
    referred["referred_by"] = referrer_id
    referrer["referrals"] = int(referrer.get("referrals", 0)) + 1
    referrer["points"] = int(referrer.get("points", 0)) + int(DB.get("settings", {}).get("points_per_referral", REFERRAL_POINTS_PER_INVITE))
    save_db(DB)
    return True


def referral_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [colored_button("رابط الدعوة", url=referral_link(user_id), style="primary", emoji_id=EMOJI_INVITE_LINK)],
        [colored_button("النقاط", callback_data="points_status", style="success", emoji_id=EMOJI_REFERRAL_NOTICE)],
    ])


def points_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [colored_button("رابط الدعوة", url=referral_link(user_id), style="primary", emoji_id=EMOJI_INVITE_LINK)],
        [colored_button("حالة النقاط", callback_data="points_status", style="success", emoji_id=EMOJI_REFERRAL_NOTICE)],
    ])


def vip_keyboard() -> InlineKeyboardMarkup:
    stars = int(DB.get("settings", {}).get("vip_stars", SUBSCRIPTION_STARS))
    return InlineKeyboardMarkup([
        [colored_button(f"VIP بـ {stars} ⭐", callback_data="buy_vip", style="success", emoji_id=EMOJI_SUBSCRIBE)],
        [colored_button("رجوع", callback_data="home", style="danger", emoji_id=EMOJI_HOME)],
    ])


def regular_sections_unlocked(user_id: int) -> bool:
    return get_user_points(user_id) >= int(DB.get("settings", {}).get("points_required_per_section", POINTS_REQUIRED_PER_SECTION))


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
        if channel.startswith("https://t.me/+") or channel.startswith("http://t.me/+"):
            # رابط الدعوة الخاص يتم عرضه للمستخدم فقط؛ التحقق الفعلي يتم عبر Chat ID.
            # لا نوقف التحقق بسبب وجود رابط الدعوة في القائمة.
            continue

        check_target = channel
        if channel.startswith("https://t.me/"):
            tail = channel.rstrip("/").split("/", 3)[-1]
            if tail and not tail.startswith("+"):
                check_target = "@" + tail.split("?")[0]
        elif channel.startswith("http://t.me/"):
            tail = channel.rstrip("/").split("/", 3)[-1]
            if tail and not tail.startswith("+"):
                check_target = "@" + tail.split("?")[0]

        try:
            member = await context.bot.get_chat_member(chat_id=check_target, user_id=user_id)
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

    # بعد الاشتراك الإجباري، الدخول للواجهة الرئيسية متاح للجميع.
    # قسم VIP وحده يطلب اشتراك النجوم، والأقسام العادية تطلب نقاط الإحالات.
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
        kwargs["text"] = f"{emoji_id} {kwargs['text']}"

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
            kwargs["text"] = f"{emoji_id} {kwargs['text']}"

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

    rows.append([colored_button("جميع الفيديوهات", url=str(DB.get("settings", {}).get("all_videos_url", ALL_VIDEOS_URL)), style="success", emoji_id=EMOJI_ALL_VIDEOS)])
    rows.append([colored_button("رابط الدعوة", callback_data="referral_page", style="primary", emoji_id=EMOJI_INVITE_LINK), colored_button("النقاط", callback_data="points_status", style="primary", emoji_id=EMOJI_REFERRAL_NOTICE)])
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
        colored_button("تفعيل VIP", callback_data="admin_activate", style="primary", emoji_id=e),
        colored_button("إلغاء اشتراك شخص", callback_data="admin_cancel_subscription", style="danger", emoji_id=d),
        colored_button("سعر VIP بالنجوم", callback_data="admin_price", style="primary", emoji_id=e),
        colored_button("الإذاعة", callback_data="admin_broadcast", style="success", emoji_id=e),
        colored_button("المستخدمون", callback_data="admin_users", style="primary", emoji_id=e),
        colored_button("تصدير الأعضاء", callback_data="admin_export_members", style="success", emoji_id=e),
        colored_button("استرجاع الأعضاء", callback_data="admin_restore_members", style="primary", emoji_id=e),
        colored_button("رابط جميع الفيديوهات", callback_data="admin_all_videos_url", style="primary", emoji_id=e),
        colored_button("إدارة الأدمن", callback_data="admin_admins", style="primary", emoji_id=e),
        colored_button("النصوص", callback_data="admin_texts", style="primary", emoji_id=e),
        colored_button("تعيين/تغيير صورة ترحيب الجروبات", callback_data="admin_group_welcome_photo", style="primary", emoji_id=e),
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

    rows.append([colored_button("إضافة قناة/جروب", callback_data="admin_req_add", style="success", emoji_id=EMOJI_ADMIN)])
    rows.append([colored_button("شرح الاشتراك الإجباري", callback_data="admin_req_help", style="danger", emoji_id=EMOJI_ADMIN)])
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
    return vip_keyboard()


async def send_required_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # الاشتراك الإجباري والقائمة الرئيسية للخاص فقط — لا تظهر أي قائمة في الجروبات.
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        return

    rows = []

    for channel in DB.get("required_channels", []):
        channel = str(channel)

        if channel.startswith("http://") or channel.startswith("https://"):
            rows.append([colored_button("الاشتراك في القناة", url=channel, style="primary", emoji_id=EMOJI_ADMIN)])
        elif channel == REQUIRED_CHANNEL_ID:
            rows.append([colored_button("الاشتراك في القناة", url=REQUIRED_CHANNEL_INVITE_URL, style="primary", emoji_id=EMOJI_ADMIN)])
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
    # صفحة الاشتراك خاصة فقط ولا تُرسل أو تُعدل داخل الجروبات.
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        return

    template = DB["settings"].get("payment_text", PAYMENT_TEXT)
    user = update.effective_user
    mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>' if user else ""
    text = template.replace("{name}", mention).replace("{stars}", str(get_subscription_stars()))

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=subscription_keyboard(), parse_mode=ParseMode.HTML)
            return
        except Exception:
            pass

    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=subscription_keyboard(), parse_mode=ParseMode.HTML)


async def send_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # القائمة الرئيسية خاصة فقط — ممنوع ظهورها في أي جروب نهائيًا.
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        return

    user = update.effective_user
    if user:
        ensure_user(user)

    template = DB["settings"].get("welcome_text", WELCOME_TEXT)
    user = update.effective_user
    if user:
        mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
        text = template.replace("{name}", mention).replace("{stars}", str(get_subscription_stars()))
    else:
        text = template.replace("{stars}", str(get_subscription_stars()))

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=home_keyboard(), parse_mode=ParseMode.HTML)
            return
        except Exception:
            pass

    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=home_keyboard(), parse_mode=ParseMode.HTML)


# ============================================================
# MEMBER JOIN NOTICE / EXPORT
# ============================================================

async def notify_new_member(context: ContextTypes.DEFAULT_TYPE, user) -> None:
    if not DB.get("settings", {}).get("member_join_notice", True):
        return
    try:
        mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(f"دخول عضو جديد\n\nالاسم: {mention}\n"
                  f"ID: <code>{user.id}</code>\n"
                  f"Username: @{user.username}" if user.username else f"دخول عضو جديد\n\nالاسم: {mention}\nID: <code>{user.id}</code>"),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.warning("Member join notice failed: %s", exc)

async def export_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    export_path = Path("members_export.json")
    payload = {"version": 1, "exported_at": int(time.time()), "users": DB.get("users", {})}
    export_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        with export_path.open("rb") as f:
            await context.bot.send_document(
                chat_id=update.effective_user.id,
                document=InputFile(f, filename="members_export.json"),
                caption=f"تم تصدير {len(DB.get('users', {}))} عضو.",
                reply_markup=admin_keyboard(),
            )
    finally:
        try:
            export_path.unlink()
        except OSError:
            pass

# ============================================================
# START
# ============================================================


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message:
        return

    # إذا كان في جروب، لا يرد
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        return

    uid = str(update.effective_user.id)
    is_new_member = uid not in DB.get("users", {})
    user = ensure_user(update.effective_user)

    # معالجة رابط الإحالة: /start ref_<ID>
    if context.args and context.args[0].startswith("ref_"):
        try:
            referrer_id = int(context.args[0].split("_", 1)[1])
        except (ValueError, IndexError):
            referrer_id = 0
        if is_new_member and referrer_id and add_referral(referrer_id, update.effective_user):
            mention = f'<a href="tg://user?id={update.effective_user.id}">{update.effective_user.full_name}</a>'
            ref_record = DB.get("users", {}).get(str(referrer_id), {})
            try:
                referral_text = (f"وصلك احالة جديدة  {mention}  🐤\n\n"
                                 f"عدد احالاتك | {int(ref_record.get('referrals', 0))}  🐤")
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=referral_text,
                    parse_mode=ParseMode.HTML,
                )
            except Exception as exc:
                logger.warning("Referral notification failed: %s", exc)

    if is_new_member and not is_admin(update.effective_user.id):
        await notify_new_member(context, update.effective_user)

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
            prices=[LabeledPrice(label="VIP شهري", amount=int(DB.get("settings", {}).get("vip_stars", SUBSCRIPTION_STARS)))],
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

    if payment.total_amount != int(DB.get("settings", {}).get("vip_stars", SUBSCRIPTION_STARS)):
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
        f"السعر: {int(DB.get('settings', {}).get('vip_stars', SUBSCRIPTION_STARS))} نجمة\n"
        f"المدة: {SUBSCRIPTION_DAYS} يوم\n\n"
        "يمكنك الآن فتح جميع الأقسام.",
        reply_markup=home_keyboard(),
    )


# ============================================================
# GROUP PROTECTION
# ============================================================

PROTECTION_KEYS = {
    "links": "الروابط",
    "usernames": "المعرفات واليوزرات",
    "numbers": "الأرقام",
    "symbols": "الرموز",
    "photos": "الصور",
    "videos": "الفيديوهات",
    "voice": "الفويس",
    "audio": "الملفات الصوتية",
    "documents": "الملفات",
    "animations": "GIF",
    "stickers": "الملصقات",
    "contacts": "جهات الاتصال",
    "locations": "المواقع",
    "polls": "الاستطلاعات",
    "forwards": "إعادة التوجيه",
    "bots": "البوتات",
    "repeat": "التكرار",
    "long_messages": "الرسائل الطويلة",
}

PROTECTION_ALIASES = {
    "الروابط": "links", "رابط": "links", "روابط": "links",
    "المعرفات": "usernames", "المعرفات واليوزرات": "usernames", "اليوزرات": "usernames", "يوزرات": "usernames",
    "الأرقام": "numbers", "ارقام": "numbers", "الأرقام": "numbers",
    "الرموز": "symbols", "رموز": "symbols",
    "الصور": "photos", "صور": "photos",
    "الفيديوهات": "videos", "فيديوهات": "videos", "الفيديو": "videos",
    "الفويس": "voice", "فويس": "voice",
    "الصوتيات": "audio", "ملفات صوتية": "audio",
    "الملفات": "documents", "ملفات": "documents",
    "gif": "animations", "GIF": "animations",
    "الملصقات": "stickers", "ملصقات": "stickers",
    "جهات الاتصال": "contacts", "جهات": "contacts",
    "المواقع": "locations", "مواقع": "locations",
    "الاستطلاعات": "polls", "استطلاعات": "polls",
    "إعادة التوجيه": "forwards", "التوجيه": "forwards", "توجيه": "forwards",
    "البوتات": "bots", "بوتات": "bots",
    "التكرار": "repeat", "تكرار": "repeat",
    "الرسائل الطويلة": "long_messages", "رسايل طويلة": "long_messages", "رسائل طويلة": "long_messages",
}
REPEAT_TRACKER = {}
LONG_MESSAGE_LIMIT = 1000
REPEAT_WINDOW_SECONDS = 30
REPEAT_COUNT_LIMIT = 3

def group_settings(chat_id: int) -> Dict[str, Any]:
    settings = DB.setdefault("group_protection", {})
    key = str(chat_id)
    if key not in settings:
        settings[key] = {k: False for k in PROTECTION_KEYS}
        settings[key]["all"] = False
        settings[key]["penalty"] = "delete"
    else:
        for k in PROTECTION_KEYS:
            settings[key].setdefault(k, False)
        settings[key].setdefault("all", False)
        settings[key].setdefault("penalty", "delete")
    return settings[key]


def protection_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    # عند فتح قسم الحماية تظهر لكل نوع زران واضحان: فتح أخضر / قفل أحمر.
    rows = []
    for key, label in PROTECTION_KEYS.items():
        rows.append([
            colored_button(
                f"فتح {label}",
                callback_data=f"protect_open:{key}",
                style="success",
                emoji_id=EMOJI_CHECK_SUB,
            ),
            colored_button(
                f"قفل {label}",
                callback_data=f"protect_lock:{key}",
                style="danger",
                emoji_id=EMOJI_DELETE,
            ),
        ])
    rows.append([
        colored_button("فتح كل شيء", callback_data="protect:all_off", style="success", emoji_id=EMOJI_CHECK_SUB),
        colored_button("قفل كل شيء", callback_data="protect:all_on", style="danger", emoji_id=EMOJI_DELETE),
    ])
    rows.append([colored_button("رجوع", callback_data="protect_back", style="primary", emoji_id=EMOJI_HOME)])
    return InlineKeyboardMarkup(rows)


def protection_penalty_keyboard(key: str) -> InlineKeyboardMarkup:
    label = PROTECTION_KEYS.get(key, key)
    return InlineKeyboardMarkup([
        [colored_button("كتم", callback_data=f"penalty:{key}:mute", style="danger", emoji_id=EMOJI_ADMIN)],
        [colored_button("حذف", callback_data=f"penalty:{key}:delete", style="primary", emoji_id=EMOJI_DELETE)],
        [colored_button("حظر", callback_data=f"penalty:{key}:ban", style="danger", emoji_id=EMOJI_DELETE)],
        [colored_button("رجوع", callback_data="protect_back", style="primary", emoji_id=EMOJI_HOME)],
    ])


def mute_duration_keyboard(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [colored_button("دقيقة", callback_data=f"mute_duration:{key}:60", style="primary", emoji_id=EMOJI_ADMIN), colored_button("10 دقائق", callback_data=f"mute_duration:{key}:600", style="primary", emoji_id=EMOJI_ADMIN)],
        [colored_button("ساعة", callback_data=f"mute_duration:{key}:3600", style="primary", emoji_id=EMOJI_ADMIN), colored_button("يوم", callback_data=f"mute_duration:{key}:86400", style="primary", emoji_id=EMOJI_ADMIN)],
        [colored_button("رجوع", callback_data=f"penalty_menu:{key}", style="primary", emoji_id=EMOJI_HOME)],
    ])


def user_is_group_admin(update: Update) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or chat.type not in ("group", "supergroup") or not user:
        return False
    try:
        member = update._bot.get_chat_member(chat.id, user.id) if False else None
    except Exception:
        member = None
    return False


def protection_violation(message, st: Dict[str, Any]) -> Optional[str]:
    text = (message.text or "") + " " + (message.caption or "")
    entities = list(message.entities or []) + list(message.caption_entities or [])
    if st.get("links") and (re.search(r"https?://|t\.me/|telegram\.me/|www\.", text, re.I) or any(getattr(e, "type", "") in ("url", "text_link") for e in entities)):
        return "الروابط"
    if st.get("usernames") and (re.search(r"@[A-Za-z0-9_]{3,}", text) or any(getattr(e, "type", "") in ("mention", "text_mention") for e in entities)):
        return "المعرفات واليوزرات"
    if st.get("numbers") and re.search(r"\d", text):
        return "الأرقام"
    if st.get("symbols") and text and re.search(r"[^\w\s\u0600-\u06FF]", text, re.UNICODE):
        return "الرموز"
    if st.get("photos") and message.photo:
        return "الصور"
    if st.get("videos") and (message.video or message.video_note):
        return "الفيديوهات"
    if st.get("voice") and message.voice:
        return "الفويس"
    if st.get("audio") and message.audio:
        return "الملفات الصوتية"
    if st.get("documents") and message.document:
        return "الملفات"
    if st.get("animations") and message.animation:
        return "GIF"
    if st.get("stickers") and message.sticker:
        return "الملصقات"
    if st.get("contacts") and message.contact:
        return "جهات الاتصال"
    if st.get("locations") and (message.location or message.venue):
        return "المواقع"
    if st.get("polls") and (message.poll or message.poll_answer):
        return "الاستطلاعات"
    if st.get("forwards") and (message.forward_origin or getattr(message, "forward_date", None)):
        return "إعادة التوجيه"
    if st.get("bots") and getattr(message.from_user, "is_bot", False):
        return "البوتات"
    if st.get("long_messages") and len(text.strip()) > LONG_MESSAGE_LIMIT:
        return "الرسائل الطويلة"
    if st.get("repeat") and text.strip():
        key = (message.chat.id, message.from_user.id)
        now = time.time()
        bucket = REPEAT_TRACKER.setdefault(key, [])
        bucket[:] = [(stamp, value) for stamp, value in bucket if now - stamp <= REPEAT_WINDOW_SECONDS]
        bucket.append((now, text.strip()))
        same = sum(1 for _, value in bucket if value == text.strip())
        if same >= REPEAT_COUNT_LIMIT:
            bucket[:] = [(stamp, value) for stamp, value in bucket if value != text.strip()]
            return "التكرار"
    return None


async def apply_group_penalty(context, chat_id: int, user_id: int, penalty: str, duration: int = 0):
    if penalty == "ban":
        await context.bot.ban_chat_member(chat_id, user_id)
    elif penalty == "mute":
        until = int(time.time()) + max(30, duration or 3600)
        await context.bot.restrict_chat_member(
            chat_id, user_id,
            permissions=__import__('telegram').ChatPermissions(can_send_messages=False),
            until_date=until,
        )


async def group_protection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or not user or chat.type not in ("group", "supergroup"):
        return
    if user.is_bot:
        return
    st = group_settings(chat.id)
    counts = st.setdefault("message_counts", {})
    uid_key = str(user.id)
    counts[uid_key] = int(counts.get(uid_key, 0)) + 1
    # Keep the DB bounded: only retain counters for users seen in this group.
    if len(counts) > 5000:
        for old_uid in list(counts)[:1000]:
            counts.pop(old_uid, None)
    save_db(DB)
    if not st.get("all") and not any(st.get(k) for k in PROTECTION_KEYS):
        return
    violation = protection_violation(message, st)
    if not violation:
        return
    try:
        await message.delete()
    except Exception as exc:
        logger.warning("Could not delete protected message in %s: %s", chat.id, exc)
    penalty = st.get(f"penalty_{violation}", st.get("penalty", "delete"))
    try:
        await apply_group_penalty(context, chat.id, user.id, penalty, st.get(f"mute_duration_{violation}", 3600))
    except Exception as exc:
        logger.warning("Protection penalty failed: %s", exc)
    mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    try:
        violation_text = f"يـ {mention}، {violation} هنا ممنوع {CUSTOM_EMOJI_LOCKED_REPLY}"
        await context.bot.send_message(
            chat.id,
            violation_text,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ============================================================
# GROUP MANDATORY SUBSCRIPTION + AUTO-REPLY
# ============================================================

async def send_group_required_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """إظهار الاشتراك الإجباري داخل الجروب مع رابطَي القناتين."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("الاشتراك في mediation_King", url="https://t.me/mediation_King")],
        [InlineKeyboardButton("الاشتراك في Bbeemmsn", url="https://t.me/Bbeemmsn")],
    ])
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=GROUP_REQUIRED_TEXT,
            reply_markup=keyboard,
        )
    except Exception as exc:
        logger.warning("Could not send group mandatory subscription message: %s", exc)


async def group_mandatory_subscription_ok(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """يتحقق بشكل صارم من القناتين قبل السماح بردود البوت في أي جروب."""
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            status = member.status
            if status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
                return False
        except Exception as exc:
            # لو تعذر التحقق، لا نسمح بتجاوز الاشتراك الإجباري.
            logger.warning("Mandatory group subscription check failed for %s / %s: %s", channel, user_id, exc)
            return False
    return True


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

    # لو الرسالة من نوع مقفول، معالج الحماية هو اللي يتولى الرد؛
    # نمنع الرد التلقائي العام عشان العضو ما ياخدش رسالتين فوق بعض.
    st = group_settings(chat.id)
    if st.get("all") or any(st.get(k) for k in PROTECTION_KEYS):
        if protection_violation(message, st):
            return

    # الاشتراك الإجباري مطبق على كل الجروبات.
    if not await group_mandatory_subscription_ok(context, user.id):
        st = group_settings(chat.id)
        notice_key = f"mandatory_notice_{user.id}"
        now = int(time.time())
        last_notice = int(st.get(notice_key, 0) or 0)
        if now - last_notice >= 60:
            st[notice_key] = now
            save_db(DB)
            await send_group_required_message(context, chat.id)
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

    data = query.data or ""

    # أزرار حماية الجروبات وكارت الكشف يجب أن تعمل داخل الجروبات.
    group_callback = (
        data.startswith("protect")
        or data.startswith("protection")
        or data.startswith("penalty")
        or data.startswith("mute_duration:")
        or data.startswith("profile_like:")
    )

    # أي أزرار للقائمة الرئيسية/الاشتراك ممنوعة داخل الجروبات، مع استثناء أزرار الحماية والكشف.
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup") and not group_callback:
        try:
            await safe_answer_callback(query, "هذا القسم متاح في الخاص فقط.", True)
        except Exception:
            pass
        try:
            if query.message:
                await query.message.delete()
        except Exception:
            pass
        return

    ensure_user(user)

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

        await send_home(update, context)
        return

    if data in ("buy_subscription", "buy_vip"):
        await buy_subscription(update, context)
        return

    if data == "referral_page":
        link = referral_link(user.id)
        points = get_user_points(user.id)
        referrals = DB.get("users", {}).get(str(user.id), {}).get("referrals", 0)
        text = (f"رابط الدعوة الخاص بك\n\n{link}\n\n"
                f"عدد احالاتك | {referrals}\n"
                f"نقاطك | {points}\n"
                f"المطلوب لفتح الأقسام | {int(DB.get('settings', {}).get('points_required_per_section', 5))}")
        await safe_answer_callback(query)
        try:
            await query.edit_message_text(text, reply_markup=points_keyboard(user.id))
        except Exception:
            pass
        return

    if data == "points_status":
        points = get_user_points(user.id)
        referrals = DB.get("users", {}).get(str(user.id), {}).get("referrals", 0)
        required = int(DB.get("settings", {}).get("points_required_per_section", 5))
        text = f"عدد احالاتك | {referrals}\nنقاطك | {points}\nالمطلوب | {required} نقاط"
        await safe_answer_callback(query)
        try:
            await query.edit_message_text(text, reply_markup=points_keyboard(user.id))
        except Exception:
            pass
        return

    if data == "admin_cancel_subscription":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        context.user_data["admin_state"] = "cancel_subscription"
        await safe_answer_callback(query)
        await query.message.reply_text("أرسل ID أو @username للشخص الذي تريد إلغاء اشتراك VIP له.")
        return

    if data == "protect_back":
        await safe_answer_callback(query)
        await query.edit_message_text("إعدادات حماية الجروب", reply_markup=protection_keyboard(update.effective_chat.id))
        return

    if (
        data.startswith("protect:")
        or data.startswith("protect_open:")
        or data.startswith("protect_lock:")
        or data.startswith("protection:")
        or data.startswith("penalty:")
        or data.startswith("penalty_menu:")
        or data.startswith("mute_duration:")
    ):
        if not update.effective_chat or update.effective_chat.type not in ("group", "supergroup"):
            await safe_answer_callback(query, "هذا القسم للجروبات فقط.", True)
            return
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, user.id)
            if member.status not in ("administrator", "creator"):
                await safe_answer_callback(query, "الأمر للمشرفين فقط.", True)
                return
        except Exception:
            await safe_answer_callback(query, "تعذر التحقق من صلاحياتك.", True)
            return
        action = data.split(":")
        st = group_settings(update.effective_chat.id)
        if data.startswith("protect_open:"):
            key = data.split(":", 1)[1]
            if key not in PROTECTION_KEYS:
                await safe_answer_callback(query, "القسم غير معروف.", True)
                return
            st[key] = False
            st.pop(f"penalty_{key}", None)
            st.pop(f"mute_duration_{key}", None)
            st["all"] = all(st.get(k, False) for k in PROTECTION_KEYS)
            save_db(DB)
            await safe_answer_callback(query, "تم الفتح.")
            await query.edit_message_text(
                f"تم فتح {PROTECTION_KEYS[key]} {CUSTOM_EMOJI_LOCK}",
                reply_markup=protection_keyboard(update.effective_chat.id),
            )
            return

        if data.startswith("protect_lock:"):
            key = data.split(":", 1)[1]
            if key not in PROTECTION_KEYS:
                await safe_answer_callback(query, "القسم غير معروف.", True)
                return
            await safe_answer_callback(query)
            await query.edit_message_text(
                f"اختر العقوبة عند قفل {PROTECTION_KEYS[key]}",
                reply_markup=protection_penalty_keyboard(key),
            )
            return

        if data.startswith("protect:"):
            key = action[1]
            if key == "all_on":
                for k in PROTECTION_KEYS: st[k] = True
                st["all"] = True
                save_db(DB)
                await safe_answer_callback(query)
                lock_text = "تم قفل كل شيء 🔹"
                await query.edit_message_text(lock_text, reply_markup=protection_keyboard(update.effective_chat.id))
                return
            if key == "all_off":
                for k in PROTECTION_KEYS: st[k] = False
                st["all"] = False
                save_db(DB)
                await safe_answer_callback(query)
                lock_text = "تم فتح كل شيء 🔹"
                await query.edit_message_text(lock_text, reply_markup=protection_keyboard(update.effective_chat.id))
                return
            await safe_answer_callback(query)
            await query.edit_message_text(f"اختر العقوبة عند قفل {PROTECTION_KEYS.get(key, key)}", reply_markup=protection_penalty_keyboard(key))
            return
        if data.startswith("penalty_menu:"):
            key=action[1]
            await safe_answer_callback(query)
            await query.edit_message_text(f"اختر العقوبة عند قفل {PROTECTION_KEYS.get(key, key)}", reply_markup=protection_penalty_keyboard(key))
            return
        if data.startswith("penalty:"):
            key, penalty = action[1], action[2]
            if penalty == "mute":
                await safe_answer_callback(query)
                await query.edit_message_text("اختار مدة الكتم", reply_markup=mute_duration_keyboard(key))
                return
            st[key] = True
            st[f"penalty_{key}"] = penalty
            save_db(DB)
            await safe_answer_callback(query)
            lock_text = f"تم حفظ البيانات\n\nتم قفل {PROTECTION_KEYS.get(key, key)} 🔹"
            await query.edit_message_text(lock_text, reply_markup=protection_keyboard(update.effective_chat.id))
            return
        if data.startswith("mute_duration:"):
            key, duration = action[1], int(action[2])
            st[key] = True
            st[f"penalty_{key}"] = "mute"
            st[f"mute_duration_{key}"] = duration
            save_db(DB)
            await safe_answer_callback(query)
            lock_text = f"تم حفظ البيانات\n\nتم قفل {PROTECTION_KEYS.get(key, key)} 🔹"
            await query.edit_message_text(lock_text, reply_markup=protection_keyboard(update.effective_chat.id))
            return

    if data.startswith("profile_like:"):
        try:
            _, chat_id_raw, target_id_raw = data.split(":", 2)
            chat_id = int(chat_id_raw)
            target_id = int(target_id_raw)
            if not update.effective_chat or update.effective_chat.id != chat_id:
                await safe_answer_callback(query, "هذا الزر ليس من هذا الجروب.", True)
                return
            st = group_settings(chat_id)
            likes = st.setdefault("likes", {})
            likes[str(target_id)] = int(likes.get(str(target_id), 0)) + 1
            save_db(DB)
            await safe_answer_callback(query, "❤")
            await query.edit_message_reply_markup(InlineKeyboardMarkup([[InlineKeyboardButton(f"❤ {likes[str(target_id)]}", callback_data=data)]]))
        except Exception:
            await safe_answer_callback(query)
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

        if category_id == VIP_SECTION_ID:
            if not subscription_active(user.id):
                await safe_answer_callback(query, "قسم VIP يحتاج اشتراك نجوم.", True)
                await send_subscription_page(update, context)
                return
        elif not regular_sections_unlocked(user.id) and not is_admin(user.id):
            required = int(DB.get("settings", {}).get("points_required_per_section", 5))
            await safe_answer_callback(query, f"تحتاج {required} نقاط من الإحالات أولًا.", True)
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
            "يمكنك إضافة قناة أو جروب عام بـ @username أو رابط t.me، أو جروب/قناة خاصة بـ chat_id يبدأ بـ -100 بعد إضافة البوت إليها.\n"
            "رابط الدعوة الخاص +xxxx يصلح للزر، لكن التحقق الآلي يحتاج chat_id لأن Telegram لا يسمح للبوت بفحص العضوية من رابط الدعوة وحده."
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
                "أرسل الآن @username أو chat_id أو رابط t.me للقناة/الجروب المطلوب.\n\nعام: @mediation_King\nخاص: -1001234567890 (بعد إضافة البوت للمجموعة/القناة)\nرابط دعوة خاص: https://t.me/+xxxx (زر فقط؛ التحقق يحتاج chat_id)\n\nللإلغاء: /cancel"
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

    if data == "admin_export_members":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query, "جاري تجهيز ملف الأعضاء...")
        await export_members(update, context)
        return

    if data == "admin_restore_members":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        context.user_data["admin_state"] = "restore_members"
        await safe_answer_callback(query)
        await query.edit_message_text("أرسل الآن ملف members_export.json أو أي ملف JSON يحتوي على users.\n\nللإلغاء: /cancel")
        return

    if data == "admin_all_videos_url":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        context.user_data["admin_state"] = "all_videos_url"
        await safe_answer_callback(query)
        await query.edit_message_text(f"الرابط الحالي:\n{DB.get('settings', {}).get('all_videos_url', ALL_VIDEOS_URL)}\n\nأرسل الرابط الجديد.\nللإلغاء: /cancel")
        return

    if data == "admin_req_help":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        await safe_answer_callback(query)
        await query.edit_message_text(
            "شرح الاشتراك الإجباري\n\n"
            "1) قناة/جروب عام: أرسل @username أو رابط t.me\n"
            "2) قناة/جروب خاص: أضف البوت إليه أولًا ثم أرسل chat_id مثل -1001234567890\n"
            "3) رابط دعوة خاص +xxxx يمكن عرضه كزر، لكن التحقق الفعلي يحتاج chat_id\n"
            "4) المستخدم يضغط اشتراك ثم تحقق، وإذا كان مشتركًا يمر للخطوة التالية.",
            reply_markup=required_channels_keyboard(),
        )
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

    if data == "admin_group_welcome_photo":
        if not is_admin(user.id):
            await safe_answer_callback(query, "غير مصرح.", True)
            return
        context.user_data["admin_state"] = "group_welcome_photo"
        await safe_answer_callback(query)
        await query.message.reply_text("أرسل صورة ترحيب الجروبات الآن.\n\nأرسل كلمة حذف لإزالة الصورة.")
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

    if state == "group_welcome_photo":
        if message.text and message.text.strip() == "حذف":
            DB["settings"]["group_welcome_photo"] = ""
            save_db(DB)
            context.user_data.pop("admin_state", None)
            await message.reply_text("تم حذف صورة ترحيب الجروبات.", reply_markup=admin_keyboard())
            return
        if not message.photo:
            await message.reply_text("أرسل صورة فقط أو اكتب حذف.")
            return
        DB["settings"]["group_welcome_photo"] = message.photo[-1].file_id
        save_db(DB)
        context.user_data.pop("admin_state", None)
        await message.reply_text("تم حفظ صورة ترحيب الجروبات.", reply_markup=admin_keyboard())
        return

    if state == "cancel_subscription":
        target = (message.text or "").strip()
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
            await message.reply_text("لم أجد الشخص في قاعدة البيانات.")
            return
        target_record["subscription_until"] = 0
        target_record["is_subscribed"] = False
        target_record["payment_charge_id"] = ""
        save_db(DB)
        context.user_data.pop("admin_state", None)
        await message.reply_text("تم إلغاء اشتراك VIP للشخص.", reply_markup=admin_keyboard())
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
            await message.reply_text("تم حذف الإيموجي من الزر.", reply_markup=category_admin_keyboard(category_id))
            return

        emoji_value = (message.text or "").strip()
        if not emoji_value:
            await message.reply_text("ابعت إيموجي حقيقي واحد، زي ⭐ أو 🔥 أو 🎬.")
            return

        # حفظ إيموجي Unicode حقيقي بدل أي Custom Emoji ID.
        category["style"]["emoji_id"] = emoji_value
        save_db(DB)
        context.user_data.pop("admin_state", None)
        context.user_data.pop("admin_category_id", None)
        await message.reply_text("تم حفظ الإيموجي الحقيقي للزر.", reply_markup=category_admin_keyboard(category_id))
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
        DB.setdefault("settings", {})["vip_stars"] = new_price
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

    if state == "all_videos_url":
        if not message.text:
            await message.reply_text("أرسل رابطًا صحيحًا يبدأ بـ https://")
            return
        url = message.text.strip()
        if not (url.startswith("https://") or url.startswith("http://") or url.startswith("tg://")):
            await message.reply_text("الرابط يجب أن يبدأ بـ https:// أو http:// أو tg://")
            return
        DB.setdefault("settings", {})["all_videos_url"] = url
        save_db(DB)
        context.user_data.pop("admin_state", None)
        await message.reply_text("تم تغيير رابط جميع الفيديوهات.", reply_markup=admin_keyboard())
        return

    if state == "restore_members":
        if not (message.document and message.document.file_name.lower().endswith(".json")):
            await message.reply_text("أرسل ملف JSON فقط.")
            return
        try:
            tg_file = await message.document.get_file()
            temp_path = Path("members_restore_temp.json")
            await tg_file.download_to_drive(custom_path=str(temp_path))
            data = json.loads(temp_path.read_text(encoding="utf-8"))
            users = data.get("users", data) if isinstance(data, dict) else {}
            if not isinstance(users, dict):
                raise ValueError("users must be an object")
            restored = 0
            for uid, record in users.items():
                if not isinstance(record, dict):
                    continue
                rid = str(record.get("id", uid))
                if not rid.isdigit():
                    continue
                DB["users"][rid] = record
                restored += 1
            save_db(DB)
            context.user_data.pop("admin_state", None)
            await message.reply_text(f"تم استرجاع {restored} عضو بنجاح.", reply_markup=admin_keyboard())
        except Exception as exc:
            logger.exception("Members restore failed: %s", exc)
            await message.reply_text("فشل استرجاع الملف. تأكد أنه ملف JSON صادر من زر التصدير.", reply_markup=admin_keyboard())
        finally:
            try:
                temp_path.unlink()
            except Exception:
                pass
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

    await send_home(update, context)


def resolve_target_user(message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2:
        return None
    target = raw[1].strip()
    if target.isdigit():
        return int(target)
    username = target.lstrip("@").lower()
    for rec in DB.get("users", {}).values():
        if str(rec.get("username", "")).lstrip("@").lower() == username:
            return int(rec.get("id"))
    return None


async def group_member_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    message, chat, actor = update.effective_message, update.effective_chat, update.effective_user
    if not message or not chat or chat.type not in ("group", "supergroup") or not actor:
        return
    try:
        me = await context.bot.get_chat_member(chat.id, actor.id)
        if me.status not in ("administrator", "creator"):
            await message.reply_text("الأمر للمشرفين فقط.")
            return
    except Exception:
        return
    target = resolve_target_user(message)
    if not target:
        await message.reply_text("استخدم الأمر بالرد على الشخص أو أرسل ID أو @username.")
        return
    target_id = target.id if hasattr(target, "id") else int(target)
    try:
        if action == "delete":
            if message.reply_to_message:
                await message.reply_to_message.delete()
            await message.reply_text("تم حذف الرسالة.")
        elif action == "kick":
            await context.bot.ban_chat_member(chat.id, target_id)
            await context.bot.unban_chat_member(chat.id, target_id, only_if_banned=True)
            await message.reply_text("تم طرد الشخص.")
        elif action == "ban":
            await context.bot.ban_chat_member(chat.id, target_id)
            await message.reply_text("تم حظر الشخص.")
        elif action == "mute":
            await context.bot.restrict_chat_member(chat.id, target_id, permissions=__import__('telegram').ChatPermissions(can_send_messages=False), until_date=int(time.time())+3600)
            await message.reply_text("تم كتم الشخص لمدة ساعة.")
        elif action == "clear":
            if message.reply_to_message:
                await message.reply_to_message.delete()
            await message.delete()
        elif action == "info":
            await group_info_command(update, context)
    except Exception as exc:
        await message.reply_text(f"تعذر تنفيذ الأمر: {exc}")


async def group_welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ترحيب موثوق بالجروبات باستخدام تحديث العضوية، مع دعم الطريقة القديمة أيضًا."""
    message = update.effective_message
    chat_member_update = getattr(update, "chat_member", None)
    chat = getattr(chat_member_update, "chat", None) if chat_member_update else getattr(message, "chat", None)

    if not chat or chat.type not in ("group", "supergroup"):
        return

    if chat_member_update:
        old_status = getattr(chat_member_update.old_chat_member, "status", None)
        new_status = getattr(chat_member_update.new_chat_member, "status", None)
        if old_status not in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED) or new_status not in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED):
            return
        member = chat_member_update.new_chat_member.user
        members = [member] if member and not member.is_bot else []
    else:
        members = list(getattr(message, "new_chat_members", None) or []) if message else []

    if not members:
        return

    st = group_settings(chat.id)
    join_dates = st.setdefault("member_join_dates", {})
    photo = str(DB.get("settings", {}).get("group_welcome_photo", "") or "").strip()
    now = int(time.time())
    joined_date = time.strftime("%Y-%m-%d", time.localtime(now))
    joined_time = time.strftime("%H:%M", time.localtime(now))

    for member in members:
        try:
            join_dates[str(member.id)] = now

            mention = (
                f'<a href="tg://user?id={member.id}">'
                f'{html.escape(member.full_name or "المستخدم")}</a>'
            )
            username = f"@{html.escape(member.username)}" if member.username else "لا يوجد"
            group_name = html.escape(chat.title or "الجروب")

            text = (
                "⁣⁣ᯓ˹𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐆𝐑𝐎𝐔𝐏 ᯤ˼\n"
                f"°•—————— {group_name} —————•°\n"
                f"°︙ نورت قروبنا يـ {mention} 🥂.\n"
                f"°︙ اسمك ⇚『{mention}』\n"
                f"°︙ ايديك ⇚『{member.id}』\n"
                f"°︙ يوزرك ⇚『{username}』\n\n"
                f"> °︙ تاريخ انضمامك ☜ {joined_date}\n"
                f"> °︙ الساعة ☜ {joined_time} .\n\n"
                f"°•—————— {group_name} —————•°"
            )

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(member.full_name or "العضو", url=f"tg://user?id={member.id}")],
                [InlineKeyboardButton("حفلات مشهير •", url="https://t.me/+Ur1mKr-uQio0ZjY8")],
            ])

            sent = False
            if photo:
                try:
                    await message.reply_photo(
                        photo=photo,
                        caption=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard,
                        allow_sending_without_reply=True,
                    )
                    sent = True
                except Exception as photo_exc:
                    # إذا كانت صورة الترحيب القديمة غير صالحة، لا نوقف الترحيب.
                    logger.exception(
                        "Group welcome photo failed in chat %s for user %s: %s",
                        chat.id, member.id, photo_exc
                    )
                    DB["settings"]["group_welcome_photo"] = ""
                    photo = ""

            if not sent:
                await message.reply_text(
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                    allow_sending_without_reply=True,
                )
        except Exception as exc:
            logger.exception(
                "Group welcome failed in chat %s for user %s: %s",
                chat.id, getattr(member, "id", "unknown"), exc
            )

    save_db(DB)


async def group_protection_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or chat.type not in ("group", "supergroup") or not user:
        return
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ("administrator", "creator"):
            await message.reply_text("الأمر للمشرفين فقط.")
            return
    except Exception:
        return

    raw = (message.text or "").strip()
    m = re.match(r"^(قفل|فتح)\s+(.+)$", raw, re.UNICODE)
    if not m:
        return
    action, target = m.group(1), re.sub(r"\s+", " ", m.group(2).strip())
    target_lower = target.lower()

    if target_lower in ("كل شيء", "كلشي", "الكل", "كل", "كل الحاجات"):
        st = group_settings(chat.id)
        enabled = action == "قفل"
        for key in PROTECTION_KEYS:
            st[key] = enabled
        st["all"] = enabled
        save_db(DB)
        lock_text = f"تم {'قفل' if enabled else 'فتح'} كل شيء 🔹"
        await message.reply_text(lock_text)
        return

    key = protection_key_from_text(target)
    if not key:
        await message.reply_text("المحدد غير معروف. مثال: قفل الملصقات أو فتح الروابط")
        return

    if action == "فتح":
        st = group_settings(chat.id)
        st[key] = False
        st.pop(f"penalty_{key}", None)
        st.pop(f"mute_duration_{key}", None)
        st["all"] = all(st.get(k, False) for k in PROTECTION_KEYS)
        save_db(DB)
        lock_text = f"تم فتح {PROTECTION_KEYS[key]} 🔹"
        await message.reply_text(lock_text)
        return

    await message.reply_text(
        f"اختر العقوبة عند قفل {PROTECTION_KEYS[key]}",
        reply_markup=protection_command_text_keyboard(key),
    )


# معرفات الـ Custom Emoji التي أرسلها المستخدم
CUSTOM_EMOJI_LOCK = "🔒"
CUSTOM_EMOJI_PROTECTION = "🛡️"
# الـ Custom Emoji المطلوب في ردود الأشياء المقفولة.
CUSTOM_EMOJI_LOCKED_REPLY = "🔒"


def protection_message_with_emoji(text: str, marker: str, emoji: str) -> tuple[str, list]:
    return text.replace(marker, emoji, 1), []


async def group_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    actor = update.effective_user
    if not message or not chat or chat.type not in ("group", "supergroup") or not actor:
        return
    target = resolve_target_user(message) or actor
    if not target:
        await message.reply_text("استخدم كشف أو ايدي بالرد على الشخص أو اكتب ID أو @username.")
        return
    target_id = target.id if hasattr(target, "id") else int(target)
    try:
        member = await context.bot.get_chat_member(chat.id, target_id)
        target_user = member.user
        status = member.status
    except Exception:
        target_user = target if hasattr(target, "id") else None
        status = "unknown"
        if target_user is None:
            await message.reply_text("لم أستطع العثور على الشخص داخل الجروب.")
            return

    username = f"@{target_user.username}" if target_user.username else "لا يوجد"
    bio = "لا يوجد"
    try:
        profile = await context.bot.get_chat(target_id)
        bio = getattr(profile, "bio", None) or "لا يوجد"
    except Exception:
        pass

    role_map = {
        "creator": "المالك",
        "administrator": "مشرف",
        "member": "عضو",
        "restricted": "مقيد",
        "left": "غادر",
        "kicked": "محظور",
    }
    role = role_map.get(str(status), str(status))
    st = group_settings(chat.id)
    message_count = int(st.get("message_counts", {}).get(str(target_id), 0))
    joined_at = st.get("member_join_dates", {}).get(str(target_id))
    if joined_at:
        joined_date = time.strftime("%Y-%m-%d", time.localtime(joined_at))
    else:
        joined_date = "غير معروف"
    now = time.localtime()
    current_time = time.strftime("%H:%M", now)
    likes = int(st.setdefault("likes", {}).get(str(target_id), 0))
    mention = f'<a href="tg://user?id={target_id}">{target_user.full_name}</a>'
    text = (
        f"كشف الشخص\n\n"
        f"اسم ⇚ {mention}\n"
        f"يوزر ⇚ {username}\n"
        f"ايدي ⇚ {target_id}\n"
        f"بايو ⇚ {bio}\n"
        f"عدد رسالة ⇚ {message_count}\n"
        f"رتبه ⇚ {role}\n"
        f"الساعة ⇚ {current_time}\n"
        f"تاريخ الانضمام ⇚ {joined_date}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"❤ {likes}", callback_data=f"profile_like:{chat.id}:{target_id}")]
    ])
    try:
        photos = await context.bot.get_user_profile_photos(target_id, limit=1)
        if photos.total_count and photos.photos:
            await context.bot.send_photo(
                chat.id,
                photo=photos.photos[0][-1].file_id,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        else:
            await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception:
        await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def protection_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or chat.type not in ("group", "supergroup") or not user:
        return
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ("administrator", "creator"):
            await update.effective_message.reply_text("الأمر للمشرفين فقط.")
            return
    except Exception:
        await update.effective_message.reply_text("تعذر التحقق من صلاحياتك.")
        return
    await update.effective_message.reply_text("إعدادات حماية الجروب", reply_markup=protection_keyboard(chat.id))


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
        # / يظهر Start للجميع، وAdmin يظهر فقط للمالك والأدمن المسجلين.
        await application.bot.set_my_commands(
            [BotCommand("start", "بدء البوت")],
            scope=BotCommandScopeDefault(),
        )
        for admin_id in DB.get("admins", []):
            try:
                await application.bot.set_my_commands(
                    [BotCommand("start", "بدء البوت"), BotCommand("admin", "لوحة الأدمن")],
                    scope=BotCommandScopeChat(chat_id=int(admin_id)),
                )
            except Exception as exc:
                logger.warning("Could not set admin commands for %s: %s", admin_id, exc)
    except Exception:
        logger.exception("Could not fetch bot info or set commands.")


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

    # حماية الجروبات قبل الردود التلقائية
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL,
            group_protection_handler,
        ),
        group=-2,
    )

    # أوامر القفل/الفتح تعمل كنص عادي بدون /
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.Regex(r"^\s*(?:قفل|فتح)\s+.+$"),
        group_protection_text_command,
    ))

    # أوامر الجروبات تعمل كنص عادي بدون /
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.Regex(r"^\s*حماية\s*$"),
        protection_command,
    ))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.Regex(r"^\s*كتم(?:\s+.*)?$"),
        lambda u,c: group_member_action(u,c,"mute"),
    ))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.Regex(r"^\s*طرد(?:\s+.*)?$"),
        lambda u,c: group_member_action(u,c,"kick"),
    ))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.Regex(r"^\s*حظر(?:\s+.*)?$"),
        lambda u,c: group_member_action(u,c,"ban"),
    ))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.Regex(r"^\s*حذف(?:\s+.*)?$"),
        lambda u,c: group_member_action(u,c,"delete"),
    ))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.Regex(r"^\s*مسح(?:\s+.*)?$"),
        lambda u,c: group_member_action(u,c,"clear"),
    ))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.Regex(r"^\s*(?:كشف|ايدي|ا|معلومات)(?:\s+.*)?$"),
        group_info_command,
    ))
    # ترحيب الجروبات: يعتمد على تحديث العضوية نفسه، لذلك يعمل حتى لو لم تصل رسالة خدمة الدخول.
    application.add_handler(
        ChatMemberHandler(group_welcome_handler, ChatMemberHandler.CHAT_MEMBER),
        group=-100,
    )

    # معالج الجروبات — الردود التلقائية
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
