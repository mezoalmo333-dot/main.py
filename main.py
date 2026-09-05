import os
import re
import json
import html
import asyncio
import logging
import subprocess
import sys
import importlib
import shutil
from tempfile import gettempdir
from datetime import datetime

import yt_dlp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.constants import ChatMemberStatus

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============================================================
# إعدادات البوت
# ============================================================

# إعدادات Railway: ضع القيم في Variables ولا تضع التوكن داخل الملف
BOT_TOKEN = os.getenv("BOT_TOKEN", "8878742478:AAF-h5bIAg_OwXQQXc89ipw37Z4yRKKvxV4").strip()

# اختياري: يمكن تغيير آيدي الأدمن من Railway Variables
ADMIN_ID = int(os.getenv("ADMIN_ID", "8037399518").strip())

# ============================================================
# قاعدة البيانات
# ============================================================

# ============================================================
# تخزين قاعدة البيانات بشكل دائم
# ============================================================
# على Railway يجب استخدام Volume حتى تبقى قاعدة البيانات بعد Redeploy.
# إذا كان RAILWAY_VOLUME_MOUNT_PATH موجوداً فسيتم استخدامه تلقائياً.
# ويمكن أيضاً تحديد DATA_DIR يدوياً.
_LEGACY_DB_FILE = os.path.join(
    gettempdir(),
    "social_downloader_bot_db.json"
)

_CONFIGURED_DATA_DIR = (
    os.getenv("DATA_DIR", "").strip()
    or os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
)

if _CONFIGURED_DATA_DIR:
    DATA_DIR = _CONFIGURED_DATA_DIR
else:
    # Railway Volume غالباً يكون mounted على /data. استخدامه تلقائياً
    # يمنع تصفير قاعدة الأعضاء عند Redeploy إذا كان الـ Volume موجوداً.
    if os.path.isdir("/data"):
        _local_data_dir = "/data"
    else:
        _local_data_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "bot_data"
        )
    try:
        os.makedirs(_local_data_dir, exist_ok=True)
        DATA_DIR = _local_data_dir
    except Exception:
        DATA_DIR = gettempdir()

try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    DATA_DIR = gettempdir()

DB_FILE = os.path.join(
    DATA_DIR,
    "social_downloader_bot_db.json"
)

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = (
    MAX_FILE_SIZE_MB * 1024 * 1024
)

# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# ============================================================
# Custom Emoji
# ============================================================

EMOJI_1 = '<tg-emoji emoji-id="5782850920610013789">✨</tg-emoji>'
EMOJI_2 = '<tg-emoji emoji-id="5890969691425347748">⚡</tg-emoji>'
EMOJI_3 = '<tg-emoji emoji-id="5890795783904565270">🔥</tg-emoji>'
EMOJI_4 = '<tg-emoji emoji-id="5782815375460671828">💎</tg-emoji>'
EMOJI_5 = '<tg-emoji emoji-id="5767120181981617136">👑</tg-emoji>'
EMOJI_6 = '<tg-emoji emoji-id="5891000366081775168">🚀</tg-emoji>'
EMOJI_7 = '<tg-emoji emoji-id="5462989862669920629">💫</tg-emoji>'
EMOJI_8 = '<tg-emoji emoji-id="5462919317832082236">⭐</tg-emoji>'
EMOJI_9 = '<tg-emoji emoji-id="5767199471372867777">🎯</tg-emoji>'

CUSTOM_EMOJI_IDS = [
    "5782850920610013789",
    "5890969691425347748",
    "5890795783904565270",
    "5782815375460671828",
    "5767120181981617136",
    "5891000366081775168",
    "5462989862669920629",
    "5462919317832082236",
    "5767199471372867777",
]

# ============================================================
# إيموجيات Telegram القديمة المستخدمة في الصفحة الرئيسية
# ============================================================

EMOJI_VIDEO = (
    '<tg-emoji emoji-id="5891223481042868350">🎬</tg-emoji>'
)

EMOJI_PIN = (
    '<tg-emoji emoji-id="5775968415906798325">📌</tg-emoji>'
)

EMOJI_POWER = (
    '<tg-emoji emoji-id="5875500121168288239">⚡</tg-emoji>'
)

EMOJI_OK = (
    '<tg-emoji emoji-id="6001388309853510348">✅</tg-emoji>'
)

EMOJI_STAR = (
    '<tg-emoji emoji-id="5967427591127176971">⭐</tg-emoji>'
)

EMOJI_SPARK = (
    '<tg-emoji emoji-id="5967507756691757055">✨</tg-emoji>'
)

EMOJI_HEART = (
    '<tg-emoji emoji-id="5891042564135459844">❤</tg-emoji>'
)

EMOJI_DOWNLOAD = (
    '<tg-emoji emoji-id="5967520637298677106">📥</tg-emoji>'
)

# ============================================================
# الإيموجيات المميزة الخاصة بالبوت فقط
# ============================================================

BOT_CUSTOM_EMOJI_IDS = [
    "5888663955412359816",
    "5891075716988016811",
    "5890866066749397234",
    "5463200135678796607",
    "5463386283856373524",
    "5462987027991503774",
    "5962888055508441682",
    "5962858574852921606",
    "5963161271263041568",
]

# ============================================================
# مكتبة الإيموجيات التي طلبها المالك
# ============================================================
# هذه الـ IDs محفوظة للاختيار اليدوي من إعدادات الأزرار فقط.
# لا يتم وضعها تلقائياً في أي كليشة أو زر.
AVAILABLE_CUSTOM_EMOJI_IDS = [
    "5890978075201509010",
    "5890941464900278076",
    "5891033729387731017",
    "5890968106582415352",
    "5891007396943239324",
    "5888585378985678792",
    "5891264747088647482",
    "5891008659663624406",
    "5891150947635173714",
    "5888979137292408953",
    "5890944978183528164",
    "5891198458563402576",
    "5891223481042868350",
    "5888585967396198556",
    "5888925871108003433",
    "5888675006363211723",
    "5890730440272123773",
    "5890960431475857412",
    "5888684446701328138",
    "5890755394032113567",
    "5888769147751373843",
    "5890711263243147926",
    "5891235511246264255",
    "5888630540566796058",
    "5891061762639271906",
    "5890946721940248671",
    "5890989903541441900",
    "5891071937416795775",
    "5891162831809681617",
    "5891131044756723016",
    "5890866066749397234",
    "5891075227361746243",
    "5891182846357281226",
    "5891000366081775168",
    "5890933368886924480",
    "5888604607554262373",
    "5891225499677496831",
    "5890723834612422946",
    "5890969691425347748",
    "5890795783904565270",
    "5890891742063893790",
    "5891011391262824495",
    "5888903253810222656",
    "5890932136231311080",
    "5890819530778744606",
    "5891075716988016811",
    "5888855708522255593",
    "5890808771885668859",
    "5888663955412359816",
    "5890864005165096780",
    "5269682734820777950",
    "5116562499268773081",
    "5118715849842099559",
    "5118886415878325117",
    "5116425257883796621",
    "5116402533211833262",
    "5116503323209368474",
    "5118372789329331110",
    "5116089640549353169",
    "5118482319585313697",
    "5118625354881172381",
    "5118775829060387648",
    "5116184812729664572",
    "5139127540182418615",
    "5136909176689135635",
    "5136767455653266361",
    "5136607107344237807",
    "5138871938088699109",
    "5138716924129051781",
    "5139039647971672860",
    "5136425078040298524",
    "5139059555145090612",
    "5139095048754824143",
    "5136592598944712102",
    "5136494497596703715",
    "5136445187077178529",
    "5136567232867861772",
    "5136707747017917294",
    "5136867713074857101",
    "5136791726513456009",
    "5136688518449333393",
    "5136444126220256119",
    "5136370613560017995",
    "5136419571892225335",
    "5136697855708234673",
    "5136382085417665757",
    "5136828508613379215",
    "5136634337436894358",
    "5138796703146574994",
    "5138693920284214322",
    "5136559729559995450",
    "5136720309797258447",
    "5138636341952644876",
    "5136686151922353153",
    "5138747345382409039",
    "5136486770950538427",
    "5136412120123966300",
    "5136758303077958598",
    "5139029962820420604",
    "5136448318108337067",
    "5139077469453681422",
]

# ============================================================
# Premium Emoji داخل كليشات الرسائل
# ============================================================
# طريقة الاستخدام من لوحة "تخصيص رسائل البوت":
#   [emoji:5462943653116792628]
# أو:
#   {emoji:5462943653116792628}
#
# يمكن وضع أكثر من Premium Emoji في نفس الكليشة.
# لا يتم وضع أي Emoji تلقائياً؛ يظهر فقط عندما يكتب الأدمن الـ ID
# داخل الكليشة بهذه الصيغة.
MESSAGE_CUSTOM_EMOJI_IDS = [
    "5462943653116792628",
    "5271929483752930708",
    "5271679851663750608",
    "5854789277765866801",
    "5253561965917266807",
]

# ============================================================
# قنوات الاشتراك الإجباري الافتراضية
# ============================================================

DEFAULT_FORCE_SUB_CHANNELS = [
    {
        "channel": "@kon_ze_athar",
        "link": "https://t.me/kon_ze_athar"
    },
    {
        "channel": "@w_x_x",
        "link": "https://t.me/w_x_x"
    },
]

# ============================================================
# قاعدة البيانات الافتراضية
# ============================================================

DEFAULT_DB = {
    "users": {},
    "settings": {
        "force_sub_enabled": True,
        "force_sub_channel": "@kon_ze_athar",
        "force_sub_link": "https://t.me/kon_ze_athar",
        "force_sub_channels": DEFAULT_FORCE_SUB_CHANNELS,
        "welcome_text": "",
        "download_text": (
            "⏳ جاري تحميل الفيديو، يرجى الانتظار..."
        ),
        "welcome_media_type": "",
        "welcome_media_id": "",
        "welcome_media_caption": "",
        # إعدادات أسماء وأيقونات الأزرار قابلة للتعديل من لوحة الأدمن.
        "button_settings": {},
        "message_settings": {},
    },
    "banned_users": [],
    "admins": []
}

# ============================================================
# تحميل قاعدة البيانات
# ============================================================

def _db_candidate_files():
    """Return every reasonable database location, newest first."""
    candidates = []
    explicit = os.getenv("DB_FILE", "").strip()
    if explicit:
        candidates.append(explicit)

    dirs = []
    if _CONFIGURED_DATA_DIR:
        dirs.append(_CONFIGURED_DATA_DIR)
    if os.path.isdir("/data"):
        dirs.append("/data")
    dirs.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data"))
    dirs.append(gettempdir())

    for directory in dirs:
        candidates.append(os.path.join(directory, "social_downloader_bot_db.json"))
        candidates.append(os.path.join(directory, "social_downloader_bot_db.json.bak"))
        candidates.append(os.path.join(directory, "social_downloader_bot_db.json.bak.1"))
        candidates.append(os.path.join(directory, "social_downloader_bot_db.json.bak.2"))
        candidates.append(os.path.join(directory, "social_downloader_bot_db.json.bak.3"))
        candidates.append(os.path.join(directory, "social_downloader_bot_db.json.bak.4"))
        candidates.append(os.path.join(directory, "social_downloader_bot_db.json.bak.5"))

    candidates.append(_LEGACY_DB_FILE)
    candidates.append(_LEGACY_DB_FILE + ".bak")

    unique = []
    seen = set()
    for item in candidates:
        item = os.path.abspath(item)
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _normalize_db(data):
    if not isinstance(data, dict):
        data = {}

    if not isinstance(data.get("users"), dict):
        data["users"] = {}
    if not isinstance(data.get("settings"), dict):
        data["settings"] = {}
    if not isinstance(data.get("banned_users"), list):
        data["banned_users"] = []
    if not isinstance(data.get("admins"), list):
        data["admins"] = []

    data["settings"].setdefault("button_settings", {})
    if not isinstance(data["settings"].get("button_settings"), dict):
        data["settings"]["button_settings"] = {}
    data["settings"].setdefault("message_settings", {})
    if not isinstance(data["settings"].get("message_settings"), dict):
        data["settings"]["message_settings"] = {}

    for key, value in DEFAULT_DB["settings"].items():
        if key not in data["settings"]:
            data["settings"][key] = json.loads(json.dumps(value, ensure_ascii=False))

    normalized_admins = []
    for admin_id in data["admins"]:
        try:
            admin_id = int(admin_id)
            if admin_id != int(ADMIN_ID) and admin_id not in normalized_admins:
                normalized_admins.append(admin_id)
        except (TypeError, ValueError):
            pass
    data["admins"] = normalized_admins

    channels = data["settings"].get("force_sub_channels")
    if not isinstance(channels, list):
        channels = []

    normalized_channels = []
    for item in channels:
        if isinstance(item, dict):
            channel = str(item.get("channel", "")).strip()
            link = str(item.get("link", "")).strip()
            if channel:
                if not link and channel.startswith("@"):
                    link = "https://t.me/" + channel[1:]
                normalized_channels.append({"channel": channel, "link": link})
        elif isinstance(item, str):
            channel = item.strip()
            if channel:
                if not channel.startswith("@"):
                    channel = "@" + channel
                normalized_channels.append({
                    "channel": channel,
                    "link": "https://t.me/" + channel[1:]
                })

    # Only use defaults when the database genuinely has no channel configuration.
    if not normalized_channels:
        old_channel = str(data["settings"].get("force_sub_channel", "")).strip()
        old_link = str(data["settings"].get("force_sub_link", "")).strip()
        if old_channel:
            normalized_channels = [{"channel": old_channel, "link": old_link}]
        elif old_link:
            match = re.search(r"t\.me/([A-Za-z0-9_]+)", old_link)
            if match:
                normalized_channels = [{"channel": "@" + match.group(1), "link": old_link}]

    if normalized_channels:
        data["settings"]["force_sub_channels"] = normalized_channels
        data["settings"]["force_sub_channel"] = normalized_channels[0]["channel"]
        data["settings"]["force_sub_link"] = normalized_channels[0]["link"]
    else:
        data["settings"]["force_sub_channels"] = []

    # Preserve old user records exactly; only fill missing harmless fields.
    for uid, user_data in list(data["users"].items()):
        if not isinstance(user_data, dict):
            continue
        user_data.setdefault("id", int(uid) if str(uid).lstrip("-").isdigit() else uid)
        user_data.setdefault("first_name", "")
        user_data.setdefault("username", "")
        user_data.setdefault("joined_at", "")
        user_data.setdefault("downloads", 0)
        user_data.setdefault("welcome_message_sent", False)

    return data


def load_db():
    """Load the oldest valid database we can find without ever replacing it with an empty DB."""
    candidates = _db_candidate_files()
    valid = []

    for path in candidates:
        try:
            if not os.path.isfile(path) or os.path.getsize(path) < 2:
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("users", {}), dict):
                valid.append((len(data.get("users", {})), os.path.getmtime(path), path, data))
        except Exception as e:
            logger.warning("Ignoring invalid database candidate %s: %s", path, e)

    if valid:
        # Prefer the database containing the most users. This is important when a
        # new deploy created an empty file while an older backup still exists.
        valid.sort(key=lambda x: (x[0], x[1]), reverse=True)
        user_count, _, source_path, data = valid[0]
        data = _normalize_db(data)
        logger.info("Database loaded from %s | users=%s", source_path, user_count)

        # If the selected file is a backup/legacy file, restore it to the active path.
        try:
            os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
            if os.path.abspath(source_path) != os.path.abspath(DB_FILE):
                shutil.copy2(source_path, DB_FILE)
                logger.info("Recovered database to %s", DB_FILE)
        except Exception as restore_error:
            logger.warning("Could not restore recovered database: %s", restore_error)
        return data

    data = _normalize_db(json.loads(json.dumps(DEFAULT_DB, ensure_ascii=False)))
    save_db(data, create_backup=False)
    logger.warning("No valid database found. A new database was created at %s", DB_FILE)
    return data


def save_db(data, create_backup=True):
    """
    Save the database atomically and keep several rolling backups.

    The important rule here is that a healthy database is never replaced by
    an empty/corrupt file.  Before replacing the live file, the previous
    version is rotated through .bak, .bak.1 ... .bak.5.
    """
    try:
        if not isinstance(data, dict) or not isinstance(data.get("users", {}), dict):
            logger.error("Refusing to save invalid database structure.")
            return False

        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        temp_file = DB_FILE + ".tmp"
        backup_file = DB_FILE + ".bak"

        # Never overwrite a populated live database with an empty one.
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as current_file:
                    current_data = json.load(current_file)
                current_users = current_data.get("users", {}) if isinstance(current_data, dict) else {}
                new_users = data.get("users", {})
                if isinstance(current_users, dict) and isinstance(new_users, dict):
                    if len(current_users) > 0 and len(new_users) == 0:
                        logger.error(
                            "Refusing to overwrite populated database (%s users) with an empty database.",
                            len(current_users)
                        )
                        return False
            except Exception as validation_error:
                # The live file is invalid; backups remain the recovery source.
                logger.warning("Could not validate current database before save: %s", validation_error)

        # Write and validate the new file before it becomes live.
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass

        with open(temp_file, "r", encoding="utf-8") as verify_file:
            verified = json.load(verify_file)
        if not isinstance(verified, dict) or not isinstance(verified.get("users", {}), dict):
            raise ValueError("Temporary database validation failed")

        if os.path.exists(DB_FILE) and create_backup:
            try:
                # Rotate older backups first.
                for index in range(5, 0, -1):
                    src = DB_FILE + (".bak" if index == 1 else f".bak.{index-1}")
                    dst = DB_FILE + f".bak.{index}"
                    if os.path.exists(src):
                        try:
                            os.replace(src, dst)
                        except OSError:
                            pass

                shutil.copy2(DB_FILE, backup_file)
            except Exception as backup_error:
                logger.warning("Database backup rotation failed: %s", backup_error)

        os.replace(temp_file, DB_FILE)
        return True

    except Exception as e:
        logger.exception("Database save error: %s", e)
        try:
            if os.path.exists(DB_FILE + ".tmp"):
                os.remove(DB_FILE + ".tmp")
        except OSError:
            pass
        return False

db = load_db()

# ============================================================
# فحص التخزين الدائم عند بدء التشغيل
# ============================================================
# لا يمكن لأي كود استرجاع أعضاء تم حذف بياناتهم نهائياً من Railway،
# لذلك نوضح حالة التخزين في السجل ونحذر إذا لم يوجد /data أو DATA_DIR.
try:
    _persistent_path = os.path.abspath(DATA_DIR)
    _is_data_volume = _persistent_path == os.path.abspath("/data") or bool(_CONFIGURED_DATA_DIR)
    logger.info(
        "Database path: %s | users: %s | persistent-volume-configured: %s",
        DB_FILE,
        len(db.get("users", {})),
        _is_data_volume
    )
    if not _is_data_volume and os.getenv("RAILWAY_ENVIRONMENT", "").strip():
        logger.warning(
            "Railway detected without an explicit persistent volume. "
            "Attach a Railway Volume mounted at /data to preserve users across redeploys."
        )
except Exception:
    pass

# ============================================================
# تحسينات الأداء - Caches
# ============================================================
_FORCE_CHAT_ID_CACHE = {}
_ADMIN_ID_SET = set()
_BANNED_ID_SET = set()


def _refresh_fast_caches():
    global _ADMIN_ID_SET, _BANNED_ID_SET

    try:
        _ADMIN_ID_SET = {int(ADMIN_ID)}
        _ADMIN_ID_SET.update(
            int(x) for x in db.get("admins", [])
            if str(x).strip().lstrip("-").isdigit()
        )
    except Exception:
        _ADMIN_ID_SET = {int(ADMIN_ID)}

    try:
        _BANNED_ID_SET = {
            int(x) for x in db.get("banned_users", [])
            if str(x).strip().lstrip("-").isdigit()
        }
    except Exception:
        _BANNED_ID_SET = set()


_refresh_fast_caches()

# ============================================================
# أدوات قنوات الاشتراك الإجباري
# ============================================================

def get_force_channels():
    channels = db["settings"].get(
        "force_sub_channels",
        []
    )

    if not isinstance(channels, list):
        channels = []

    result = []

    for item in channels:
        if not isinstance(item, dict):
            continue

        channel = str(
            item.get("channel", "")
        ).strip()

        link = str(
            item.get("link", "")
        ).strip()

        if channel:
            result.append({
                "channel": channel,
                "link": link
            })

    return result


def save_force_channels(channels):
    normalized = []

    for item in channels:
        if not isinstance(item, dict):
            continue

        channel = str(
            item.get("channel", "")
        ).strip()

        link = str(
            item.get("link", "")
        ).strip()

        if not channel:
            continue

        if not link:
            if channel.startswith("@"):
                link = "https://t.me/" + channel[1:]

        normalized.append({
            "channel": channel,
            "link": link
        })

    db["settings"][
        "force_sub_channels"
    ] = normalized

    # توافق مع النسخة القديمة
    if normalized:
        db["settings"][
            "force_sub_channel"
        ] = normalized[0]["channel"]

        db["settings"][
            "force_sub_link"
        ] = normalized[0]["link"]

    else:
        db["settings"][
            "force_sub_channel"
        ] = ""

        db["settings"][
            "force_sub_link"
        ] = ""

    save_db(db)


def add_force_channel(channel, link=""):
    channel = channel.strip()
    link = link.strip()

    if not link and channel.startswith("@"):
        link = "https://t.me/" + channel[1:]

    channels = get_force_channels()

    for item in channels:
        if item["channel"].lower() == channel.lower():
            item["link"] = link or item.get("link", "")
            save_force_channels(channels)
            _FORCE_CHAT_ID_CACHE.pop(channel.lower(), None)
            return False

    channels.append({
        "channel": channel,
        "link": link
    })

    save_force_channels(channels)
    return True


def remove_force_channel(index):
    channels = get_force_channels()

    if index < 0 or index >= len(channels):
        return False

    channels.pop(index)
    save_force_channels(channels)
    _FORCE_CHAT_ID_CACHE.clear()
    return True


# ============================================================
# تحديث yt-dlp تلقائياً لحل تغييرات TikTok
# ============================================================

def update_yt_dlp():
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-warn-script-location",
                "--upgrade",
                "yt-dlp",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=120,
        )
        importlib.reload(yt_dlp)
        logger.info("yt-dlp updated successfully")
    except Exception as e:
        logger.warning("yt-dlp update skipped: %s", e)


def update_yt_dlp_tiktok_fallback():
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-warn-script-location",
                "--upgrade",
                "https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.zip",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=180,
        )

        if result.returncode != 0:
            return False

        importlib.reload(yt_dlp)
        logger.info("yt-dlp TikTok fallback updated successfully")
        return True

    except Exception as e:
        logger.warning("yt-dlp TikTok fallback update failed: %s", e)
        return False


# ============================================================
# أدوات عامة
# ============================================================

def is_admin(user_id: int) -> bool:
    try:
        return int(user_id) in _ADMIN_ID_SET
    except (TypeError, ValueError):
        return False


def get_admins() -> list:
    try:
        return [
            int(x)
            for x in db.get("admins", [])
            if int(x) != int(ADMIN_ID)
        ]
    except Exception:
        return []


def is_banned(user_id: int) -> bool:
    try:
        return int(user_id) in _BANNED_ID_SET
    except (TypeError, ValueError):
        return False


def add_user(user):
    if not user:
        return

    user_id = str(user.id)
    first_name = user.first_name or ""
    username = user.username or ""
    existing = db["users"].get(user_id)

    if existing is None:
        db["users"][user_id] = {
            "id": user.id,
            "first_name": first_name,
            "username": username,
            "joined_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "downloads": 0,
            "welcome_message_sent": False,
        }
        save_db(db)
        return

    changed = (
        existing.get("first_name", "") != first_name
        or existing.get("username", "") != username
    )
    if changed:
        existing["first_name"] = first_name
        existing["username"] = username
        save_db(db)


def get_user_count():
    return len(
        db.get(
            "users",
            {}
        )
    )


def get_download_count():
    total = 0

    for user in db.get(
        "users",
        {}
    ).values():

        try:
            total += int(
                user.get(
                    "downloads",
                    0
                )
            )
        except Exception:
            pass

    return total


def increment_download(user_id):
    user_id = str(user_id)

    if user_id in db["users"]:
        current = db["users"][user_id].get(
            "downloads",
            0
        )

        try:
            current = int(current)
        except Exception:
            current = 0

        db["users"][user_id][
            "downloads"
        ] = current + 1

        save_db(db)


# ============================================================
# حماية نص الترحيب من أخطاء format
# ============================================================

class SafeFormatDict(dict):

    def __missing__(self, key):
        return "{" + key + "}"


_CUSTOM_EMOJI_TOKEN_RE = re.compile(
    r"(?:\[emoji:(\d+)\]|\{emoji:(\d+)\})",
    re.IGNORECASE
)

# الصيغة المختصرة للكليشات: النص|Premium_Emoji_ID
_CUSTOM_EMOJI_PIPE_RE = re.compile(
    r"([^|\n]+?)\|(\d{5,30})(?=\s|$)",
    re.UNICODE
)


def _render_custom_emoji_markup(text):
    """
    يحول الصيغة:
        [emoji:123456789]
    أو:
        {emoji:123456789}
    إلى Telegram HTML:
        <tg-emoji emoji-id="123456789">⭐</tg-emoji>

    لا يضيف أي Premium Emoji من تلقاء نفسه.
    """
    if text is None:
        return ""

    value = str(text)

    def repl(match):
        emoji_id = match.group(1) or match.group(2)
        if not emoji_id or not emoji_id.isdigit():
            return match.group(0)
        return f'<tg-emoji emoji-id="{emoji_id}">⭐</tg-emoji>'

    # الصيغ القديمة: [emoji:ID] و {emoji:ID}
    value = _CUSTOM_EMOJI_TOKEN_RE.sub(repl, value)

    # الصيغة الجديدة المطلوبة: النص|ID
    def pipe_repl(match):
        label = match.group(1).strip()
        emoji_id = match.group(2)
        if not label or not emoji_id.isdigit():
            return match.group(0)
        return f'{label} <tg-emoji emoji-id="{emoji_id}">⭐</tg-emoji>'

    return _CUSTOM_EMOJI_PIPE_RE.sub(pipe_repl, value)


def _protect_custom_emoji_tokens(text):
    """
    يحمي {emoji:ID} من str.format_map حتى لا تعتبره Python
    متغيراً أو format specifier.
    """
    if text is None:
        return ""

    value = str(text)
    saved = {}

    def repl(match):
        token = f"__CUSTOM_EMOJI_TOKEN_{len(saved)}__"
        saved[token] = match.group(0)
        return token

    protected = _CUSTOM_EMOJI_TOKEN_RE.sub(repl, value)
    return protected, saved


def _restore_custom_emoji_tokens(text, saved):
    value = str(text)
    for token, original in saved.items():
        value = value.replace(token, original)
    return value


def format_welcome_text(
    text,
    first_name,
    username,
    user_id
):
    protected, saved = _protect_custom_emoji_tokens(text)

    values = SafeFormatDict({
        "first_name": first_name,
        "username": username,
        "user_id": user_id
    })

    try:
        result = protected.format_map(values)
    except Exception:
        result = protected

    result = _restore_custom_emoji_tokens(result, saved)
    return _replace_plain_emojis(_render_custom_emoji_markup(result))


# ============================================================
# إعدادات أسماء وإيموجيات الأزرار
# ============================================================

BUTTON_DEFAULTS = {
    "platform_tiktok": ("TikTok", "5391044040860906456"),
    "back_home": ("🔙 رجوع", ""),
    "admin_stats": ("📊 الإحصائيات", "5782850920610013789"),
    "admin_broadcast": ("📢 إذاعة", "5890969691425347748"),
    "admin_welcome_photo": ("📸 ترحيب صورة", "5890795783904565270"),
    "admin_welcome_video": ("🎬 ترحيب فيديو", "5782815375460671828"),
    "admin_welcome_text": ("✏️ نص الترحيب", "5767120181981617136"),
    "admin_delete_media": ("🗑 حذف ميديا الترحيب", "5891000366081775168"),
    "admin_force_sub": ("🔐 الاشتراك الإجباري", "5462989862669920629"),
    "admin_download_text": ("📝 رسالة التحميل", "5462919317832082236"),
    "admin_ban": ("🚫 حظر مستخدم", "5767199471372867777"),
    "admin_unban": ("♻️ فك حظر", "5782815375460671828"),
    "admin_admins": ("👑 المشرفون", "5782850920610013789"),
    "admin_users": ("👥 المستخدمون", "5782850920610013789"),
    "admin_panel": ("🔄 تحديث اللوحة", "5890969691425347748"),
    "check_subscription": ("🔄 تحقّق من الاشتراك", "5890969691425347748"),
    "admin_add_admin": ("➕ إضافة مشرف", "5888663955412359816"),
    "admin_remove_admin": ("🗑 حذف مشرف", "5891075716988016811"),
    "force_enable": ("🟢 تفعيل", "5782815375460671828"),
    "force_disable": ("🔴 تعطيل", "5891000366081775168"),
    "force_add_channel": ("➕ إضافة قناة", "5888663955412359816"),
    "force_remove_channel": ("🗑 حذف قناة", "5891075716988016811"),
    "force_list_channels": ("📋 تحديث القنوات", "5890866066749397234"),
}

def get_button_setting(key):
    default_text, default_emoji = BUTTON_DEFAULTS.get(
        key,
        (key, "")
    )
    settings = db.setdefault("settings", {})
    button_settings = settings.setdefault(
        "button_settings",
        {}
    )
    item = button_settings.get(key, {})

    if not isinstance(item, dict):
        item = {}

    return {
        "text": str(item.get("text", default_text)),
        "emoji_id": str(item.get("emoji_id", default_emoji)).strip(),
    }


def button_text(key, fallback=None):
    if fallback is None:
        fallback = BUTTON_DEFAULTS.get(
            key,
            (key, "")
        )[0]

    return get_button_setting(key).get(
        "text",
        fallback
    ) or fallback


def button_emoji(key, fallback=""):
    value = get_button_setting(key).get(
        "emoji_id",
        fallback
    ).strip()

    return value


def set_button_setting(key, text_value, emoji_id=""):
    if key not in BUTTON_DEFAULTS:
        return False

    text_value = str(text_value).strip()
    emoji_id = str(emoji_id).strip()

    if not text_value:
        return False

    if emoji_id and not emoji_id.isdigit():
        return False

    db.setdefault("settings", {}).setdefault(
        "button_settings",
        {}
    )[key] = {
        "text": text_value,
        "emoji_id": emoji_id,
    }

    save_db(db)
    return True


def reset_button_setting(key):
    if key in db.get("settings", {}).get(
        "button_settings",
        {}
    ):
        db["settings"]["button_settings"].pop(
            key,
            None
        )
        save_db(db)
    return True


# ============================================================
# إعدادات رسائل البوت القابلة للتعديل من لوحة الأدمن
# ============================================================

MESSAGE_DEFAULTS = {
    "home": "",
    "new_user_welcome": "",
    "platform_tiktok": "تم اختيار TikTok\n\nالرجاء إرسال رابط الفيديو:",
    "download_status": "⏳ جاري تحميل الفيديو، يرجى الانتظار...",
    "sending_status": "🚀 جاري إرسال الفيديو...",
    "success": "✅ تم تحميل الفيديو بنجاح\n\nالمصدر: {platform}",
    "download_error": "❌ فشل تحميل الفيديو\n\n{error}",
    "help": "طريقة استخدام البوت\n\n1️⃣ اضغط /start\n2️⃣ اختر TikTok\n3️⃣ أرسل رابط الفيديو\n4️⃣ انتظر حتى يكتمل التحميل\n\nالتحميل يتم تلقائياً.",
    "force_sub": "يجب عليك الاشتراك في جميع القنوات المطلوبة أولاً.",
    "force_sub_done": "بعد الاشتراك اضغط على زر التحقق.",
}


def get_message_setting(key, fallback=None):
    if fallback is None:
        fallback = MESSAGE_DEFAULTS.get(key, "")
    settings = db.setdefault("settings", {})
    values = settings.setdefault("message_settings", {})
    value = values.get(key, "")
    return str(value) if value else fallback


def set_message_setting(key, value):
    if key not in MESSAGE_DEFAULTS:
        return False
    value = str(value)
    if not value.strip():
        return False
    db.setdefault("settings", {}).setdefault("message_settings", {})[key] = value
    # توافق كامل مع زر "رسالة التحميل" القديم.
    if key == "download_status":
        db.setdefault("settings", {})["download_text"] = value
    save_db(db)
    return True


def message_editor_text():
    labels = {
        "home": "الرسالة الرئيسية",
        "new_user_welcome": "ترحيب العضو الجديد",
        "platform_tiktok": "رسالة اختيار TikTok",
        "download_status": "رسالة بدء التحميل",
        "sending_status": "رسالة إرسال الفيديو",
        "success": "رسالة نجاح التحميل",
        "download_error": "رسالة خطأ التحميل",
        "help": "رسالة المساعدة",
        "force_sub": "رسالة الاشتراك الإجباري",
        "force_sub_done": "النص بعد الاشتراك",
    }
    lines = [
        f"{EMOJI_5} <b>تخصيص رسائل البوت</b> {EMOJI_5}",
        "",
        "اختر الرسالة التي تريد تعديلها:",
    ]
    for key, label in labels.items():
        lines.append(f"• {label}")
    lines.extend([
        "",
        "المتغيرات المتاحة حسب الرسالة:",
        "<code>{first_name}</code> <code>{username}</code> <code>{user_id}</code>",
        "<code>{platform}</code> <code>{error}</code>",
    ])
    return "\n".join(lines)


def message_editor_keyboard():
    labels = {
        "home": "🏠 الرئيسية",
        "new_user_welcome": "👋 العضو الجديد",
        "platform_tiktok": "🎵 TikTok",
        "download_status": "⏳ بدء التحميل",
        "sending_status": "📤 إرسال الفيديو",
        "success": "✅ نجاح التحميل",
        "download_error": "❌ خطأ التحميل",
        "help": "❓ المساعدة",
        "force_sub": "🔐 الاشتراك الإجباري",
        "force_sub_done": "✔️ بعد الاشتراك",
    }
    rows = []
    for key, label in labels.items():
        rows.append([
            InlineKeyboardButton(
                label,
                callback_data=f"message_edit_{key}",
                style="primary",
                icon_custom_emoji_id=(button_emoji("admin_welcome_text", EMOJI_IDS()["text"]) or None)
            )
        ])
    rows.append([
        InlineKeyboardButton(
            "🔙 رجوع للوحة الأدمن",
            callback_data="admin_panel",
            style="primary",
            icon_custom_emoji_id=EMOJI_IDS()["back"]
        )
    ])
    return InlineKeyboardMarkup(rows)


def button_emoji_keyboard(key):
    rows = []
    # 2 per row; the emoji itself is rendered by Telegram from its ID.
    for i in range(0, len(AVAILABLE_CUSTOM_EMOJI_IDS), 2):
        row = []
        for emoji_id in AVAILABLE_CUSTOM_EMOJI_IDS[i:i + 2]:
            row.append(InlineKeyboardButton(
                "✨ اختيار",
                callback_data=f"button_emoji_{key}_{emoji_id}",
                style="primary",
                icon_custom_emoji_id=emoji_id
            ))
        rows.append(row)
    rows.append([
        InlineKeyboardButton(
            "🗑 إزالة الإيموجي",
            callback_data=f"button_emoji_clear_{key}",
            style="danger"
        )
    ])
    rows.append([
        InlineKeyboardButton(
            "🔙 رجوع",
            callback_data="admin_buttons",
            style="primary",
            icon_custom_emoji_id=EMOJI_IDS()["back"]
        )
    ])
    return InlineKeyboardMarkup(rows)


def button_editor_text():
    lines = [
        f"{EMOJI_5} <b>تخصيص أزرار البوت</b> {EMOJI_5}",
        "",
        f"{EMOJI_1} اختر أي زر لتغيير اسمه والإيموجي المميز الخاص به.",
        "",
        "<b>الإيموجيات المضافة للمكتبة:</b>",
    ]

    for emoji_id in AVAILABLE_CUSTOM_EMOJI_IDS:
        lines.append(
            f"<code>{emoji_id}</code>"
        )

    lines.extend([
        "",
        "عند التعديل أرسل بالشكل:",
        "<code>اسم الزر|emoji_id</code>",
        "",
        "أو لتغيير الاسم فقط:",
        "<code>اسم الزر</code>",
        "",
        "اترك emoji_id فارغاً لإزالة أيقونة الزر المميزة.",
    ])

    return "\n".join(lines)


def button_editor_keyboard():
    rows = []

    for key, (default_text, default_emoji) in BUTTON_DEFAULTS.items():
        current = get_button_setting(key)
        rows.append([
            InlineKeyboardButton(
                current["text"],
                callback_data=f"button_edit_{key}",
                style="primary",
                icon_custom_emoji_id=(
                    current["emoji_id"]
                    or default_emoji
                    or None
                )
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "🔙 رجوع للوحة الأدمن",
            callback_data="admin_panel",
            style="primary",
            icon_custom_emoji_id=EMOJI_IDS()["back"]
        )
    ])

    return InlineKeyboardMarkup(rows)


# ============================================================
# أزرار المنصات
# ============================================================

def get_platform_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                text=button_text("platform_tiktok", "TikTok"),
                callback_data="platform_tiktok",
                style="danger",
                icon_custom_emoji_id=(
                    button_emoji("platform_tiktok", "5391044040860906456")
                    or None
                )
            )
        ]
    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# ============================================================
# زر الرجوع
# ============================================================

def get_back_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                button_text("back_home", "🔙 رجوع"),
                callback_data="back_home",
                style="primary",
                icon_custom_emoji_id=(
                    button_emoji("back_home", EMOJI_IDS()["back"])
                    or None
                )
            )
        ]
    ])


# ============================================================
# Custom Emoji IDs للأزرار
# ============================================================

def EMOJI_IDS():

    return {
        "stats": "5782850920610013789",
        "broadcast": "5890969691425347748",
        "photo": "5890795783904565270",
        "video": "5782815375460671828",
        "text": "5767120181981617136",
        "delete": "5891000366081775168",
        "force": "5462989862669920629",
        "download": "5462919317832082236",
        "ban": "5767199471372867777",
        "users": "5782850920610013789",
        "refresh": "5890969691425347748",
        "back": "5890795783904565270",
        "enable": "5782815375460671828",
        "disable": "5891000366081775168",
        "channel": "5462989862669920629",
        "link": "5462919317832082236",
        "cancel": "5767199471372867777",
        "add": "5888663955412359816",
        "remove": "5891075716988016811",
        "list": "5890866066749397234",
    }


# ============================================================
# لوحة الأدمن
# ============================================================

def admin_keyboard():

    ids = EMOJI_IDS()

    keyboard = [

        [
            InlineKeyboardButton(
                button_text("admin_stats", "📊 الإحصائيات"),
                callback_data="admin_stats",
                style="primary",
                icon_custom_emoji_id=(button_emoji("admin_stats", ids["stats"]) or None)
            ),
            InlineKeyboardButton(
                button_text("admin_broadcast", "📢 إذاعة"),
                callback_data="admin_broadcast",
                style="danger",
                icon_custom_emoji_id=(button_emoji("admin_broadcast", ids["broadcast"]) or None)
            )
        ],

        [
            InlineKeyboardButton(
                button_text("admin_welcome_photo", "📸 ترحيب صورة"),
                callback_data="admin_welcome_photo",
                style="primary",
                icon_custom_emoji_id=(button_emoji("admin_welcome_photo", ids["photo"]) or None)
            ),
            InlineKeyboardButton(
                button_text("admin_welcome_video", "🎬 ترحيب فيديو"),
                callback_data="admin_welcome_video",
                style="danger",
                icon_custom_emoji_id=(button_emoji("admin_welcome_video", ids["video"]) or None)
            )
        ],

        [
            InlineKeyboardButton(
                button_text("admin_welcome_text", "✏️ نص الترحيب"),
                callback_data="admin_welcome_text",
                style="primary",
                icon_custom_emoji_id=(button_emoji("admin_welcome_text", ids["text"]) or None)
            ),
            InlineKeyboardButton(
                button_text("admin_delete_media", "🗑 حذف ميديا الترحيب"),
                callback_data="admin_delete_media",
                style="danger",
                icon_custom_emoji_id=(button_emoji("admin_delete_media", ids["delete"]) or None)
            )
        ],

        [
            InlineKeyboardButton(
                button_text("admin_force_sub", "🔐 الاشتراك الإجباري"),
                callback_data="admin_force_sub",
                style="primary",
                icon_custom_emoji_id=(button_emoji("admin_force_sub", ids["force"]) or None)
            )
        ],

        [
            InlineKeyboardButton(
                button_text("admin_download_text", "📝 رسالة التحميل"),
                callback_data="admin_download_text",
                style="danger",
                icon_custom_emoji_id=(button_emoji("admin_download_text", ids["download"]) or None)
            )
        ],

        [
            InlineKeyboardButton(
                button_text("admin_ban", "🚫 حظر مستخدم"),
                callback_data="admin_ban",
                style="danger",
                icon_custom_emoji_id=(button_emoji("admin_ban", ids["ban"]) or None)
            ),
            InlineKeyboardButton(
                button_text("admin_unban", "♻️ فك حظر"),
                callback_data="admin_unban",
                style="primary",
                icon_custom_emoji_id=(button_emoji("admin_unban", ids["enable"]) or None)
            )
        ],

        [
            InlineKeyboardButton(
                button_text("admin_admins", "👑 المشرفون"),
                callback_data="admin_admins",
                style="primary",
                icon_custom_emoji_id=(button_emoji("admin_users", ids["users"]) or None)
            ),
            InlineKeyboardButton(
                button_text("admin_users", "👥 المستخدمون"),
                callback_data="admin_users",
                style="primary",
                icon_custom_emoji_id=(button_emoji("admin_users", ids["users"]) or None)
            )
        ],

        [
            InlineKeyboardButton(
                "💬 تخصيص رسائل البوت",
                callback_data="admin_messages",
                style="primary",
                icon_custom_emoji_id=ids["text"]
            )
        ],
        [
            InlineKeyboardButton(
                "📤 تصدير الأعضاء",
                callback_data="admin_export_users",
                style="primary",
                icon_custom_emoji_id=ids["users"]
            ),
            InlineKeyboardButton(
                "📥 استرجاع الأعضاء",
                callback_data="admin_import_users",
                style="primary",
                icon_custom_emoji_id=ids["add"]
            )
        ],
        [
            InlineKeyboardButton(
                "🎨 تخصيص الأزرار",
                callback_data="admin_buttons",
                style="primary",
                icon_custom_emoji_id=ids["refresh"]
            )
        ],
        [
            InlineKeyboardButton(
                button_text("admin_panel", "🔄 تحديث اللوحة"),
                callback_data="admin_panel",
                style="primary",
                icon_custom_emoji_id=(
                    button_emoji("admin_panel", ids["refresh"])
                    or None
                )
            )
        ]
    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# ============================================================
# نص لوحة الأدمن
# ============================================================

def admin_panel_text():

    settings = db["settings"]

    force_status = (
        f"{EMOJI_6} مفعّل"
        if settings.get(
            "force_sub_enabled"
        )
        else f"{EMOJI_3} متوقف"
    )

    channels = get_force_channels()

    if channels:
        channel_text = f"{len(channels)} قناة"
    else:
        channel_text = "غير محددة"

    media_type = settings.get(
        "welcome_media_type"
    )

    if media_type == "photo":
        media_status = f"{EMOJI_3} صورة"

    elif media_type == "video":
        media_status = f"{EMOJI_6} فيديو"

    else:
        media_status = f"{EMOJI_3} لا يوجد"

    return (
        f"{EMOJI_5} <b>لوحة تحكم الأدمن</b> "
        f"{EMOJI_5}\n\n"

        f"{EMOJI_4} <b>المستخدمون:</b> "
        f"<code>{get_user_count()}</code>\n"

        f"{EMOJI_2} <b>إجمالي التحميلات:</b> "
        f"<code>{get_download_count()}</code>\n"

        f"{EMOJI_9} <b>الاشتراك الإجباري:</b> "
        f"<b>{force_status}</b>\n"

        f"{EMOJI_1} <b>القنوات:</b> "
        f"<code>{html.escape(str(channel_text))}</code>\n"

        f"{EMOJI_7} <b>ميديا الترحيب:</b> "
        f"<b>{media_status}</b>\n"

        f"👑 <b>المشرفون الإضافيون:</b> "
        f"<code>{len(get_admins())}</code>\n\n"

        f"{EMOJI_8} <b>اختر العملية المطلوبة:</b>"
    )


# ============================================================
# الصفحة الرئيسية
# ============================================================

async def send_home(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    first_name = html.escape(
        user.first_name or "مستخدم"
    )

    username = (
        f"@{html.escape(user.username)}"
        if user.username
        else "لا يوجد"
    )

    user_id = user.id

    custom_text = get_message_setting("home", "").strip()
    if not custom_text:
        custom_text = db["settings"].get("welcome_text", "").strip()

    if custom_text:
        caption = format_welcome_text(
            custom_text,
            first_name,
            username,
            user_id
        )
    else:

        caption = (
            f"{EMOJI_VIDEO} "
            f"<b>أهلـاً بـيك يـ {first_name}</b> "
            f"{EMOJI_VIDEO}\n\n"

            f"{EMOJI_PIN} "
            f"<b>يـوزرك</b>  |  {username}\n"

            f"{EMOJI_PIN} "
            f"<b>ايديـك</b>  |  "
            f"<code>{user_id}</code>\n\n"

            f"{EMOJI_OK} "
            f"<b>فـــــــي بــــوت التحـميـل "
            f"مـن سـوشـيال ميـديـا</b> "
            f"{EMOJI_STAR}{EMOJI_SPARK}\n\n"

            f"{EMOJI_POWER} "
            f"<b>المطور | @v_u_k</b>\n"

            f"{EMOJI_HEART} "
            f"<b>اختر المنصة لبدء التحميل:</b>"
        )

    media_type = db["settings"].get(
        "welcome_media_type"
    )

    media_id = db["settings"].get(
        "welcome_media_id"
    )

    target_message = update.message

    if not target_message and update.callback_query:
        target_message = (
            update.callback_query.message
        )

    if not target_message:
        return

    try:

        if media_type == "photo" and media_id:

            await target_message.reply_photo(
                photo=media_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=get_platform_keyboard()
            )

        elif media_type == "video" and media_id:

            await target_message.reply_video(
                video=media_id,
                caption=caption,
                parse_mode="HTML",
                supports_streaming=True,
                reply_markup=get_platform_keyboard()
            )

        else:

            await target_message.reply_text(
                caption,
                parse_mode="HTML",
                reply_markup=get_platform_keyboard()
            )

    except Exception as e:

        logger.exception(
            "Welcome message error: %s",
            e
        )

        try:
            await target_message.reply_text(
                caption,
                parse_mode="HTML",
                reply_markup=get_platform_keyboard()
            )
        except Exception:
            pass


# ============================================================
# الاشتراك الإجباري
# ============================================================

async def check_force_subscription(
    update,
    context
):
    """
    فحص الاشتراك الإجباري.

    يتم أولاً حل القناة بواسطة get_chat ثم استخدام chat.id الحقيقي
    مع get_chat_member. هذا أكثر ثباتاً من الاعتماد على @username فقط.

    عند الضغط على زر التحقق:
    - إذا كان مشتركاً في كل القنوات -> نجاح وفتح البوت.
    - إذا كان ناقصاً -> نفس رسالة الاشتراك تتحدث بدون تكرار رسائل.
    - كل قناة تظهر بحالتها الحالية.
    """

    settings = db.setdefault("settings", {})

    if not settings.get("force_sub_enabled", False):
        return True

    channels = get_force_channels()

    if not channels:
        return True

    user = update.effective_user

    if not user:
        return False

    checked_channels = []
    missing_channels = []
    errors = []

    async def check_one_channel(item):
        channel = str(item.get("channel", "")).strip()
        link = str(item.get("link", "")).strip()

        if not channel:
            return None

        if not link and channel.startswith("@"):
            link = "https://t.me/" + channel[1:]

        result = {
            "channel": channel,
            "link": link,
            "subscribed": False,
            "error": ""
        }

        try:
            cache_key = channel.lower()
            chat_id = _FORCE_CHAT_ID_CACHE.get(cache_key)

            if chat_id is None:
                chat = await context.bot.get_chat(chat_id=channel)
                chat_id = chat.id
                _FORCE_CHAT_ID_CACHE[cache_key] = chat_id

            member = await context.bot.get_chat_member(
                chat_id=chat_id,
                user_id=user.id
            )

            status = str(getattr(member, "status", "")).lower()
            is_member = bool(getattr(member, "is_member", False))

            result["subscribed"] = (
                status in {"member", "administrator", "creator", "owner"}
                or (status == "restricted" and is_member)
            )

        except Exception as e:
            error_text = str(e).strip()
            result["error"] = error_text
            logger.error(
                "Force subscription check failed | channel=%s | user=%s | error=%s",
                channel,
                user.id,
                error_text
            )

        return result

    # فحص كل القنوات بالتوازي بدلاً من انتظار كل قناة على حدة.
    results = await asyncio.gather(
        *(check_one_channel(item) for item in channels),
        return_exceptions=True
    )

    for result in results:
        if isinstance(result, Exception):
            logger.error("Force subscription task failed: %s", result)
            continue
        if result is None:
            continue

        checked_channels.append(result)

        if result.get("error"):
            errors.append(
                f"{result['channel']}: {result['error']}"
            )

        if not result.get("subscribed", False):
            missing_channels.append(result)

    # لا توجد قنوات صالحة للفحص.
    if not checked_channels:
        return True

    # كل القنوات متحققة.
    if not missing_channels:
        return True

    query = getattr(
        update,
        "callback_query",
        None
    )

    buttons = []

    # عرض حالة كل قناة، وليس X ثابتة.
    for item in checked_channels:
        channel = item["channel"]
        link = item["link"]

        if item["subscribed"]:
            buttons.append([
                InlineKeyboardButton(
                    f"✅ تم الاشتراك {channel}",
                    callback_data="subscription_already_ok",
                    style="primary",
                    icon_custom_emoji_id=(button_emoji("force_enable", EMOJI_IDS()["enable"]) or None)
                )
            ])

        elif link:
            buttons.append([
                InlineKeyboardButton(
                    f"❌ اشترك {channel}",
                    url=link,
                    style="primary",
                    icon_custom_emoji_id=(button_emoji("force_add_channel", EMOJI_IDS()["channel"]) or None)
                )
            ])

    buttons.append([
        InlineKeyboardButton(
            button_text("check_subscription", "🔄 تحقّق من الاشتراك"),
            callback_data="check_subscription",
            style="primary",
            icon_custom_emoji_id=(button_emoji("check_subscription", EMOJI_IDS()["refresh"]) or None)
        )
    ])

    text_lines = [
        f"{EMOJI_5} <b>الاشتراك الإجباري</b> {EMOJI_5}",
        "",
        f"{EMOJI_1} {html.escape(get_message_setting("force_sub", MESSAGE_DEFAULTS["force_sub"]))}",
        ""
    ]

    for item in checked_channels:
        channel = html.escape(
            item["channel"]
        )

        if item["subscribed"]:
            text_lines.append(
                f"✅ <b>{channel}</b> — تم الاشتراك"
            )
        else:
            text_lines.append(
                f"❌ <b>{channel}</b> — لم يتم التحقق"
            )

    text_lines.extend([
        "",
        f"{EMOJI_6} {html.escape(get_message_setting("force_sub_done", MESSAGE_DEFAULTS["force_sub_done"]))}"
    ])

    # إذا تعذر الوصول للقناة، وضّح أن المشكلة في صلاحيات البوت.
    if errors:
        text_lines.extend([
            "",
            "⚠️ <b>تعذر فحص إحدى القنوات.</b>",
            "تأكد أن البوت أدمن داخل القناة وأن معرف القناة صحيح."
        ])

    subscription_text = "\n".join(
        text_lines
    )

    if query and query.message:
        try:
            await query.edit_message_text(
                subscription_text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            logger.warning(
                "Could not edit subscription message: %s",
                e
            )
    else:
        message = update.effective_message

        if message:
            try:
                await message.reply_text(
                    subscription_text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception as e:
                logger.warning(
                    "Could not send subscription message: %s",
                    e
                )

    if query:
        if errors:
            await query.answer(
                "⚠️ تعذر فحص قناة. تأكد أن البوت أدمن فيها.",
                show_alert=True
            )
        else:
            await query.answer(
                "❌ لم يكتمل الاشتراك في جميع القنوات.",
                show_alert=True
            )

    return False


# ============================================================
# /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    # تحديد ما إذا كان هذا أول دخول فعلي للمستخدم قبل إضافته لقاعدة البيانات
    user_id = str(user.id)
    is_new_user = user_id not in db.get("users", {})

    add_user(user)

    # إشعار الأدمن مرة واحدة فقط عند دخول عضو جديد للبوت
    if is_new_user:
        first_name = html.escape(user.first_name or "بدون اسم")
        username = html.escape(user.username or "لا يوجد")
        username_text = f"@{username}" if user.username else "لا يوجد"

        admin_notification = (
            f"{EMOJI_5} <b>عضو جديد دخل البوت!</b> {EMOJI_5}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{EMOJI_7} <b>الاسم:</b> {first_name}\n"
            f"{EMOJI_4} <b>اليوزر:</b> {username_text}\n"
            f"{EMOJI_9} <b>الآيدي:</b> <code>{user.id}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{EMOJI_1} <b>تم تسجيل العضو بنجاح في قاعدة بيانات البوت.</b>"
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_notification,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(
                "Could not send new member notification to admin: %s",
                e
            )

    if is_banned(user.id):

        await update.effective_message.reply_text(
            f"{EMOJI_3} <b>تم حظرك من استخدام البوت.</b>",
            parse_mode="HTML"
        )

        return

    subscribed = await check_force_subscription(
        update,
        context
    )

    if not subscribed:
        return

    context.user_data.pop(
        "selected_platform",
        None
    )

    # ترحيب خاص بالعضو الجديد عند أول دخول ناجح للبوت
    user_id = str(user.id)
    user_data = db.get("users", {}).get(user_id, {})

    if not user_data.get("welcome_message_sent", False):
        first_name = html.escape(user.first_name or "عضو جديد")

        welcome_message = get_message_setting(
            "new_user_welcome",
            ""
        ).strip()
        if welcome_message:
            welcome_message = format_welcome_text(
                welcome_message,
                user.first_name or "عضو جديد",
                "@" + user.username if user.username else "لا يوجد",
                user.id
            )
        else:
            welcome_message = (
                f"{EMOJI_5} <b>أهلاً وسهلاً بك يا {first_name}</b> {EMOJI_5}\n\n"
                f"{EMOJI_1} <b>نورت البوت، سعداء بانضمامك إلينا!</b>\n"
                f"{EMOJI_6} يمكنك الآن اختيار المنصة وإرسال رابط الفيديو للتحميل."
            )

        await update.effective_message.reply_text(
            welcome_message,
            parse_mode="HTML"
        )

        db["users"][user_id]["welcome_message_sent"] = True
        save_db(db)

    await send_home(
        update,
        context
    )


# ============================================================
# Callback الرئيسي
# ============================================================

async def button_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    user = update.effective_user

    if not user:
        return

    if is_banned(user.id):

        await query.answer(
            "🚫 أنت محظور من استخدام البوت.",
            show_alert=True
        )

        return

    data = query.data or ""

    # ========================================================
    # الاشتراك
    # ========================================================

    if data == "check_subscription":

        subscribed = await check_force_subscription(
            update,
            context
        )

        if subscribed:
            await query.answer(
                "تم التحقق من الاشتراك ✅",
                show_alert=True
            )

            try:
                if query.message:
                    await query.message.delete()
            except Exception:
                pass

            await send_home(
                update,
                context
            )

        return

    if data == "subscription_already_ok":
        await query.answer(
            "هذه القناة تم التحقق منها بالفعل ✅"
        )
        return

    # ========================================================
    # الصفحة الرئيسية
    # ========================================================

    if data == "back_home":

        context.user_data.pop(
            "selected_platform",
            None
        )

        await send_home(
            update,
            context
        )

        return

    # ========================================================
    # لوحة الأدمن
    # ========================================================

    if (
        data.startswith("admin_")
        or data.startswith("force_")
        or data.startswith("button_edit_")
        or data.startswith("button_choose_emoji_")
        or data.startswith("button_emoji_")
    ):

        if not is_admin(user.id):

            await query.answer(
                "🚫 هذه اللوحة خاصة بالأدمن.",
                show_alert=True
            )

            return

        await admin_callback(
            update,
            context,
            data
        )

        return
    # ========================================================
    # TikTok
    # ========================================================

    if data == "platform_tiktok":

        context.user_data[
            "selected_platform"
        ] = "TikTok"

        msg = get_message_setting("platform_tiktok", MESSAGE_DEFAULTS["platform_tiktok"])
        msg = format_welcome_text(msg, user.first_name or "", "@" + user.username if user.username else "لا يوجد", user.id)

        await query.edit_message_text(
            msg,
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )

        return


# ============================================================
# لوحة الأدمن
# ============================================================

async def admin_callback(
    update,
    context,
    data
):

    query = update.callback_query

    # ========================================================
    # تصدير واسترجاع الأعضاء
    # ========================================================

    if data == "admin_export_users":
        try:
            export_path = os.path.join(gettempdir(), "bot_users_backup.json")
            export_data = {
                "users": db.get("users", {}),
                "banned_users": db.get("banned_users", []),
                "admins": db.get("admins", []),
                "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            await query.message.reply_document(
                document=export_path,
                caption=f"{EMOJI_6} <b>نسخة احتياطية من الأعضاء</b>\nعدد الأعضاء: <b>{get_user_count()}</b>",
                parse_mode="HTML"
            )
            try:
                os.remove(export_path)
            except OSError:
                pass
        except Exception as e:
            logger.exception("Export users error: %s", e)
            await query.answer("تعذر إنشاء النسخة الاحتياطية.", show_alert=True)
        return

    if data == "admin_import_users":
        context.user_data["admin_action"] = "restore_db"
        await query.edit_message_text(
            f"{EMOJI_5} <b>استرجاع الأعضاء</b> {EMOJI_5}\n\n"
            f"أرسل الآن ملف <code>social_downloader_bot_db.json</code> أو نسخة الأعضاء التي صدّرها البوت.\n\n"
            f"⚠️ الاسترجاع <b>دمج</b> وليس حذفاً: الأعضاء الحاليون لن يتم حذفهم، والأعضاء الموجودون في النسخة القديمة ستتم إضافتهم.\n\n"
            f"إذا كانت لديك قاعدة البيانات القديمة التي اختفى منها الأعضاء، أرسلها هنا.\n\n"
            f"للإلغاء: <code>/cancel</code>",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )
        return

    # ========================================================
    # تخصيص رسائل البوت
    # ========================================================

    if data == "admin_messages":
        context.user_data.pop("admin_action", None)
        await query.edit_message_text(
            message_editor_text(),
            parse_mode="HTML",
            reply_markup=message_editor_keyboard()
        )
        return

    if data.startswith("message_edit_"):
        key = data.replace("message_edit_", "", 1)
        if key not in MESSAGE_DEFAULTS:
            await query.answer("الرسالة غير موجودة.", show_alert=True)
            return
        context.user_data["admin_action"] = f"message_edit:{key}"
        current = get_message_setting(key, MESSAGE_DEFAULTS[key])
        await query.edit_message_text(
            f"{EMOJI_5} <b>تعديل الرسالة</b>\n\n"
            f"{EMOJI_1} أرسل النص الجديد الآن.\n\n"
            f"<b>النص الحالي:</b>\n<code>{html.escape(current)}</code>\n\n"
            f"المتغيرات: <code>{{first_name}}</code> <code>{{username}}</code> <code>{{user_id}}</code> <code>{{platform}}</code> <code>{{error}}</code>\n\n"
            f"للإلغاء: <code>/cancel</code>",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )
        return

    # ========================================================
    # تخصيص الأزرار
    # ========================================================

    if data == "admin_buttons":

        context.user_data.pop(
            "admin_action",
            None
        )

        await query.edit_message_text(
            button_editor_text(),
            parse_mode="HTML",
            reply_markup=button_editor_keyboard()
        )

        return

    if data.startswith("button_choose_emoji_"):
        key = data.replace("button_choose_emoji_", "", 1)
        if key not in BUTTON_DEFAULTS:
            await query.answer("الزر غير موجود.", show_alert=True)
            return
        await query.edit_message_text(
            f"{EMOJI_5} <b>اختر Premium Emoji للزر</b>\n\n"
            f"اضغط على الإيموجي الذي تريده ليتم تعيينه فوراً.",
            parse_mode="HTML",
            reply_markup=button_emoji_keyboard(key)
        )
        return

    if data.startswith("button_emoji_clear_"):
        key = data.replace("button_emoji_clear_", "", 1)
        if key not in BUTTON_DEFAULTS:
            await query.answer("الزر غير موجود.", show_alert=True)
            return
        current = get_button_setting(key)
        set_button_setting(key, current["text"], "")
        await query.answer("تمت إزالة الإيموجي المميز.", show_alert=True)
        await query.edit_message_text(
            f"{EMOJI_6} <b>تم إزالة إيموجي الزر.</b>\n\n"
            f"الزر: <b>{html.escape(current['text'])}</b>\n\n"
            f"يمكنك اختيار إيموجي آخر الآن.",
            parse_mode="HTML",
            reply_markup=button_emoji_keyboard(key)
        )
        return

    if data.startswith("button_emoji_"):
        payload = data.replace("button_emoji_", "", 1)
        # split from the right because the emoji id is numeric and key contains underscores
        parts = payload.rsplit("_", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            await query.answer("إيموجي غير صالح.", show_alert=True)
            return
        key, emoji_id = parts
        if key not in BUTTON_DEFAULTS or emoji_id not in AVAILABLE_CUSTOM_EMOJI_IDS:
            await query.answer("الإيموجي غير متاح.", show_alert=True)
            return
        current = get_button_setting(key)
        set_button_setting(key, current["text"], emoji_id)
        context.user_data.pop("admin_action", None)
        await query.answer("تم تعيين الإيموجي فعلياً للزر.", show_alert=True)
        await query.edit_message_text(
            f"{EMOJI_6} <b>تم تغيير إيموجي الزر بنجاح.</b>\n\n"
            f"الزر: <b>{html.escape(current['text'])}</b>\n"
            f"emoji_id: <code>{emoji_id}</code>",
            parse_mode="HTML",
            reply_markup=button_editor_keyboard()
        )
        return

    if data.startswith("button_edit_"):

        key = data.replace(
            "button_edit_",
            "",
            1
        )

        if key not in BUTTON_DEFAULTS:
            await query.answer(
                "هذا الزر غير موجود.",
                show_alert=True
            )
            return

        context.user_data["admin_action"] = (
            f"button_edit:{key}"
        )

        current = get_button_setting(key)

        keyboard = [
            [
                InlineKeyboardButton(
                    "🎨 اختر Premium Emoji",
                    callback_data=f"button_choose_emoji_{key}",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS()["text"]
                )
            ],
            [
                InlineKeyboardButton(
                    "🗑 إزالة الإيموجي",
                    callback_data=f"button_emoji_clear_{key}",
                    style="danger"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 رجوع",
                    callback_data="admin_buttons",
                    style="primary",
                    icon_custom_emoji_id=EMOJI_IDS()["back"]
                )
            ]
        ]

        await query.edit_message_text(
            f"{EMOJI_5} <b>تعديل الزر</b>\n\n"
            f"{EMOJI_1} الزر الحالي: <b>{html.escape(current['text'])}</b>\n"
            f"{EMOJI_4} الإيموجي الحالي: <code>{html.escape(current['emoji_id'] or 'لا يوجد')}</code>\n\n"
            f"🎨 اضغط <b>اختر Premium Emoji</b> لتظهر لك الإيموجيات وتختار منها مباشرة.\n\n"
            f"أو أرسل اسم الزر فقط، أو بالشكل: <code>اسم الزر|emoji_id</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ========================================================
    # اللوحة الرئيسية
    # ========================================================

    if data == "admin_panel":

        await query.edit_message_text(
            admin_panel_text(),
            parse_mode="HTML",
            reply_markup=admin_keyboard()
        )

        return

    # ========================================================
    # الإحصائيات
    # ========================================================

    if data == "admin_stats":

        text = (
            f"{EMOJI_5} <b>إحصائيات البوت</b> "
            f"{EMOJI_5}\n\n"

            f"{EMOJI_4} عدد المستخدمين: "
            f"<b>{get_user_count()}</b>\n"

            f"{EMOJI_2} عدد التحميلات: "
            f"<b>{get_download_count()}</b>\n"

            f"{EMOJI_3} المحظورون: "
            f"<b>{len(db.get('banned_users', []))}</b>"
        )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # إذاعة
    # ========================================================

    if data == "admin_broadcast":

        context.user_data[
            "admin_action"
        ] = "broadcast"

        await query.edit_message_text(
            f"{EMOJI_5} <b>إذاعة للمستخدمين</b> "
            f"{EMOJI_5}\n\n"

            f"{EMOJI_1} أرسل الآن الرسالة "
            f"التي تريد إرسالها للجميع.\n\n"

            f"{EMOJI_6} يمكنك إرسال نص أو "
            f"صورة أو فيديو أو ملف.\n\n"

            f"{EMOJI_9} للإلغاء استخدم "
            f"<code>/cancel</code>.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # ترحيب صورة
    # ========================================================

    if data == "admin_welcome_photo":

        context.user_data[
            "admin_action"
        ] = "welcome_photo"

        await query.edit_message_text(
            f"{EMOJI_3} <b>تغيير صورة الترحيب</b>\n\n"
            f"{EMOJI_1} أرسل الصورة الآن.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # ترحيب فيديو
    # ========================================================

    if data == "admin_welcome_video":

        context.user_data[
            "admin_action"
        ] = "welcome_video"

        await query.edit_message_text(
            f"{EMOJI_6} <b>تغيير فيديو الترحيب</b>\n\n"
            f"{EMOJI_1} أرسل الفيديو الآن.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # نص الترحيب
    # ========================================================

    if data == "admin_welcome_text":

        context.user_data[
            "admin_action"
        ] = "welcome_text"

        await query.edit_message_text(
            f"{EMOJI_1} <b>تغيير نص الترحيب</b>\n\n"

            f"{EMOJI_4} أرسل النص الجديد.\n\n"

            f"{EMOJI_8} المتغيرات المتاحة:\n"
            f"<code>{{first_name}}</code>\n"
            f"<code>{{username}}</code>\n"
            f"<code>{{user_id}}</code>",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # حذف الميديا
    # ========================================================

    if data == "admin_delete_media":

        db["settings"][
            "welcome_media_type"
        ] = ""

        db["settings"][
            "welcome_media_id"
        ] = ""

        db["settings"][
            "welcome_media_caption"
        ] = ""

        save_db(db)

        await query.answer(
            "تم حذف ميديا الترحيب.",
            show_alert=True
        )

        await query.edit_message_text(
            admin_panel_text(),
            parse_mode="HTML",
            reply_markup=admin_keyboard()
        )

        return

    # ========================================================
    # الاشتراك الإجباري
    # ========================================================

    if data == "admin_force_sub":

        await admin_force_menu(
            query
        )

        return

    # ========================================================
    # رسالة التحميل
    # ========================================================

    if data == "admin_download_text":

        context.user_data[
            "admin_action"
        ] = "download_text"

        current = db["settings"].get(
            "download_text",
            ""
        )

        await query.edit_message_text(
            f"{EMOJI_2} <b>رسالة التحميل</b>\n\n"

            f"{EMOJI_7} الحالية:\n"
            f"<code>{html.escape(current)}</code>\n\n"

            f"{EMOJI_1} أرسل الرسالة الجديدة.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # حظر
    # ========================================================

    if data == "admin_ban":

        context.user_data[
            "admin_action"
        ] = "ban_user"

        await query.edit_message_text(
            f"{EMOJI_3} <b>حظر مستخدم</b>\n\n"
            f"{EMOJI_9} أرسل ID المستخدم الآن.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # فك الحظر
    # ========================================================

    if data == "admin_unban":

        context.user_data[
            "admin_action"
        ] = "unban_user"

        await query.edit_message_text(
            f"{EMOJI_6} <b>فك حظر مستخدم</b>\n\n"
            f"{EMOJI_9} أرسل ID المستخدم الآن.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # المشرفون
    # ========================================================

    if data == "admin_admins":

        admins = get_admins()

        lines = [
            f"👑 <b>إدارة المشرفين</b> 👑",
            "",
            f"👑 المالك الأساسي: <code>{ADMIN_ID}</code>",
            f"👥 المشرفون الإضافيون: <b>{len(admins)}</b>",
            ""
        ]

        if admins:
            for index, admin_id in enumerate(admins, 1):
                lines.append(
                    f"{index}. <code>{admin_id}</code>"
                )
        else:
            lines.append("لا يوجد مشرفون إضافيون حالياً.")

        keyboard = [
            [
                InlineKeyboardButton(
                    button_text("admin_add_admin", "➕ إضافة مشرف"),
                    callback_data="admin_add_admin",
                    style="primary",
                    icon_custom_emoji_id=(button_emoji("force_add_channel", EMOJI_IDS()["add"]) or None)
                )
            ],
            [
                InlineKeyboardButton(
                    button_text("admin_remove_admin", "🗑 حذف مشرف"),
                    callback_data="admin_remove_admin",
                    style="danger",
                    icon_custom_emoji_id=(button_emoji("force_remove_channel", EMOJI_IDS()["remove"]) or None)
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 رجوع",
                    callback_data="admin_panel",
                    style="primary",
                    icon_custom_emoji_id=(button_emoji("admin_panel", EMOJI_IDS()["back"]) or None)
                )
            ]
        ]

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ========================================================
    # إضافة مشرف
    # ========================================================

    if data == "admin_add_admin":

        context.user_data["admin_action"] = "add_admin"

        await query.edit_message_text(
            "➕ <b>إضافة مشرف جديد</b>\n\n"
            "👤 أرسل الآن <b>ID</b> المستخدم الذي تريد منحه صلاحيات الأدمن.\n\n"
            "💡 مثال: <code>123456789</code>\n\n"
            "🚫 لإلغاء العملية استخدم <code>/cancel</code>.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # حذف مشرف
    # ========================================================

    if data == "admin_remove_admin":

        admins = get_admins()

        if not admins:
            await query.answer(
                "لا يوجد مشرفون إضافيون لحذفهم.",
                show_alert=True
            )
            return

        context.user_data["admin_action"] = "remove_admin"

        await query.edit_message_text(
            "🗑 <b>حذف مشرف</b>\n\n"
            "👤 أرسل الآن ID المشرف الذي تريد حذف صلاحياته.\n\n"
            + "\n".join(
                f"• <code>{admin_id}</code>"
                for admin_id in admins
            )
            + "\n\n🚫 لإلغاء العملية استخدم <code>/cancel</code>.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # المستخدمون
    # ========================================================

    if data == "admin_users":

        users = list(
            db.get(
                "users",
                {}
            ).values()
        )

        if not users:

            text = (
                f"{EMOJI_3} "
                f"لا يوجد مستخدمون حتى الآن."
            )

        else:

            lines = [
                f"{EMOJI_4} "
                f"<b>آخر المستخدمين</b>",
                ""
            ]

            for user_data in users[-20:]:

                uid = user_data.get(
                    "id",
                    ""
                )

                name = html.escape(
                    str(
                        user_data.get(
                            "first_name",
                            ""
                        )
                    )
                )

                username = user_data.get(
                    "username"
                )

                if username:

                    username_text = (
                        "@"
                        + html.escape(
                            str(username)
                        )
                    )

                else:

                    username_text = (
                        "بدون يوزر"
                    )

                lines.append(
                    f"{EMOJI_1} {name} | "
                    f"{username_text} | "
                    f"<code>{uid}</code>"
                )

            text = "\n".join(
                lines
            )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # تفعيل الاشتراك
    # ========================================================

    if data == "force_enable":

        db["settings"][
            "force_sub_enabled"
        ] = True

        save_db(db)

        await query.answer(
            "تم تفعيل الاشتراك الإجباري.",
            show_alert=True
        )

        await admin_force_menu(
            query
        )

        return

    # ========================================================
    # تعطيل الاشتراك
    # ========================================================

    if data == "force_disable":

        db["settings"][
            "force_sub_enabled"
        ] = False

        save_db(db)

        await query.answer(
            "تم تعطيل الاشتراك الإجباري.",
            show_alert=True
        )

        await admin_force_menu(
            query
        )

        return

    # ========================================================
    # إضافة قناة جديدة
    # ========================================================

    if data == "force_add_channel":

        context.user_data[
            "admin_action"
        ] = "force_add_channel"

        await query.edit_message_text(
            f"{EMOJI_4} <b>إضافة قناة اشتراك إجباري</b>\n\n"

            f"{EMOJI_1} أرسل @username الخاص بالقناة.\n\n"

            f"{EMOJI_8} مثال:\n"
            f"<code>@my_channel</code>\n\n"

            f"{EMOJI_3} يجب أن يكون البوت "
            f"مضافاً إلى القناة كأدمن.\n\n"

            f"{EMOJI_9} يمكنك إضافة أي عدد من القنوات.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # حذف قناة
    # ========================================================

    if data == "force_remove_channel":

        channels = get_force_channels()

        if not channels:

            await query.answer(
                "لا توجد قنوات لحذفها.",
                show_alert=True
            )

            return

        await force_remove_menu(
            query
        )

        return

    # ========================================================
    # قائمة القنوات
    # ========================================================

    if data == "force_list_channels":

        await admin_force_menu(
            query
        )

        return

    # ========================================================
    # تحديد القناة القديمة - توافق
    # ========================================================

    if data == "force_set_channel":

        context.user_data[
            "admin_action"
        ] = "force_add_channel"

        await query.edit_message_text(
            f"{EMOJI_4} <b>إضافة قناة الاشتراك</b>\n\n"

            f"{EMOJI_1} أرسل @username الخاص بالقناة.\n\n"

            f"{EMOJI_8} مثال:\n"
            f"<code>@my_channel</code>\n\n"

            f"{EMOJI_3} يجب أن يكون البوت "
            f"مضافاً إلى القناة كأدمن.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # رابط القناة القديمة - توافق
    # ========================================================

    if data == "force_set_link":

        context.user_data[
            "admin_action"
        ] = "force_link"

        await query.edit_message_text(
            f"{EMOJI_7} <b>رابط القناة</b>\n\n"
            f"{EMOJI_1} أرسل الرابط بالشكل التالي:\n"
            f"<code>@channel|https://t.me/channel</code>\n\n"
            f"{EMOJI_8} أو أرسل الرابط فقط إذا كانت القناة "
            f"موجودة بالفعل.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )

        return

    # ========================================================
    # حذف قناة محددة
    # ========================================================

    if data.startswith("force_remove_"):

        try:
            index = int(
                data.replace(
                    "force_remove_",
                    "",
                    1
                )
            )
        except ValueError:
            return

        channels = get_force_channels()

        if len(channels) <= 1:

            await query.answer(
                "لا يمكن حذف آخر قناة. أضف قناة أخرى أولاً أو عطّل الاشتراك الإجباري.",
                show_alert=True
            )

            return

        if remove_force_channel(index):

            await query.answer(
                "تم حذف القناة.",
                show_alert=True
            )

            await admin_force_menu(
                query
            )

        return


# ============================================================
# قائمة الاشتراك الإجباري
# ============================================================

async def admin_force_menu(query):

    enabled = db["settings"].get(
        "force_sub_enabled"
    )

    status = (
        f"{EMOJI_6} مفعّل"
        if enabled
        else f"{EMOJI_3} متوقف"
    )

    channels = get_force_channels()

    ids = EMOJI_IDS()

    if channels:

        channel_lines = []

        for index, item in enumerate(
            channels,
            1
        ):

            channel = html.escape(
                str(
                    item.get(
                        "channel",
                        ""
                    )
                )
            )

            link = html.escape(
                str(
                    item.get(
                        "link",
                        ""
                    )
                )
            )

            channel_lines.append(
                f"{EMOJI_1} <b>{index}.</b> "
                f"<code>{channel}</code>\n"
                f"   {EMOJI_7} <code>{link}</code>"
            )

        channels_text = "\n".join(
            channel_lines
        )

    else:

        channels_text = (
            f"{EMOJI_3} لا توجد قنوات."
        )

    text = (
        f"{EMOJI_5} "
        f"<b>إعدادات الاشتراك الإجباري</b> "
        f"{EMOJI_5}\n\n"

        f"{EMOJI_4} الحالة: <b>{status}</b>\n\n"

        f"{EMOJI_8} <b>القنوات الحالية:</b>\n"
        f"{channels_text}\n\n"

        f"{EMOJI_1} يمكنك إضافة أو حذف "
        f"القنوات من الأزرار بالأسفل."
    )

    keyboard = [

        [
            InlineKeyboardButton(
                button_text("force_enable", "🟢 تفعيل"),
                callback_data="force_enable",
                style="primary",
                icon_custom_emoji_id=(
                    button_emoji("force_enable", ids["enable"]) or None
                )
            ),

            InlineKeyboardButton(
                button_text("force_disable", "🔴 تعطيل"),
                callback_data="force_disable",
                style="danger",
                icon_custom_emoji_id=(
                    button_emoji("force_disable", ids["disable"]) or None
                )
            )
        ],

        [
            InlineKeyboardButton(
                button_text("force_add_channel", "➕ إضافة قناة"),
                callback_data="force_add_channel",
                style="primary",
                icon_custom_emoji_id=(
                    button_emoji("force_add_channel", ids["add"]) or None
                )
            ),

            InlineKeyboardButton(
                button_text("force_remove_channel", "🗑 حذف قناة"),
                callback_data="force_remove_channel",
                style="danger",
                icon_custom_emoji_id=(
                    button_emoji("force_remove_channel", ids["remove"]) or None
                )
            )
        ],

        [
            InlineKeyboardButton(
                button_text("force_list_channels", "📋 تحديث القنوات"),
                callback_data="force_list_channels",
                style="primary",
                icon_custom_emoji_id=(
                    button_emoji("force_list_channels", ids["list"]) or None
                )
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 رجوع",
                callback_data="admin_panel",
                style="primary",
                icon_custom_emoji_id=(button_emoji("admin_panel", ids["back"]) or None)
            )
        ]
    ]

    try:

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

    except Exception as e:

        logger.warning(
            "Force menu edit error: %s",
            e
        )


async def force_remove_menu(query):

    channels = get_force_channels()

    ids = EMOJI_IDS()

    buttons = []

    for index, item in enumerate(
        channels
    ):

        channel = item.get(
            "channel",
            ""
        )

        buttons.append([
            InlineKeyboardButton(
                f"🗑 {channel}",
                callback_data=f"force_remove_{index}",
                style="danger",
                icon_custom_emoji_id=(button_emoji("force_remove_channel", ids["remove"]) or None)
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 رجوع",
            callback_data="admin_force_sub",
            style="primary",
            icon_custom_emoji_id=(button_emoji("admin_panel", ids["back"]) or None)
        )
    ])

    await query.edit_message_text(
        f"{EMOJI_5} <b>حذف قناة</b> {EMOJI_5}\n\n"
        f"{EMOJI_1} اختر القناة التي تريد حذفها:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            buttons
        )
    )


# ============================================================
# زر الرجوع للأدمن
# ============================================================

def get_back_admin_keyboard():

    ids = EMOJI_IDS()

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 رجوع للوحة الأدمن",
                callback_data="admin_panel",
                style="primary",
                icon_custom_emoji_id=(button_emoji("admin_panel", ids["back"]) or None)
            )
        ]
    ])


# ============================================================
# أمر الأدمن
# ============================================================

async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user or not is_admin(
        user.id
    ):

        await update.effective_message.reply_text(
            f"{EMOJI_3} "
            f"<b>هذا الأمر خاص بالأدمن.</b>",
            parse_mode="HTML"
        )

        return

    context.user_data.pop(
        "admin_action",
        None
    )

    await update.effective_message.reply_text(
        admin_panel_text(),
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# ============================================================
# معالجة رسائل الأدمن
# ============================================================

async def handle_admin_message(
    update,
    context
):

    user = update.effective_user

    if not user or not is_admin(
        user.id
    ):
        return False

    action = context.user_data.get(
        "admin_action"
    )

    if not action:
        return False

    message = update.effective_message

    # ========================================================
    # استرجاع الأعضاء من ملف JSON قديم
    # ========================================================

    if action == "restore_db":
        if not message.document:
            await message.reply_text("❌ أرسل ملف JSON فقط.")
            return True

        try:
            temp_path = os.path.join(gettempdir(), f"restore_{user.id}.json")
            tg_file = await message.document.get_file()
            await tg_file.download_to_drive(temp_path)
            with open(temp_path, "r", encoding="utf-8") as f:
                imported = json.load(f)

            imported_users = imported.get("users", {}) if isinstance(imported, dict) else {}
            if not isinstance(imported_users, dict):
                raise ValueError("صيغة ملف الأعضاء غير صحيحة")

            before = get_user_count()
            added = 0
            updated = 0
            for uid, user_data in imported_users.items():
                if not isinstance(user_data, dict):
                    continue
                uid = str(uid)
                if uid in db["users"]:
                    # لا نستبدل بيانات أحدث؛ نملأ الناقص فقط ونحتفظ بعداد التحميل.
                    current = db["users"][uid]
                    for field in ("id", "first_name", "username", "joined_at", "welcome_message_sent"):
                        if field not in current and field in user_data:
                            current[field] = user_data[field]
                    if "downloads" in user_data:
                        try:
                            current["downloads"] = max(int(current.get("downloads", 0)), int(user_data.get("downloads", 0)))
                        except Exception:
                            pass
                    updated += 1
                else:
                    db["users"][uid] = dict(user_data)
                    db["users"][uid].setdefault("id", int(uid) if uid.lstrip("-").isdigit() else uid)
                    db["users"][uid].setdefault("first_name", "")
                    db["users"][uid].setdefault("username", "")
                    db["users"][uid].setdefault("joined_at", "")
                    db["users"][uid].setdefault("downloads", 0)
                    db["users"][uid].setdefault("welcome_message_sent", False)
                    added += 1

            # استرجاع الحظر والمشرفين أيضاً دون حذف الموجود.
            for uid in imported.get("banned_users", []) if isinstance(imported, dict) else []:
                try:
                    uid = int(uid)
                    if uid not in db["banned_users"]:
                        db["banned_users"].append(uid)
                except Exception:
                    pass
            for aid in imported.get("admins", []) if isinstance(imported, dict) else []:
                try:
                    aid = int(aid)
                    if aid != int(ADMIN_ID) and aid not in db["admins"]:
                        db["admins"].append(aid)
                except Exception:
                    pass

            save_db(db)
            _refresh_fast_caches()
            context.user_data.pop("admin_action", None)
            await message.reply_text(
                f"{EMOJI_6} <b>تم استرجاع قاعدة الأعضاء.</b>\n\n"
                f"قبل الاسترجاع: <b>{before}</b>\n"
                f"تمت إضافة: <b>{added}</b>\n"
                f"تمت مطابقة/تحديث: <b>{updated}</b>\n"
                f"الإجمالي الآن: <b>{get_user_count()}</b>",
                parse_mode="HTML",
                reply_markup=admin_keyboard()
            )
        except Exception as e:
            logger.exception("Restore database error: %s", e)
            await message.reply_text(
                f"❌ تعذر استرجاع الملف.\n<code>{html.escape(str(e))}</code>",
                parse_mode="HTML"
            )
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return True

    # ========================================================
    # تعديل رسالة من لوحة الأدمن
    # ========================================================

    if action.startswith("message_edit:"):
        key = action.split(":", 1)[1]
        if key not in MESSAGE_DEFAULTS:
            context.user_data.pop("admin_action", None)
            await message.reply_text("❌ الرسالة غير موجودة.")
            return True
        if not message.text:
            await message.reply_text("❌ أرسل نصاً فقط.")
            return True

        # حفظ النص الخام حتى يبقى قابلاً للتعديل لاحقاً.
        # Premium Emoji يكتب داخل الكليشة هكذا:
        # [emoji:5462943653116792628]
        # أو {emoji:5462943653116792628}
        raw_text = message.text
        if not set_message_setting(key, raw_text):
            await message.reply_text("❌ تعذر حفظ الرسالة.")
            return True

        context.user_data.pop("admin_action", None)

        preview = _render_custom_emoji_markup(raw_text)
        try:
            await message.reply_text(
                f"{EMOJI_6} <b>تم حفظ الرسالة بنجاح.</b>\n\n"
                f"<b>معاينة:</b>\n{preview}\n\n"
                f"🎨 Premium Emoji: اكتب <code>النص|ID</code> داخل الكليشة.\n"
                f"مثال: <code>ليدر|5271929483752930708</code>",
                parse_mode="HTML",
                reply_markup=message_editor_keyboard()
            )
        except Exception:
            # إذا كان الـ ID غير متاح/غير مقبول من Telegram، لا نفقد النص المحفوظ.
            await message.reply_text(
                f"{EMOJI_6} <b>تم حفظ الرسالة.</b>\n\n"
                f"لإضافة Premium Emoji استخدم: <code>النص|ID</code>",
                parse_mode="HTML",
                reply_markup=message_editor_keyboard()
            )
        return True

    # ========================================================
    # تعديل اسم وإيموجي زر
    # ========================================================

    if action.startswith("button_edit:"):

        key = action.split(
            ":",
            1
        )[1]

        if key not in BUTTON_DEFAULTS:
            context.user_data.pop(
                "admin_action",
                None
            )
            await message.reply_text(
                f"{EMOJI_3} الزر غير موجود."
            )
            return True

        if not message.text:
            await message.reply_text(
                f"{EMOJI_3} أرسل اسم الزر، ويمكنك إضافة emoji_id بعد |."
            )
            return True

        value = message.text.strip()

        parts = value.split(
            "|",
            1
        )

        new_text = parts[0].strip()
        new_emoji = (
            parts[1].strip()
            if len(parts) > 1
            else get_button_setting(key)["emoji_id"]
        )

        if not new_text:
            await message.reply_text(
                f"{EMOJI_3} اسم الزر لا يمكن أن يكون فارغاً."
            )
            return True

        if new_emoji and not new_emoji.isdigit():
            await message.reply_text(
                f"{EMOJI_3} emoji_id يجب أن يكون أرقاماً فقط."
            )
            return True

        # لا نفرض الإيموجيات الثمانية على الزر؛ المكتبة اختيارية.
        if not set_button_setting(
            key,
            new_text,
            new_emoji
        ):
            await message.reply_text(
                f"{EMOJI_3} تعذر حفظ إعداد الزر."
            )
            return True

        context.user_data.pop(
            "admin_action",
            None
        )

        await message.reply_text(
            f"{EMOJI_6} <b>تم تحديث الزر بنجاح.</b>\n\n"
            f"{EMOJI_4} الاسم: "
            f"<b>{html.escape(new_text)}</b>\n"
            f"{EMOJI_7} emoji_id: "
            f"<code>{html.escape(new_emoji or 'لا يوجد')}</code>",
            parse_mode="HTML",
            reply_markup=button_editor_keyboard()
        )

        return True

    # ========================================================
    # إذاعة
    # ========================================================

    if action == "broadcast":

        context.user_data.pop(
            "admin_action",
            None
        )

        sent = 0
        failed = 0

        await message.reply_text(
            f"{EMOJI_2} جاري بدء الإذاعة..."
        )

        for user_id in list(
            db.get(
                "users",
                {}
            ).keys()
        ):

            try:

                await message.copy(
                    chat_id=int(user_id)
                )

                sent += 1

                await asyncio.sleep(
                    0.05
                )

            except Exception as e:

                failed += 1

                logger.warning(
                    "Broadcast failed for %s: %s",
                    user_id,
                    e
                )

        await message.reply_text(
            f"{EMOJI_6} <b>انتهت الإذاعة</b>\n\n"

            f"{EMOJI_4} تم الإرسال: "
            f"<b>{sent}</b>\n"

            f"{EMOJI_3} فشل: "
            f"<b>{failed}</b>",
            parse_mode="HTML"
        )

        return True

    # ========================================================
    # صورة الترحيب
    # ========================================================

    if action == "welcome_photo":

        if not message.photo:

            await message.reply_text(
                f"{EMOJI_3} أرسل صورة فقط."
            )

            return True

        photo = message.photo[-1]

        db["settings"][
            "welcome_media_type"
        ] = "photo"

        db["settings"][
            "welcome_media_id"
        ] = photo.file_id

        db["settings"][
            "welcome_media_caption"
        ] = message.caption or ""

        save_db(db)

        context.user_data.pop(
            "admin_action",
            None
        )

        await message.reply_text(
            f"{EMOJI_6} "
            f"تم حفظ صورة الترحيب بنجاح."
        )

        return True

    # ========================================================
    # فيديو الترحيب
    # ========================================================

    if action == "welcome_video":

        if not message.video:

            await message.reply_text(
                f"{EMOJI_3} أرسل فيديو فقط."
            )

            return True

        video = message.video

        db["settings"][
            "welcome_media_type"
        ] = "video"

        db["settings"][
            "welcome_media_id"
        ] = video.file_id

        db["settings"][
            "welcome_media_caption"
        ] = message.caption or ""

        save_db(db)

        context.user_data.pop(
            "admin_action",
            None
        )

        await message.reply_text(
            f"{EMOJI_6} "
            f"تم حفظ فيديو الترحيب بنجاح."
        )

        return True

    # ========================================================
    # نص الترحيب
    # ========================================================

    if action == "welcome_text":

        if not message.text:

            await message.reply_text(
                f"{EMOJI_3} أرسل نصاً فقط."
            )

            return True

        db["settings"][
            "welcome_text"
        ] = message.text

        save_db(db)

        context.user_data.pop(
            "admin_action",
            None
        )

        await message.reply_text(
            f"{EMOJI_6} "
            f"<b>تم تحديث نص الترحيب.</b>\n\n"

            f"{EMOJI_8} المتغيرات:\n"
            f"<code>{{first_name}}</code>\n"
            f"<code>{{username}}</code>\n"
            f"<code>{{user_id}}</code>",
            parse_mode="HTML"
        )

        return True

    # ========================================================
    # رسالة التحميل
    # ========================================================

    if action == "download_text":

        if not message.text:

            await message.reply_text(
                f"{EMOJI_3} أرسل نصاً فقط."
            )

            return True

        db["settings"][
            "download_text"
        ] = message.text

        save_db(db)

        context.user_data.pop(
            "admin_action",
            None
        )

        await message.reply_text(
            f"{EMOJI_6} "
            f"<b>تم تحديث رسالة التحميل.</b>",
            parse_mode="HTML"
        )

        return True

    # ========================================================
    # إضافة قناة اشتراك
    # ========================================================

    if action == "force_add_channel":

        if not message.text:

            await message.reply_text(
                f"{EMOJI_3} "
                f"أرسل @username القناة."
            )

            return True

        value = message.text.strip()

        # دعم @username فقط أو @username|رابط القناة
        parts = [
            part.strip()
            for part in value.split(
                "|",
                1
            )
        ]

        channel = parts[0]

        if not channel.startswith("@"):

            await message.reply_text(
                f"{EMOJI_3} "
                f"يجب أن يبدأ معرف القناة بـ @"
            )

            return True

        link = (
            parts[1]
            if len(parts) > 1
            else ""
        )

        if link and not re.match(
            r"^https?://",
            link,
            re.IGNORECASE
        ):

            await message.reply_text(
                f"{EMOJI_3} "
                f"الرابط يجب أن يبدأ بـ https://"
            )

            return True

        added = add_force_channel(
            channel,
            link
        )

        context.user_data.pop(
            "admin_action",
            None
        )

        if added:

            await message.reply_text(
                f"{EMOJI_6} "
                f"<b>تمت إضافة قناة الاشتراك.</b>\n\n"

                f"{EMOJI_4} القناة:\n"
                f"<code>{html.escape(channel)}</code>\n\n"

                f"{EMOJI_7} الرابط:\n"
                f"<code>{html.escape(link or 'تم توليده تلقائياً')}</code>\n\n"

                f"{EMOJI_3} تأكد أن البوت أدمن داخل القناة.",
                parse_mode="HTML"
            )

        else:

            await message.reply_text(
                f"{EMOJI_2} "
                f"<b>القناة موجودة بالفعل وتم تحديث رابطها.</b>\n\n"
                f"<code>{html.escape(channel)}</code>",
                parse_mode="HTML"
            )

        return True

    # ========================================================
    # رابط القناة - توافق مع النظام القديم
    # ========================================================

    if action == "force_link":

        if not message.text:

            await message.reply_text(
                f"{EMOJI_3} "
                f"أرسل رابط القناة."
            )

            return True

        link = message.text.strip()

        if not re.match(
            r"^https?://",
            link,
            re.IGNORECASE
        ):

            await message.reply_text(
                f"{EMOJI_3} "
                f"أرسل رابطاً يبدأ بـ https://"
            )

            return True

        channels = get_force_channels()

        if channels:

            channels[0]["link"] = link
            save_force_channels(channels)

        else:

            await message.reply_text(
                f"{EMOJI_3} لا توجد قناة محفوظة لتعيين الرابط عليها. أضف قناة أولاً."
            )
            return True

        context.user_data.pop(
            "admin_action",
            None
        )

        await message.reply_text(
            f"{EMOJI_6} "
            f"<b>تم حفظ رابط القناة.</b>",
            parse_mode="HTML"
        )

        return True

    # ========================================================
    # إضافة مشرف
    # ========================================================

    if action == "add_admin":

        if not message.text:
            await message.reply_text(
                f"{EMOJI_3} أرسل ID صحيح."
            )
            return True

        try:
            target_id = int(message.text.strip())
        except ValueError:
            await message.reply_text(
                f"{EMOJI_3} الـ ID يجب أن يكون أرقاماً فقط."
            )
            return True

        if target_id == int(ADMIN_ID):
            context.user_data.pop("admin_action", None)
            await message.reply_text(
                "👑 هذا المستخدم هو المالك الأساسي بالفعل."
            )
            return True

        admins = get_admins()

        if target_id in admins:
            context.user_data.pop("admin_action", None)
            await message.reply_text(
                f"⚠️ المستخدم <code>{target_id}</code> مشرف بالفعل.",
                parse_mode="HTML"
            )
            return True

        db.setdefault("admins", []).append(target_id)
        save_db(db)
        _refresh_fast_caches()
        context.user_data.pop("admin_action", None)

        await message.reply_text(
            f"{EMOJI_6} <b>تمت إضافة المشرف بنجاح.</b>\n\n"
            f"👑 ID: <code>{target_id}</code>\n\n"
            "يمكنه الآن استخدام لوحة الأدمن وإدارتها.",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )
        return True

    # ========================================================
    # حذف مشرف
    # ========================================================

    if action == "remove_admin":

        if not message.text:
            await message.reply_text(
                f"{EMOJI_3} أرسل ID صحيح."
            )
            return True

        try:
            target_id = int(message.text.strip())
        except ValueError:
            await message.reply_text(
                f"{EMOJI_3} الـ ID يجب أن يكون أرقاماً فقط."
            )
            return True

        if target_id == int(ADMIN_ID):
            context.user_data.pop("admin_action", None)
            await message.reply_text(
                "🚫 لا يمكن حذف المالك الأساسي من المشرفين."
            )
            return True

        admins = get_admins()

        if target_id not in admins:
            context.user_data.pop("admin_action", None)
            await message.reply_text(
                f"⚠️ المستخدم <code>{target_id}</code> ليس مشرفاً إضافياً.",
                parse_mode="HTML"
            )
            return True

        db["admins"] = [
            int(x)
            for x in db.get("admins", [])
            if int(x) != target_id
        ]
        save_db(db)
        _refresh_fast_caches()
        context.user_data.pop("admin_action", None)

        await message.reply_text(
            f"{EMOJI_6} <b>تم حذف المشرف بنجاح.</b>\n\n"
            f"👤 ID: <code>{target_id}</code>",
            parse_mode="HTML",
            reply_markup=get_back_admin_keyboard()
        )
        return True

    # ========================================================
    # حظر
    # ========================================================

    if action == "ban_user":

        if not message.text:

            await message.reply_text(
                f"{EMOJI_3} "
                f"أرسل ID صحيح."
            )

            return True

        try:

            target_id = int(
                message.text.strip()
            )

        except ValueError:

            await message.reply_text(
                f"{EMOJI_3} "
                f"الـ ID يجب أن يكون أرقاماً فقط."
            )

            return True

        if target_id == ADMIN_ID:

            await message.reply_text(
                f"{EMOJI_3} "
                f"لا يمكنك حظر الأدمن."
            )

            return True

        if target_id not in db[
            "banned_users"
        ]:

            db[
                "banned_users"
            ].append(target_id)

        save_db(db)
        _refresh_fast_caches()

        context.user_data.pop(
            "admin_action",
            None
        )

        await message.reply_text(
            f"{EMOJI_3} "
            f"<b>تم حظر المستخدم:</b>\n"
            f"<code>{target_id}</code>",
            parse_mode="HTML"
        )

        return True

    # ========================================================
    # فك الحظر
    # ========================================================

    if action == "unban_user":

        if not message.text:

            await message.reply_text(
                f"{EMOJI_3} "
                f"أرسل ID صحيح."
            )

            return True

        try:

            target_id = int(
                message.text.strip()
            )

        except ValueError:

            await message.reply_text(
                f"{EMOJI_3} "
                f"الـ ID يجب أن يكون أرقاماً فقط."
            )

            return True

        if target_id in db[
            "banned_users"
        ]:

            db[
                "banned_users"
            ].remove(target_id)

        save_db(db)
        _refresh_fast_caches()

        context.user_data.pop(
            "admin_action",
            None
        )

        await message.reply_text(
            f"{EMOJI_6} "
            f"<b>تم فك حظر المستخدم:</b>\n"
            f"<code>{target_id}</code>",
            parse_mode="HTML"
        )

        return True

    return False


# ============================================================
# روابط المنصات
# ============================================================

def is_youtube_url(url):

    return bool(
        re.search(
            r"(youtube\.com|youtu\.be|youtube-nocookie\.com)",
            url,
            re.IGNORECASE
        )
    )


def is_tiktok_url(url):

    return bool(
        re.search(
            r"(tiktok\.com|vm\.tiktok\.com)",
            url,
            re.IGNORECASE
        )
    )


# ============================================================
# إعدادات yt-dlp
# ============================================================

def get_youtube_cookies_file():
    """
    العثور على ملف Cookies الخاص بيوتيوب.
    يمكن تحديد المسار من YOUTUBE_COOKIES_FILE،
    أو وضع youtube_cookies.txt / cookies.txt بجانب الملف.
    """
    candidates = []

    env_path = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()

    if env_path:
        candidates.append(env_path)

    base_dir = os.path.dirname(os.path.abspath(__file__))

    candidates.extend([
        os.path.join(base_dir, "youtube_cookies.txt"),
        os.path.join(base_dir, "cookies.txt"),
        os.path.join(gettempdir(), "youtube_cookies.txt"),
        os.path.join(gettempdir(), "cookies.txt"),
    ])

    for path in candidates:
        try:
            if path and os.path.isfile(path) and os.path.getsize(path) > 20:
                return path
        except OSError:
            continue

    return None


def make_ydl_opts(youtube_mode=False):
    opts = {
        "outtmpl": os.path.join(
            gettempdir(),
            "%(title)s_%(id)s.%(ext)s"
        ),
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,

        # ملف واحد فيه الفيديو والصوت، حتى لا يحتاج التحميل إلى ffmpeg.
        "format": (
            "best[ext=mp4][acodec!=none][vcodec!=none][filesize<50M]/"
            "best[ext=mp4][acodec!=none][vcodec!=none]/"
            "best[acodec!=none][vcodec!=none][filesize<50M]/"
            "best[acodec!=none][vcodec!=none]"
        ),

        "noplaylist": True,
        "socket_timeout": 60,
        "retries": 3,
        "fragment_retries": 3,
        "file_access_retries": 2,
        "extractor_retries": 2,
        "concurrent_fragment_downloads": 4,
        "continuedl": True,
        "overwrites": False,
        "nocheckcertificate": True,
        "geo_bypass": True,

        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    if youtube_mode:
        # لا نطلب video-only + audio-only لأن دمجهما يحتاج ffmpeg.
        opts["format"] = (
            "best[ext=mp4][acodec!=none][vcodec!=none][filesize<50M]/"
            "best[ext=mp4][acodec!=none][vcodec!=none]/"
            "best[acodec!=none][vcodec!=none][filesize<50M]/"
            "best[acodec!=none][vcodec!=none]"
        )

        cookies_file = get_youtube_cookies_file()

        if cookies_file:
            opts["cookiefile"] = cookies_file
            logger.info(
                "YouTube cookies enabled: %s",
                cookies_file
            )
        else:
            logger.warning(
                "YouTube cookies file not found. "
                "Set YOUTUBE_COOKIES_FILE or add youtube_cookies.txt."
            )

        opts["extractor_args"] = {
            "youtube": {
                "player_client": [
                    "web",
                    "mweb",
                    "web_embedded"
                ]
            }
        }

    return opts


# ============================================================
# تحميل الفيديو
# ============================================================

def download_video_sync(url):

    def extract_and_find_file(youtube_mode=False):

        opts = make_ydl_opts(
            youtube_mode=youtube_mode
        )

        with yt_dlp.YoutubeDL(
            opts
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            prepared = ydl.prepare_filename(
                info
            )

            possible_files = [
                prepared,
                os.path.splitext(
                    prepared
                )[0] + ".mp4",
                os.path.splitext(
                    prepared
                )[0] + ".mkv",
                os.path.splitext(
                    prepared
                )[0] + ".webm",
                os.path.splitext(
                    prepared
                )[0] + ".mov",
            ]

            # بعد الدمج قد يكون اسم الملف النهائي مختلفاً قليلاً
            if info.get("requested_downloads"):
                for requested in info.get(
                    "requested_downloads",
                    []
                ):
                    path = requested.get(
                        "filepath"
                    )

                    if path:
                        possible_files.append(
                            path
                        )

            for path in dict.fromkeys(
                possible_files
            ):

                if os.path.exists(path):

                    return path

            # البحث عن أحدث ملف فيديو في temp عند عدم تطابق الاسم
            temp_dir = gettempdir()
            candidates = []

            for name in os.listdir(
                temp_dir
            ):

                full_path = os.path.join(
                    temp_dir,
                    name
                )

                if not os.path.isfile(
                    full_path
                ):
                    continue

                if name.endswith(
                    (
                        ".mp4",
                        ".mkv",
                        ".webm",
                        ".mov"
                    )
                ):

                    try:
                        candidates.append(
                            (
                                os.path.getmtime(
                                    full_path
                                ),
                                full_path
                            )
                        )
                    except Exception:
                        pass

            if candidates:
                candidates.sort(
                    reverse=True
                )

                return candidates[0][1]

            raise FileNotFoundError(
                "لم يتم العثور على الملف بعد التحميل."
            )

    try:

        return extract_and_find_file()

    except Exception as e:

        error_text = str(e).lower()

        # YouTube يتغير باستمرار؛ إعادة المحاولة بعد تحديث yt-dlp
        youtube_error = (
            "youtube" in url.lower()
            and (
                "sign in to confirm" in error_text
                or "confirm you’re not a bot" in error_text
                or "confirm you're not a bot" in error_text
                or "requested format is not available" in error_text
                or "unable to extract" in error_text
                or "nsig" in error_text
                or "signature" in error_text
                or "po token" in error_text
                or "player response" in error_text
                or "http error 403" in error_text
            )
        )

        if youtube_error:

            logger.warning(
                "YouTube extractor error detected; trying yt-dlp update."
            )

            try:
                return extract_and_find_file(
                    youtube_mode=True
                )
            except Exception as alternate_error:
                logger.warning(
                    "YouTube alternate player clients failed: %s",
                    alternate_error
                )

            if update_yt_dlp_tiktok_fallback():

                return extract_and_find_file(
                    youtube_mode=True
                )

        if (
            "tiktok" in url.lower()
            and (
                "unable to extract universal data for rehydration"
                in error_text
                or "universal data" in error_text
            )
        ):

            logger.warning(
                "TikTok extractor error detected; trying yt-dlp fallback update."
            )

            if update_yt_dlp_tiktok_fallback():

                return extract_and_find_file()

        raise


# ============================================================
# تنظيف الملف
# ============================================================

def remove_file(path):

    if not path:
        return

    try:

        if os.path.exists(path):
            os.remove(path)

    except Exception as e:

        logger.warning(
            "File remove error: %s",
            e
        )


# ============================================================
# معالجة الروابط ورسائل الأدمن
# ============================================================

async def handle_url(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    add_user(user)

    # ========================================================
    # الأدمن
    # ========================================================

    if is_admin(user.id):

        handled = await handle_admin_message(
            update,
            context
        )

        if handled:
            return

    # ========================================================
    # الحظر
    # ========================================================

    if is_banned(user.id):

        await update.effective_message.reply_text(
            f"{EMOJI_3} "
            f"<b>تم حظرك من استخدام البوت.</b>",
            parse_mode="HTML"
        )

        return

    # ========================================================
    # الاشتراك
    # ========================================================

    if not await check_force_subscription(
        update,
        context
    ):
        return

    # ========================================================
    # التأكد من وجود نص
    # ========================================================

    url = (
        update.effective_message.text or ""
    ).strip()

    if not url:
        return

    # ========================================================
    # المنصة المختارة
    # ========================================================

    platform = context.user_data.get(
        "selected_platform"
    )

    if not platform:

        await update.effective_message.reply_text(
            f"{EMOJI_3} "
            f"يرجى اختيار المنصة أولاً عبر /start"
        )

        return

    # ========================================================
    # فحص الرابط
    # ========================================================

    if platform == "TikTok":

        if not is_tiktok_url(url):

            await update.effective_message.reply_text(
                f"{EMOJI_3} "
                f"هذا ليس رابط TikTok صحيحاً."
            )

            return

    # ========================================================
    # رسالة التحميل
    # ========================================================

    download_message = get_message_setting(
        "download_status",
        db["settings"].get("download_text", MESSAGE_DEFAULTS["download_status"])
    )

    try:
        # نُبقي HTML آمناً، ثم نسمح فقط بصيغة Premium Emoji الخاصة بنا.
        raw_download_message = str(download_message)
        protected, saved = _protect_custom_emoji_tokens(raw_download_message)
        protected = html.escape(protected)
        protected = _restore_custom_emoji_tokens(protected, saved)
        download_message = _render_custom_emoji_markup(protected)
    except Exception:
        download_message = "⏳ جاري تحميل الفيديو..."

    status_message = await (
        update.effective_message.reply_text(
            f"{EMOJI_2} "
            f"{download_message}\n\n"

            f"{EMOJI_4} المنصة: "
            f"<b>{html.escape(platform)}</b>",
            parse_mode="HTML"
        )
    )

    file_path = None

    try:

        # ====================================================
        # تحميل خارج Event Loop
        # ====================================================

        file_path = await asyncio.to_thread(
            download_video_sync,
            url
        )

        if (
            not file_path
            or not os.path.exists(file_path)
        ):

            raise Exception(
                "لم يتم تحميل الملف."
            )

        # ====================================================
        # الحجم
        # ====================================================

        file_size = os.path.getsize(
            file_path
        )

        if file_size > MAX_FILE_SIZE_BYTES:

            size_mb = (
                file_size
                / (1024 * 1024)
            )

            await status_message.edit_text(
                f"{EMOJI_3} "
                f"<b>حجم الفيديو كبير جداً</b>\n\n"

                f"{EMOJI_4} الحجم: "
                f"<b>{size_mb:.1f} MB</b>\n"

                f"{EMOJI_9} الحد الأقصى: "
                f"<b>{MAX_FILE_SIZE_MB} MB</b>",
                parse_mode="HTML"
            )

            return

        # ====================================================
        # إرسال الفيديو
        # ====================================================

        await status_message.edit_text(
            _render_custom_emoji_markup(get_message_setting("sending_status", MESSAGE_DEFAULTS["sending_status"])),
            parse_mode="HTML"
        )

        with open(
            file_path,
            "rb"
        ) as video_file:

            await update.effective_message.reply_video(
                video=video_file,

                caption=format_welcome_text(
                    get_message_setting("success", MESSAGE_DEFAULTS["success"]),
                    user.first_name or "",
                    "@" + user.username if user.username else "لا يوجد",
                    user.id
                ).replace("{platform}", html.escape(platform)),

                parse_mode="HTML",

                supports_streaming=True
            )

        increment_download(
            user.id
        )

        context.user_data.pop(
            "selected_platform",
            None
        )

        try:

            await status_message.delete()

        except Exception:

            pass

    except Exception as e:

        logger.exception(
            "Download error"
        )

        error_text = str(e)

        if len(error_text) > 500:

            error_text = (
                error_text[:500]
                + "..."
            )

        try:

            await status_message.edit_text(
                _render_custom_emoji_markup(get_message_setting("download_error", MESSAGE_DEFAULTS["download_error"]).replace("{error}", html.escape(error_text))),
                parse_mode="HTML"
            )

        except Exception:

            try:

                await update.effective_message.reply_text(
                    f"{EMOJI_3} "
                    f"حدث خطأ أثناء تحميل الفيديو."
                )

            except Exception:

                pass

    finally:

        remove_file(
            file_path
        )


# ============================================================
# /help
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text_value = get_message_setting("help", MESSAGE_DEFAULTS["help"])
    await update.effective_message.reply_text(
        _render_custom_emoji_markup(text_value),
        parse_mode="HTML"
    )


# ============================================================
# /cancel
# ============================================================

async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user or not is_admin(
        user.id
    ):
        return

    context.user_data.pop(
        "admin_action",
        None
    )

    await update.effective_message.reply_text(
        f"{EMOJI_6} "
        f"<b>تم إلغاء العملية.</b>",
        parse_mode="HTML"
    )


# ============================================================
# Error Handler
# ============================================================

async def error_handler(
    update,
    context
):

    error = context.error

    logger.exception(
        "Unhandled exception: %s",
        error
    )


# ============================================================
# تشغيل البوت
# ============================================================

def main():

    update_yt_dlp()

    if not BOT_TOKEN:

        print(
            "❌ لم يتم العثور على BOT_TOKEN. أضفه في Railway Variables."
        )

        return

    print(
        "======================================"
    )

    print(
        "🤖 Social Downloader Bot"
    )

    print(
        "======================================"
    )

    print(
        f"👑 Admin ID: {ADMIN_ID}"
    )

    print(
        f"👥 Users: {get_user_count()}"
    )

    print(
        f"💾 Database: {DB_FILE}"
    )

    print(
        f"📢 Force Sub Channels: {len(get_force_channels())}"
    )

    print(
        "🚀 Starting bot..."
    )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        # يسمح بمعالجة تحديثات عدة مستخدمين بالتوازي.
        .concurrent_updates(32)
        # زيادة اتصالات Telegram المتاحة لتقليل انتظار الطلبات.
        .connection_pool_size(64)
        .pool_timeout(10.0)
        .build()
    )

    # ========================================================
    # Commands
    # ========================================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    app.add_handler(
        CommandHandler(
            "cancel",
            cancel_command
        )
    )

    # ========================================================
    # Callback Buttons
    # ========================================================

    app.add_handler(
        CallbackQueryHandler(
            button_callback
        )
    )

    # ========================================================
    # النصوص
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            handle_url
        )
    )

    # ========================================================
    # صور وفيديوهات الأدمن
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (filters.PHOTO | filters.VIDEO),
            handle_url
        )
    )

    # ========================================================
    # ملفات الأدمن (استرجاع قاعدة الأعضاء)
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.Document.ALL,
            handle_url
        )
    )

    # ========================================================
    # Error Handler
    # ========================================================

    app.add_error_handler(
        error_handler
    )

    print(
        "======================================"
    )

    print(
        "✅ البوت يعمل الآن."
    )

    print(
        "======================================"
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )



# ============================================================
# V3 ENHANCEMENTS
# ============================================================

_ORIGINAL_ADMIN_CALLBACK = admin_callback
_ORIGINAL_HANDLE_ADMIN_MESSAGE = handle_admin_message
_ORIGINAL_BUTTON_CALLBACK = button_callback
_ORIGINAL_HANDLE_URL = handle_url

ENHANCED_MESSAGE_DEFAULTS = {
    "home": "",
    "new_user_welcome": "",
    "platform_tiktok": "تم اختيار TikTok\n\nأرسل رابط الفيديو الآن.",
    "download_status": "⏳ جاري تحميل الفيديو، يرجى الانتظار...",
    "sending_status": "🚀 جاري إرسال الفيديو...",
    "success": "✅ تم تحميل الفيديو بنجاح\n\nالمصدر: {platform}",
    "download_error": "❌ فشل تحميل الفيديو\n\n{error}",
    "help": "طريقة الاستخدام:\n\n/start - فتح البوت\n/referrals - نظام الإحالات\n/top - المتصدرون\n/help - المساعدة",
    "force_sub": "يجب عليك الاشتراك في القنوات المطلوبة أولاً.",
    "force_sub_done": "بعد الاشتراك اضغط على زر التحقق.",
    "maintenance": "🛠 البوت في وضع الصيانة حالياً.\n\nحاول مرة أخرى لاحقاً.",
    "referral_welcome": "🎁 نظام الإحالات\n\nشارك رابطك مع أصدقائك واحصل على نقاط عند دخول مستخدم جديد من رابطك.",
    "referral_stats": "🎁 إحالاتك: {referrals}\n🏆 نقاطك: {points}\n🔗 رابطك:\n{link}",
    "leaderboard": "🏆 المتصدرون\n\n{leaders}",
    "referral_new": "🎉 تمت إضافة إحالة جديدة إلى حسابك!\n\nعدد الإحالات: {referrals}\nالنقاط: {points}",
    "referral_invalid": "⚠️ رابط الإحالة غير صالح.",
    "duplicate_referral": "ℹ️ تم تسجيل حسابك من قبل، ولا يمكن احتساب الإحالة مرة أخرى.",
    "no_platform": "يرجى اختيار المنصة أولاً عبر /start.",
    "banned": "🚫 تم حظرك من استخدام البوت.",
}
for _k, _v in ENHANCED_MESSAGE_DEFAULTS.items():
    MESSAGE_DEFAULTS.setdefault(_k, _v)

def _ensure_enhanced_settings():
    s = db.setdefault("settings", {})
    s.setdefault("maintenance_enabled", False)
    s.setdefault("maintenance_text", ENHANCED_MESSAGE_DEFAULTS["maintenance"])
    s.setdefault("referrals_enabled", True)
    s.setdefault("referral_points", 1)
    s.setdefault("referral_leaders_limit", 10)
    s.setdefault("referral_claimed_users", {})
    s.setdefault("button_styles", {})
    s.setdefault("custom_emoji_library", [])
    if not isinstance(s["referral_claimed_users"], dict):
        s["referral_claimed_users"] = {}
    if not isinstance(s["button_styles"], dict):
        s["button_styles"] = {}
    if not isinstance(s["custom_emoji_library"], list):
        s["custom_emoji_library"] = []
    for eid in AVAILABLE_CUSTOM_EMOJI_IDS:
        if eid not in s["custom_emoji_library"]:
            s["custom_emoji_library"].append(eid)
    save_db(db, create_backup=False)

_ensure_enhanced_settings()

def _repair_repeated_button_emojis():
    # إصلاح حالة قديمة كان فيها نفس Premium Emoji يظهر على كل الأزرار.
    settings = db.setdefault("settings", {})
    button_settings = settings.setdefault("button_settings", {})
    pairs = []
    for key in BUTTON_DEFAULTS:
        item = button_settings.get(key)
        if isinstance(item, dict):
            eid = str(item.get("emoji_id", "") or "").strip()
            if eid:
                pairs.append((key, eid))
    if len(pairs) < 3 or len({eid for _, eid in pairs}) != 1:
        return
    shared = pairs[0][1]
    # لا نغيّر إعداداً مقصوداً إذا كان مطابقاً للإيموجي الافتراضي لنفس الزر.
    if any(str(default_emoji) == shared for _, default_emoji in BUTTON_DEFAULTS.values()):
        return
    changed = False
    for key, _default in BUTTON_DEFAULTS.items():
        item = button_settings.get(key)
        if isinstance(item, dict) and str(item.get("emoji_id", "") or "").strip() == shared:
            item["emoji_id"] = ""
            button_settings[key] = item
            changed = True
    if changed:
        save_db(db)

_repair_repeated_button_emojis()

def _enhanced_message(key, fallback=None, **values):
    fallback = ENHANCED_MESSAGE_DEFAULTS.get(key, fallback or "")
    try:
        value = get_message_setting(key, fallback)
        protected, saved = _protect_custom_emoji_tokens(value)
        if values:
            protected = protected.format_map(SafeFormatDict(values))
        protected = _restore_custom_emoji_tokens(protected, saved)
        rendered = _render_custom_emoji_markup(protected)
        return _replace_plain_emojis(rendered)
    except Exception:
        return _replace_plain_emojis(_render_custom_emoji_markup(fallback))

def _button_style(key, fallback="primary"):
    value = str(db["settings"].get("button_styles", {}).get(key, fallback) or fallback).lower()
    return "primary" if value == "default" else (value if value in {"primary", "success", "danger"} else fallback)

# Premium Emoji requested by the owner: glyph -> Telegram custom emoji ID.
REQUESTED_CUSTOM_EMOJI_MAP = {
    '⭐': "5890978075201509010",
    '✅': "5891033729387731017",
    '☑️': "5891264747088647482",
    '♦️': "5891150947635173714",
    '💪': "5888979137292408953",
    '⚜️': "5890944978183528164",
    '📞': "5891198458563402576",
    '✈️': "5891223481042868350",
    '👑': "5888585967396198556",
    '🌟': "5888675006363211723",
    '❤️': "5888684446701328138",
    '🆕': "5890711263243147926",
    '✔️': "5891235511246264255",
    '‼️': "5888630540566796058",
    '💯': "5891061762639271906",
    '💎': "5890946721940248671",
    '🛍': "5890989903541441900",
    '⌛': "5891071937416795775",
    '🔝': "5891162831809681617",
    '💰': "5890866066749397234",
    '🥇': "5891182846357281226",
    '😭': "5890933368886924480",
    '🛡': "5891225499677496831",
    '🔜': "5890723834612422946",
    '☠': "5890969691425347748",
    '☄️': "5890795783904565270",
    '💫': "5890891742063893790",
    '🖤': "5888903253810222656",
    '🤍': "5890932136231311080",
    '🧡': "5891075716988016811",
    '😍': "5890808771885668859",
    '🔥': "5888663955412359816",
    '😢': "5890864005165096780",
    '🟢': "5116425257883796621",
    '🆓': "5116503323209368474",
    '📱': "5118372789329331110",
    '⭕️': "5118775829060387648",
    '📶': "5139127540182418615",
    '🛜': "5136607107344237807",
    '🔐': "5139095048754824143",
    '🧑\u200d🦱': "5136867713074857101",
    '🍏': "5136688518449333393",
    '🛒': "5136444126220256119",
    '🤖': "5136697855708234673",
    '💻': "5136382085417665757",
    '💙': "5136828508613379215",
    '💬': "5136634337436894358",
    '📹': "5138796703146574994",
    '💩': "5138693920284214322",
    '🏳': "5136758303077958598",
}

# Match all supplied custom emoji glyphs, longest first (e.g. ❤️ / ☄️ / ☑️).
_REQUESTED_EMOJI_RE = re.compile(
    "|".join(re.escape(x) for x in sorted(REQUESTED_CUSTOM_EMOJI_MAP, key=len, reverse=True))
)

def _replace_plain_emojis(text):
    """Replace normal emoji in visible text with Telegram Premium Emoji markup."""
    if text is None:
        return ""
    value = str(text)
    parts = re.split(r'(<tg-emoji\\b[^>]*>.*?</tg-emoji>)', value, flags=re.S | re.I)
    for i in range(0, len(parts), 2):
        parts[i] = _REQUESTED_EMOJI_RE.sub(
            lambda m: f'<tg-emoji emoji-id="{REQUESTED_CUSTOM_EMOJI_MAP[m.group(0)]}">{m.group(0)}</tg-emoji>',
            parts[i]
        )
    return "".join(parts)

def _make_button(text, callback_data=None, url=None, key="", emoji_id=None, style=None):
    # Never expose ordinary emoji in buttons; use a Telegram custom emoji icon instead.
    raw_text = str(text or "")
    plain_emoji_ids = [REQUESTED_CUSTOM_EMOJI_MAP[e] for e in _REQUESTED_EMOJI_RE.findall(raw_text)]
    clean_text = _REQUESTED_EMOJI_RE.sub("", raw_text).strip()
    data = {"text": clean_text or raw_text}
    if callback_data is not None:
        data["callback_data"] = callback_data
    if url is not None:
        data["url"] = url

    # Default: primary. Add/enable => success. Delete/disable/ban/remove => danger.
    action_key = f"{key} {callback_data or ''} {raw_text}".lower()
    if style is not None:
        chosen = style
    elif any(x in action_key for x in ("enable", "activate", "add_", "add ", "تفعيل", "إضافة", "مفعّل", "مفعلة", "مفعّلة")):
        chosen = "success"
    elif any(x in action_key for x in ("disable", "delete", "remove", "ban", "clear", "حذف", "تعطيل", "حظر", "إزالة", "غير مفعل")):
        chosen = "danger"
    else:
        chosen = _button_style(key, "primary") if key else "primary"
    if chosen != "default":
        data["style"] = chosen

    eid = emoji_id or (button_emoji(key, "") if key else "")
    if not eid and plain_emoji_ids:
        eid = plain_emoji_ids[0]
    if eid:
        data["icon_custom_emoji_id"] = eid
    try:
        return InlineKeyboardButton(**data)
    except TypeError:
        data.pop("style", None)
        try:
            return InlineKeyboardButton(**data)
        except TypeError:
            data.pop("icon_custom_emoji_id", None)
            return InlineKeyboardButton(**data)

# -------------------- Referrals --------------------

def _referral_stats(user_id):
    r = db.get("users", {}).get(str(user_id), {})
    try:
        referrals = max(0, int(r.get("referrals", 0)))
    except Exception:
        referrals = 0
    try:
        points = max(0, int(r.get("referral_points", referrals)))
    except Exception:
        points = referrals
    return referrals, points

def _referral_link(username, user_id):
    return f"https://t.me/{username}?start=ref_{user_id}" if username else ""

def _register_referral(new_user_id, payload):
    s = db["settings"]
    if not s.get("referrals_enabled", True):
        return None
    payload = str(payload or "")
    if payload.startswith("ref_"):
        payload = payload[4:]
    if not payload.isdigit():
        return None
    referrer_id = int(payload)
    new_id = int(new_user_id)
    if referrer_id == new_id:
        return "self"
    if str(referrer_id) not in db["users"]:
        return "invalid"
    claimed = s.setdefault("referral_claimed_users", {})
    if str(new_id) in claimed:
        return "duplicate"
    referrer = db["users"].get(str(referrer_id))
    if not isinstance(referrer, dict):
        return "invalid"
    referrer["referrals"] = int(referrer.get("referrals", 0) or 0) + 1
    referrer["referral_points"] = int(referrer.get("referral_points", 0) or 0) + int(s.get("referral_points", 1) or 1)
    claimed[str(new_id)] = referrer_id
    db["users"][str(new_id)]["referred_by"] = referrer_id
    save_db(db)
    return referrer_id

def _leaderboard_lines(limit=10):
    rows = []
    for uid, r in db.get("users", {}).items():
        if not isinstance(r, dict):
            continue
        referrals, points = _referral_stats(uid)
        if referrals or points:
            name = str(r.get("first_name") or r.get("username") or uid)
            rows.append((points, referrals, name))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    result = []
    for i, (points, referrals, name) in enumerate(rows[:int(limit)], 1):
        result.append(f"<b>{i}.</b> {html.escape(name[:40])} — إحالات: <b>{referrals}</b> | نقاط: <b>{points}</b>")
    return "\n".join(result) if result else "لا توجد إحالات حتى الآن."

def referral_keyboard():
    return InlineKeyboardMarkup([
        [_make_button("🎁 إحالاتي", "referral_stats", key="referral_stats")],
        [_make_button("🏆 المتصدرون", "referral_leaders", key="referral_leaders")],
        [_make_button("🔙 الرئيسية", "back_home", key="back_home")],
    ])

async def referrals_command(update, context):
    user = update.effective_user
    if not user:
        return
    if is_banned(user.id):
        await update.effective_message.reply_text(_enhanced_message("banned"), parse_mode="HTML")
        return
    if not db["settings"].get("referrals_enabled", True):
        await update.effective_message.reply_text("نظام الإحالات غير متاح حالياً.")
        return
    add_user(user)
    me = await context.bot.get_me()
    referrals, points = _referral_stats(user.id)
    await update.effective_message.reply_text(
        _enhanced_message("referral_stats", referrals=referrals, points=points,
                           link=html.escape(_referral_link(me.username, user.id))),
        parse_mode="HTML", reply_markup=referral_keyboard()
    )

async def top_command(update, context):
    user = update.effective_user
    if not user:
        return
    await update.effective_message.reply_text(
        _enhanced_message("leaderboard", leaders=_leaderboard_lines(
            int(db["settings"].get("referral_leaders_limit", 10) or 10)
        )),
        parse_mode="HTML", reply_markup=referral_keyboard()
    )

# -------------------- Maintenance --------------------

def _maintenance_enabled():
    return bool(db["settings"].get("maintenance_enabled", False))

def _maintenance_text():
    return _enhanced_message("maintenance", db["settings"].get("maintenance_text", ""))

def maintenance_keyboard():
    return InlineKeyboardMarkup([
        [_make_button("🟢 تفعيل" if not _maintenance_enabled() else "🔴 تعطيل",
                      "maintenance_toggle", key="admin_maintenance")],
        [_make_button("✏️ تخصيص رسالة الصيانة", "maintenance_message", key="admin_welcome_text")],
        [_make_button("🔙 رجوع", "admin_panel", key="back_home")],
    ])

def referrals_admin_keyboard():
    enabled = bool(db["settings"].get("referrals_enabled", True))
    return InlineKeyboardMarkup([
        [_make_button("🟢 تفعيل" if not enabled else "🔴 تعطيل", "referrals_toggle", key="admin_referrals")],
        [_make_button("🔢 نقاط الإحالة", "referral_points_set", key="admin_referrals")],
        [_make_button("🏆 عدد المتصدرين", "referral_limit_set", key="admin_referrals")],
        [_make_button("🔙 رجوع", "admin_panel", key="back_home")],
    ])

# -------------------- User start/home --------------------

async def start(update, context):
    user = update.effective_user
    if not user:
        return
    uid = str(user.id)
    is_new = uid not in db.get("users", {})
    payload = context.args[0].strip() if context.args else ""
    add_user(user)

    referral_result = _register_referral(user.id, payload) if is_new else None
    if is_banned(user.id):
        await update.effective_message.reply_text(_enhanced_message("banned"), parse_mode="HTML")
        return
    if _maintenance_enabled() and not is_admin(user.id):
        await update.effective_message.reply_text(_maintenance_text(), parse_mode="HTML")
        return

    if isinstance(referral_result, int):
        try:
            refs, points = _referral_stats(referral_result)
            await context.bot.send_message(
                referral_result,
                _enhanced_message("referral_new", referrals=refs, points=points),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning("Referral notification failed: %s", e)

    if not await check_force_subscription(update, context):
        return

    context.user_data.pop("selected_platform", None)
    if is_new:
        welcome = _enhanced_message("new_user_welcome", "").strip()
        if welcome:
            welcome = format_welcome_text(welcome, user.first_name or "عضو جديد",
                                           "@" + user.username if user.username else "لا يوجد", user.id)
            try:
                await update.effective_message.reply_text(welcome, parse_mode="HTML")
            except Exception:
                pass
    await send_home(update, context)

def get_platform_keyboard():
    return InlineKeyboardMarkup([
        [_make_button(button_text("platform_tiktok", "TikTok"), "platform_tiktok",
                      key="platform_tiktok", emoji_id=button_emoji("platform_tiktok", ""))],
        [_make_button("🎁 نظام الإحالات", "referrals", key="referrals")],
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup([[
        _make_button(button_text("back_home", "🔙 رجوع"), "back_home",
                     key="back_home", emoji_id=button_emoji("back_home", ""))
    ]])

# -------------------- All-message editor --------------------

MESSAGE_LABELS = {
    "home": "🏠 الرئيسية",
    "new_user_welcome": "👋 ترحيب العضو الجديد",
    "platform_tiktok": "🎵 اختيار TikTok",
    "download_status": "⏳ بدء التحميل",
    "sending_status": "📤 إرسال الفيديو",
    "success": "✅ نجاح التحميل",
    "download_error": "❌ خطأ التحميل",
    "help": "❓ المساعدة",
    "force_sub": "🔐 الاشتراك الإجباري",
    "force_sub_done": "✔️ بعد الاشتراك",
    "maintenance": "🛠 الصيانة",
    "referral_stats": "🎁 إحالاتي",
    "leaderboard": "🏆 المتصدرون",
    "referral_new": "🎉 إحالة جديدة",
    "no_platform": "📱 لم يتم اختيار منصة",
    "banned": "🚫 المحظور",
}

def message_editor_text():
    return _replace_plain_emojis((
        f"{EMOJI_5} <b>تخصيص كل رسائل البوت</b> {EMOJI_5}\n\n"
        "اختر أي رسالة ثم أرسل الكليشة الجديدة.\n"
        "يمكنك استخدام HTML والمتغيرات المتاحة.\n\n"
        "<code>{first_name}</code> <code>{username}</code> <code>{user_id}</code>\n"
        "<code>{platform}</code> <code>{error}</code> <code>{referrals}</code>\n"
        "<code>{points}</code> <code>{link}</code> <code>{leaders}</code>"
    ))

def message_editor_keyboard():
    # لا نضع Premium Emoji موحّداً على كل أزرار محرر الرسائل.
    rows = []
    for key, label in MESSAGE_LABELS.items():
        rows.append([_make_button(label, f"message_edit_{key}", style="primary", emoji_id="")])
    rows.append([_make_button("🔙 رجوع للوحة الأدمن", "admin_panel", key="back_home")])
    return InlineKeyboardMarkup(rows)

# -------------------- Button styles --------------------

def set_button_style(key, style):
    if key not in BUTTON_DEFAULTS and key not in {"referrals", "referral_stats", "referral_leaders", "admin_maintenance", "admin_referrals", "admin_copy_source"}:
        return False
    if style not in {"default", "primary", "success", "danger"}:
        return False
    db["settings"].setdefault("button_styles", {})[key] = style
    save_db(db)
    return True

def button_style_keyboard(key):
    current = _button_style(key, "primary")
    rows = []
    for value, label in [
        ("primary", "🔵 أساسي"),
        ("success", "🟢 نجاح"),
        ("danger", "🔴 تحذير"),
    ]:
        mark = " ✓" if current == value else ""
        rows.append([_make_button(label + mark, f"button_style_{key}_{value}", style=value)])
    rows.append([_make_button("🔙 رجوع", "admin_buttons", key="back_home")])
    return InlineKeyboardMarkup(rows)

def button_editor_text():
    return _replace_plain_emojis((
        f"{EMOJI_5} <b>تخصيص الأزرار والألوان</b> {EMOJI_5}\n\n"
        "غيّر اسم الزر والإيموجي المميز من الأزرار الحالية، "
        "وغيّر النمط من 🎨.\n\n"
        "الشفاف/العادي = زر Telegram طبيعي بدون لون مميز."
    ))

def button_editor_keyboard():
    rows = []
    for key, (default_text, default_emoji) in BUTTON_DEFAULTS.items():
        current = get_button_setting(key)
        rows.append([
            _make_button(current["text"], f"button_edit_{key}", key=key,
                         emoji_id=current["emoji_id"] or ""),
            _make_button("🎨", f"button_style_menu_{key}", key="admin_buttons")
        ])
    for key, label in [("referrals", "🎁 الإحالات"), ("referral_stats", "📊 إحالاتي"), ("referral_leaders", "🏆 المتصدرون")]:
        rows.append([_make_button(label, f"button_style_menu_{key}", key="admin_buttons", emoji_id="")])
    rows.append([_make_button("🧹 إزالة Premium Emoji من كل الأزرار", "button_reset_all_emojis", style="danger", emoji_id="")])
    rows.append([_make_button("🔙 رجوع للوحة الأدمن", "admin_panel", key="back_home")])
    return InlineKeyboardMarkup(rows)

# -------------------- Admin panel --------------------

def admin_panel_text():
    return (
        f"{EMOJI_5} <b>لوحة تحكم الأدمن</b> {EMOJI_5}\n\n"
        f"{EMOJI_4} المستخدمون: <b>{get_user_count()}</b>\n"
        f"{EMOJI_2} التحميلات: <b>{get_download_count()}</b>\n"
        f"{EMOJI_9} الاشتراك الإجباري: <b>{'🟢 مفعّل' if db['settings'].get('force_sub_enabled') else '🔴 متوقف'}</b>\n"
        f"🛠 وضع الصيانة: <b>{'🟢 مفعّل' if _maintenance_enabled() else '🔴 متوقف'}</b>\n"
        f"🎁 الإحالات: <b>{'🟢 مفعّلة' if db['settings'].get('referrals_enabled', True) else '🔴 متوقفة'}</b>\n"
        f"👑 المشرفون الإضافيون: <b>{len(get_admins())}</b>\n\n"
        "اختر العملية المطلوبة:"
    )

def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            _make_button(button_text("admin_stats", "📊 الإحصائيات"), "admin_stats", key="admin_stats"),
            _make_button(button_text("admin_broadcast", "📢 إذاعة"), "admin_broadcast", key="admin_broadcast"),
        ],
        [
            _make_button(button_text("admin_welcome_photo", "📸 ترحيب صورة"), "admin_welcome_photo", key="admin_welcome_photo"),
            _make_button(button_text("admin_welcome_video", "🎬 ترحيب فيديو"), "admin_welcome_video", key="admin_welcome_video"),
        ],
        [
            _make_button(button_text("admin_welcome_text", "✏️ نص الترحيب"), "admin_welcome_text", key="admin_welcome_text"),
            _make_button(button_text("admin_delete_media", "🗑 حذف ميديا الترحيب"), "admin_delete_media", key="admin_delete_media"),
        ],
        [
            _make_button(button_text("admin_force_sub", "🔐 الاشتراك الإجباري"), "admin_force_sub", key="admin_force_sub"),
            _make_button("🛠 وضع الصيانة", "admin_maintenance", key="admin_maintenance"),
        ],
        [
            _make_button("🎁 نظام الإحالات", "admin_referrals", key="admin_referrals"),
            _make_button("💬 تخصيص كل الرسائل", "admin_messages", key="admin_welcome_text"),
        ],
        [
            _make_button("🎨 الأزرار والألوان", "admin_buttons", key="admin_buttons"),
            _make_button(button_text("admin_download_text", "📝 رسالة التحميل"), "admin_download_text", key="admin_download_text"),
        ],
        [
            _make_button(button_text("admin_ban", "🚫 حظر مستخدم"), "admin_ban", key="admin_ban"),
            _make_button(button_text("admin_unban", "♻️ فك حظر"), "admin_unban", key="admin_unban"),
        ],
        [
            _make_button(button_text("admin_admins", "👑 المشرفون"), "admin_admins", key="admin_admins"),
            _make_button(button_text("admin_users", "👥 المستخدمون"), "admin_users", key="admin_users"),
        ],
        [
            _make_button("📤 تصدير الأعضاء", "admin_export_users", key="admin_users"),
            _make_button("📥 استرجاع الأعضاء", "admin_import_users", key="admin_users"),
        ],
        [_make_button("📄 نسخ النسخة الحالية", "admin_copy_source", key="admin_copy_source")],
        [_make_button("🔄 تحديث اللوحة", "admin_panel", key="admin_panel")],
    ])

# -------------------- Admin callback extension --------------------

async def admin_callback(update, context, data):
    query = update.callback_query
    if not query:
        return

    if data == "admin_copy_source":
        source_path = os.path.abspath(__file__)
        if not os.path.isfile(source_path):
            await query.answer("ملف النسخة الحالية غير موجود.", show_alert=True)
            return
        try:
            await query.message.reply_document(
                document=source_path,
                caption=_replace_plain_emojis("<b>📄 هذه هي النسخة الحالية من ملف البوت.</b>"),
                parse_mode="HTML"
            )
            await query.answer("تم إرسال النسخة الحالية من البوت.")
        except Exception as exc:
            logger.exception("Source copy failed: %s", exc)
            await query.answer("تعذر إرسال النسخة الحالية.", show_alert=True)
        return

    if data == "admin_maintenance":
        await query.edit_message_text(
            f"🛠 <b>وضع الصيانة</b>\n\nالحالة: <b>{'مفعّل' if _maintenance_enabled() else 'متوقف'}</b>\n\n"
            "عند التفعيل يتوقف التحميل للمستخدمين العاديين، والأدمن يستمر بالعمل.",
            parse_mode="HTML", reply_markup=maintenance_keyboard()
        )
        return

    if data == "maintenance_toggle":
        db["settings"]["maintenance_enabled"] = not _maintenance_enabled()
        save_db(db)
        await query.answer("تم تحديث وضع الصيانة.")
        await query.edit_message_text(
            f"🛠 <b>وضع الصيانة</b>\n\nالحالة: <b>{'مفعّل' if _maintenance_enabled() else 'متوقف'}</b>",
            parse_mode="HTML", reply_markup=maintenance_keyboard()
        )
        return

    if data == "maintenance_message":
        context.user_data["admin_action"] = "maintenance_message"
        await query.edit_message_text(
            "🛠 <b>رسالة الصيانة</b>\n\nأرسل الكليشة الجديدة الآن.\n\n/cancel",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[_make_button("🔙 رجوع", "admin_maintenance", key="back_home")]])
        )
        return

    if data == "admin_referrals":
        await query.edit_message_text(
            "🎁 <b>نظام الإحالات</b>\n\n"
            f"الحالة: <b>{'مفعّل' if db['settings'].get('referrals_enabled', True) else 'متوقف'}</b>\n"
            f"النقاط لكل إحالة: <b>{int(db['settings'].get('referral_points', 1) or 1)}</b>\n"
            f"المتصدرون: <b>{int(db['settings'].get('referral_leaders_limit', 10) or 10)}</b>\n\n"
            "منع التعدد هنا يمنع احتساب نفس حساب Telegram أكثر من مرة. Telegram Bot API لا يوفر IP/device للشخص.",
            parse_mode="HTML", reply_markup=referrals_admin_keyboard()
        )
        return

    if data == "referrals_toggle":
        db["settings"]["referrals_enabled"] = not bool(db["settings"].get("referrals_enabled", True))
        save_db(db)
        await query.answer("تم تحديث نظام الإحالات.")
        await query.edit_message_text(
            "🎁 <b>نظام الإحالات</b>\n\n"
            f"الحالة: <b>{'مفعّل' if db['settings']['referrals_enabled'] else 'متوقف'}</b>",
            parse_mode="HTML", reply_markup=referrals_admin_keyboard()
        )
        return

    if data == "referral_points_set":
        context.user_data["admin_action"] = "referral_points_set"
        await query.edit_message_text("🔢 أرسل نقاط الإحالة من 1 إلى 100000.\n\n/cancel", parse_mode="HTML",
                                       reply_markup=InlineKeyboardMarkup([[_make_button("🔙 رجوع", "admin_referrals", key="back_home")]]))
        return

    if data == "referral_limit_set":
        context.user_data["admin_action"] = "referral_limit_set"
        await query.edit_message_text("🏆 أرسل عدد المتصدرين من 3 إلى 50.\n\n/cancel", parse_mode="HTML",
                                       reply_markup=InlineKeyboardMarkup([[_make_button("🔙 رجوع", "admin_referrals", key="back_home")]]))
        return

    # Broadcast menu with optional transparent button.
    if data == "admin_broadcast":
        context.user_data.pop("admin_action", None)
        await query.edit_message_text(
            "📢 <b>إذاعة</b>\n\nاختر النوع:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [_make_button("📢 إذاعة عادية", "broadcast_plain", key="admin_broadcast")],
                [_make_button("🔗 إذاعة + زر شفاف", "broadcast_with_button", key="admin_broadcast")],
                [_make_button("🔙 رجوع", "admin_panel", key="back_home")],
            ])
        )
        return

    if data == "broadcast_plain":
        context.user_data["admin_action"] = "broadcast"
        await query.edit_message_text("📢 أرسل الآن الرسالة أو الصورة أو الفيديو أو الملف.\n\n/cancel", parse_mode="HTML",
                                       reply_markup=InlineKeyboardMarkup([[_make_button("🔙 إلغاء", "admin_panel", key="back_home")]]))
        return

    if data == "broadcast_with_button":
        context.user_data["admin_action"] = "broadcast_button_message"
        await query.edit_message_text(
            "🔗 <b>إذاعة + زر شفاف</b>\n\nأرسل المحتوى أولاً، وبعدها أرسل:\n"
            "<code>اسم الزر|https://example.com</code>\n\n"
            "الزر سيكون ملوّناً ويستخدم Premium Emoji.\n\n/cancel",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[_make_button("🔙 إلغاء", "admin_panel", key="back_home")]])
        )
        return

    if data == "button_reset_all_emojis":
        settings = db.setdefault("settings", {})
        button_settings = settings.setdefault("button_settings", {})
        for key, (default_text, _default_emoji) in BUTTON_DEFAULTS.items():
            item = button_settings.get(key, {})
            if not isinstance(item, dict):
                item = {}
            button_settings[key] = {
                "text": str(item.get("text", default_text) or default_text),
                "emoji_id": "",
            }
        save_db(db)
        await query.answer("تمت إزالة Premium Emoji من جميع الأزرار.", show_alert=True)
        await query.edit_message_text(
            button_editor_text(),
            parse_mode="HTML",
            reply_markup=button_editor_keyboard()
        )
        return

    if data.startswith("button_style_menu_"):
        key = data.replace("button_style_menu_", "", 1)
        await query.edit_message_text(
            f"🎨 <b>تغيير لون/نمط الزر</b>\n\nالحالي: <code>{html.escape(_button_style(key, 'primary'))}</code>",
            parse_mode="HTML", reply_markup=button_style_keyboard(key)
        )
        return

    if data.startswith("button_style_"):
        raw = data.replace("button_style_", "", 1)
        try:
            key, style = raw.rsplit("_", 1)
        except ValueError:
            await query.answer("بيانات غير صالحة.", show_alert=True)
            return
        if set_button_style(key, style):
            await query.answer("تم حفظ النمط.")
            await query.edit_message_text(button_editor_text(), parse_mode="HTML",
                                           reply_markup=button_editor_keyboard())
        else:
            await query.answer("النمط غير صالح.", show_alert=True)
        return

    if data.startswith("message_edit_"):
        key = data.replace("message_edit_", "", 1)
        if key not in MESSAGE_DEFAULTS:
            await query.answer("الرسالة غير موجودة.", show_alert=True)
            return
        context.user_data["admin_action"] = f"message_edit:{key}"
        current = get_message_setting(key, MESSAGE_DEFAULTS[key])
        await query.edit_message_text(
            f"✏️ <b>تعديل الرسالة</b>\n\nأرسل الكليشة الجديدة الآن.\n\n"
            f"<b>الحالية:</b>\n<code>{html.escape(current)}</code>\n\n"
            "المتغيرات: <code>{first_name}</code> <code>{username}</code> <code>{user_id}</code> "
            "<code>{platform}</code> <code>{error}</code> <code>{referrals}</code> "
            "<code>{points}</code> <code>{link}</code> <code>{leaders}</code>\n\n"
            "🎨 لإضافة Premium Emoji داخل الكليشة استخدم: "
            "<code>[emoji:5462943653116792628]</code> أو <code>{emoji:5462943653116792628}</code>\n"
            "يمكنك استبدال الـ ID بأي ID رقمي صالح.\n\n/cancel",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[_make_button("🔙 رجوع", "admin_messages", key="back_home")]])
        )
        return

    await _ORIGINAL_ADMIN_CALLBACK(update, context, data)

# -------------------- Admin message extension --------------------

async def handle_admin_message(update, context):
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not is_admin(user.id):
        return await _ORIGINAL_HANDLE_ADMIN_MESSAGE(update, context)

    action = context.user_data.get("admin_action")

    if action == "maintenance_message":
        if not message.text:
            await message.reply_text("❌ أرسل نصاً فقط.")
            return True
        db["settings"]["maintenance_text"] = message.text
        db["settings"].setdefault("message_settings", {})["maintenance"] = message.text
        save_db(db)
        context.user_data.pop("admin_action", None)
        await message.reply_text("✅ تم حفظ رسالة الصيانة.", reply_markup=maintenance_keyboard())
        return True

    if action == "referral_points_set":
        try:
            value = int((message.text or "").strip())
            if not 1 <= value <= 100000:
                raise ValueError
        except ValueError:
            await message.reply_text("❌ أرسل رقماً من 1 إلى 100000.")
            return True
        db["settings"]["referral_points"] = value
        save_db(db)
        context.user_data.pop("admin_action", None)
        await message.reply_text("✅ تم حفظ نقاط الإحالة.", reply_markup=referrals_admin_keyboard())
        return True

    if action == "referral_limit_set":
        try:
            value = int((message.text or "").strip())
            if not 3 <= value <= 50:
                raise ValueError
        except ValueError:
            await message.reply_text("❌ أرسل رقماً من 3 إلى 50.")
            return True
        db["settings"]["referral_leaders_limit"] = value
        save_db(db)
        context.user_data.pop("admin_action", None)
        await message.reply_text("✅ تم حفظ عدد المتصدرين.", reply_markup=referrals_admin_keyboard())
        return True

    if action == "broadcast_button_message":
        context.user_data["broadcast_source_message_id"] = message.message_id
        context.user_data["broadcast_source_chat_id"] = message.chat_id
        context.user_data["admin_action"] = "broadcast_button_config"
        await message.reply_text(
            "🔗 أرسل الآن:\n<code>اسم الزر|https://example.com</code>\n\n"
            "سيكون الزر ملوّناً ويستخدم Premium Emoji.",
            parse_mode="HTML"
        )
        return True

    if action == "broadcast_button_config":
        if not message.text or "|" not in message.text:
            await message.reply_text("❌ الصيغة: اسم الزر|https://example.com")
            return True
        label, url = [x.strip() for x in message.text.split("|", 1)]
        if not label or not re.match(r"^https?://", url, re.IGNORECASE):
            await message.reply_text("❌ الرابط يجب أن يبدأ بـ http:// أو https://")
            return True
        source_id = context.user_data.get("broadcast_source_message_id")
        source_chat = context.user_data.get("broadcast_source_chat_id")
        if not source_id or not source_chat:
            context.user_data.pop("admin_action", None)
            await message.reply_text("❌ انتهت جلسة الإذاعة. ابدأ من جديد.")
            return True

        markup = InlineKeyboardMarkup([[_make_button(label, url=url, style="primary")]])
        sent = failed = 0
        await message.reply_text("📢 جاري إرسال الإذاعة...")
        for uid in list(db.get("users", {}).keys()):
            try:
                await context.bot.copy_message(
                    chat_id=int(uid), from_chat_id=int(source_chat),
                    message_id=int(source_id), reply_markup=markup
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                failed += 1
                logger.warning("Broadcast with button failed for %s: %s", uid, e)

        context.user_data.pop("admin_action", None)
        context.user_data.pop("broadcast_source_message_id", None)
        context.user_data.pop("broadcast_source_chat_id", None)
        await message.reply_text(
            f"✅ <b>انتهت الإذاعة</b>\n\nتم الإرسال: <b>{sent}</b>\nفشل: <b>{failed}</b>",
            parse_mode="HTML", reply_markup=admin_keyboard()
        )
        return True

    return await _ORIGINAL_HANDLE_ADMIN_MESSAGE(update, context)

# -------------------- User callback extension --------------------

async def button_callback(update, context):
    """Unified callback router for all user/admin inline buttons."""
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return

    data = query.data or ""

    # Acknowledge immediately so Telegram does not keep the loading spinner.
    try:
        await query.answer()
    except Exception:
        pass

    if is_banned(user.id):
        try:
            await query.answer("🚫 أنت محظور من استخدام البوت.", show_alert=True)
        except Exception:
            pass
        return

    # Admin and V3 callbacks go directly to the enhanced admin handler.
    admin_prefixes = (
        "admin_", "admin_copy_source", "force_", "button_choose_emoji_",
        "button_emoji_", "button_style_", "button_reset_all_emojis", "message_edit_", "maintenance_", "referral_",
        "referrals_", "broadcast_"
    )

    if data == "referrals":
        me = await context.bot.get_me()
        refs, points = _referral_stats(user.id)
        await query.edit_message_text(
            _enhanced_message(
                "referral_stats",
                referrals=refs,
                points=points,
                link=html.escape(_referral_link(me.username, user.id)),
            ),
            parse_mode="HTML",
            reply_markup=referral_keyboard(),
        )
        return

    if data == "referral_stats":
        me = await context.bot.get_me()
        refs, points = _referral_stats(user.id)
        await query.edit_message_text(
            _enhanced_message(
                "referral_stats",
                referrals=refs,
                points=points,
                link=html.escape(_referral_link(me.username, user.id)),
            ),
            parse_mode="HTML",
            reply_markup=referral_keyboard(),
        )
        return

    if data == "referral_leaders":
        await query.edit_message_text(
            _enhanced_message(
                "leaderboard",
                leaders=_leaderboard_lines(
                    int(db["settings"].get("referral_leaders_limit", 10) or 10)
                ),
            ),
            parse_mode="HTML",
            reply_markup=referral_keyboard(),
        )
        return

    if data == "referrals_toggle":
        if not is_admin(user.id):
            await query.answer("🚫 هذه اللوحة خاصة بالأدمن.", show_alert=True)
            return
        await admin_callback(update, context, data)
        return

    if data.startswith(admin_prefixes):
        if not is_admin(user.id):
            try:
                await query.answer(
                    "🚫 هذه اللوحة خاصة بالأدمن.",
                    show_alert=True
                )
            except Exception:
                pass
            return
        try:
            await admin_callback(update, context, data)
        except Exception as exc:
            logger.exception("Admin callback failed: %s", exc)
            try:
                await query.answer(
                    "❌ حدث خطأ أثناء تنفيذ الأمر.",
                    show_alert=True
                )
            except Exception:
                pass
        return

    # Original callbacks: TikTok, back, subscription, etc.
    try:
        await _ORIGINAL_BUTTON_CALLBACK(update, context)
    except Exception as exc:
        logger.exception("User callback failed: %s", exc)
        try:
            await query.answer(
                "❌ تعذر تنفيذ الأمر، حاول مرة أخرى.",
                show_alert=True
            )
        except Exception:
            pass

# -------------------- Help / URL --------------------

async def help_command(update, context):
    user = update.effective_user
    if user and _maintenance_enabled() and not is_admin(user.id):
        await update.effective_message.reply_text(_maintenance_text(), parse_mode="HTML")
        return
    await update.effective_message.reply_text(_enhanced_message("help"), parse_mode="HTML")

async def handle_url(update, context):
    user = update.effective_user
    if user and _maintenance_enabled() and not is_admin(user.id):
        await update.effective_message.reply_text(_maintenance_text(), parse_mode="HTML")
        return
    return await _ORIGINAL_HANDLE_URL(update, context)

# -------------------- Telegram command menu --------------------

async def _post_init(application):
    try:
        from telegram import BotCommand, BotCommandScopeChat
        common = [
            BotCommand("start", "فتح البوت"),
            BotCommand("referrals", "نظام الإحالات"),
            BotCommand("top", "المتصدرون"),
            BotCommand("help", "المساعدة"),
        ]
        await application.bot.set_my_commands(common)
        admin_commands = common + [
            BotCommand("admin", "لوحة الأدمن"),
            BotCommand("cancel", "إلغاء العملية"),
        ]
        ids = {int(ADMIN_ID), *get_admins()}
        for aid in ids:
            try:
                await application.bot.set_my_commands(
                    admin_commands, scope=BotCommandScopeChat(chat_id=aid)
                )
            except Exception as e:
                logger.warning("Admin command menu failed for %s: %s", aid, e)
    except Exception as e:
        logger.warning("Command menu setup failed: %s", e)

# -------------------- Patched main --------------------

def main():
    update_yt_dlp()
    if not BOT_TOKEN:
        print("❌ لم يتم العثور على BOT_TOKEN. أضفه في Railway Variables.")
        return
    print("======================================")
    print("🤖 Social Downloader Bot V3")
    print("======================================")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"👥 Users: {get_user_count()}")
    print(f"💾 Database: {DB_FILE}")
    print(f"📢 Force Sub Channels: {len(get_force_channels())}")
    print(f"🛠 Maintenance: {_maintenance_enabled()}")
    print(f"🎁 Referrals: {db['settings'].get('referrals_enabled', True)}")
    print("🚀 Starting bot...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(32)
        .connection_pool_size(64)
        .pool_timeout(10.0)
        .post_init(_post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("referrals", referrals_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & (filters.PHOTO | filters.VIDEO), handle_url))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.Document.ALL, handle_url))
    app.add_error_handler(error_handler)
    print("======================================")
    print("✅ البوت يعمل الآن.")
    print("======================================")
    app.run_polling(allowed_updates=Update.ALL_TYPES)



# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()
