# -*- coding: utf-8 -*-
import telebot
from telebot import types
import sqlite3
import time
import re
import html
import secrets
import json
import urllib.request
from collections import defaultdict, deque
from threading import Thread, Lock

# =========================================================
# الإعدادات
# =========================================================
BOT_TOKEN = "8682892405:AAGp7zV4d2gades5_X4piF-1UQMZgOw1AAI"

DEVELOPER_ID = 8037399518
BOT_USERNAME = "LeaAeDr_Bot"
DB_NAME = "protection_bot.db"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

ADD_TO_GROUP_URL = (
    f"https://t.me/{BOT_USERNAME}?startgroup"
    "&admin=delete_messages+restrict_members+invite_users+pin_messages+"
    "change_info+manage_topics+manage_video_chats"
)

# =========================================================
# Custom Emoji IDs
# =========================================================
CE_ADD_GROUP = "6014859822669765417"
CE_OWNER_DEVELOPER = "6026358867460366307"
CE_MEMBER = "6026214410530333332"
CE_ERROR = "5463150060655104540"
CE_SUCCESS = "5462991735275670716"
CE_ADMIN = "6024070839597540699"
CE_ID = "6026322901404229165"
CE_USERNAME = "5463083548791556323"
CE_START = "6014944072748244263"
CE_PROTECTION = "5891225499677496831"
CE_RANKS = "5463397536670697642"
CE_PERSON = "5463295393758464486"
CE_WORDS = "4936296803390718929"
CE_EVERYONE = "5461018558580401820"
CE_COMMANDS = "5463200135678796607"
CE_WELCOME = "5764739309810751596"
CE_AFTER_PERSON = "5890941464900278076"
CE_END = "5776345243452447613"

# Custom Emoji requested for reply buttons / welcome / developer button
CE_REPLY_BUTTON = "5274008024585871702"
CE_WELCOME_LINE = "5256143829672672750"
CE_DEV_BUTTON = "5260233433107407649"

def tg_emoji(emoji_id, alt="🔹"):
    return f'<tg-emoji emoji-id="{emoji_id}">{alt}</tg-emoji>'

# =========================================================
# تنسيق الرسائل
# =========================================================
def decorate_text(text):
    """
    تنسيق موحد للإيموجيات المخصصة:
    - إيموجي المعنى يكون في نهاية عنوان/سطر الكلمة، وليس داخل الجملة.
    - إيموجي البداية يوضع فقط إذا لم يبدأ السطر بإيموجي آخر.
    - الترحيب له إيموجي خاص في البداية ولا نضيف فوقه إيموجي البداية.
    - النجاح والخطأ لهما إيموجي خاص في البداية.
    - ID واليوزر لهما إيموجي قبل البيانات.
    """
    if not text or not isinstance(text, str):
        return text

    out = text

    # ---------------------------------------------------------
    # 1) إزالة الإيموجيات القديمة من عناوين الأقسام فقط
    #    حتى لا تصبح الإيموجيات داخل/قبل الكلمة.
    # ---------------------------------------------------------
    heading_patterns = [
        # (regex, replacement text, custom emoji)
        (r'(<b>)\s*[👑📚🛡️🔒🚫⚙️👥]\s*(نظام الرتب\s*:?)\s*(</b>)',
         r'\1\2 ' + tg_emoji(CE_RANKS, "👑") + r'\3'),
        (r'(<b>)\s*[👑📚🛡️🔒🚫⚙️👥]\s*(الحماية\s*:?)\s*(</b>)',
         r'\1\2 ' + tg_emoji(CE_PROTECTION, "🛡️") + r'\3'),
        (r'(<b>)\s*[👑📚🛡️🔒🚫⚙️👥]\s*(الإدارة|الادارة\s*:?)\s*(</b>)',
         r'\1\2 ' + tg_emoji(CE_ADMIN, "🛡️") + r'\3'),
        (r'(<b>)\s*[👑📚🛡️🔒🚫⚙️👥]\s*(الكلمات\s*:?)\s*(</b>)',
         r'\1\2 ' + tg_emoji(CE_WORDS, "🚫") + r'\3'),
        (r'(<b>)\s*[👑📚🛡️🔒🚫⚙️👥]\s*(للجميع\s*:?)\s*(</b>)',
         r'\1\2 ' + tg_emoji(CE_EVERYONE, "👥") + r'\3'),
        (r'(<b>)\s*[👑📚🛡️🔒🚫⚙️👥]\s*(قائمة أوامر البوت)\s*(</b>)',
         r'\1\2 ' + tg_emoji(CE_COMMANDS, "📚") + r'\3'),
        (r'(<b>)\s*[👑📚🛡️🔒🚫⚙️👥]\s*(قائمة اوامر البوت)\s*(</b>)',
         r'\1\2 ' + tg_emoji(CE_COMMANDS, "📚") + r'\3'),
    ]

    for pattern, replacement in heading_patterns:
        out = re.sub(pattern, replacement, out)

    # ---------------------------------------------------------
    # 2) لو العنوان مكتوب بدون إيموجي يدوي، ضعه في آخر العنوان.
    #    نعمل ذلك على مستوى السطر حتى لا ندخل الإيموجي وسط الجملة.
    # ---------------------------------------------------------
    semantic_heads = [
        ("قائمة أوامر البوت", CE_COMMANDS, "📚"),
        ("قائمة اوامر البوت", CE_COMMANDS, "📚"),
        ("نظام الرتب", CE_RANKS, "👑"),
        ("الحماية", CE_PROTECTION, "🛡️"),
        ("حماية", CE_PROTECTION, "🛡️"),
        ("الإدارة", CE_ADMIN, "🛡️"),
        ("الادارة", CE_ADMIN, "🛡️"),
        ("الكلمات", CE_WORDS, "🚫"),
        ("للجميع", CE_EVERYONE, "👥"),
    ]

    lines = []
    for line in out.split("\n"):
        plain = re.sub(r"<[^>]+>", "", line).strip()

        # لا نلمس الفواصل.
        if not plain or plain.startswith("┈"):
            lines.append(line)
            continue

        for phrase, emoji_id, alt in semantic_heads:
            # الإيموجي الدلالي يخص عنوان/سطر يبدأ بالكلمة فقط،
            # وليس أي جملة تحتوي عليها مثل "قفل حماية الجدد".
            if plain.startswith(phrase):
                # إذا كان هذا سطر عنوان، ضع الإيموجي في آخر النص
                # وليس قبل الكلمة.
                if "<b>" in line and "</b>" in line:
                    # احذف الإيموجي المخصص السابق لنفس العنوان إن وجد.
                    line = re.sub(
                        rf'<tg-emoji[^>]*>.*?</tg-emoji>\s*',
                        '',
                        line,
                        count=1
                    )
                    # احذف الإيموجي العادي الذي كان قبل العنوان.
                    line = re.sub(r'(<b>)\s*[^\w<>&]+(?=\s*' + re.escape(phrase) + r')',
                                  r'\1', line, count=1)
                    # أضف الإيموجي قبل إغلاق bold.
                    line = line.replace(
                        "</b>",
                        " " + tg_emoji(emoji_id, alt) + "</b>",
                        1
                    )
                else:
                    # لا نغير الجمل العادية التي تحتوي الكلمة في المنتصف.
                    # فقط العناوين/الأسطر القصيرة التي تبدأ بها.
                    if plain.startswith(phrase):
                        line = line.rstrip() + " " + tg_emoji(emoji_id, alt)
                break

        lines.append(line)

    out = "\n".join(lines)

    # ---------------------------------------------------------
    # 3) ID واليوزر: الإيموجي قبل الليبل كما طلبت.
    # ---------------------------------------------------------
    out = re.sub(
        r'(الـ? ID الخاص بك:|الايدي:|𝐈𝐃\s*:)',
        tg_emoji(CE_ID, "🆔") + r'\1',
        out
    )

    out = re.sub(
        r'(اليوزر:|𝐔𝐒𝐄𝐑\s*:)',
        tg_emoji(CE_USERNAME, "👤") + r'\1',
        out
    )

    # ---------------------------------------------------------
    # 4) نجاح/خطأ: الإيموجي الخاص فقط في بداية السطر.
    #    وبالتالي لا نضيف فوقه CE_START.
    # ---------------------------------------------------------
    lines = []
    for line in out.split("\n"):
        plain = re.sub(r"<[^>]+>", "", line).strip()

        if any(x in plain for x in (
            "فشل", "خطأ", "خطا", "تعذر",
            "لم أستطع", "لا أستطيع", "غير مسموح"
        )):
            if not re.match(r'\s*<tg-emoji', line):
                line = tg_emoji(CE_ERROR, "❌") + " " + line

        elif any(x in plain for x in (
            "تم ", "نجاح", "بنجاح",
            "تم التعديل", "تم الرفع", "تم تنزيل"
        )):
            if not re.match(r'\s*<tg-emoji', line):
                line = tg_emoji(CE_SUCCESS, "✅") + " " + line

        lines.append(line)

    out = "\n".join(lines)

    # ---------------------------------------------------------
    # 5) الترحيب: الإيموجي الخاص أول شيء.
    #    لا نضيف CE_START قبله.
    # ---------------------------------------------------------
    if any(x in out for x in ("أهلًا وسهلًا", "أهلاً وسهلاً", "مرحبًـا")):
        # امنع تكرار إيموجي الترحيب عند تعديل/إعادة إرسال الرسالة.
        if not out.lstrip().startswith(f'<tg-emoji emoji-id="{CE_WELCOME}">'):
            out = tg_emoji(CE_WELCOME, "👋") + " " + out.lstrip()

    # ---------------------------------------------------------
    # 6) CE_START قبل بداية السطر فقط إذا لم يوجد إيموجي آخر هناك.
    #    ونتجنب الفواصل والعناوين التي تبدأ أصلًا بتاج/إيموجي.
    # ---------------------------------------------------------
    final_lines = []
    for line in out.split("\n"):
        stripped = line.lstrip()

        if not stripped or stripped.startswith("┈"):
            final_lines.append(line)
            continue

        # لو السطر يبدأ بتاج tg-emoji فلا تضف CE_START.
        if stripped.startswith("<tg-emoji"):
            final_lines.append(line)
            continue

        # افحص بداية النص بعد HTML tags.
        visible = re.sub(r"<[^>]+>", "", stripped).lstrip()

        # أي إيموجي موجود بالفعل في بداية السطر = لا CE_START.
        if visible and re.match(
            r'^(?:[\U0001F000-\U0001FAFF\u2600-\u27BF]|[©®™])',
            visible
        ):
            final_lines.append(line)
            continue

        # لو السطر عبارة عن HTML يبدأ بـ <b> ثم النص، نضع CE_START
        # بعد وسم البداية حتى يظهر قبل الجملة فعلًا.
        if stripped.startswith("<b>"):
            line = "<b>" + tg_emoji(CE_START, "🔹") + " " + stripped[3:]
        else:
            line = tg_emoji(CE_START, "🔹") + " " + stripped

        final_lines.append(line)

    out = "\n".join(final_lines)

    # ---------------------------------------------------------
    # 7) إيموجي نهاية الرسالة.
    # ---------------------------------------------------------
    end_emoji = tg_emoji(CE_END, "🔚")
    if out and not out.rstrip().endswith(end_emoji):
        out = out.rstrip() + "\n" + end_emoji

    return out


# =========================================================
# تطبيق تنسيق الإيموجي على كل الرسائل الصادرة
# =========================================================
_original_send_message = bot.send_message
_original_send_photo = bot.send_photo
_original_send_video = bot.send_video
_original_send_document = bot.send_document
_original_send_audio = bot.send_audio
_original_send_voice = bot.send_voice
_original_edit_message_text = bot.edit_message_text


def _send_message_decorated(chat_id, text, *args, **kwargs):
    return _original_send_message(chat_id, decorate_text(text), *args, **kwargs)


def _decorate_caption_kwargs(kwargs):
    if kwargs.get("caption"):
        kwargs["caption"] = decorate_text(kwargs["caption"])
    return kwargs


def _send_photo_decorated(chat_id, photo, *args, **kwargs):
    return _original_send_photo(
        chat_id, photo, *args, **_decorate_caption_kwargs(kwargs)
    )


def _send_video_decorated(chat_id, video, *args, **kwargs):
    return _original_send_video(
        chat_id, video, *args, **_decorate_caption_kwargs(kwargs)
    )


def _send_document_decorated(chat_id, document, *args, **kwargs):
    return _original_send_document(
        chat_id, document, *args, **_decorate_caption_kwargs(kwargs)
    )


def _send_audio_decorated(chat_id, audio, *args, **kwargs):
    return _original_send_audio(
        chat_id, audio, *args, **_decorate_caption_kwargs(kwargs)
    )


def _send_voice_decorated(chat_id, voice, *args, **kwargs):
    return _original_send_voice(
        chat_id, voice, *args, **_decorate_caption_kwargs(kwargs)
    )


def _edit_message_text_decorated(text, chat_id=None, message_id=None, *args, **kwargs):
    return _original_edit_message_text(
        decorate_text(text),
        chat_id,
        message_id,
        *args,
        **kwargs
    )


bot.send_message = _send_message_decorated
bot.send_photo = _send_photo_decorated
bot.send_video = _send_video_decorated
bot.send_document = _send_document_decorated
bot.send_audio = _send_audio_decorated
bot.send_voice = _send_voice_decorated
bot.edit_message_text = _edit_message_text_decorated


# =========================================================
# قاعدة البيانات
# =========================================================
db = sqlite3.connect(DB_NAME, check_same_thread=False)
db.row_factory = sqlite3.Row
cursor = db.cursor()


def table_columns(table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cursor.fetchall()}


def add_column_if_missing(table, column, definition):
    if column not in table_columns(table):
        try:
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )
            db.commit()
        except Exception as e:
            print(f"[DB] Migration error {table}.{column}: {e}")


cursor.execute("""
CREATE TABLE IF NOT EXISTS groups (
    chat_id INTEGER PRIMARY KEY,
    title TEXT DEFAULT '',
    welcome INTEGER DEFAULT 1,
    links INTEGER DEFAULT 1,
    photos INTEGER DEFAULT 0,
    videos INTEGER DEFAULT 0,
    documents INTEGER DEFAULT 0,
    stickers INTEGER DEFAULT 0,
    audio INTEGER DEFAULT 0,
    animations INTEGER DEFAULT 0,
    spam INTEGER DEFAULT 1,
    flood INTEGER DEFAULT 1,
    repeat_messages INTEGER DEFAULT 1,
    new_member_protection INTEGER DEFAULT 0,
    max_warnings INTEGER DEFAULT 3
)
""")
db.commit()


for c, d in {
    "title": "TEXT DEFAULT ''",
    "welcome": "INTEGER DEFAULT 1",
    "links": "INTEGER DEFAULT 1",
    "photos": "INTEGER DEFAULT 0",
    "videos": "INTEGER DEFAULT 0",
    "documents": "INTEGER DEFAULT 0",
    "stickers": "INTEGER DEFAULT 0",
    "audio": "INTEGER DEFAULT 0",
    "animations": "INTEGER DEFAULT 0",
    "spam": "INTEGER DEFAULT 1",
    "flood": "INTEGER DEFAULT 1",
    "repeat_messages": "INTEGER DEFAULT 1",
    "new_member_protection": "INTEGER DEFAULT 0",
    "max_warnings": "INTEGER DEFAULT 3"
}.items():
    add_column_if_missing("groups", c, d)


cursor.execute("""
CREATE TABLE IF NOT EXISTS group_users (
    chat_id INTEGER,
    user_id INTEGER,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    messages INTEGER DEFAULT 0,
    warnings INTEGER DEFAULT 0,
    joined_at INTEGER DEFAULT 0,
    last_seen INTEGER DEFAULT 0,
    PRIMARY KEY(chat_id,user_id)
)
""")
db.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS blacklist (
    chat_id INTEGER,
    word TEXT,
    PRIMARY KEY(chat_id,word)
)
""")
db.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    admin_id INTEGER,
    target_id INTEGER,
    action TEXT,
    details TEXT,
    created_at INTEGER
)
""")
db.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    chat_id INTEGER,
    setting TEXT,
    value TEXT,
    PRIMARY KEY(chat_id,setting)
)
""")
db.commit()

# الردود التلقائية - محفوظة داخل SQLite حتى لا تضيع بعد إعادة التشغيل
cursor.execute("""
CREATE TABLE IF NOT EXISTS auto_replies (
    chat_id INTEGER NOT NULL,
    trigger TEXT NOT NULL,
    reply_text TEXT NOT NULL DEFAULT '',
    button_enabled INTEGER DEFAULT 0,
    button_text TEXT DEFAULT '',
    button_url TEXT DEFAULT '',
    button_emoji_id TEXT DEFAULT '',
    PRIMARY KEY(chat_id,trigger)
)
""")
db.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS group_ranks (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rank TEXT NOT NULL,
    PRIMARY KEY(chat_id,user_id)
)
""")
db.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS rank_permissions (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    permission TEXT NOT NULL,
    PRIMARY KEY(chat_id,user_id,permission)
)
""")
db.commit()

print("Database Ready / Migration Completed")


# =========================================================
# أدوات عامة
# =========================================================
def now():
    return int(time.time())


def clean_text(text):
    if not text:
        return ""

    text = text.strip()

    if text.startswith("/"):
        text = text[1:]

    for a, b in {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ة": "ه",
        "ى": "ي"
    }.items():
        text = text.replace(a, b)

    return text.lower().strip()


def command_parts(message):
    text = (message.text or "").strip()

    if text.startswith("/"):
        text = text[1:]

    parts = text.split(maxsplit=1)

    return (
        clean_text(parts[0]) if parts else "",
        parts[1].strip() if len(parts) > 1 else ""
    )


def ensure_group(chat):
    if chat.type not in ("group", "supergroup"):
        return

    cursor.execute(
        "INSERT OR IGNORE INTO groups(chat_id,title) VALUES(?,?)",
        (chat.id, chat.title or "")
    )

    cursor.execute(
        "UPDATE groups SET title=? WHERE chat_id=?",
        (chat.title or "", chat.id)
    )

    db.commit()


def get_group(chat_id):
    cursor.execute(
        "SELECT * FROM groups WHERE chat_id=?",
        (chat_id,)
    )
    return cursor.fetchone()


def group_setting(chat_id, column):
    row = get_group(chat_id)
    return bool(row[column]) if row else False


def set_group_setting(chat_id, column, value):
    cursor.execute(
        f"UPDATE groups SET {column}=? WHERE chat_id=?",
        (1 if value else 0, chat_id)
    )
    db.commit()


def get_setting(chat_id, name, default=None):
    cursor.execute(
        "SELECT value FROM settings WHERE chat_id=? AND setting=?",
        (chat_id, name)
    )

    row = cursor.fetchone()

    return row["value"] if row else default


def set_setting(chat_id, name, value):
    cursor.execute("""
        INSERT INTO settings(chat_id,setting,value)
        VALUES(?,?,?)
        ON CONFLICT(chat_id,setting)
        DO UPDATE SET value=excluded.value
    """, (chat_id, name, str(value)))

    db.commit()


def full_name(user):
    n = " ".join(
        x for x in [
            user.first_name or "",
            user.last_name or ""
        ] if x
    ).strip()

    return n or "مستخدم"


def username_text(user):
    return "@" + user.username if user.username else "لا يوجد"


def mention(user, owner=False):
    name = html.escape(full_name(user))
    if owner:
        return f'<a href="tg://user?id={user.id}">{name}</a>'
    return (
        tg_emoji(CE_PERSON, "👤") +
        f'<a href="tg://user?id={user.id}">{name}</a>' +
        tg_emoji(CE_AFTER_PERSON, "✨")
    )


# =========================================================
# الأزرار
# =========================================================
def button(
    text,
    callback_data=None,
    url=None,
    style="primary",
    icon_custom_emoji_id=None
):
    kwargs = {
        "text": text,
        "style": style
    }

    if callback_data is not None:
        kwargs["callback_data"] = callback_data

    if url is not None:
        kwargs["url"] = url

    if icon_custom_emoji_id is not None:
        kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id

    try:
        return types.InlineKeyboardButton(**kwargs)

    except TypeError:
        kwargs.pop("icon_custom_emoji_id", None)

        try:
            return types.InlineKeyboardButton(**kwargs)

        except TypeError:
            kwargs.pop("style", None)

            return types.InlineKeyboardButton(**kwargs)


# =========================================================
# التحويل التلقائي للعملات ($ -> EGP + TON)
# =========================================================
CURRENCY_CACHE_SECONDS = 600
CURRENCY_HTTP_TIMEOUT = 7
LOVELY_UPDATES_URL = "https://t.me/LeaDeR_E"

_currency_cache = {
    "usd_egp": None,
    "ton_usd": None,
    "updated_at": 0
}
_currency_cache_lock = Lock()


def transparent_url_button(text, url, emoji_id=None):
    """
    زر رابط عادي بدون style حتى يظهر بشكل شفاف/افتراضي في تيليجرام.
    إذا كان Telegram/PyTelegramBotAPI يدعم icon_custom_emoji_id يتم
    وضع الإيموجي تلقائيًا، وإذا لم يدعمه الإصدار يبقى الزر رابطًا عاديًا.
    """
    kwargs = {
        "text": text,
        "url": url
    }

    if emoji_id:
        kwargs["icon_custom_emoji_id"] = str(emoji_id)

    try:
        return types.InlineKeyboardButton(**kwargs)
    except TypeError:
        kwargs.pop("icon_custom_emoji_id", None)
        try:
            return types.InlineKeyboardButton(**kwargs)
        except Exception:
            return None
    except Exception:
        return None


def _http_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=CURRENCY_HTTP_TIMEOUT
    ) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def get_currency_rates():
    """
    يجلب:
    - سعر الدولار مقابل الجنيه المصري.
    - سعر TON بالدولار.

    يتم التخزين مؤقتًا لمدة 10 دقائق حتى لا يتم إرسال طلبات
    خارجية مع كل رسالة.
    """
    current_time = time.time()

    with _currency_cache_lock:
        if (
            _currency_cache["usd_egp"] is not None
            and _currency_cache["ton_usd"] is not None
            and current_time - _currency_cache["updated_at"]
            < CURRENCY_CACHE_SECONDS
        ):
            return (
                _currency_cache["usd_egp"],
                _currency_cache["ton_usd"]
            )

    usd_egp = None
    ton_usd = None

    try:
        data = _http_json(
            "https://open.er-api.com/v6/latest/USD"
        )

        rates = data.get("rates", {})
        usd_egp = float(rates.get("EGP"))
    except Exception as e:
        print("[Currency USD/EGP Error]", e)

    try:
        data = _http_json(
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=the-open-network&vs_currencies=usd"
        )

        ton_usd = float(
            data["the-open-network"]["usd"]
        )
    except Exception as e:
        print("[Currency TON Error]", e)

    if (
        usd_egp is not None
        and ton_usd is not None
        and usd_egp > 0
        and ton_usd > 0
    ):
        with _currency_cache_lock:
            _currency_cache["usd_egp"] = usd_egp
            _currency_cache["ton_usd"] = ton_usd
            _currency_cache["updated_at"] = current_time

        return usd_egp, ton_usd

    with _currency_cache_lock:
        if (
            _currency_cache["usd_egp"] is not None
            and _currency_cache["ton_usd"] is not None
        ):
            return (
                _currency_cache["usd_egp"],
                _currency_cache["ton_usd"]
            )

    return None, None


def normalize_money_number(value):
    """
    يحول الأرقام المكتوبة بفواصل أو أرقام عربية إلى رقم قابل للحساب.
    """
    if not value:
        return None

    value = value.strip()

    arabic_digits = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩٫٬",
        "0123456789.,"
    )
    value = value.translate(arabic_digits)

    value = value.replace(",", "")

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number <= 0:
        return None

    return number


def extract_usd_amount(text):
    """
    يلتقط مبلغ الدولار عندما يظهر بالشكل:
    1$
    $1
    1 $
    $ 1
    1 USD
    1 USDT
    1 دولار
    """
    if not text:
        return None

    normalized = text.translate(
        str.maketrans(
            "٠١٢٣٤٥٦٧٨٩٫٬",
            "0123456789.,"
        )
    )

    number_pattern = r"([0-9]+(?:[.,][0-9]+)?)"

    patterns = [
        rf"\$\s*{number_pattern}",
        rf"{number_pattern}\s*\$",
        rf"{number_pattern}\s*(?:USD|USDT|دولار)\b"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE
        )

        if not match:
            continue

        # المجموعة الوحيدة في كل نمط هي قيمة الرقم.
        amount = normalize_money_number(
            match.group(1)
        )

        if amount is not None:
            return amount

    return None


def format_money(value, decimals=2):
    if value >= 1000000:
        return f"{value:,.0f}"

    if value >= 1000:
        return f"{value:,.2f}"

    return f"{value:,.{decimals}f}"


def send_currency_conversion(message, usd_amount):
    usd_egp, ton_usd = get_currency_rates()

    if (
        usd_egp is None
        or ton_usd is None
        or usd_egp <= 0
        or ton_usd <= 0
    ):
        print("[Currency] Could not get live rates.")
        return False

    egp_amount = usd_amount * usd_egp
    ton_amount = usd_amount / ton_usd

    text = (
        "💱 <b>تحويل العملة</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"💵 <b>{format_money(usd_amount, 4)} USD</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"🇪🇬 <b>{format_money(egp_amount, 2)} EGP</b>\n"
        f"💎 <b>{format_money(ton_amount, 4)} TON</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"💵 1 USD = {format_money(usd_egp, 2)} EGP\n"
        f"💎 1 TON = {format_money(ton_usd, 4)} USD"
    )

    markup = types.InlineKeyboardMarkup()
    updates_button = transparent_url_button(
        "Lovely Updates",
        LOVELY_UPDATES_URL
    )

    if updates_button is not None:
        markup.add(updates_button)

    try:
        bot.reply_to(
            message,
            text,
            reply_markup=markup
        )
        return True
    except Exception as e:
        print("[Currency Send Error]", e)
        return False


def automatic_currency_conversion(message):
    """
    عند ظهور مبلغ بالدولار في الرسالة، يرسل التحويل تلقائيًا
    إلى الجنيه المصري وTON.
    """
    if (
        not message
        or not message.from_user
        or message.from_user.is_bot
    ):
        return False

    text = message.text or message.caption or ""

    if not text:
        return False

    usd_amount = extract_usd_amount(text)

    if usd_amount is None:
        return False

    return send_currency_conversion(
        message,
        usd_amount
    )


# =========================================================
# المستخدمون
# =========================================================
def register_user(message, count_message=True):
    if (
        not message.from_user
        or message.chat.type not in ("group", "supergroup")
    ):
        return

    ensure_group(message.chat)

    u = message.from_user
    inc = 1 if count_message else 0

    cursor.execute("""
        INSERT INTO group_users
        (
            chat_id,
            user_id,
            first_name,
            last_name,
            username,
            messages,
            warnings,
            joined_at,
            last_seen
        )
        VALUES(?,?,?,?,?,?,?,?,?)

        ON CONFLICT(chat_id,user_id)
        DO UPDATE SET
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            username=excluded.username,
            messages=group_users.messages+?,
            last_seen=excluded.last_seen
    """, (
        message.chat.id,
        u.id,
        u.first_name or "",
        u.last_name or "",
        u.username or "",
        inc,
        0,
        now(),
        now(),
        inc
    ))

    db.commit()


def register_member(chat_id, user):
    cursor.execute("""
        INSERT INTO group_users
        (
            chat_id,
            user_id,
            first_name,
            last_name,
            username,
            messages,
            warnings,
            joined_at,
            last_seen
        )
        VALUES(?,?,?,?,?,?,?,?,?)

        ON CONFLICT(chat_id,user_id)
        DO UPDATE SET
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            username=excluded.username,
            last_seen=excluded.last_seen
    """, (
        chat_id,
        user.id,
        user.first_name or "",
        user.last_name or "",
        user.username or "",
        0,
        0,
        now(),
        now()
    ))

    db.commit()


# =========================================================
# الرتب
# =========================================================
RANK_ORDER = {
    "member": 0,
    "animal": 10,
    "moderator": 20,
    "admin": 30,
    "manager": 40,
    "assistant_owner": 50,
    "owner": 100
}


RANK_NAMES = {
    "animal": "حيوان",
    "moderator": "المشرف",
    "admin": "الادمن",
    "manager": "المدير",
    "assistant_owner": "مساعد المالك",
    "owner": "المالك"
}


TITLE_NAMES = {
    "moderator": "المشرف",
    "assistant_owner": "المشرف الكبــير"
}


def is_developer(user_id):
    return user_id == DEVELOPER_ID


def get_member(chat_id, user_id):
    try:
        return bot.get_chat_member(chat_id, user_id)
    except Exception:
        return None


def is_creator(chat_id, user_id):
    m = get_member(chat_id, user_id)
    return bool(m and m.status == "creator")


def is_admin(chat_id, user_id):
    if is_developer(user_id):
        return True

    m = get_member(chat_id, user_id)

    return bool(
        m and m.status in ("administrator", "creator")
    )


def bot_is_admin(chat_id):
    try:
        me = bot.get_me()
        m = bot.get_chat_member(chat_id, me.id)

        return m.status in (
            "administrator",
            "creator"
        )

    except Exception:
        return False


def target_is_admin(chat_id, user_id):
    m = get_member(chat_id, user_id)

    return bool(
        m and m.status in (
            "administrator",
            "creator"
        )
    )


def get_rank(chat_id, user_id):
    if is_creator(chat_id, user_id):
        return "owner"

    cursor.execute(
        """
        SELECT rank
        FROM group_ranks
        WHERE chat_id=? AND user_id=?
        """,
        (chat_id, user_id)
    )

    row = cursor.fetchone()

    return row["rank"] if row else "member"


def rank_level(rank):
    return RANK_ORDER.get(rank, 0)


def set_rank(chat_id, user_id, rank):
    if rank == "member":

        cursor.execute(
            """
            DELETE FROM group_ranks
            WHERE chat_id=? AND user_id=?
            """,
            (chat_id, user_id)
        )

    else:

        cursor.execute("""
            INSERT INTO group_ranks(
                chat_id,
                user_id,
                rank
            )
            VALUES(?,?,?)

            ON CONFLICT(chat_id,user_id)
            DO UPDATE SET rank=excluded.rank
        """, (
            chat_id,
            user_id,
            rank
        ))

    db.commit()


def remove_rank_permissions(chat_id, user_id):
    cursor.execute(
        """
        DELETE FROM rank_permissions
        WHERE chat_id=? AND user_id=?
        """,
        (chat_id, user_id)
    )

    db.commit()


def get_permissions(chat_id, user_id):
    cursor.execute(
        """
        SELECT permission
        FROM rank_permissions
        WHERE chat_id=? AND user_id=?
        """,
        (chat_id, user_id)
    )

    return {
        r["permission"]
        for r in cursor.fetchall()
    }


def can_manage_rank(actor_rank, target_rank, action):
    if target_rank == "owner":
        return False

    if actor_rank == "owner":
        return True

    if actor_rank == "assistant_owner":
        return target_rank != "assistant_owner"

    if actor_rank == "manager":
        return target_rank in (
            "admin",
            "moderator",
            "animal"
        )

    return False


def can_use_moderation(actor_rank):
    return rank_level(actor_rank) >= rank_level("admin")


def rank_command_error(message, text):
    bot.reply_to(message, text)
    return True


def bot_promote(
    chat_id,
    user_id,
    rank,
    permissions=None
):
    # رتب داخل البوت فقط
    if rank in (
        "animal",
        "admin",
        "manager"
    ):
        return True

    if rank == "moderator" and permissions is None:
        permissions = set()

    if permissions is None:
        permissions = {
            "can_change_info",
            "can_delete_messages",
            "can_restrict_members",
            "can_invite_users",
            "can_pin_messages",
            "can_manage_video_chats",
            "can_manage_topics"
        }

    kwargs = {
        "can_change_info":
            "can_change_info" in permissions,

        "can_delete_messages":
            "can_delete_messages" in permissions,

        "can_restrict_members":
            "can_restrict_members" in permissions,

        "can_invite_users":
            "can_invite_users" in permissions,

        "can_pin_messages":
            "can_pin_messages" in permissions,

        "can_manage_video_chats":
            "can_manage_video_chats" in permissions,

        "can_manage_topics":
            "can_manage_topics" in permissions
    }

    # مساعد المالك
    if rank == "assistant_owner":

        kwargs.update({
            "can_change_info": True,
            "can_delete_messages": True,
            "can_restrict_members": True,
            "can_invite_users": True,
            "can_pin_messages": True,
            "can_manage_video_chats": True,
            "can_manage_topics": True,
            "can_promote_members": True
        })

    elif rank == "moderator":
        kwargs["can_promote_members"] = False

    try:

        bot.promote_chat_member(
            chat_id,
            user_id,
            **kwargs
        )

        title = TITLE_NAMES.get(rank)

        if title:

            try:
                bot.set_chat_administrator_custom_title(
                    chat_id,
                    user_id,
                    title
                )
            except Exception:
                pass

        return True

    except Exception as e:
        print("[PROMOTE]", e)
        return False


def bot_demote(chat_id, user_id):
    try:

        bot.promote_chat_member(
            chat_id,
            user_id,
            can_change_info=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_video_chats=False,
            can_manage_topics=False,
            can_promote_members=False
        )

        return True

    except Exception as e:
        print("[DEMOTE]", e)
        return False


def target_protected(message, target):
    if not target:
        return True

    tr = get_rank(
        message.chat.id,
        target.id
    )

    ar = get_rank(
        message.chat.id,
        message.from_user.id
    )

    if tr == "owner":
        return True

    if rank_level(tr) >= rank_level(ar):
        return True

    return False


def admin_required(message):
    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return False

    ar = get_rank(
        message.chat.id,
        message.from_user.id
    )

    if not can_use_moderation(ar):

        bot.reply_to(
            message,
            "❌ هذا الأمر للأدمن فما فوق."
        )

        return False

    return True


# =========================================================
# سجل الإدارة
# =========================================================
def log_action(
    chat_id,
    admin_id,
    target_id,
    action,
    details=""
):
    cursor.execute("""
        INSERT INTO actions(
            chat_id,
            admin_id,
            target_id,
            action,
            details,
            created_at
        )
        VALUES(?,?,?,?,?,?)
    """, (
        chat_id,
        admin_id,
        target_id,
        action,
        details,
        now()
    ))

    db.commit()


# =========================================================
# استخراج الهدف
# =========================================================
def get_target(message, argument=""):

    if (
        message.reply_to_message
        and message.reply_to_message.from_user
    ):
        return message.reply_to_message.from_user

    argument = argument.strip()

    if not argument:
        return None

    if re.fullmatch(r"-?\d+", argument):

        m = get_member(
            message.chat.id,
            int(argument)
        )

        return m.user if m else None

    username = argument.lstrip("@").lower()

    cursor.execute("""
        SELECT user_id
        FROM group_users
        WHERE chat_id=?
        AND LOWER(username)=?
        LIMIT 1
    """, (
        message.chat.id,
        username
    ))

    row = cursor.fetchone()

    if row:

        m = get_member(
            message.chat.id,
            row["user_id"]
        )

        return m.user if m else None

    return None


# =========================================================
# الكشف والمالك
# =========================================================
def show_profile(message, target):

    if not target:

        bot.reply_to(
            message,
            "❌ لم أستطع العثور على المستخدم.\n"
            "استخدم الأمر بالرد أو بالـ ID."
        )

        return

    cursor.execute(
        """
        SELECT messages,warnings
        FROM group_users
        WHERE chat_id=? AND user_id=?
        """,
        (
            message.chat.id,
            target.id
        )
    )

    row = cursor.fetchone()

    messages = row["messages"] if row else 0
    warnings = row["warnings"] if row else 0

    caption = (
        f"🔎 <b>كشف المستخدم</b>\n"
        f"<b>الاسم:</b> {mention(target)}\n"
        f"┈┅⊷━⊷┅┅┈\n"
        f"<b>اليوزر:</b> "
        f"{html.escape(username_text(target))}\n"
        f"┈┅⊷━⊷┅┅┈\n"
        f"<b>الايدي:</b> "
        f"<code>{target.id}</code>\n"
        f"┈┅⊷━⊷┅┅┈\n"
        f"<b>رسائله:</b> "
        f"<code>{messages}</code>\n"
        f"┈┅⊷━⊷┅┅┈\n"
        f"<b>تحذيراته:</b> "
        f"<code>{warnings}</code>"
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        button(
            full_name(target)[:30],
            url=f"tg://user?id={target.id}",
            style="success",
            icon_custom_emoji_id=CE_MEMBER
        )
    )

    try:

        photos = bot.get_user_profile_photos(
            target.id,
            limit=1
        )

        if photos.total_count:

            bot.send_photo(
                message.chat.id,
                photos.photos[0][-1].file_id,
                caption=caption,
                reply_markup=markup
            )

            return

    except Exception:
        pass

    bot.send_message(
        message.chat.id,
        caption,
        reply_markup=markup
    )


def get_owner_user(chat_id):

    try:

        admins = bot.get_chat_administrators(chat_id)

        for m in admins:

            if m.status == "creator":
                return m.user

    except Exception as e:
        print("[OWNER]", e)

    return None


def owner_profile(message):

    owner = get_owner_user(message.chat.id)

    if not owner:

        bot.reply_to(
            message,
            "❌ لم أستطع العثور على مالك المجموعة."
        )

        return

    text = (
        "✢ 𝐓𝐇𝐄 𝐎𝐖𝐍𝐄𝐑 ✢\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"𝐍𝐀𝐌𝐄  :   ✢ {mention(owner, owner=True)} ✢\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"𝐔𝐒𝐄𝐑  :   ✢ "
        f"{html.escape(username_text(owner))} ✢\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"𝐈𝐃  :  ✢ "
        f"<code>{owner.id}</code> ✢\n"
        "┈┅⊷━⊷┅┅┈"
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        button(
            full_name(owner)[:30],
            url=f"tg://user?id={owner.id}",
            style="success",
            icon_custom_emoji_id=CE_OWNER_DEVELOPER
        )
    )

    try:

        photos = bot.get_user_profile_photos(
            owner.id,
            limit=1
        )

        if photos.total_count:

            bot.send_photo(
                message.chat.id,
                photos.photos[0][-1].file_id,
                caption=text,
                reply_markup=markup
            )

            return

    except Exception:
        pass

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup
    )


# =========================================================
# التحذيرات والكتم
# =========================================================
def get_warnings(chat_id, user_id):

    cursor.execute(
        """
        SELECT warnings
        FROM group_users
        WHERE chat_id=? AND user_id=?
        """,
        (
            chat_id,
            user_id
        )
    )

    r = cursor.fetchone()

    return r["warnings"] if r else 0


def set_warnings(chat_id, user_id, count):

    cursor.execute(
        """
        UPDATE group_users
        SET warnings=?
        WHERE chat_id=? AND user_id=?
        """,
        (
            count,
            chat_id,
            user_id
        )
    )

    db.commit()


def mute_user(chat_id, user_id):

    bot.restrict_chat_member(
        chat_id,
        user_id,
        permissions=types.ChatPermissions(
            can_send_messages=False
        )
    )


def unmute_user(chat_id, user_id):

    bot.restrict_chat_member(
        chat_id,
        user_id,
        permissions=types.ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )


def ban_user(chat_id, user_id):
    bot.ban_chat_member(
        chat_id,
        user_id
    )


def unban_user(chat_id, user_id):
    bot.unban_chat_member(
        chat_id,
        user_id
    )


def kick_user(chat_id, user_id):

    bot.ban_chat_member(
        chat_id,
        user_id
    )

    bot.unban_chat_member(
        chat_id,
        user_id
    )


def add_warning(message, target):

    chat_id = message.chat.id

    register_member(
        chat_id,
        target
    )

    current = (
        get_warnings(
            chat_id,
            target.id
        ) + 1
    )

    set_warnings(
        chat_id,
        target.id,
        current
    )

    row = get_group(chat_id)

    maximum = (
        row["max_warnings"]
        if row
        else 3
    )

    log_action(
        chat_id,
        message.from_user.id,
        target.id,
        "تحذير",
        f"{current}/{maximum}"
    )

    if current >= maximum:

        try:

            mute_user(
                chat_id,
                target.id
            )

            set_warnings(
                chat_id,
                target.id,
                0
            )

            return (
                f"⚠️ تم تحذير {mention(target)}\n"
                f"📊 وصل إلى {maximum}\n"
                "🔇 تم كتمه تلقائيًا."
            )

        except Exception:
            pass

    return (
        f"⚠️ تم تحذير {mention(target)}\n"
        f"📊 التحذيرات: "
        f"<code>{current}/{maximum}</code>"
    )


# =========================================================
# الحماية
# =========================================================
def contains_link(text):

    if not text:
        return False

    return any(
        re.search(
            p,
            text,
            re.I
        )
        for p in [
            r"https?://",
            r"www\.",
            r"t\.me/",
            r"telegram\.me/",
            r"@\w+\.\w+"
        ]
    )


def is_blacklisted(chat_id, text):

    if not text:
        return False

    cursor.execute(
        """
        SELECT word
        FROM blacklist
        WHERE chat_id=?
        """,
        (chat_id,)
    )

    return any(
        r["word"].lower() in text.lower()
        for r in cursor.fetchall()
    )


flood_cache = defaultdict(
    lambda: defaultdict(deque)
)


def check_flood(chat_id, user_id):

    q = flood_cache[
        chat_id
    ][
        user_id
    ]

    t = time.time()

    while q and t - q[0] > 5:
        q.popleft()

    q.append(t)

    if len(q) >= 6:

        q.clear()

        return True

    return False


repeat_cache = defaultdict(
    lambda: defaultdict(
        lambda: deque(maxlen=4)
    )
)


def check_repeat(chat_id, user_id, text):

    if not text:
        return False

    q = repeat_cache[
        chat_id
    ][
        user_id
    ]

    q.append(
        text.strip().lower()
    )

    return (
        len(q) >= 3
        and len(set(q)) == 1
    )


def delete_message_safe(message):

    try:

        bot.delete_message(
            message.chat.id,
            message.message_id
        )

    except Exception:
        pass


# =========================================================
# الإعدادات
# =========================================================
def all_locks(chat_id, state):

    for c in [
        "links",
        "photos",
        "videos",
        "documents",
        "stickers",
        "audio",
        "animations"
    ]:

        set_group_setting(
            chat_id,
            c,
            state
        )


def send_settings(message):

    row = get_group(
        message.chat.id
    )

    if not row:
        return

    def icon(v):
        return "🟢" if v else "🔴"

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    fields = [
        ("welcome", "الترحيب"),
        ("links", "الروابط"),
        ("photos", "الصور"),
        ("videos", "الفيديو"),
        ("documents", "الملفات"),
        ("stickers", "الملصقات"),
        ("audio", "الصوت"),
        ("animations", "المتحركات"),
        ("repeat_messages", "التكرار"),
        ("new_member_protection", "حماية الجدد")
    ]

    for col, label in fields:

        markup.add(
            button(
                f"{icon(row[col])} {label}",
                callback_data="toggle_" + col,
                style=(
                    "success"
                    if row[col]
                    else "danger"
                )
            )
        )

    markup.add(
        button(
            "🔒 قفل الكل",
            callback_data="lock_all",
            style="danger"
        ),
        button(
            "🔓 فتح الكل",
            callback_data="unlock_all",
            style="success"
        )
    )

    bot.send_message(
        message.chat.id,
        "⚙️ <b>لوحة إعدادات الحماية</b>\n\n"
        "🟢 مفعّل\n"
        "🔴 معطّل",
        reply_markup=markup
    )


# =========================================================
# الأوامر
# =========================================================
def commands_text(owner=None):

    extra = (
        f"\n\n👑 <b>مالك المجموعة:</b> "
        f"{mention(owner, owner=True)}"
        if owner
        else ""
    )

    return (
        "<b>قائمة أوامر البوت</b>\n"
        "┈┅⊷━⊷┅┅┈\n"

        "<b>للجميع:</b>\n"
        "<code>الاوامر</code> • "
        "<code>مساعدة</code> • "
        "<code>ايدي</code> • "
        "<code>معلوماتي</code>\n"

        "<code>كشف</code> • "
        "<code>معلومات</code> • "
        "<code>البوت</code> • "
        "<code>المطور</code> • "
        "<code>المالك</code>\n"

        "┈┅⊷━⊷┅┅┈\n"

        "<b>الإدارة:</b>\n"
        "<code>حظر</code> • "
        "<code>فك حظر</code> • "
        "<code>طرد</code> • "
        "<code>كتم</code> • "
        "<code>فك كتم</code>\n"

        "<code>تحذير</code> • "
        "<code>تحذيرات</code> • "
        "<code>مسح التحذيرات</code> • "
        "<code>الغاء تحذير</code>\n"

        "┈┅⊷━⊷┅┅┈\n"

        "<b>نظام الرتب:</b>\n"
        "<code>رفع مساعد المالك</code> • "
        "<code>تنزيل مساعد المالك</code>\n"

        "<code>رفع مدير</code> • "
        "<code>تنزيل مدير</code>\n"

        "<code>رفع ادمن</code> • "
        "<code>تنزيل ادمن</code>\n"

        "<code>رفع مشرف</code> • "
        "<code>تنزيل مشرف</code>\n"

        "<code>رفع حيوان</code> • "
        "<code>تنزيل حيوان</code>\n"

        "┈┅⊷━⊷┅┅┈\n"

        "<b>الحماية:</b>\n"
        "<code>قفل الروابط</code> • "
        "<code>قفل الصور</code> • "
        "<code>قفل الفيديو</code>\n"

        "<code>قفل الملفات</code> • "
        "<code>قفل الملصقات</code> • "
        "<code>قفل الصوت</code>\n"

        "<code>قفل المتحركات</code> • "
        "<code>قفل التكرار</code> • "
        "<code>قفل حماية الجدد</code>\n"

        "<code>قفل الكل</code> • "
        "<code>فتح الكل</code>\n"

        "┈┅⊷━⊷┅┅┈\n"

        "<b>الكلمات:</b> "
        "<code>منع كلمة ...</code> • "
        "<code>الغاء منع كلمة ...</code> • "
        "<code>قائمة الكلمات</code>\n"

        "<b>الردود:</b> "
        "<code>اضف رد ...</code> • "
        "<code>حذف رد ...</code> • "
        "<code>قائمة الردود</code>\n"

        "<b>الإدارة:</b> "
        "<code>الاعدادات</code> • "
        "<code>احصائيات</code> • "
        "<code>السجل</code>"

        + extra
    )


# =========================================================
# لوحة صلاحيات المشرف
# =========================================================
MOD_PERMS = {

    "change_info": (
        "✏️ تغيير المعلومات",
        "can_change_info"
    ),

    "delete_messages": (
        "🗑 حذف الرسائل",
        "can_delete_messages"
    ),

    "restrict_members": (
        "🔇 تقييد الأعضاء",
        "can_restrict_members"
    ),

    "invite_users": (
        "👥 دعوة الأعضاء",
        "can_invite_users"
    ),

    "pin_messages": (
        "📌 تثبيت الرسائل",
        "can_pin_messages"
    ),

    "manage_video_chats": (
        "🎥 إدارة المكالمات",
        "can_manage_video_chats"
    ),

    "manage_topics": (
        "🧵 إدارة المواضيع",
        "can_manage_topics"
    )
}


pending_promotions = {}


def moderator_panel(call, token):

    p = pending_promotions.get(token)

    if not p:

        bot.answer_callback_query(
            call.id,
            "❌ انتهت العملية.",
            show_alert=True
        )

        return

    selected = p["permissions"]

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    for key, (label, _) in MOD_PERMS.items():

        on = key in selected

        markup.add(
            button(
                ("🟢 " if on else "🔴 ") + label,
                callback_data=f"mp:{token}:{key}",
                style=(
                    "success"
                    if on
                    else "danger"
                )
            )
        )

    markup.add(
        button(
            "✅ تأكيد رفع المشرف",
            callback_data=f"mconfirm:{token}",
            style="success"
        )
    )

    markup.add(
        button(
            "❌ إلغاء",
            callback_data=f"mcancel:{token}",
            style="danger"
        )
    )

    bot.edit_message_text(
        "🛡️ <b>اختيار صلاحيات المشرف</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"👤 الهدف: {mention(p['target'])}\n\n"
        "اختر الصلاحيات ثم اضغط تأكيد.\n"
        "⚠️ صلاحية رفع المشرفين محجوزة "
        "لنظام الرتب ولا تُمنح للمشرف.",

        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# الردود التلقائية
# =========================================================
reply_pending = {}


def get_auto_reply(chat_id, text):
    if not text:
        return None

    key = clean_text(text)

    cursor.execute(
        """
        SELECT *
        FROM auto_replies
        WHERE chat_id=? AND trigger=?
        LIMIT 1
        """,
        (chat_id, key)
    )

    return cursor.fetchone()


def save_auto_reply(
    chat_id,
    trigger,
    reply_text,
    button_enabled=False,
    button_text="",
    button_url="",
    button_emoji_id=""
):
    cursor.execute(
        """
        INSERT INTO auto_replies(
            chat_id,
            trigger,
            reply_text,
            button_enabled,
            button_text,
            button_url,
            button_emoji_id
        )
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(chat_id,trigger)
        DO UPDATE SET
            reply_text=excluded.reply_text,
            button_enabled=excluded.button_enabled,
            button_text=excluded.button_text,
            button_url=excluded.button_url,
            button_emoji_id=excluded.button_emoji_id
        """,
        (
            chat_id,
            clean_text(trigger),
            reply_text,
            1 if button_enabled else 0,
            button_text,
            button_url,
            button_emoji_id
        )
    )
    db.commit()


def delete_auto_reply(chat_id, trigger):
    cursor.execute(
        "DELETE FROM auto_replies WHERE chat_id=? AND trigger=?",
        (chat_id, clean_text(trigger))
    )
    db.commit()
    return cursor.rowcount > 0


def extract_custom_emoji_id(message):
    """
    يلتقط ID الإيموجي المخصص تلقائيًا من الرسالة،
    بدون أن يكتب المستخدم الـ ID يدويًا.
    """
    if not message:
        return None

    entities = []

    for attr in ("entities", "caption_entities"):
        value = getattr(message, attr, None)
        if value:
            entities.extend(value)

    for entity in entities:
        if getattr(entity, "type", "") == "custom_emoji":
            emoji_id = getattr(entity, "custom_emoji_id", None)
            if emoji_id:
                return str(emoji_id)

    return None


def reply_button_markup(row):
    if not row or not row["button_enabled"]:
        return None

    button_text = row["button_text"] or "Lovely Updates"
    button_url = row["button_url"] or LOVELY_UPDATES_URL
    emoji_id = row["button_emoji_id"] or CE_REPLY_BUTTON

    markup = types.InlineKeyboardMarkup()
    b = transparent_url_button(
        button_text,
        button_url,
        emoji_id=emoji_id
    )

    if b is not None:
        markup.add(b)

    return markup


def send_saved_auto_reply(message, row):
    if not row:
        return False

    markup = reply_button_markup(row)

    try:
        bot.reply_to(
            message,
            row["reply_text"],
            reply_markup=markup
        )
        return True
    except Exception as e:
        print("[Auto Reply Send Error]", e)
        return False


def ask_reply_button(call, token):
    p = reply_pending.get(token)
    if not p:
        bot.answer_callback_query(
            call.id,
            "❌ انتهت العملية.",
            show_alert=True
        )
        return

    markup = types.InlineKeyboardMarkup()
    markup.row(
        button(
            "نعم",
            callback_data=f"replybtn_yes:{token}",
            style="primary",
            icon_custom_emoji_id=CE_REPLY_BUTTON
        ),
        button(
            "لا",
            callback_data=f"replybtn_no:{token}",
            style="primary",
            icon_custom_emoji_id=CE_REPLY_BUTTON
        )
    )

    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "هل تريد إضافة زر شفاف للرد؟",
        reply_markup=markup
    )


def start_add_reply(message, trigger):
    if not trigger:
        bot.reply_to(
            message,
            "❌ اكتب الكلمة بعد الأمر.\nمثال: <code>اضف رد كاشي</code>"
        )
        return True

    token = secrets.token_hex(8)
    reply_pending[token] = {
        "chat_id": message.chat.id,
        "initiator": message.from_user.id,
        "trigger": clean_text(trigger),
        "step": "reply"
    }

    bot.reply_to(
        message,
        f"📝 تم اختيار الكلمة: <code>{html.escape(trigger)}</code>\n\n"
        "أرسل الآن نص الرد الذي تريد حفظه."
    )
    return True


def continue_reply_setup(message):
    if not message or not message.from_user:
        return False

    for token, p in list(reply_pending.items()):
        if (
            p.get("chat_id") != message.chat.id
            or p.get("initiator") != message.from_user.id
        ):
            continue

        step = p.get("step")

        if step == "reply":
            reply_text = message.text or message.caption or ""
            if not reply_text.strip():
                bot.reply_to(message, "❌ أرسل نص الرد فقط.")
                return True

            p["reply_text"] = reply_text
            p["step"] = "button_choice"
            ask_markup = types.InlineKeyboardMarkup()
            ask_markup.row(
                button(
                    "نعم",
                    callback_data=f"replybtn_yes:{token}",
                    style="primary",
                    icon_custom_emoji_id=CE_REPLY_BUTTON
                ),
                button(
                    "لا",
                    callback_data=f"replybtn_no:{token}",
                    style="primary",
                    icon_custom_emoji_id=CE_REPLY_BUTTON
                )
            )
            bot.reply_to(
                message,
                "✅ تم حفظ نص الرد مؤقتًا.\n\nهل تريد إضافة زر شفاف للرد؟",
                reply_markup=ask_markup
            )
            return True

        if step == "button_text":
            text = message.text or ""
            if not text.strip():
                bot.reply_to(message, "❌ أرسل نص الزر.")
                return True
            p["button_text"] = text.strip()
            p["step"] = "button_url"
            bot.reply_to(
                message,
                "🔗 أرسل رابط الزر كاملًا، مثال:\n<code>https://t.me/LeaDeR_E</code>"
            )
            return True

        if step == "button_url":
            url = (message.text or "").strip()
            if not re.match(r"^https?://", url, re.I):
                bot.reply_to(message, "❌ أرسل رابطًا يبدأ بـ http:// أو https://")
                return True
            p["button_url"] = url
            p["step"] = "button_emoji"
            bot.reply_to(
                message,
                "✨ أرسل الآن الإيموجي المخصص للزر.\n"
                "سيتم التقاط الـ ID تلقائيًا، ولا تحتاج لكتابته."
            )
            return True

        if step == "button_emoji":
            emoji_id = extract_custom_emoji_id(message)
            if not emoji_id:
                bot.reply_to(
                    message,
                    "❌ لم أجد Premium Emoji في الرسالة. أرسل الإيموجي المخصص نفسه."
                )
                return True
            p["button_emoji_id"] = emoji_id
            save_auto_reply(
                p["chat_id"],
                p["trigger"],
                p["reply_text"],
                True,
                p.get("button_text", ""),
                p.get("button_url", ""),
                p.get("button_emoji_id", CE_REPLY_BUTTON)
            )
            reply_pending.pop(token, None)
            bot.reply_to(message, "✅ تم حفظ الرد والزر بنجاح.")
            return True

    return False


def finalize_reply_without_button(call, token):
    p = reply_pending.get(token)
    if not p:
        bot.answer_callback_query(call.id, "❌ انتهت العملية.", show_alert=True)
        return

    if p.get("initiator") != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ هذه العملية ليست لك.", show_alert=True)
        return

    save_auto_reply(
        p["chat_id"],
        p["trigger"],
        p["reply_text"],
        False,
        "",
        "",
        ""
    )
    reply_pending.pop(token, None)
    bot.answer_callback_query(call.id, "✅ تم حفظ الرد")
    try:
        bot.edit_message_text(
            "✅ تم حفظ الرد بدون زر.",
            call.message.chat.id,
            call.message.message_id
        )
    except Exception:
        pass


def continue_reply_button_setup(call, token):
    p = reply_pending.get(token)
    if not p:
        bot.answer_callback_query(call.id, "❌ انتهت العملية.", show_alert=True)
        return

    if p.get("initiator") != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ هذه العملية ليست لك.", show_alert=True)
        return

    p["step"] = "button_text"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "🔘 أرسل اسم الزر الذي سيظهر أسفل الرد."
    )


# =========================================================
# لوحة الأدمن الخاصة بالمطور
# =========================================================
def admin_panel_markup():

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.row(
        button(
            "📊 الإحصائيات",
            callback_data="admin:stats",
            style="primary",
            icon_custom_emoji_id=CE_ADMIN
        ),
        button(
            "👥 المجموعات",
            callback_data="admin:groups",
            style="primary",
            icon_custom_emoji_id=CE_MEMBER
        )
    )

    markup.row(
        button(
            "💬 الردود",
            callback_data="admin:replies",
            style="primary",
            icon_custom_emoji_id=CE_REPLY_BUTTON
        ),
        button(
            "📝 السجل",
            callback_data="admin:actions",
            style="primary",
            icon_custom_emoji_id=CE_COMMANDS
        )
    )

    markup.row(
        button(
            "🔄 تحديث",
            callback_data="admin:refresh",
            style="primary",
            icon_custom_emoji_id=CE_REPLY_BUTTON
        ),
        button(
            "❌ إغلاق",
            callback_data="admin:close",
            style="danger",
            icon_custom_emoji_id=CE_ERROR
        )
    )

    return markup


def send_admin_panel(chat_id, message_id=None):

    if chat_id != DEVELOPER_ID:
        return False

    text = (
        "🛡️ <b>لوحة أدمن البوت</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        "مرحبًا بك في لوحة التحكم الخاصة بالمطور.\n\n"
        "من هنا يمكنك متابعة حالة البوت، المجموعات،\n"
        "الردود التلقائية، وسجل الإجراءات.\n"
        "┈┅⊷━⊷┅┅┈"
    )

    if message_id is not None:
        try:
            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=admin_panel_markup()
            )
            return True
        except Exception:
            pass

    bot.send_message(
        chat_id,
        text,
        reply_markup=admin_panel_markup()
    )
    return True


def admin_stats_text():

    cursor.execute("SELECT COUNT(*) AS c FROM groups")
    groups_count = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) AS c FROM group_users")
    members_count = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) AS c FROM auto_replies")
    replies_count = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) AS c FROM actions")
    actions_count = cursor.fetchone()["c"]

    return (
        "📊 <b>إحصائيات البوت</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"👥 المجموعات: <code>{groups_count}</code>\n"
        f"👤 الأعضاء المسجلون: <code>{members_count}</code>\n"
        f"💬 الردود التلقائية: <code>{replies_count}</code>\n"
        f"📝 إجراءات الإدارة: <code>{actions_count}</code>\n"
        "┈┅⊷━⊷┅┅┈"
    )


def admin_groups_text():

    cursor.execute(
        "SELECT chat_id,title FROM groups ORDER BY rowid DESC LIMIT 30"
    )
    rows = cursor.fetchall()

    if not rows:
        return "👥 <b>المجموعات</b>\n┈┅⊷━⊷┅┅┈\nلا توجد مجموعات مسجلة حتى الآن."

    lines = [
        "👥 <b>المجموعات المسجلة</b>",
        "┈┅⊷━⊷┅┅┈"
    ]

    for index, row in enumerate(rows, 1):
        title = html.escape(row["title"] or "بدون اسم")
        lines.append(
            f"{index}. <b>{title}</b> — <code>{row['chat_id']}</code>"
        )

    return "\n".join(lines)


def admin_replies_text():

    cursor.execute(
        "SELECT chat_id,trigger,button_enabled FROM auto_replies ORDER BY rowid DESC LIMIT 40"
    )
    rows = cursor.fetchall()

    if not rows:
        return "💬 <b>الردود التلقائية</b>\n┈┅⊷━⊷┅┅┈\nلا توجد ردود محفوظة."

    lines = [
        "💬 <b>آخر الردود التلقائية</b>",
        "┈┅⊷━⊷┅┅┈"
    ]

    for index, row in enumerate(rows, 1):
        trigger = html.escape(row["trigger"] or "")
        has_button = "🔘" if row["button_enabled"] else "▫️"
        lines.append(
            f"{index}. <code>{trigger}</code> {has_button} — <code>{row['chat_id']}</code>"
        )

    return "\n".join(lines)


def admin_actions_text():

    cursor.execute(
        "SELECT chat_id,admin_id,target_id,action,details,created_at FROM actions ORDER BY id DESC LIMIT 25"
    )
    rows = cursor.fetchall()

    if not rows:
        return "📝 <b>سجل الإجراءات</b>\n┈┅⊷━⊷┅┅┈\nلا يوجد سجل حتى الآن."

    lines = [
        "📝 <b>آخر إجراءات الإدارة</b>",
        "┈┅⊷━⊷┅┅┈"
    ]

    for row in rows:
        action = html.escape(row["action"] or "")
        details = html.escape(row["details"] or "")
        suffix = f" — {details}" if details else ""
        lines.append(
            f"• <b>{action}</b> — <code>{row['admin_id']}</code>{suffix}"
        )

    return "\n".join(lines)


def send_admin_section(call, text):

    if call.from_user.id != DEVELOPER_ID:
        bot.answer_callback_query(
            call.id,
            "❌ هذه اللوحة للمطور فقط.",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_panel_markup()
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=admin_panel_markup()
        )


# =========================================================
# START الخاص
# =========================================================
def start_private(message):

    user = message.from_user

    text = (
        f"مرحبًـا ⤦{mention(user)} ⤥\n"
        "┈┅⊷━⊷┅┅┈\n"
        "هذا البوت مخصص لإدارة وحماية "
        "المجموعات بالكـامل.\n"
        "┈┅⊷━⊷┅┅┈\n"
        "اضـف البـوت فـي المجـموعـه "
        "الخـاصـه بـك وارفـعـه مشـرف "
        "مع جمـيع الصـلاحيـات."
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        button(
            "اضفنـي آلى مجمـوعـتـك",
            url=ADD_TO_GROUP_URL,
            style="primary",
            icon_custom_emoji_id=CE_ADD_GROUP
        )
    )

    if user.id == DEVELOPER_ID:
        markup.add(
            button(
                "🛡️ لوحة الأدمن",
                callback_data="admin:open",
                style="primary",
                icon_custom_emoji_id=CE_ADMIN
            )
        )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup
    )


# =========================================================
# الأعضاء الجدد
# =========================================================

# النسخة الأصلية محفوظة كما هي دون تشغيلها، لضمان عدم فقد أي وظيفة/سطر من النسخة السابقة.
def new_members_handler_legacy_original(message):

    ensure_group(message.chat)

    if not group_setting(
        message.chat.id,
        "welcome"
    ):
        return

    names = []

    for u in message.new_chat_members or []:

        if u.is_bot:
            continue

        register_member(
            message.chat.id,
            u
        )

        names.append(
            mention(u)
        )

    if not names:
        return

    text = (
        "🎉 <b>أهلًا وسهلًا!</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        + "\n".join(names)
        + "\n"
        "┈┅⊷━⊷┅┅┈\n"
        "❤️ نورتوا الجروب!"
    )

    markup = types.InlineKeyboardMarkup()

    markup.row(
        button(
            "📖 الأوامر",
            callback_data="show_commands",
            style="primary"
        ),

        button(
            "⚙️ الإعدادات",
            callback_data="settings",
            style="primary"
        )
    )

    try:

        sent = bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup
        )

        Thread(
            target=lambda: (
                time.sleep(60),
                delete_message_safe(sent)
            ),
            daemon=True
        ).start()

    except Exception:
        pass


@bot.message_handler(
    content_types=["new_chat_members"]
)
def new_members_handler(message):

    ensure_group(message.chat)

    if not group_setting(
        message.chat.id,
        "welcome"
    ):
        return

    for u in message.new_chat_members or []:

        if u.is_bot:
            continue

        register_member(
            message.chat.id,
            u
        )

        safe_name = html.escape(full_name(u))
        safe_username = html.escape(username_text(u))

        welcome_text = (
            f"{tg_emoji(CE_WELCOME_LINE, '👋')} "
            f"اهـلا بيك يـ {safe_name}\n"
            f"{tg_emoji(CE_WELCOME_LINE, '👤')} يـوزرك | {safe_username}\n"
            f"{tg_emoji(CE_WELCOME_LINE, '🆔')} ايديـك | <code>{u.id}</code>"
        )

        markup = types.InlineKeyboardMarkup()

        markup.row(
            transparent_url_button(
                "اضافني الي مجموعاتك",
                ADD_TO_GROUP_URL,
                emoji_id=CE_REPLY_BUTTON
            )
        )

        markup.row(
            transparent_url_button(
                "Dev BoT",
                "https://t.me/L1_D_R",
                emoji_id=CE_DEV_BUTTON
            )
        )

        try:
            photos = bot.get_user_profile_photos(
                u.id,
                limit=1
            )

            if photos.total_count:
                sent = bot.send_photo(
                    message.chat.id,
                    photos.photos[0][-1].file_id,
                    caption=welcome_text,
                    reply_markup=markup
                )
            else:
                sent = bot.send_message(
                    message.chat.id,
                    welcome_text,
                    reply_markup=markup
                )

            Thread(
                target=lambda m=sent: (
                    time.sleep(60),
                    delete_message_safe(m)
                ),
                daemon=True
            ).start()

        except Exception as e:
            print("[Welcome Error]", e)
            try:
                sent = bot.send_message(
                    message.chat.id,
                    welcome_text,
                    reply_markup=markup
                )
                Thread(
                    target=lambda m=sent: (
                        time.sleep(60),
                        delete_message_safe(m)
                    ),
                    daemon=True
                ).start()
            except Exception:
                pass


# =========================================================
# الراوتر
# =========================================================
@bot.message_handler(
    content_types=[
        "text",
        "photo",
        "video",
        "document",
        "audio",
        "voice",
        "sticker",
        "animation",
        "video_note",
        "contact",
        "location",
        "poll"
    ]
)
def main_handler(message):

    try:

        if (
            message.from_user
            and not message.from_user.is_bot
        ):
            register_user(
                message,
                True
            )

        if message.chat.type == "private":

            if automatic_currency_conversion(message):
                return

            handle_private(message)
            return

        ensure_group(
            message.chat
        )

        if continue_reply_setup(message):
            return

        if automatic_currency_conversion(message):
            return

        if message.text:

            command, argument = command_parts(
                message
            )

            if (
                command
                and handle_command(
                    message,
                    command,
                    argument
                )
            ):
                return

        if message.text:
            saved_reply = get_auto_reply(
                message.chat.id,
                message.text
            )
            if saved_reply:
                send_saved_auto_reply(message, saved_reply)
                return

        protection_engine(message)

    except Exception as e:
        print("[Handler Error]", e)


def handle_private(message):

    raw_text = (message.text or "").strip()

    if (
        message.from_user
        and message.from_user.id == DEVELOPER_ID
        and clean_text(raw_text) in (
            "لوحة الادمن",
            "لوحة الادمن",
            "لوحه الادمن",
            "admin",
            "panel"
        )
    ):
        send_admin_panel(message.chat.id)
        return

    command, argument = command_parts(
        message
    )

    if command == "start":

        start_private(message)
        return

    if command in (
        "الاوامر",
        "مساعده"
    ):

        bot.send_message(
            message.chat.id,
            commands_text()
        )

        return

    if command == "ايدي":

        bot.send_message(
            message.chat.id,
            f"🆔 <b>الـ ID الخاص بك:</b>\n"
            f"<code>{message.from_user.id}</code>"
        )

        return

    if command == "البوت":

        bot.send_message(
            message.chat.id,
            "🤖 <b>بوت حماية وإدارة المجموعات</b>\n\n"
            "⚡ Polling\n"
            "💾 SQLite\n"
            "🛡️ حماية وإدارة"
        )

        return

    if command == "المطور":

        mk = types.InlineKeyboardMarkup()

        mk.add(
            button(
                "المطور",
                url=f"tg://user?id={DEVELOPER_ID}",
                style="success",
                icon_custom_emoji_id=CE_OWNER_DEVELOPER
            )
        )

        bot.send_message(
            message.chat.id,
            "👨‍💻 <b>مطور البوت</b>",
            reply_markup=mk
        )


# =========================================================
# معالجة الرتب
# =========================================================
def rank_action(
    message,
    action,
    rank,
    target
):

    chat_id = message.chat.id

    actor = message.from_user

    actor_rank = get_rank(
        chat_id,
        actor.id
    )

    target_rank = get_rank(
        chat_id,
        target.id
    )

    if not can_manage_rank(
        actor_rank,
        target_rank,
        action
    ):

        return rank_command_error(
            message,
            f"❌ لا يمكنك {action} "
            f"رتبة "
            f"{RANK_NAMES.get(target_rank,target_rank)}.\n"
            f"رتبتك: "
            f"<b>{RANK_NAMES.get(actor_rank,actor_rank)}</b>"
        )

    if (
        target.id == actor.id
        and rank != "animal"
    ):

        return rank_command_error(
            message,
            "❌ لا يمكنك استخدام هذا الأمر على نفسك."
        )

    if (
        rank == "assistant_owner"
        and not is_creator(
            chat_id,
            actor.id
        )
    ):

        return rank_command_error(
            message,
            "❌ رفع وتنزيل مساعد المالك للمالك فقط."
        )

    if (
        rank == "manager"
        and actor_rank not in (
            "owner",
            "assistant_owner"
        )
    ):

        return rank_command_error(
            message,
            "❌ رفع المدير للمالك أو مساعد المالك فقط."
        )

    if (
        rank == "admin"
        and actor_rank not in (
            "owner",
            "assistant_owner",
            "manager"
        )
    ):

        return rank_command_error(
            message,
            "❌ لا يمكنك رفع أدمن."
        )

    if (
        rank == "moderator"
        and actor_rank not in (
            "owner",
            "assistant_owner",
            "manager"
        )
    ):

        return rank_command_error(
            message,
            "❌ لا يمكنك رفع مشرف."
        )

    if (
        rank == "animal"
        and actor_rank not in (
            "owner",
            "assistant_owner",
            "manager"
        )
    ):

        return rank_command_error(
            message,
            "❌ لا يمكنك رفع حيوان."
        )

    # رفع مشرف
    if (
        action == "رفع"
        and rank == "moderator"
    ):

        token = secrets.token_hex(5)

        pending_promotions[token] = {
            "chat_id": chat_id,
            "target": target,
            "initiator": actor.id,
            "rank": "moderator",
            "permissions": set()
        }

        fake_call = type(
            "C",
            (),
            {
                "id": None,
                "message": message
            }
        )()

        moderator_panel(
            fake_call,
            token
        )

        return True

    # الرفع
    if action == "رفع":

        if not bot_promote(
            chat_id,
            target.id,
            rank
        ):

            return rank_command_error(
                message,
                "❌ فشل رفع الرتبة. "
                "تأكد أن البوت أدمن ولديه "
                "صلاحية إضافة مشرفين."
            )

        set_rank(
            chat_id,
            target.id,
            rank
        )

        if rank != "moderator":
            remove_rank_permissions(
                chat_id,
                target.id
            )

        log_action(
            chat_id,
            actor.id,
            target.id,
            "رفع " + RANK_NAMES[rank]
        )

        bot.reply_to(
            message,
            f"✅ تم رفع {mention(target)} "
            f"إلى <b>{RANK_NAMES[rank]}</b>."
        )

        return True

    # تنزيل
    if target_rank != rank:

        return rank_command_error(
            message,
            f"❌ المستخدم ليس برتبة "
            f"<b>{RANK_NAMES[rank]}</b>."
        )

    remove_rank_permissions(
        chat_id,
        target.id
    )

    set_rank(
        chat_id,
        target.id,
        "member"
    )

    if target_rank in (
        "moderator",
        "assistant_owner"
    ):

        if not bot_demote(
            chat_id,
            target.id
        ):

            set_rank(
                chat_id,
                target.id,
                target_rank
            )

            return rank_command_error(
                message,
                "❌ فشل تنزيل المشرف من Telegram. "
                "تأكد من صلاحيات البوت."
            )

    log_action(
        chat_id,
        actor.id,
        target.id,
        "تنزيل " + RANK_NAMES[rank]
    )

    bot.reply_to(
        message,
        f"✅ تم تنزيل {mention(target)} "
        f"من رتبة <b>{RANK_NAMES[rank]}</b>."
    )

    return True


# =========================================================
# الأوامر الرئيسية
# =========================================================
def handle_command(
    message,
    command,
    argument
):

    chat_id = message.chat.id

    # الأوامر
    if command in (
        "الاوامر",
        "مساعده"
    ):

        owner = get_owner_user(
            chat_id
        )

        mk = types.InlineKeyboardMarkup()

        if owner:

            mk.add(
                button(
                    full_name(owner)[:30],
                    url=f"tg://user?id={owner.id}",
                    style="primary",
                    icon_custom_emoji_id=CE_OWNER_DEVELOPER
                )
            )

        bot.reply_to(
            message,
            commands_text(owner),
            reply_markup=mk
        )

        return True

    # ايدي / معلوماتي
    if command in (
        "ايدي",
        "معلوماتي"
    ):

        u = message.from_user

        bot.reply_to(
            message,
            f"👤 {mention(u)}\n"
            "┈┅⊷━⊷┅┅┈\n"
            f"🆔 <code>{u.id}</code>\n"
            "┈┅⊷━⊷┅┅┈\n"
            f"👤 {html.escape(username_text(u))}"
        )

        return True

    # كشف
    if command == "كشف":

        show_profile(
            message,
            get_target(
                message,
                argument
            )
        )

        return True

    # المالك
    if command == "المالك":

        owner_profile(
            message
        )

        return True

    # معلومات
    if command == "معلومات":

        try:
            members = bot.get_chat_member_count(
                chat_id
            )

        except Exception:
            members = "غير معروف"

        bot.reply_to(
            message,
            f"🏠 <b>معلومات المجموعة</b>\n"
            "┈┅⊷━⊷┅┅┈\n"
            f"📌 {html.escape(message.chat.title or '')}\n"
            f"🆔 <code>{chat_id}</code>\n"
            f"👥 <code>{members}</code>"
        )

        return True

    # البوت
    if command == "البوت":

        bot.reply_to(
            message,
            "🤖 <b>بوت حماية متطور</b>\n"
            "💾 SQLite\n"
            "🛡️ حماية روابط وكلمات ووسائط\n"
            "⚠️ نظام تحذيرات\n"
            "👑 نظام رتب"
        )

        return True

    # المطور
    if command == "المطور":

        mk = types.InlineKeyboardMarkup()

        mk.add(
            button(
                "المطور",
                url=f"tg://user?id={DEVELOPER_ID}",
                style="success",
                icon_custom_emoji_id=CE_OWNER_DEVELOPER
            )
        )

        bot.reply_to(
            message,
            "👨‍💻 <b>مطور البوت</b>",
            reply_markup=mk
        )

        return True

    # أوامر الرتب
    if command in (
        "رفع",
        "تنزيل"
    ):

        arg = clean_text(
            argument
        )

        rank_alias = {
            "مساعد المالك": "assistant_owner",
            "مدير": "manager",
            "ادمن": "admin",
            "ادمـن": "admin",
            "مشرف": "moderator",
            "حيوان": "animal"
        }

        found = None
        target_arg = ""

        for label, rank in rank_alias.items():

            if arg == label:

                found = rank
                target_arg = ""
                break

            prefix = label + " "

            if arg.startswith(prefix):

                found = rank

                target_arg = argument[
                    len(label):
                ].strip()

                break

        if found:

            target = get_target(
                message,
                target_arg
            )

            if not target:

                bot.reply_to(
                    message,
                    "❌ استخدم الأمر بالرد على "
                    "المستخدم أو اكتب @username أو ID."
                )

                return True

            return rank_action(
                message,
                command,
                found,
                target
            )

    # أوامر الإدارة
    admin_commands = {
        "حظر",
        "فك",
        "فكحظر",
        "طرد",
        "كتم",
        "فككتم",
        "تحذير",
        "تحذيرات",
        "مسح",
        "الغاء",
        "قفل",
        "فتح",
        "منع",
        "احصائيات",
        "السجل",
        "الاعدادات"
    }

    if (
        command in admin_commands
        and not admin_required(message)
    ):
        return True

    actor_rank = get_rank(
        chat_id,
        message.from_user.id
    )

    # حظر
    if command == "حظر":

        t = get_target(
            message,
            argument
        )

        if not t:

            bot.reply_to(
                message,
                "❌ استخدم الأمر بالرد "
                "أو @username أو ID."
            )

            return True

        if (
            target_protected(message, t)
            or target_is_admin(
                chat_id,
                t.id
            )
        ):

            bot.reply_to(
                message,
                "❌ لا يمكنك حظر هذا "
                "المستخدم بسبب رتبته."
            )

            return True

        try:

            ban_user(
                chat_id,
                t.id
            )

            log_action(
                chat_id,
                message.from_user.id,
                t.id,
                "حظر"
            )

            bot.reply_to(
                message,
                f"🚫 تم حظر {mention(t)}."
            )

        except Exception:

            bot.reply_to(
                message,
                "❌ فشل الحظر."
            )

        return True

    # فك الحظر
    if command in (
        "فك",
        "فكحظر"
    ):

        t = get_target(
            message,
            argument
        )

        if not t:

            bot.reply_to(
                message,
                "❌ استخدم الأمر بالرد أو ID."
            )

            return True

        try:

            unban_user(
                chat_id,
                t.id
            )

            log_action(
                chat_id,
                message.from_user.id,
                t.id,
                "فك حظر"
            )

            bot.reply_to(
                message,
                f"✅ تم فك حظر {mention(t)}."
            )

        except Exception:

            bot.reply_to(
                message,
                "❌ لم أستطع فك الحظر."
            )

        return True

    # طرد
    if command == "طرد":

        t = get_target(
            message,
            argument
        )

        if not t:

            bot.reply_to(
                message,
                "❌ استخدم الأمر بالرد."
            )

            return True

        if (
            target_protected(message, t)
            or target_is_admin(
                chat_id,
                t.id
            )
        ):

            bot.reply_to(
                message,
                "❌ لا يمكنك طرد هذا المستخدم."
            )

            return True

        try:

            kick_user(
                chat_id,
                t.id
            )

            log_action(
                chat_id,
                message.from_user.id,
                t.id,
                "طرد"
            )

            bot.reply_to(
                message,
                f"👢 تم طرد {mention(t)}."
            )

        except Exception:

            bot.reply_to(
                message,
                "❌ فشل الطرد."
            )

        return True

    # كتم وفك كتم
    if command in (
        "كتم",
        "فككتم"
    ):

        t = get_target(
            message,
            argument
        )

        if not t:

            bot.reply_to(
                message,
                "❌ استخدم الأمر بالرد."
            )

            return True

        if (
            command == "كتم"
            and target_protected(
                message,
                t
            )
        ):

            bot.reply_to(
                message,
                "❌ لا يمكنك كتم هذه الرتبة."
            )

            return True

        try:

            if command == "كتم":
                mute_user(
                    chat_id,
                    t.id
                )
            else:
                unmute_user(
                    chat_id,
                    t.id
                )

            log_action(
                chat_id,
                message.from_user.id,
                t.id,
                command
            )

            bot.reply_to(
                message,
                (
                    "🔇 تم كتم "
                    if command == "كتم"
                    else "🔊 تم فك كتم "
                )
                + mention(t)
                + "."
            )

        except Exception:

            bot.reply_to(
                message,
                "❌ تعذر تنفيذ الأمر."
            )

        return True

    # تحذير
    if command == "تحذير":

        t = get_target(
            message,
            argument
        )

        if not t:

            bot.reply_to(
                message,
                "❌ استخدم الأمر بالرد."
            )

            return True

        if target_protected(
            message,
            t
        ):

            bot.reply_to(
                message,
                "❌ لا يمكنك تحذير هذه الرتبة."
            )

            return True

        bot.reply_to(
            message,
            add_warning(
                message,
                t
            )
        )

        return True

    # التحذيرات
    if command == "تحذيرات":

        t = (
            get_target(
                message,
                argument
            )
            or message.from_user
        )

        row = get_group(chat_id)

        mx = (
            row["max_warnings"]
            if row
            else 3
        )

        bot.reply_to(
            message,
            f"⚠️ <b>تحذيرات {mention(t)}</b>\n"
            f"📊 <code>"
            f"{get_warnings(chat_id,t.id)}"
            f"/{mx}</code>"
        )

        return True

    # مسح التحذيرات
    if (
        command == "مسح"
        and clean_text(argument) == "التحذيرات"
    ):

        t = get_target(
            message,
            ""
        )

        if not t:

            bot.reply_to(
                message,
                "❌ استخدم الأمر بالرد."
            )

            return True

        set_warnings(
            chat_id,
            t.id,
            0
        )

        log_action(
            chat_id,
            message.from_user.id,
            t.id,
            "مسح التحذيرات"
        )

        bot.reply_to(
            message,
            "✅ تم مسح التحذيرات."
        )

        return True

    # الغاء
    if command == "الغاء":

        a = clean_text(
            argument
        )

        if a == "تحذير":

            t = get_target(
                message,
                ""
            )

            if not t:

                bot.reply_to(
                    message,
                    "❌ استخدم الأمر بالرد."
                )

                return True

            set_warnings(
                chat_id,
                t.id,
                max(
                    0,
                    get_warnings(
                        chat_id,
                        t.id
                    ) - 1
                )
            )

            bot.reply_to(
                message,
                "✅ تم إلغاء تحذير."
            )

            return True

        if a.startswith("منع كلمه "):

            word = argument.split(
                maxsplit=2
            )[2].strip().lower()

            cursor.execute(
                """
                DELETE FROM blacklist
                WHERE chat_id=? AND word=?
                """,
                (
                    chat_id,
                    word
                )
            )

            db.commit()

            bot.reply_to(
                message,
                "✅ تم إلغاء منع "
                f"<code>{html.escape(word)}</code>"
            )

            return True

    # قفل وفتح
    if command in (
        "قفل",
        "فتح"
    ):

        a = clean_text(
            argument
        )

        lm = {
            "الروابط": "links",
            "الصور": "photos",
            "الفيديو": "videos",
            "الملفات": "documents",
            "الملصقات": "stickers",
            "الصوت": "audio",
            "المتحركات": "animations",
            "التكرار": "repeat_messages"
        }

        if a == "الكل":

            all_locks(
                chat_id,
                command == "قفل"
            )

            bot.reply_to(
                message,
                (
                    "🔒 تم قفل الكل."
                    if command == "قفل"
                    else
                    "🔓 تم فتح الكل."
                )
            )

            return True

        if a in (
            "حمايه الجدد",
            "حماية الجدد"
        ):

            set_group_setting(
                chat_id,
                "new_member_protection",
                command == "قفل"
            )

            bot.reply_to(
                message,
                (
                    "🔒 تم تفعيل حماية الجدد."
                    if command == "قفل"
                    else
                    "🔓 تم تعطيل حماية الجدد."
                )
            )

            return True

        if a in lm:

            set_group_setting(
                chat_id,
                lm[a],
                command == "قفل"
            )

            bot.reply_to(
                message,
                (
                    "🔒 تم قفل "
                    if command == "قفل"
                    else
                    "🔓 تم فتح "
                )
                + argument
                + "."
            )

            return True

    # منع كلمة
    if command == "منع":

        a = argument.strip()

        if clean_text(a).startswith(
            "كلمه "
        ):

            a = a.split(
                maxsplit=1
            )[1]

        if not a:

            bot.reply_to(
                message,
                "❌ اكتب الكلمة."
            )

            return True

        cursor.execute(
            """
            INSERT OR IGNORE INTO blacklist(
                chat_id,
                word
            )
            VALUES(?,?)
            """,
            (
                chat_id,
                a.lower()
            )
        )

        db.commit()

        bot.reply_to(
            message,
            "🚫 تمت إضافة "
            f"<code>{html.escape(a)}</code>"
        )

        return True

    # قائمة الكلمات
    if (
        command == "قائمة"
        and clean_text(argument) == "الكلمات"
    ):

        cursor.execute(
            """
            SELECT word
            FROM blacklist
            WHERE chat_id=?
            """,
            (chat_id,)
        )

        words = [
            r["word"]
            for r in cursor.fetchall()
        ]

        bot.reply_to(
            message,
            "📋 <b>الكلمات الممنوعة</b>\n"
            "┈┅⊷━⊷┅┅┈\n"
            + (
                "\n".join(
                    "🚫 " + html.escape(w)
                    for w in words
                )
                if words
                else
                "لا توجد كلمات ممنوعة."
            )
        )

        return True

    # الاحصائيات
    if command == "احصائيات":

        cursor.execute(
            """
            SELECT
                COUNT(*) users,
                COALESCE(
                    SUM(messages),
                    0
                ) messages
            FROM group_users
            WHERE chat_id=?
            """,
            (chat_id,)
        )

        s = cursor.fetchone()

        cursor.execute(
            """
            SELECT COUNT(*) n
            FROM blacklist
            WHERE chat_id=?
            """,
            (chat_id,)
        )

        w = cursor.fetchone()["n"]

        cursor.execute(
            """
            SELECT COUNT(*) n
            FROM actions
            WHERE chat_id=?
            """,
            (chat_id,)
        )

        a = cursor.fetchone()["n"]

        bot.reply_to(
            message,
            "📊 <b>إحصائيات المجموعة</b>\n"
            "┈┅⊷━⊷┅┅┈\n"
            f"👥 <code>{s['users']}</code>\n"
            f"💬 <code>{s['messages']}</code>\n"
            f"🚫 <code>{w}</code>\n"
            f"📝 <code>{a}</code>"
        )

        return True

    # السجل
    if command == "السجل":

        cursor.execute(
            """
            SELECT *
            FROM actions
            WHERE chat_id=?
            ORDER BY id DESC
            LIMIT 20
            """,
            (chat_id,)
        )

        rows = cursor.fetchall()

        if not rows:

            bot.reply_to(
                message,
                "📝 لا يوجد سجل."
            )

            return True

        lines = [
            "📝 <b>آخر إجراءات الإدارة</b>",
            "┈┅⊷━⊷┅┅┈"
        ]

        for r in rows:

            lines.append(
                f"• <b>"
                f"{html.escape(r['action'] or '')}"
                f"</b> — "
                f"<code>{r['admin_id']}</code>"
            )

        bot.reply_to(
            message,
            "\n".join(lines)
        )

        return True

    # الإعدادات
    if command == "الاعدادات":

        send_settings(
            message
        )

        return True

    return False


# =========================================================
# Callbacks
# =========================================================
@bot.callback_query_handler(
    func=lambda call: True
)
def callbacks(call):

    try:

        if not call.message:
            return

        chat_id = call.message.chat.id
        uid = call.from_user.id

        # لوحة الأدمن الخاصة بالمطور
        if call.data == "admin:open":
            if uid != DEVELOPER_ID or chat_id != DEVELOPER_ID:
                bot.answer_callback_query(
                    call.id,
                    "❌ لوحة الأدمن للمطور فقط.",
                    show_alert=True
                )
                return

            bot.answer_callback_query(call.id)
            send_admin_panel(chat_id, call.message.message_id)
            return

        if call.data.startswith("admin:"):
            if uid != DEVELOPER_ID or chat_id != DEVELOPER_ID:
                bot.answer_callback_query(
                    call.id,
                    "❌ لوحة الأدمن للمطور فقط.",
                    show_alert=True
                )
                return

            action = call.data.split(":", 1)[1]

            if action in ("refresh", "open"):
                bot.answer_callback_query(call.id)
                send_admin_panel(chat_id, call.message.message_id)
                return

            if action == "stats":
                send_admin_section(call, admin_stats_text())
                return

            if action == "groups":
                send_admin_section(call, admin_groups_text())
                return

            if action == "replies":
                send_admin_section(call, admin_replies_text())
                return

            if action == "actions":
                send_admin_section(call, admin_actions_text())
                return

            if action == "close":
                bot.answer_callback_query(call.id, "تم إغلاق لوحة الأدمن")
                try:
                    bot.delete_message(chat_id, call.message.message_id)
                except Exception:
                    try:
                        bot.edit_message_text(
                            "✅ تم إغلاق لوحة الأدمن.",
                            chat_id,
                            call.message.message_id
                        )
                    except Exception:
                        pass
                return

        # اختيار إضافة زر للرد
        if call.data.startswith("replybtn_yes:"):

            token = call.data.split(":", 1)[1]
            p = reply_pending.get(token)

            if not p or p.get("initiator") != uid:
                bot.answer_callback_query(
                    call.id,
                    "❌ هذه العملية ليست لك أو انتهت.",
                    show_alert=True
                )
                return

            continue_reply_button_setup(call, token)
            return

        if call.data.startswith("replybtn_no:"):

            token = call.data.split(":", 1)[1]
            finalize_reply_without_button(call, token)
            return

        # قائمة الأوامر
        if call.data == "show_commands":

            bot.answer_callback_query(
                call.id
            )

            owner = get_owner_user(
                chat_id
            )

            mk = types.InlineKeyboardMarkup()

            if owner:

                mk.add(
                    button(
                        full_name(owner)[:30],
                        url=f"tg://user?id={owner.id}",
                        style="primary",
                        icon_custom_emoji_id=CE_OWNER_DEVELOPER
                    )
                )

            bot.send_message(
                chat_id,
                commands_text(owner),
                reply_markup=mk
            )

            return

        # الإعدادات
        if call.data == "settings":

            if not can_use_moderation(
                get_rank(
                    chat_id,
                    uid
                )
            ):

                bot.answer_callback_query(
                    call.id,
                    "❌ الأدمن فما فوق فقط.",
                    show_alert=True
                )

                return

            bot.answer_callback_query(
                call.id
            )

            send_settings(
                call.message
            )

            return

        # لوحة المشرف
        if call.data.startswith("mp:"):

            _, token, key = call.data.split(
                ":",
                2
            )

            p = pending_promotions.get(
                token
            )

            if (
                not p
                or p["chat_id"] != chat_id
                or p["initiator"] != uid
            ):

                bot.answer_callback_query(
                    call.id,
                    "❌ هذه اللوحة ليست لك أو انتهت.",
                    show_alert=True
                )

                return

            if key in p["permissions"]:

                p["permissions"].remove(
                    key
                )

            else:

                p["permissions"].add(
                    key
                )

            bot.answer_callback_query(
                call.id,
                "تم التعديل"
            )

            moderator_panel(
                call,
                token
            )

            return

        # تأكيد رفع المشرف
        if call.data.startswith(
            "mconfirm:"
        ):

            token = call.data.split(
                ":",
                1
            )[1]

            p = pending_promotions.get(
                token
            )

            if (
                not p
                or p["chat_id"] != chat_id
                or p["initiator"] != uid
            ):

                bot.answer_callback_query(
                    call.id,
                    "❌ انتهت العملية.",
                    show_alert=True
                )

                return

            target = p["target"]

            if not can_manage_rank(
                get_rank(chat_id, uid),
                get_rank(chat_id, target.id),
                "رفع"
            ):

                bot.answer_callback_query(
                    call.id,
                    "❌ لم تعد تملك صلاحية الرفع.",
                    show_alert=True
                )

                return

            perms = {
                MOD_PERMS[k][1]
                for k in p["permissions"]
            }

            if not bot_promote(
                chat_id,
                target.id,
                "moderator",
                perms
            ):

                bot.answer_callback_query(
                    call.id,
                    "❌ فشل الرفع. "
                    "تأكد من صلاحيات البوت.",
                    show_alert=True
                )

                return

            set_rank(
                chat_id,
                target.id,
                "moderator"
            )

            remove_rank_permissions(
                chat_id,
                target.id
            )

            for perm in p["permissions"]:

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO rank_permissions(
                        chat_id,
                        user_id,
                        permission
                    )
                    VALUES(?,?,?)
                    """,
                    (
                        chat_id,
                        target.id,
                        perm
                    )
                )

            db.commit()

            log_action(
                chat_id,
                uid,
                target.id,
                "رفع مشرف",
                ",".join(
                    p["permissions"]
                )
            )

            pending_promotions.pop(
                token,
                None
            )

            bot.answer_callback_query(
                call.id,
                "✅ تم رفع المشرف"
            )

            bot.edit_message_text(
                f"✅ تم رفع {mention(target)} "
                "إلى <b>المشرف</b>.",
                chat_id,
                call.message.message_id
            )

            return

        # إلغاء
        if call.data.startswith(
            "mcancel:"
        ):

            token = call.data.split(
                ":",
                1
            )[1]

            p = pending_promotions.get(
                token
            )

            if (
                p
                and p["initiator"] == uid
            ):

                pending_promotions.pop(
                    token,
                    None
                )

            bot.answer_callback_query(
                call.id,
                "تم الإلغاء"
            )

            try:

                bot.edit_message_text(
                    "❌ تم إلغاء رفع المشرف.",
                    chat_id,
                    call.message.message_id
                )

            except Exception:
                pass

            return

        # صلاحيات الإدارة
        if not can_use_moderation(
            get_rank(
                chat_id,
                uid
            )
        ):

            bot.answer_callback_query(
                call.id,
                "❌ هذا للأدمن فما فوق.",
                show_alert=True
            )

            return

        # قفل الكل / فتح الكل
        if call.data in (
            "lock_all",
            "unlock_all"
        ):

            all_locks(
                chat_id,
                call.data == "lock_all"
            )

            bot.answer_callback_query(
                call.id,
                "تم"
            )

            try:

                bot.delete_message(
                    chat_id,
                    call.message.message_id
                )

            except Exception:
                pass

            send_settings(
                call.message
            )

            return

        # تبديل الإعداد
        if call.data.startswith(
            "toggle_"
        ):

            setting = call.data[7:]

            valid = {
                "welcome",
                "links",
                "photos",
                "videos",
                "documents",
                "stickers",
                "audio",
                "animations",
                "repeat_messages",
                "new_member_protection"
            }

            if setting not in valid:
                return

            cur = group_setting(
                chat_id,
                setting
            )

            set_group_setting(
                chat_id,
                setting,
                not cur
            )

            bot.answer_callback_query(
                call.id,
                "✅ تم التعديل"
            )

            try:

                bot.delete_message(
                    chat_id,
                    call.message.message_id
                )

            except Exception:
                pass

            send_settings(
                call.message
            )

    except Exception as e:

        print(
            "[Callback Error]",
            e
        )


# =========================================================
# محرك الحماية
# =========================================================
def protection_engine(message):

    if (
        not message.from_user
        or message.from_user.is_bot
    ):
        return

    chat_id = message.chat.id
    uid = message.from_user.id

    if can_use_moderation(
        get_rank(
            chat_id,
            uid
        )
    ):
        return

    row = get_group(
        chat_id
    )

    if not row:
        return

    text = (
        message.text
        or message.caption
        or ""
    )

    # الكلمات والروابط
    if (
        is_blacklisted(
            chat_id,
            text
        )
        or (
            row["links"]
            and contains_link(text)
        )
    ):

        delete_message_safe(
            message
        )

        return

    # Flood
    if (
        row["flood"]
        and check_flood(
            chat_id,
            uid
        )
    ):

        try:

            mute_user(
                chat_id,
                uid
            )

        except Exception:
            pass

        return

    # التكرار
    if (
        row["repeat_messages"]
        and text
        and check_repeat(
            chat_id,
            uid,
            text
        )
    ):

        delete_message_safe(
            message
        )

        return

    ct = message.content_type

    if (
        (
            row["photos"]
            and ct == "photo"
        )

        or (
            row["videos"]
            and ct == "video"
        )

        or (
            row["documents"]
            and ct == "document"
        )

        or (
            row["stickers"]
            and ct == "sticker"
        )

        or (
            row["audio"]
            and ct in (
                "audio",
                "voice",
                "video_note"
            )
        )

        or (
            row["animations"]
            and ct == "animation"
        )
    ):

        delete_message_safe(
            message
        )


# =========================================================
# التشغيل
# =========================================================
def run_bot_forever():

    print(
        "==================================="
    )

    print(
        " Protection Bot Started"
    )

    print(
        " Bot: @" + BOT_USERNAME
    )

    print(
        " Database:",
        DB_NAME
    )

    print(
        " Rank System: ON"
    )

    print(
        " Custom Emoji: ON"
    )

    print(
        " Auto-Reconnect: ON"
    )

    print(
        "==================================="
    )

    # حذف الـWebhook تلقائيًا قبل بدء Long Polling
    # حتى لا يحدث تعارض 409 بين getUpdates وWebhook.
    try:
        bot.remove_webhook()
        print("[Webhook] Removed successfully")
    except Exception as e:
        print("[Webhook Cleanup Error]", e)

    time.sleep(1)

    while True:

        try:

            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30
            )

            time.sleep(5)

        except KeyboardInterrupt:

            print(
                "Bot stopped."
            )

            break

        except Exception as e:

            print(
                "[Polling Error]",
                e
            )

            try:
                bot.stop_polling()
            except Exception:
                pass

            # التأكد من حذف الـWebhook أيضًا بعد أي خطأ في Polling.
            try:
                bot.remove_webhook()
            except Exception:
                pass

            time.sleep(5)


run_bot_forever()
