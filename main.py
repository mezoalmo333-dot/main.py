# -*- coding: utf-8 -*-
import telebot
from telebot import types
import sqlite3
import time
import re
import html
import secrets
import json
import io
import os
import logging
import traceback
import urllib.request
from collections import defaultdict, deque
from threading import Thread, Lock

# =========================================================
# الإعدادات
# =========================================================
BOT_TOKEN = "8878742478:AAF-h5bIAg_OwXQQXc89ipw37Z4yRKKvxV4"

DEVELOPER_ID = 8037399518
BOT_USERNAME = "v_u_kbot"
DB_NAME = "protection_bot.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
telebot.logger.setLevel(logging.INFO)

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
CE_BOT_REPLY = "5201842613983917014"
CE_TON_PRICE = "5260450573768990626"
CE_TON_ANALYSIS = "5357069174512303778"
CE_FORCE_SUB = "5271801931814165886"

# الإيموجيات المميزة المطلوبة للترحيب والأزرار
CE_WELCOME_HELLO = "5258501105293205250"
CE_WELCOME_INFO = "5258503720928288433"
CE_ADD_TO_GROUP_REQUESTED = "5274008024585871702"
CE_ADMIN_USERNAME = "5260399854500191689"
UPDATE_MAX_URL = "https://t.me/LeaDeR_E"

def tg_emoji(emoji_id, alt="🔹"):
    return f'<tg-emoji emoji-id="{emoji_id}">{alt}</tg-emoji>'

# =========================================================
# تنسيق الرسائل
# =========================================================
def strip_non_custom_emoji(text):
    """إزالة Emoji العادي من رسائل البوت مع الحفاظ على Premium Emoji."""
    if not text or not isinstance(text, str):
        return text

    protected = []

    def protect(match):
        protected.append(match.group(0))
        return f"__CUSTOM_EMOJI_{len(protected) - 1}__"

    text = re.sub(
        r'<tg-emoji\b[^>]*>.*?</tg-emoji>',
        protect,
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    emoji_pattern = re.compile(
        r'[\U0001F000-\U0001FAFF\u2600-\u27BF\u2300-\u23FF]'
        r'[\uFE0E\uFE0F]?'
        r'(?:[\u200D][\U0001F000-\U0001FAFF\u2600-\u27BF])*'
        r'(?:[\U0001F3FB-\U0001F3FF])?'
    )
    text = emoji_pattern.sub('', text)

    for index, value in enumerate(protected):
        text = text.replace(f"__CUSTOM_EMOJI_{index}__", value)

    return text


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

    return strip_non_custom_emoji(out)


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

# المستخدمون الذين فتحوا البوت في الخاص، لاستخدام الإذاعة والإشعارات.
cursor.execute("""
CREATE TABLE IF NOT EXISTS bot_private_users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    first_seen INTEGER DEFAULT 0,
    last_seen INTEGER DEFAULT 0
)
""")
db.commit()

# البوتات التي يعرفها البوت داخل المجموعات. Telegram لا يوفر API لسرد كل أعضاء المجموعة.
cursor.execute("""
CREATE TABLE IF NOT EXISTS known_bots (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    first_name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    discovered_at INTEGER DEFAULT 0,
    PRIMARY KEY(chat_id,user_id)
)
""")
db.commit()

# منع تكرار إشعار المطور عند أول استخدام للخاص.
cursor.execute("""
CREATE TABLE IF NOT EXISTS developer_notifications (
    user_id INTEGER PRIMARY KEY,
    notified_at INTEGER DEFAULT 0
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

# حفظ تنسيق الرد الأصلي (عريض / اقتباس / Premium Emoji / روابط وغيرها)
try:
    cursor.execute(
        "ALTER TABLE auto_replies ADD COLUMN reply_entities TEXT DEFAULT ''"
    )
    db.commit()
except sqlite3.OperationalError:
    pass

# حفظ أكثر من زر شفاف لكل رد بصيغة JSON، مع الحفاظ على الأزرار القديمة.
try:
    cursor.execute(
        "ALTER TABLE auto_replies ADD COLUMN button_data TEXT DEFAULT ''"
    )
    db.commit()
except sqlite3.OperationalError:
    pass

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
CREATE TABLE IF NOT EXISTS global_bans (
    user_id INTEGER PRIMARY KEY,
    created_at INTEGER DEFAULT 0,
    admin_id INTEGER DEFAULT 0
)
""")
db.commit()


# قنوات الاشتراك الإجباري للمجموعات
cursor.execute("""
CREATE TABLE IF NOT EXISTS force_sub_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    username TEXT DEFAULT '',
    title TEXT DEFAULT '',
    url TEXT DEFAULT '',
    button_text TEXT DEFAULT 'Update MaX',
    emoji_id TEXT DEFAULT '5271801931814165886',
    enabled INTEGER DEFAULT 1,
    UNIQUE(chat_id)
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

    if not parts:
        return "", ""

    command = clean_text(parts[0])
    argument = parts[1].strip() if len(parts) > 1 else ""

    # أوامر متعددة الكلمات للردود
    if command in ("اضف", "اضيف") and argument:
        second = argument.split(maxsplit=1)[0]
        if clean_text(second) == "رد":
            command = "اضف_رد"
            argument = argument[len(second):].strip()
    elif command == "حذف" and argument:
        second = argument.split(maxsplit=1)[0]
        if clean_text(second) == "رد":
            command = "حذف_رد"
            argument = argument[len(second):].strip()
    elif command == "قائمة" and argument:
        second = argument.split(maxsplit=1)[0]
        if clean_text(second) == "الردود":
            command = "قائمة_الردود"
            argument = argument[len(second):].strip()

    # أوامر من كلمتين يجب أن تصل للراوتر كأمر واحد،
    # خصوصًا "فك كتم" حتى لا يتم تفسيرها بالخطأ كـ "فك حظر".
    if command == "طرد" and argument:
        second = argument.split(maxsplit=1)[0]
        if clean_text(second) in ("البوتات", "بوتات"):
            command = "طرد_البوتات"
            argument = argument[len(second):].strip()

    if command == "تحليل" and argument:
        second = argument.split(maxsplit=1)[0]
        second_clean = clean_text(second)

        if second_clean == "تون":
            command = "تحليل_تون"
            argument = argument[len(second):].strip()
        elif second_clean in ("دولار", "الدولار", "usd", "usdt"):
            command = "تحليل_دولار"
            argument = argument[len(second):].strip()

    if command == "فك" and argument:
        second = argument.split(maxsplit=1)[0]
        second_clean = clean_text(second)

        if second_clean == "كتم":
            command = "فككتم"
            argument = argument[len(second):].strip()

        elif second_clean == "حظر":
            command = "فكحظر"
            argument = argument[len(second):].strip()

    elif command == "حظر" and argument:
        second = argument.split(maxsplit=1)[0]
        second_clean = clean_text(second)

        if second_clean == "عام":
            command = "حظرعام"
            argument = argument[len(second):].strip()

    return command, argument


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
    style="danger",
    icon_custom_emoji_id=None
):
    # جميع أزرار البوت بلون واحد: danger.
    # أي Emoji عادي في اسم الزر يتم حذفه؛ الأيقونة المميزة تُرسل عبر icon_custom_emoji_id.
    text = strip_non_custom_emoji(str(text or "")).strip()
    kwargs = {
        "text": text,
        "style": "danger"
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

# بيانات تحليل TON لمدة 24 ساعة
TON_MARKET_CACHE_SECONDS = 60
_ton_market_cache = {
    "price_usd": None,
    "change_24h": None,
    "high_24h": None,
    "low_24h": None,
    "updated_at": 0
}
_ton_market_cache_lock = Lock()


def transparent_url_button(text, url, emoji_id=None):
    """
    زر رابط للردود. يُحافظ على اسم الوظيفة القديم للتوافق،
    لكن مظهر الأزرار الآن موحد بلون danger كما طلب المطور.
    """
    text = strip_non_custom_emoji(str(text or "")).strip()
    kwargs = {
        "text": text,
        "url": url,
        "style": "danger"
    }

    if emoji_id:
        kwargs["icon_custom_emoji_id"] = str(emoji_id)

    try:
        return types.InlineKeyboardButton(**kwargs)
    except TypeError:
        kwargs.pop("icon_custom_emoji_id", None)
        try:
            return types.InlineKeyboardButton(**kwargs)
        except TypeError:
            kwargs.pop("style", None)
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


def get_ton_market_data():
    """
    يجلب سعر TON الحالي بالدولار مع نسبة التغير خلال آخر 24 ساعة،
    وأعلى/أقل سعر خلال 24 ساعة.
    """
    current_time = time.time()

    with _ton_market_cache_lock:
        if (
            _ton_market_cache["price_usd"] is not None
            and _ton_market_cache["change_24h"] is not None
            and current_time - _ton_market_cache["updated_at"]
            < TON_MARKET_CACHE_SECONDS
        ):
            return (
                _ton_market_cache["price_usd"],
                _ton_market_cache["change_24h"],
                _ton_market_cache["high_24h"],
                _ton_market_cache["low_24h"]
            )

    try:
        data = _http_json(
            "https://api.coingecko.com/api/v3/coins/the-open-network"
            "?localization=false&tickers=false&market_data=true"
            "&community_data=false&developer_data=false&sparkline=false"
        )

        market = data.get("market_data", {})
        current = market.get("current_price", {})
        price_usd = float(current.get("usd"))
        change_24h = float(
            market.get("price_change_percentage_24h") or 0
        )
        high_24h = market.get("high_24h", {}).get("usd")
        low_24h = market.get("low_24h", {}).get("usd")

        if high_24h is not None:
            high_24h = float(high_24h)
        if low_24h is not None:
            low_24h = float(low_24h)

        if price_usd <= 0:
            raise ValueError("Invalid TON price")

        with _ton_market_cache_lock:
            _ton_market_cache["price_usd"] = price_usd
            _ton_market_cache["change_24h"] = change_24h
            _ton_market_cache["high_24h"] = high_24h
            _ton_market_cache["low_24h"] = low_24h
            _ton_market_cache["updated_at"] = current_time

        return price_usd, change_24h, high_24h, low_24h

    except Exception as e:
        print("[TON Market Error]", e)

    with _ton_market_cache_lock:
        if _ton_market_cache["price_usd"] is not None:
            return (
                _ton_market_cache["price_usd"],
                _ton_market_cache["change_24h"] or 0,
                _ton_market_cache["high_24h"],
                _ton_market_cache["low_24h"]
            )

    return None, None, None, None


def extract_ton_amount(text):
    """
    يلتقط مبلغ TON بالشكل:
    1TON / 1 TON / TON 1 / 1تون / 1 طن
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
        rf"{number_pattern}\s*(?:TON|تون|طن)",
        rf"(?:TON|تون|طن)\s*{number_pattern}"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE
        )

        if not match:
            continue

        amount = normalize_money_number(
            match.group(1)
        )

        if amount is not None:
            return amount

    return None


def send_ton_conversion(message, ton_amount):
    """عرض سعر TON فقط عند كتابة كمية TON."""
    usd_egp, _ = get_currency_rates()
    ton_usd, _, _, _ = get_ton_market_data()

    if (
        usd_egp is None
        or ton_usd is None
        or usd_egp <= 0
        or ton_usd <= 0
    ):
        print("[TON Conversion] Could not get live rates.")
        return False

    usd_amount = ton_amount * ton_usd
    egp_amount = usd_amount * usd_egp
    price_emoji = tg_emoji(CE_TON_PRICE, "💎")

    text = (
        "<b>ToN</b>\n"
        f"{price_emoji} <b>{format_money(egp_amount, 2)} EGP</b>\n"
        f"{price_emoji} <b>{format_money(usd_amount, 4)} USD</b>"
    )

    markup = types.InlineKeyboardMarkup()
    updates_button = button(
        "MaX",
        url=LOVELY_UPDATES_URL,
        style="danger"
    )
    if updates_button is not None:
        markup.add(updates_button)

    try:
        bot.reply_to(message, text, reply_markup=markup)
        return True
    except Exception as e:
        print("[TON Conversion Send Error]", e)
        return False


def send_ton_analysis(message):
    """تحليل TON: السعر الحالي واتجاه آخر 24 ساعة."""
    usd_egp, _ = get_currency_rates()
    ton_usd, change_24h, high_24h, low_24h = get_ton_market_data()

    if (
        usd_egp is None
        or ton_usd is None
        or usd_egp <= 0
        or ton_usd <= 0
    ):
        bot.reply_to(
            message,
            "❌ تعذر جلب سعر TON حاليًا، حاول مرة أخرى بعد قليل."
        )
        return True

    change_24h = change_24h or 0.0
    if change_24h > 0:
        trend = "<b>صعود</b>"
        trend_value = f"+{change_24h:.2f}%"
    elif change_24h < 0:
        trend = "<b>هبوط</b>"
        trend_value = f"{change_24h:.2f}%"
    else:
        trend = "<b>مستقر</b>"
        trend_value = "0.00%"

    price_emoji = tg_emoji(CE_TON_PRICE, "💎")
    analysis_emoji = tg_emoji(CE_TON_ANALYSIS, "🔹")
    text = (
        f"{analysis_emoji} <b>تحليل ToN</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"{price_emoji} <b>{format_money(ton_usd * usd_egp, 2)} EGP</b>\n"
        f"{price_emoji} <b>{format_money(ton_usd, 4)} USD</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"{trend} آخر 24 ساعة: <b>{trend_value}</b>"
    )

    if high_24h is not None and low_24h is not None:
        text += (
            "\n"
            f"أعلى سعر: <b>{format_money(high_24h, 4)} USD</b>\n"
            f"أقل سعر: <b>{format_money(low_24h, 4)} USD</b>"
        )

    markup = types.InlineKeyboardMarkup()
    updates_button = button(
        "MaX",
        url=LOVELY_UPDATES_URL,
        style="danger"
    )
    if updates_button is not None:
        markup.add(updates_button)

    bot.reply_to(message, text, reply_markup=markup)
    return True

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
    price_emoji = tg_emoji(CE_TON_PRICE, "💎")

    text = (
        "<b>DoLLar</b>\n"
        f"{price_emoji} <b>{format_money(egp_amount, 2)} EGP</b>\n"
        f"{price_emoji} <b>{format_money(usd_amount, 4)} USD</b>"
    )

    markup = types.InlineKeyboardMarkup()
    updates_button = button(
        "MaX",
        url=LOVELY_UPDATES_URL,
        style="danger"
    )
    if updates_button is not None:
        markup.add(updates_button)

    try:
        bot.reply_to(message, text, reply_markup=markup)
        return True
    except Exception as e:
        print("[Currency Send Error]", e)
        return False


def send_dollar_analysis(message):
    """تحليل الدولار بصيغة موحدة مع تحليل TON."""
    usd_egp, ton_usd = get_currency_rates()
    if usd_egp is None or ton_usd is None or usd_egp <= 0 or ton_usd <= 0:
        bot.reply_to(message, "تعذر جلب سعر الدولار حاليًا، حاول مرة أخرى بعد قليل.")
        return True

    price_emoji = tg_emoji(CE_TON_PRICE, "💎")
    analysis_emoji = tg_emoji(CE_TON_ANALYSIS, "🔹")
    text = (
        f"{analysis_emoji} <b>تحليل DoLLar</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"{price_emoji} <b>{format_money(usd_egp, 2)} EGP</b>\n"
        f"{price_emoji} <b>1.0000 USD</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"{price_emoji} <b>1 USD = {format_money(usd_egp, 2)} EGP</b>"
    )
    markup = types.InlineKeyboardMarkup()
    b = button("MaX", url=LOVELY_UPDATES_URL, style="danger")
    if b is not None:
        markup.add(b)
    try:
        bot.reply_to(message, text, reply_markup=markup)
        return True
    except Exception as e:
        print("[Dollar Analysis Send Error]", e)
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

    ton_amount = extract_ton_amount(text)

    if ton_amount is not None:
        return send_ton_conversion(
            message,
            ton_amount
        )

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

    # إذا تم تحديد هدف صريح بعد الأمر (@username أو ID) نستخدمه أولًا.
    # هذا يسمح مثلًا بكتابة: "طرد 123456" حتى لو كانت الرسالة ردًا على شخص آخر.
    argument = (argument or "").strip()

    if argument:
        target_token = argument.split(maxsplit=1)[0].strip()

        if re.fullmatch(r"-?\d+", target_token):

            m = get_member(
                message.chat.id,
                int(target_token)
            )

            return m.user if m else None

        username = target_token.lstrip("@").lower()

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

    # بدون هدف صريح: استخدم المستخدم الذي تم الرد عليه.
    if (
        message.reply_to_message
        and message.reply_to_message.from_user
    ):
        return message.reply_to_message.from_user

    return None

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


def is_global_banned(user_id):
    cursor.execute(
        "SELECT 1 FROM global_bans WHERE user_id=? LIMIT 1",
        (user_id,)
    )
    return cursor.fetchone() is not None


def global_ban_user(user_id, admin_id=0):
    cursor.execute(
        "INSERT OR REPLACE INTO global_bans(user_id,created_at,admin_id) VALUES(?,?,?)",
        (user_id, now(), admin_id)
    )
    db.commit()

    cursor.execute("SELECT chat_id FROM groups")
    chat_ids = [row["chat_id"] for row in cursor.fetchall()]

    success = 0
    skipped = 0

    for group_chat_id in chat_ids:
        try:
            if not bot_is_admin(group_chat_id):
                skipped += 1
                continue

            bot.ban_chat_member(
                group_chat_id,
                user_id
            )
            success += 1
        except Exception as e:
            skipped += 1
            print(f"[Global Ban] {group_chat_id}: {e}")

    return success, skipped


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
# قائمة الأوامر التفاعلية
# =========================================================
def commands_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    rows = [
        ("🔒 أوامر القفل", "locks", "🔓 أوامر الفتح", "unlocks"),
        ("👥 أوامر المجموعات", "groups", "👮 أوامر الإدارة", "admin"),
        ("🛡️ أوامر الحماية", "protection", "👑 أوامر الرتب", "ranks"),
        ("💬 أوامر الردود", "replies", "💎 أوامر TON", "ton"),
    ]
    for a, ac, b, bc in rows:
        markup.row(
            button(a, callback_data=f"cmdcat:{ac}", style="primary", icon_custom_emoji_id=CE_COMMANDS),
            button(b, callback_data=f"cmdcat:{bc}", style="primary", icon_custom_emoji_id=CE_COMMANDS)
        )
    markup.row(button("📋 كل الأوامر", callback_data="cmdcat:all", style="primary", icon_custom_emoji_id=CE_COMMANDS))
    return markup


def command_category_text(category):
    texts = {
        "locks": "🔒 <b>أوامر القفل</b>\n┈┅⊷━⊷┅┅┈\n<code>قفل الروابط</code>\n<code>قفل الصور</code>\n<code>قفل الفيديو</code>\n<code>قفل الملفات</code>\n<code>قفل الملصقات</code>\n<code>قفل الصوت</code>\n<code>قفل المتحركات</code>\n<code>قفل التكرار</code>\n<code>قفل حماية الجدد</code>\n<code>قفل الكل</code>",
        "unlocks": "🔓 <b>أوامر الفتح</b>\n┈┅⊷━⊷┅┅┈\n<code>فتح الروابط</code>\n<code>فتح الصور</code>\n<code>فتح الفيديو</code>\n<code>فتح الملفات</code>\n<code>فتح الملصقات</code>\n<code>فتح الصوت</code>\n<code>فتح المتحركات</code>\n<code>فتح التكرار</code>\n<code>فتح حماية الجدد</code>\n<code>فتح الكل</code>",
        "groups": "👥 <b>أوامر المجموعات</b>\n┈┅⊷━⊷┅┅┈\n<code>معلومات</code>\n<code>احصائيات</code>\n<code>السجل</code>\n<code>الاعدادات</code>\n<code>المالك</code>\n<code>المطور</code>",
        "admin": "👮 <b>أوامر الإدارة</b>\n┈┅⊷━⊷┅┅┈\n<code>حظر</code>\n<code>فك حظر</code>\n<code>حظر عام</code>\n<code>طرد</code>\n<code>كتم</code>\n<code>فك كتم</code>\n<code>تحذير</code>\n<code>تحذيرات</code>\n<code>مسح التحذيرات</code>\n<code>الغاء تحذير</code>",
        "protection": "🛡️ <b>أوامر الحماية</b>\n┈┅⊷━⊷┅┅┈\n<code>منع كلمة ...</code>\n<code>الغاء منع كلمة ...</code>\n<code>قائمة الكلمات</code>\n<code>قفل الروابط</code>\n<code>قفل التكرار</code>\n<code>قفل حماية الجدد</code>",
        "ranks": "👑 <b>أوامر الرتب</b>\n┈┅⊷━⊷┅┅┈\n<code>رفع مساعد المالك</code>\n<code>تنزيل مساعد المالك</code>\n<code>رفع مدير</code>\n<code>تنزيل مدير</code>\n<code>رفع ادمن</code>\n<code>تنزيل ادمن</code>\n<code>رفع مشرف</code>\n<code>تنزيل مشرف</code>\n<code>رفع حيوان</code>\n<code>تنزيل حيوان</code>",
        "replies": "💬 <b>أوامر الردود</b>\n┈┅⊷━⊷┅┅┈\n<code>اضف رد</code>\nاتبع الخطوات لإضافة الكلمة والرد، ويمكنك إضافة أكثر من زر شفاف لنفس الرد.\n\n<code>حذف رد</code>\n<code>قائمة الردود</code>",
        "ton": "💎 <b>أوامر TON</b>\n┈┅⊷━⊷┅┅┈\n<code>1ton</code> أو <code>1تون</code> — سعر TON\n<code>تحليل تون</code> — تحليل آخر 24 ساعة\n<code>تحليل دولار</code> — سعر الدولار مقابل الجنيه",
    }
    return texts.get(category, "📚 <b>قائمة أوامر البوت</b>")


def commands_back_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(button("↩️ رجوع للأوامر", callback_data="cmdcat:home", style="primary", icon_custom_emoji_id=CE_COMMANDS))
    return markup


def send_commands_menu(message):
    text = "📚 <b>قائمة أوامر البوت</b>\n┈┅⊷━⊷┅┅┈\nاختر القسم الذي تريد أوامره:"
    bot.reply_to(message, text, reply_markup=commands_menu_markup())


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
admin_pending = {}
broadcast_pending = {}


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
    row = cursor.fetchone()
    if row:
        return row

    # الرد العام يُطبق على كل المجموعات ما لم يوجد رد خاص بالمجموعة.
    cursor.execute(
        """
        SELECT *
        FROM auto_replies
        WHERE chat_id=0 AND trigger=?
        LIMIT 1
        """,
        (key,)
    )
    return cursor.fetchone()


def save_auto_reply(
    chat_id,
    trigger,
    reply_text,
    button_enabled=False,
    button_text="",
    button_url="",
    button_emoji_id="",
    reply_entities="",
    button_data=None
):
    """حفظ الرد مع دعم أكثر من زر شفاف، مع إبقاء الحقول القديمة للتوافق."""
    if button_data is None:
        button_data = []
        if button_enabled and button_url:
            button_data.append({
                "text": button_text or "MaX",
                "url": button_url,
                "emoji_id": button_emoji_id or ""
            })

    try:
        button_data_json = json.dumps(button_data, ensure_ascii=False)
    except Exception:
        button_data_json = "[]"

    first = button_data[0] if button_data else {}
    first_text = first.get("text", button_text or "")
    first_url = first.get("url", button_url or "")
    first_emoji = first.get("emoji_id", button_emoji_id or "")

    cursor.execute(
        """
        INSERT INTO auto_replies(
            chat_id,
            trigger,
            reply_text,
            button_enabled,
            button_text,
            button_url,
            button_emoji_id,
            reply_entities,
            button_data
        )
        VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(chat_id,trigger)
        DO UPDATE SET
            reply_text=excluded.reply_text,
            button_enabled=excluded.button_enabled,
            button_text=excluded.button_text,
            button_url=excluded.button_url,
            button_emoji_id=excluded.button_emoji_id,
            reply_entities=excluded.reply_entities,
            button_data=excluded.button_data
        """,
        (
            chat_id,
            clean_text(trigger),
            reply_text,
            1 if button_data else 0,
            first_text,
            first_url,
            first_emoji,
            reply_entities or "",
            button_data_json
        )
    )
    db.commit()


def get_reply_buttons(row):
    """إرجاع كل الأزرار المحفوظة، مع دعم الردود القديمة ذات الزر الواحد."""
    if not row:
        return []

    raw = row["button_data"] if "button_data" in row.keys() else ""
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                result = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    text = str(item.get("text", "")).strip()
                    if text == "Lovely Updates":
                        text = "MaX"
                    url = str(item.get("url", "")).strip()
                    if text and url:
                        result.append({
                            "text": text,
                            "url": url,
                            "emoji_id": str(item.get("emoji_id", "") or "")
                        })
                if result:
                    return result
        except Exception:
            pass

    if row["button_enabled"] and row["button_url"]:
        return [{
            "text": ("MaX" if row["button_text"] == "Lovely Updates" else (row["button_text"] or "MaX")),
            "url": row["button_url"],
            "emoji_id": row["button_emoji_id"] or ""
        }]

    return []


def serialize_message_entities(message):
    """حفظ تنسيق رسالة الرد كما أرسلها المستخدم."""
    entities = getattr(message, "entities", None)
    if not entities:
        entities = getattr(message, "caption_entities", None)
    if not entities:
        return ""

    payload = []
    fields = (
        "type", "offset", "length", "url", "language",
        "custom_emoji_id", "expandable"
    )

    for entity in entities:
        item = {}
        for field in fields:
            value = getattr(entity, field, None)
            if value is not None:
                item[field] = value
        if item.get("type"):
            payload.append(item)

    try:
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return ""


def deserialize_message_entities(raw):
    """إعادة MessageEntity objects لإرسال الرد بنفس التنسيق."""
    if not raw:
        return None
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(data, list):
            return None
        entities = []
        for item in data:
            if not isinstance(item, dict) or not item.get("type"):
                continue
            try:
                entities.append(types.MessageEntity(**item))
            except Exception:
                basic = {
                    key: item[key]
                    for key in ("type", "offset", "length")
                    if key in item
                }
                for key in ("url", "language", "custom_emoji_id", "expandable"):
                    if key in item:
                        basic[key] = item[key]
                try:
                    entities.append(types.MessageEntity(**basic))
                except Exception:
                    pass
        return entities or None
    except Exception:
        return None


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
    buttons = get_reply_buttons(row)
    if not buttons:
        return None

    markup = types.InlineKeyboardMarkup()
    for item in buttons:
        b = transparent_url_button(
            item["text"],
            item["url"],
            emoji_id=item.get("emoji_id") or None
        )
        if b is not None:
            markup.add(b)

    return markup if markup.keyboard else None


def send_saved_auto_reply(message, row):
    if not row:
        return False

    markup = reply_button_markup(row)
    entities = deserialize_message_entities(
        row["reply_entities"] if "reply_entities" in row.keys() else ""
    )

    try:
        kwargs = {"reply_markup": markup}
        if entities:
            kwargs["entities"] = entities
            kwargs["parse_mode"] = None

        kwargs["reply_to_message_id"] = message.message_id
        _original_send_message(
            message.chat.id,
            row["reply_text"],
            **kwargs
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
    token = secrets.token_hex(8)

    if not trigger:
        reply_pending[token] = {
            "chat_id": message.chat.id,
            "initiator": message.from_user.id,
            "trigger": "",
            "step": "trigger",
            "buttons": []
        }
        bot.reply_to(message, "أرسل الآن الكلمة التي تريد إضافة رد لها.")
        return True

    reply_pending[token] = {
        "chat_id": message.chat.id,
        "initiator": message.from_user.id,
        "trigger": clean_text(trigger),
        "step": "reply",
        "buttons": []
    }

    bot.reply_to(
        message,
        f"تم اختيار الكلمة: <code>{html.escape(trigger)}</code>\n\n"
        "أرسل الآن نص الرد الذي تريد حفظه."
    )
    return True


def ask_more_reply_buttons(chat_id, token):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        button(
            "إضافة زر آخر",
            callback_data=f"replybtn_more_yes:{token}",
            style="primary",
            icon_custom_emoji_id=CE_REPLY_BUTTON
        ),
        button(
            "حفظ الرد",
            callback_data=f"replybtn_more_no:{token}",
            style="primary",
            icon_custom_emoji_id=CE_REPLY_BUTTON
        )
    )
    bot.send_message(
        chat_id,
        "✅ تم إضافة الزر.\n\nهل تريد إضافة زر شفاف آخر؟",
        reply_markup=markup
    )


def _save_pending_reply(token, with_buttons=True):
    p = reply_pending.get(token)
    if not p:
        return False

    buttons = p.get("buttons", []) if with_buttons else []
    first = buttons[0] if buttons else {}
    save_auto_reply(
        p["chat_id"],
        p["trigger"],
        p.get("reply_text", ""),
        bool(buttons),
        first.get("text", ""),
        first.get("url", ""),
        first.get("emoji_id", ""),
        p.get("reply_entities", ""),
        buttons
    )
    reply_pending.pop(token, None)
    return True


def continue_reply_setup(message):
    if not message or not message.from_user:
        return False

    for token, p in list(reply_pending.items()):
        pending_chat_id = p.get("chat_id")
        if (
            pending_chat_id not in (0, message.chat.id)
            or p.get("initiator") != message.from_user.id
        ):
            continue
        if pending_chat_id == 0 and message.from_user.id != DEVELOPER_ID:
            continue

        step = p.get("step")

        if step == "trigger":
            trigger = (message.text or "").strip()
            if not trigger:
                bot.reply_to(message, "أرسل كلمة نصية صالحة للرد.")
                return True
            p["trigger"] = clean_text(trigger)
            p["step"] = "reply"
            bot.reply_to(message, "تم اختيار الكلمة. أرسل الآن نص الرد الذي تريد حفظه.")
            return True

        if step == "reply":
            reply_text = message.text or message.caption or ""
            if not reply_text.strip():
                bot.reply_to(message, "❌ أرسل نص الرد فقط.")
                return True

            p["reply_text"] = reply_text
            p["reply_entities"] = serialize_message_entities(message)
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
                bot.reply_to(message, "❌ أرسل نص الزر. ويمكنك وضع أي إيموجي عادي داخل اسم الزر.")
                return True
            # أسماء الأزرار لا تدعم MessageEntity؛ نزيل Emoji العادي من الاسم
            # ونستخدم custom_emoji_id كأيقونة للزر إن كان موجودًا.
            p["button_text"] = strip_non_custom_emoji(text.strip()).strip() or "زر"
            p["step"] = "button_url"
            bot.reply_to(
                message,
                "🔗 أرسل رابط الزر كاملًا.\n"
                "يدعم روابط Telegram والروابط https/http وأي رابط صالح تقبله Telegram."
            )
            return True

        if step == "button_url":
            url = (message.text or "").strip()
            if not url or not re.match(r"^(?:https?|tg)://\S+$", url, re.I):
                bot.reply_to(message, "❌ أرسل رابطًا صالحًا مثل: <code>https://t.me/LeaDeR_E</code>")
                return True
            p["button_url"] = url
            p["step"] = "button_emoji"
            bot.reply_to(
                message,
                "✨ أرسل Premium Emoji للزر إذا أردت أيقونة مخصصة، أو اكتب <code>تخطي</code>.\n"
                "يدعم روابط Telegram وhttp/https وPremium Emoji تلقائيًا."
            )
            return True

        if step == "button_emoji":
            raw = (message.text or "").strip()
            emoji_id = extract_custom_emoji_id(message)
            if raw and clean_text(raw) in ("تخطي", "تخطي الايموجي", "بدون", "لا"):
                emoji_id = ""
            elif not emoji_id and not raw:
                bot.reply_to(message, "❌ أرسل Premium Emoji أو اكتب تخطي.")
                return True

            p.setdefault("buttons", []).append({
                "text": p.get("button_text", "زر"),
                "url": p.get("button_url", ""),
                "emoji_id": emoji_id or ""
            })
            p.pop("button_text", None)
            p.pop("button_url", None)
            p["step"] = "button_more"
            ask_more_reply_buttons(message.chat.id, token)
            return True

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

    _save_pending_reply(token, with_buttons=False)
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
        "🔘 أرسل اسم الزر الأول.\nيمكنك كتابة أي إيموجي عادي داخله."
    )



# =========================================================
# لوحة الأدمن الخاصة بالمطور
# =========================================================
def admin_panel_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.row(
        button("الإحصائيات", callback_data="admin:stats", icon_custom_emoji_id=CE_ADMIN),
        button("المجموعات", callback_data="admin:groups", icon_custom_emoji_id=CE_MEMBER)
    )
    markup.row(
        button("الردود", callback_data="admin:replies", icon_custom_emoji_id=CE_REPLY_BUTTON),
        button("السجل", callback_data="admin:actions", icon_custom_emoji_id=CE_COMMANDS)
    )
    markup.row(
        button("الإذاعة", callback_data="admin:broadcast", icon_custom_emoji_id=CE_REPLY_BUTTON),
        button("إضافة رد عام", callback_data="admin:global_reply", icon_custom_emoji_id=CE_REPLY_BUTTON)
    )
    markup.row(
        button("تصدير الأعضاء", callback_data="admin:export", icon_custom_emoji_id=CE_MEMBER),
        button("استرجاع الأعضاء", callback_data="admin:restore", icon_custom_emoji_id=CE_MEMBER)
    )
    markup.row(
        button("الاشتراك الإجباري", callback_data="admin:force_channels", icon_custom_emoji_id=CE_FORCE_SUB),
        button("التحكم", callback_data="admin:control", icon_custom_emoji_id=CE_ADMIN)
    )
    markup.row(
        button("تحديث", callback_data="admin:refresh", icon_custom_emoji_id=CE_REPLY_BUTTON),
        button("إغلاق", callback_data="admin:close", icon_custom_emoji_id=CE_ERROR)
    )
    return markup


def admin_control_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        button("المجموعات", callback_data="admin:groups", icon_custom_emoji_id=CE_MEMBER),
        button("الردود", callback_data="admin:replies", icon_custom_emoji_id=CE_REPLY_BUTTON)
    )
    markup.row(
        button("الإذاعة", callback_data="admin:broadcast", icon_custom_emoji_id=CE_REPLY_BUTTON),
        button("إضافة رد عام", callback_data="admin:global_reply", icon_custom_emoji_id=CE_REPLY_BUTTON)
    )
    markup.row(
        button("الاشتراك الإجباري", callback_data="admin:force_channels", icon_custom_emoji_id=CE_FORCE_SUB),
        button("السجل", callback_data="admin:actions", icon_custom_emoji_id=CE_COMMANDS)
    )
    markup.row(button("رجوع", callback_data="admin:open", icon_custom_emoji_id=CE_COMMANDS))
    return markup


def admin_control_text():
    return (
        "<b>التحكم الكامل بالبوت</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        "من هنا تتحكم في المجموعات، الردود، الاشتراك الإجباري، والسجل.\n"
        "إدارة القنوات الإجبارية متاحة من زر الاشتراك الإجباري."
    )


def export_members_file(chat_id):
    cursor.execute("SELECT * FROM group_users ORDER BY chat_id,user_id")
    members = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM groups ORDER BY chat_id")
    groups = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM force_sub_channels ORDER BY id")
    force_channels = [dict(r) for r in cursor.fetchall()]
    payload = {
        "format": "protection_bot_members_v2",
        "created_at": now(),
        "members": members,
        "groups": groups,
        "force_sub_channels": force_channels
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    f = io.BytesIO(data)
    f.name = "protection_bot_members_backup.json"
    bot.send_document(chat_id, f, caption="نسخة احتياطية لأعضاء البوت والمجموعات.")


def _iter_backup_members(payload):
    """يدعم نسخ JSON القديمة والجديدة حتى لا تظهر نتيجة 0 عضو بسبب اختلاف اسم المفتاح."""
    candidates = []
    if isinstance(payload, dict):
        for key in ("members", "group_users", "users", "members_data", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates.extend(value)
            elif isinstance(value, dict):
                for chat_key, rows in value.items():
                    if isinstance(rows, list):
                        for item in rows:
                            if isinstance(item, dict) and "chat_id" not in item:
                                item = dict(item)
                                try:
                                    item["chat_id"] = int(chat_key)
                                except Exception:
                                    pass
                            candidates.append(item)
    elif isinstance(payload, list):
        candidates.extend(payload)
    return candidates


def _iter_backup_groups(payload):
    if not isinstance(payload, dict):
        return []
    for key in ("groups", "chats", "group_data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def restore_members_file(message):
    if not message.document:
        bot.reply_to(message, "أرسل ملف JSON الخاص بالنسخة الاحتياطية.")
        return True
    try:
        info = bot.get_file(message.document.file_id)
        raw = bot.download_file(info.file_path)
        payload = json.loads(raw.decode("utf-8-sig"))

        members = _iter_backup_members(payload)
        groups = _iter_backup_groups(payload)
        restored_members = 0
        restored_groups = 0
        seen = set()

        group_cols = [
            "chat_id", "title", "welcome", "links", "photos", "videos",
            "documents", "stickers", "audio", "animations", "spam",
            "flood", "repeat_messages", "new_member_protection", "max_warnings"
        ]

        for g in groups:
            if not isinstance(g, dict) or g.get("chat_id") is None:
                continue
            vals = [g.get(c, 0 if c not in ("title",) else "") for c in group_cols]
            placeholders = ",".join("?" for _ in group_cols)
            cursor.execute(
                f"INSERT OR IGNORE INTO groups({','.join(group_cols)}) VALUES({placeholders})",
                vals
            )
            if cursor.rowcount:
                restored_groups += 1

        for m in members:
            if not isinstance(m, dict):
                continue
            chat_id = m.get("chat_id", m.get("group_id", m.get("chat")))
            user_id = m.get("user_id", m.get("id"))
            if isinstance(chat_id, dict):
                chat_id = chat_id.get("id")
            if isinstance(user_id, dict):
                user_id = user_id.get("id")
            try:
                chat_id = int(chat_id)
                user_id = int(user_id)
            except (TypeError, ValueError):
                continue
            if (chat_id, user_id) in seen:
                continue
            seen.add((chat_id, user_id))

            # إذا كانت نسخة قديمة لا تحتوي اسم الأعمدة، ندعم aliases الشائعة.
            first_name = m.get("first_name", m.get("name", "")) or ""
            last_name = m.get("last_name", "") or ""
            username = m.get("username", m.get("user_name", "")) or ""
            cursor.execute("""
                INSERT INTO group_users(
                    chat_id,user_id,first_name,last_name,username,messages,warnings,joined_at,last_seen
                ) VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(chat_id,user_id) DO UPDATE SET
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    username=excluded.username,
                    messages=excluded.messages,
                    warnings=excluded.warnings,
                    joined_at=excluded.joined_at,
                    last_seen=excluded.last_seen
            """, (
                chat_id, user_id, first_name, last_name, username,
                int(m.get("messages", 0) or 0),
                int(m.get("warnings", 0) or 0),
                int(m.get("joined_at", m.get("created_at", 0)) or 0),
                int(m.get("last_seen", 0) or 0)
            ))
            restored_members += 1

        if isinstance(payload, dict):
            for fc in payload.get("force_sub_channels", payload.get("force_channels", [])) or []:
                if not isinstance(fc, dict) or fc.get("chat_id") is None:
                    continue
                cursor.execute("""
                    INSERT INTO force_sub_channels(chat_id,username,title,url,button_text,emoji_id,enabled)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(chat_id) DO UPDATE SET
                        username=excluded.username,title=excluded.title,url=excluded.url,
                        button_text=excluded.button_text,emoji_id=excluded.emoji_id,enabled=excluded.enabled
                """, (
                    fc.get("chat_id"), fc.get("username", ""), fc.get("title", ""),
                    fc.get("url", ""), fc.get("button_text", "Update MaX"),
                    fc.get("emoji_id", CE_FORCE_SUB), fc.get("enabled", 1)
                ))

        db.commit()
        bot.reply_to(
            message,
            f"تم استرجاع <b>{restored_members}</b> عضو و<b>{restored_groups}</b> مجموعة بنجاح."
        )
    except Exception as e:
        print("[Restore Members Error]", e)
        bot.reply_to(message, "تعذر استرجاع الملف. تأكد أنه ملف JSON صحيح أو نسخة قديمة من البوت.")
    return True


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
# الاشتراك الإجباري للمجموعات
# =========================================================
def get_force_channels():
    cursor.execute(
        "SELECT * FROM force_sub_channels WHERE enabled=1 ORDER BY id"
    )
    return cursor.fetchall()


def normalize_channel_ref(value):
    value = (value or "").strip()
    if value.startswith("https://t.me/"):
        tail = value.split("https://t.me/", 1)[1].strip("/")
        if tail and not tail.startswith("+"):
            return "@" + tail.split("/", 1)[0]
    if value.startswith("http://t.me/"):
        tail = value.split("http://t.me/", 1)[1].strip("/")
        if tail and not tail.startswith("+"):
            return "@" + tail.split("/", 1)[0]
    if value.startswith("@"): return value.split()[0]
    if re.fullmatch(r"-100\d+", value): return value
    if re.fullmatch(r"[A-Za-z0-9_]{4,}", value): return "@" + value
    return value


def add_force_channel(value):
    ref = normalize_channel_ref(value)
    if not ref:
        return False, "أرسل @username أو رابط القناة العام."
    try:
        chat = bot.get_chat(ref)
    except Exception as e:
        return False, "تعذر الوصول للقناة. تأكد أن اليوزر صحيح وأن البوت موجود في القناة."
    if chat.type != "channel":
        return False, "المصدر المضاف يجب أن يكون قناة Telegram."
    username = getattr(chat, "username", None) or ""
    url = f"https://t.me/{username}" if username else ""
    if not url:
        return False, "القناة يجب أن تكون لها رابط عام @username حتى يستطيع المستخدم فتحها."
    cursor.execute("""
        INSERT INTO force_sub_channels(chat_id,username,title,url,button_text,emoji_id,enabled)
        VALUES(?,?,?,?,?,?,1)
        ON CONFLICT(chat_id) DO UPDATE SET
            username=excluded.username,
            title=excluded.title,
            url=excluded.url,
            enabled=1
    """, (chat.id, username, chat.title or "", url, "Update MaX", CE_FORCE_SUB))
    db.commit()
    return True, chat.title or username


def remove_force_channel(channel_id):
    cursor.execute("DELETE FROM force_sub_channels WHERE id=?", (channel_id,))
    db.commit()
    return cursor.rowcount > 0


def user_subscribed_to_channel(user_id, row):
    try:
        member = bot.get_chat_member(row["chat_id"], user_id)
        return member.status in ("creator", "administrator", "member")
    except Exception as e:
        print("[Force Sub Check]", row["chat_id"], e)
        return False


def force_sub_missing(user_id):
    missing = []
    for row in get_force_channels():
        if not user_subscribed_to_channel(user_id, row):
            missing.append(row)
    return missing


def force_sub_markup(user_id, channels=None):
    channels = channels if channels is not None else get_force_channels()
    markup = types.InlineKeyboardMarkup(row_width=2)
    for row in channels:
        subscribed = user_subscribed_to_channel(user_id, row)
        channel_url = row["url"] or ""
        channel_title = row["title"] or row["username"] or "الاشتراك"
        if channel_url:
            subscribe_btn = transparent_url_button(
                "اشتراك " + channel_title[:18],
                channel_url,
                emoji_id=row["emoji_id"] or CE_FORCE_SUB
            )
            if subscribe_btn:
                markup.row(
                    subscribe_btn,
                    button(
                        "تم التحقق" if subscribed else "تحقق",
                        callback_data=f"force_sub_check:{row['id']}",
                        icon_custom_emoji_id=CE_FORCE_SUB
                    )
                )
        else:
            markup.add(button(
                "تم التحقق" if subscribed else "تحقق",
                callback_data=f"force_sub_check:{row['id']}",
                icon_custom_emoji_id=CE_FORCE_SUB
            ))

    update_btn = transparent_url_button("Update Max", UPDATE_MAX_URL, emoji_id=CE_REPLY_BUTTON)
    if update_btn:
        markup.add(update_btn)
    return markup


def send_force_sub_prompt(message, missing=None):
    if not message.from_user:
        return True
    missing = missing if missing is not None else force_sub_missing(message.from_user.id)
    if not missing:
        return False
    markup = force_sub_markup(message.from_user.id, get_force_channels())
    text = (
        "<b>الاشتراك الإجباري</b>\n"
        "┈┅⊷━⊷┅┅┈\n"
        "يجب الاشتراك في القنوات المطلوبة قبل الكتابة في المجموعة.\n"
        "اضغط على الزر للاشتراك، ثم اضغط عليه مرة أخرى للتحقق."
    )
    try:
        sent = bot.send_message(message.chat.id, text, reply_markup=markup)
        Thread(target=lambda: (time.sleep(90), delete_message_safe(sent)), daemon=True).start()
    except Exception as e:
        print("[Force Sub Prompt]", e)
    return True


def enforce_force_subscription(message):
    if (not message.from_user or message.from_user.is_bot or
            message.chat.type not in ("group", "supergroup")):
        return False
    if not get_force_channels():
        return False
    # الإدارة والمالك مستثنون حتى لا يتعطل التحكم بالمجموعة.
    if is_admin(message.chat.id, message.from_user.id):
        return False
    missing = force_sub_missing(message.from_user.id)
    if not missing:
        return False
    delete_message_safe(message)
    send_force_sub_prompt(message, missing)
    return True


def force_channels_admin_text():
    rows = get_force_channels()
    lines = ["<b>قنوات الاشتراك الإجباري</b>", "┈┅⊷━⊷┅┅┈"]
    if not rows:
        lines.append("لا توجد قنوات مضافة.")
    else:
        for i, row in enumerate(rows, 1):
            lines.append(f"{i}. <b>{html.escape(row['title'] or row['username'] or '')}</b> — <code>{html.escape(row['username'] or '')}</code>")
    return "\n".join(lines)


def force_channels_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        button("إضافة قناة", callback_data="admin:force_add", style="primary", icon_custom_emoji_id=CE_FORCE_SUB),
        button("حذف قناة", callback_data="admin:force_remove", style="danger", icon_custom_emoji_id=CE_ERROR)
    )
    markup.row(button("تحديث", callback_data="admin:force_channels", style="success", icon_custom_emoji_id=CE_REPLY_BUTTON))
    markup.row(button("رجوع", callback_data="admin:open", style="primary", icon_custom_emoji_id=CE_COMMANDS))
    return markup


def send_force_channels_admin(chat_id, message_id=None):
    text = force_channels_admin_text()
    markup = force_channels_admin_markup()
    if message_id is not None:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return True
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)
    return True


def force_remove_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for row in get_force_channels():
        markup.add(button(
            f"حذف: {row['title'] or row['username']}",
            callback_data=f"admin:force_delete:{row['id']}",
            style="danger",
            icon_custom_emoji_id=CE_ERROR
        ))
    markup.add(button("رجوع", callback_data="admin:force_channels", style="primary", icon_custom_emoji_id=CE_COMMANDS))
    return markup


# =========================================================
# START الخاص
# =========================================================
def start_private(message):
    user = message.from_user
    safe_name = html.escape(full_name(user))

    track_private_user(message, notify=True)

    text = (
        f"{tg_emoji(CE_WELCOME_HELLO, '•')} مرحبًـا يـ {safe_name}\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"{tg_emoji(CE_WELCOME_INFO, '•')}هذا البوت مخصص لإدارة وحماية المجموعات بالكـامل.\n"
        "┈┅⊷━⊷┅┅┈\n"
        f"{tg_emoji(CE_WELCOME_INFO, '•')} اضـف البـوت فـي المجـموعـه الخـاصـه بـك وارفـعـه مشـرف مع جمـيع الصـلاحيـات."
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        button(
            "اضفني لمجموعتك",
            url=ADD_TO_GROUP_URL,
            icon_custom_emoji_id=CE_ADD_TO_GROUP_REQUESTED
        )
    )
    markup.add(
        button(
            "Update Max",
            url=UPDATE_MAX_URL,
            icon_custom_emoji_id=CE_REPLY_BUTTON
        )
    )

    if user.id == DEVELOPER_ID:
        markup.add(
            button(
                "لوحة الأدمن",
                callback_data="admin:open",
                icon_custom_emoji_id=CE_ADMIN
            )
        )

    bot.send_message(message.chat.id, text, reply_markup=markup)


# =========================================================
# الحظر العام
# =========================================================
def enforce_global_ban(message):
    if (
        not message.from_user
        or message.from_user.is_bot
        or message.chat.type not in ("group", "supergroup")
    ):
        return False

    if not is_global_banned(message.from_user.id):
        return False

    try:
        if bot_is_admin(message.chat.id):
            bot.ban_chat_member(
                message.chat.id,
                message.from_user.id
            )
            delete_message_safe(message)
    except Exception as e:
        print("[Global Ban Enforcement]", e)

    return True


# =========================================================
# الأعضاء الجدد
# =========================================================

@bot.my_chat_member_handler()
def bot_chat_membership_handler(message):
    try:
        new_status = getattr(getattr(message, "new_chat_member", None), "status", "")
        old_status = getattr(getattr(message, "old_chat_member", None), "status", "")

        if message.chat.type in ("group", "supergroup"):
            if new_status in ("member", "administrator") and old_status in ("left", "kicked", ""):
                ensure_group(message.chat)
                notify_group_event("added", message)
            elif new_status in ("left", "kicked") and old_status in ("member", "administrator", "creator"):
                ensure_group(message.chat)
                notify_group_event("removed", message)
        elif message.chat.type == "private":
            # فتح الخاص/إلغاء الحظر يُسجل كمستخدم.
            if new_status in ("member", "administrator"):
                track_private_user(message, notify=True)

        print(f"[Bot Membership] {message.chat.id} old={old_status} new={new_status}")
    except Exception as e:
        print("[Group Tracking Error]", e)


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

    # نُسجل كل عضو جديد حتى لو كان البوت سيغلق رسالة الترحيب لاحقًا.
    for u in message.new_chat_members or []:
        if u.is_bot:
            register_known_bot(message.chat.id, u)
            continue
        register_member(message.chat.id, u)

        if is_global_banned(u.id):
            try:
                if bot_is_admin(message.chat.id):
                    bot.ban_chat_member(message.chat.id, u.id)
            except Exception as e:
                print("[Global Ban New Member]", e)
            continue

        if not group_setting(message.chat.id, "welcome"):
            continue

        safe_name = html.escape(full_name(u))
        welcome_text = (
            f"{tg_emoji(CE_WELCOME_HELLO, '•')} مرحبًـا يـ {safe_name}\n"
            "┈┅⊷━⊷┅┅┈\n"
            f"{tg_emoji(CE_WELCOME_INFO, '•')}هذا البوت مخصص لإدارة وحماية المجموعات بالكـامل.\n"
            "┈┅⊷━⊷┅┅┈\n"
            f"{tg_emoji(CE_WELCOME_INFO, '•')} اضـف البـوت فـي المجـموعـه الخـاصـه بـك وارفـعـه مشـرف مع جمـيع الصـلاحيـات."
        )

        markup = types.InlineKeyboardMarkup()
        add_btn = transparent_url_button(
            "اضفني لمجموعتك",
            ADD_TO_GROUP_URL,
            emoji_id=CE_ADD_TO_GROUP_REQUESTED
        )
        if add_btn:
            markup.add(add_btn)
        update_btn = transparent_url_button(
            "Update Max",
            UPDATE_MAX_URL,
            emoji_id=CE_REPLY_BUTTON
        )
        if update_btn:
            markup.add(update_btn)

        try:
            photos = bot.get_user_profile_photos(u.id, limit=1)
            if photos.total_count:
                sent = bot.send_photo(
                    message.chat.id,
                    photos.photos[0][-1].file_id,
                    caption=welcome_text,
                    reply_markup=markup
                )
            else:
                sent = bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
            Thread(
                target=lambda m=sent: (time.sleep(60), delete_message_safe(m)),
                daemon=True
            ).start()
        except Exception as e:
            print("[Welcome Error]", e)
            try:
                sent = bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
                Thread(
                    target=lambda m=sent: (time.sleep(60), delete_message_safe(m)),
                    daemon=True
                ).start()
            except Exception:
                pass


# =========================================================
# التتبع والإذاعة وإدارة البوتات
# =========================================================
def track_private_user(message, notify=True):
    if not message or not message.from_user or message.chat.type != "private":
        return
    u = message.from_user
    ts = now()
    cursor.execute("""
        INSERT INTO bot_private_users(user_id,first_name,last_name,username,first_seen,last_seen)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            username=excluded.username,
            last_seen=excluded.last_seen
    """, (u.id, u.first_name or "", u.last_name or "", u.username or "", ts, ts))
    db.commit()

    if not notify or u.id == DEVELOPER_ID:
        return
    cursor.execute("SELECT 1 FROM developer_notifications WHERE user_id=?", (u.id,))
    if cursor.fetchone():
        return
    try:
        notify_text = (
            f"{tg_emoji(CE_ADMIN, '•')} مستخدم جديد استخدم البوت\n"
            "┈┅⊷━⊷┅┅┈\n"
            f"{tg_emoji(CE_PERSON, '•')} الاسم: <a href=\"tg://user?id={u.id}\">{html.escape(full_name(u))}</a>\n"
            f"{tg_emoji(CE_USERNAME, '•')} اليوزر: {html.escape(username_text(u))}\n"
            f"{tg_emoji(CE_ID, '•')} الايدي: <code>{u.id}</code>"
        )
        bot.send_message(DEVELOPER_ID, notify_text)
        cursor.execute(
            "INSERT OR REPLACE INTO developer_notifications(user_id,notified_at) VALUES(?,?)",
            (u.id, ts)
        )
        db.commit()
    except Exception as e:
        print("[Developer User Notification]", e)


def register_known_bot(chat_id, user):
    if not user or not getattr(user, "is_bot", False):
        return
    cursor.execute("""
        INSERT INTO known_bots(chat_id,user_id,first_name,username,discovered_at)
        VALUES(?,?,?,?,?)
        ON CONFLICT(chat_id,user_id) DO UPDATE SET
            first_name=excluded.first_name,
            username=excluded.username
    """, (chat_id, user.id, user.first_name or "", user.username or "", now()))
    db.commit()


def notify_group_event(kind, message):
    if not message or not message.from_user:
        return
    chat = message.chat
    actor = message.from_user
    label = "تمت إضافة البوت إلى مجموعة" if kind == "added" else "تمت إزالة البوت من مجموعة"
    try:
        text = (
            f"{tg_emoji(CE_ADMIN, '•')} {label}\n"
            "┈┅⊷━⊷┅┅┈\n"
            f"{tg_emoji(CE_MEMBER, '•')} المجموعة: <b>{html.escape(chat.title or 'بدون اسم')}</b>\n"
            f"{tg_emoji(CE_ID, '•')} ايدي المجموعة: <code>{chat.id}</code>\n"
            f"{tg_emoji(CE_PERSON, '•')} بواسطة: <a href=\"tg://user?id={actor.id}\">{html.escape(full_name(actor))}</a>\n"
            f"{tg_emoji(CE_USERNAME, '•')} اليوزر: {html.escape(username_text(actor))}"
        )
        bot.send_message(DEVELOPER_ID, text)
    except Exception as e:
        print("[Developer Group Notification]", e)


def get_known_group_bots(chat_id):
    bots = {}
    try:
        admins = bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.user and admin.user.is_bot:
                bots[admin.user.id] = admin.user
                register_known_bot(chat_id, admin.user)
    except Exception as e:
        print("[Bots Admin Scan]", e)

    cursor.execute("SELECT user_id,first_name,username FROM known_bots WHERE chat_id=?", (chat_id,))
    for row in cursor.fetchall():
        if row["user_id"] not in bots:
            class _KnownBot:
                pass
            u = _KnownBot()
            u.id = row["user_id"]
            u.first_name = row["first_name"] or "Bot"
            u.last_name = ""
            u.username = row["username"] or ""
            u.is_bot = True
            bots[u.id] = u

    # تأكد أن السجلات القديمة ما زالت تشير لأعضاء موجودين.
    result = []
    for u in list(bots.values()):
        try:
            m = bot.get_chat_member(chat_id, u.id)
            if m and m.status not in ("left", "kicked"):
                result.append(m.user)
        except Exception:
            # إذا تعذر الفحص، لا نعرض السجل القديم لتجنب نتائج وهمية.
            pass
    return result


def format_bot_list(message):
    bots = get_known_group_bots(message.chat.id)
    if not bots:
        return "لا توجد بوتات معروفة حاليًا في المجموعة. Telegram لا يتيح للبوتات قراءة قائمة جميع الأعضاء." 
    lines = ["<b>البوتات الموجودة</b>", "┈┅⊷━⊷┅┅┈"]
    for i, u in enumerate(bots, 1):
        uname = f"@{html.escape(u.username)}" if getattr(u, "username", None) else "لا يوجد يوزر"
        lines.append(f"{i}. <a href=\"tg://user?id={u.id}\">{html.escape(full_name(u))}</a> — {uname}")
    return "\n".join(lines)


def kick_all_known_bots(message):
    bots = get_known_group_bots(message.chat.id)
    if not bots:
        bot.reply_to(message, "لا توجد بوتات معروفة يمكن طردها حاليًا.")
        return True
    me = bot.get_me()
    kicked = 0
    skipped = 0
    for u in bots:
        if u.id == me.id:
            skipped += 1
            continue
        try:
            member = bot.get_chat_member(message.chat.id, u.id)
            if member.status == "administrator":
                try:
                    bot.promote_chat_member(
                        message.chat.id, u.id,
                        can_change_info=False,
                        can_delete_messages=False,
                        can_invite_users=False,
                        can_restrict_members=False,
                        can_pin_messages=False,
                        can_manage_video_chats=False,
                        can_manage_topics=False,
                        can_promote_members=False
                    )
                except Exception:
                    skipped += 1
                    continue
            if member.status == "creator":
                skipped += 1
                continue
            kick_user(message.chat.id, u.id)
            kicked += 1
        except Exception as e:
            print("[Kick Bot]", u.id, e)
            skipped += 1
    bot.reply_to(message, f"تم طرد <b>{kicked}</b> بوت. تعذر طرد <b>{skipped}</b>.")
    return True


def send_admins_list(message):
    try:
        admins = bot.get_chat_administrators(message.chat.id)
    except Exception:
        bot.reply_to(message, "تعذر جلب المشرفين حاليًا.")
        return True
    lines = ["<b>مشرفو المجموعة</b>", "┈┅⊷━⊷┅┅┈"]
    for i, admin in enumerate(admins, 1):
        u = admin.user
        uname = f"@{html.escape(u.username)}" if u.username else "لا يوجد يوزر"
        lines.append(
            f"{i}. {tg_emoji(CE_ADMIN_USERNAME, '•')} "
            f"<a href=\"tg://user?id={u.id}\">{html.escape(full_name(u))}</a> — {uname}"
        )
    bot.reply_to(message, "\n".join(lines))
    return True


def broadcast_recipients():
    cursor.execute("SELECT user_id FROM bot_private_users")
    private_ids = {int(r["user_id"]) for r in cursor.fetchall()}
    cursor.execute("SELECT chat_id FROM groups")
    group_ids = {int(r["chat_id"]) for r in cursor.fetchall()}
    return sorted(private_ids | group_ids)


def perform_broadcast(source_message, reply_markup=None):
    recipients = broadcast_recipients()
    ok = 0
    failed = 0
    for target_id in recipients:
        if target_id == DEVELOPER_ID:
            continue
        try:
            kwargs = {
                "chat_id": target_id,
                "from_chat_id": source_message.chat.id,
                "message_id": source_message.message_id
            }
            if reply_markup is not None:
                kwargs["reply_markup"] = reply_markup
            bot.copy_message(**kwargs)
            ok += 1
            time.sleep(0.03)
        except Exception as e:
            failed += 1
            print("[Broadcast]", target_id, e)
    return ok, failed


def start_broadcast(message):
    admin_pending[message.from_user.id] = "broadcast_message"
    bot.send_message(
        message.chat.id,
        "أرسل الآن رسالة الإذاعة بأي نوع يدعمه Telegram.\n"
        "بعدها يمكنك إضافة زر شفاف للرابط مع Premium Emoji تلقائيًا."
    )


def broadcast_button_choice(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        button("شفاف", callback_data=f"broadcast_btn_yes:{uid}", icon_custom_emoji_id=CE_REPLY_BUTTON),
        button("إرسال الآن", callback_data=f"broadcast_btn_no:{uid}", icon_custom_emoji_id=CE_REPLY_BUTTON)
    )
    return markup


def start_global_reply(message):
    token = secrets.token_hex(8)
    reply_pending[token] = {
        "chat_id": 0,
        "initiator": message.from_user.id,
        "trigger": "",
        "step": "trigger",
        "buttons": [],
        "global": True
    }
    bot.send_message(message.chat.id, "أرسل الآن كلمة الرد العام.")

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
        # معالجة /start أولاً قبل قاعدة البيانات أو أي حماية أخرى.
        # هذا يمنع فشل أي جزء ثانوي من تعطيل أول استجابة للمستخدم.
        if message.chat and message.chat.type == "private":
            _start_command, _start_argument = command_parts(message)
            if _start_command == "start":
                try:
                    if message.from_user and not message.from_user.is_bot:
                        track_private_user(message, notify=True)
                except Exception as _track_error:
                    print("[Start Tracking Error]", repr(_track_error))
                    traceback.print_exc()

                try:
                    start_private(message)
                except Exception as _start_error:
                    print("[START HANDLER ERROR]", repr(_start_error))
                    traceback.print_exc()
                    try:
                        bot.send_message(
                            message.chat.id,
                            "حدث خطأ أثناء تجهيز رسالة البداية. راجع سجل التشغيل لمعرفة السبب."
                        )
                    except Exception as _send_error:
                        print("[START FALLBACK SEND ERROR]", repr(_send_error))
                        traceback.print_exc()
                return

        if (
            message.from_user
            and not message.from_user.is_bot
        ):
            try:
                register_user(
                    message,
                    True
                )
            except Exception as _register_error:
                print("[Register User Error]", repr(_register_error))
                traceback.print_exc()

        if message.chat.type == "private":

            if message.from_user:
                track_private_user(message, notify=True)

            if message.from_user and message.from_user.id == DEVELOPER_ID and admin_pending.get(message.from_user.id) == "broadcast_message":
                admin_pending.pop(message.from_user.id, None)
                broadcast_pending[message.from_user.id] = {"message": message}
                bot.send_message(
                    message.chat.id,
                    "تم تجهيز رسالة الإذاعة. هل تريد إضافة زر شفاف؟",
                    reply_markup=broadcast_button_choice(message.from_user.id)
                )
                return

            if message.from_user and message.from_user.id == DEVELOPER_ID and message.from_user.id in admin_pending:
                pending = admin_pending.get(message.from_user.id)
                if pending == "broadcast_button_text":
                    data = broadcast_pending.get(message.from_user.id)
                    if not data:
                        admin_pending.pop(message.from_user.id, None)
                        bot.send_message(message.chat.id, "انتهت عملية الإذاعة. ابدأها من لوحة الأدمن مرة أخرى.")
                        return
                    text = strip_non_custom_emoji((message.text or "").strip()).strip()
                    if not text:
                        bot.send_message(message.chat.id, "أرسل اسم الزر بدون Emoji عادي؛ Premium Emoji يمكن إرساله وسيتم التقاطه تلقائيًا.")
                        return
                    data["button_text"] = text
                    admin_pending[message.from_user.id] = "broadcast_button_url"
                    bot.send_message(message.chat.id, "أرسل رابط الزر كاملًا. يدعم Telegram وhttp/https.")
                    return

                if pending == "broadcast_button_url":
                    data = broadcast_pending.get(message.from_user.id)
                    url = (message.text or "").strip()
                    if not data:
                        admin_pending.pop(message.from_user.id, None)
                        bot.send_message(message.chat.id, "انتهت عملية الإذاعة.")
                        return
                    if not re.match(r"^(?:https?|tg)://\S+$", url, re.I):
                        bot.send_message(message.chat.id, "أرسل رابطًا صالحًا يبدأ بـ https:// أو http:// أو tg://")
                        return
                    data["button_url"] = url
                    admin_pending[message.from_user.id] = "broadcast_button_emoji"
                    bot.send_message(message.chat.id, "أرسل Premium Emoji للزر، أو اكتب تخطي.")
                    return

                if pending == "broadcast_button_emoji":
                    data = broadcast_pending.get(message.from_user.id)
                    if not data:
                        admin_pending.pop(message.from_user.id, None)
                        bot.send_message(message.chat.id, "انتهت عملية الإذاعة.")
                        return
                    raw = (message.text or "").strip()
                    emoji_id = extract_custom_emoji_id(message)
                    if raw and clean_text(raw) in ("تخطي", "بدون", "لا"):
                        emoji_id = ""
                    data["button_emoji_id"] = emoji_id or ""
                    admin_pending.pop(message.from_user.id, None)
                    source = data["message"]
                    b = transparent_url_button(data.get("button_text", "زر"), data.get("button_url", ""), data.get("button_emoji_id") or None)
                    markup = types.InlineKeyboardMarkup()
                    if b:
                        markup.add(b)
                    ok, failed = perform_broadcast(source, markup if markup.keyboard else None)
                    broadcast_pending.pop(message.from_user.id, None)
                    bot.send_message(message.chat.id, f"تمت الإذاعة إلى <b>{ok}</b> جهة. تعذر الإرسال إلى <b>{failed}</b>.")
                    return

            if message.from_user and message.from_user.id == DEVELOPER_ID and message.document and admin_pending.get(message.from_user.id) == "restore_members":
                admin_pending.pop(message.from_user.id, None)
                restore_members_file(message)
                return

            if automatic_currency_conversion(message):
                return

            handle_private(message)
            return

        ensure_group(
            message.chat
        )

        # تنفيذ الحظر العام قبل أي رد أو أمر آخر.
        if enforce_global_ban(message):
            return

        if enforce_force_subscription(message):
            return

        if message.text and message.text.strip() == ".":
            markup = types.InlineKeyboardMarkup()
            btn = transparent_url_button(
                "صلي علي النبي",
                "https://t.me/LeaDeR_E"
            )
            if btn:
                markup.add(btn)
            bot.send_message(
                message.chat.id,
                "صلي علي النبي",
                reply_markup=markup
            )
            return

        if message.text and clean_text(message.text) == "بوت":
            try:
                me = bot.get_me()
                bot_name = full_name(me)
            except Exception:
                bot_name = BOT_USERNAME

            bot.send_message(
                message.chat.id,
                "تاارا اسمي "
                + html.escape(bot_name)
                + " متشوف "
                + tg_emoji(CE_BOT_REPLY, "🤖")
            )
            return

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
        print("[Handler Error]", repr(e))
        traceback.print_exc()


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

    if message.from_user and message.from_user.id == DEVELOPER_ID and message.from_user.id in admin_pending and message.text:
        pending_action = admin_pending.get(message.from_user.id)
        if pending_action == "force_add":
            admin_pending.pop(message.from_user.id, None)
            ok, result = add_force_channel(message.text)
            if ok:
                bot.send_message(message.chat.id, f"تمت إضافة القناة: <b>{html.escape(str(result))}</b>")
                send_force_channels_admin(message.chat.id)
            else:
                bot.send_message(message.chat.id, f"تعذر الإضافة: {html.escape(str(result))}")
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
        send_commands_menu(message)
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

    # أدوات المجموعة الخاصة بالبوتات والمشرفين.
    if command in ("البوتات", "بوتات"):
        return_command = format_bot_list(message)
        bot.reply_to(message, return_command)
        return True

    if command in ("طرد_البوتات", "طردالبوتات"):
        if not admin_required(message):
            return True
        return kick_all_known_bots(message)

    if command == "المشرفين":
        return send_admins_list(message)

    # الأوامر
    if command in (
        "الاوامر",
        "مساعده"
    ):
        send_commands_menu(message)
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

    # تحليل TON
    if command == "تحليل_تون":
        return send_ton_analysis(message)

    # تحليل الدولار
    if command == "تحليل_دولار":
        return send_dollar_analysis(message)

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

    # الردود التلقائية
    if command == "اضف_رد":
        return start_add_reply(message, argument)

    if command == "حذف_رد":
        if not argument:
            bot.reply_to(message, "❌ اكتب الكلمة التي تريد حذف ردها.")
            return True
        if delete_auto_reply(chat_id, argument):
            bot.reply_to(message, f"✅ تم حذف رد <code>{html.escape(argument)}</code>.")
        else:
            bot.reply_to(message, "❌ لا يوجد رد محفوظ بهذه الكلمة.")
        return True

    if command == "قائمة_الردود":
        cursor.execute("SELECT trigger FROM auto_replies WHERE chat_id=? ORDER BY trigger COLLATE NOCASE", (chat_id,))
        rows = cursor.fetchall()
        text = "📋 <b>الردود التلقائية</b>\n┈┅⊷━⊷┅┅┈\n"
        text += "\n".join(f"• <code>{html.escape(r['trigger'])}</code>" for r in rows) if rows else "لا توجد ردود تلقائية محفوظة."
        bot.reply_to(message, text)
        return True

    # أوامر الإدارة
    admin_commands = {
        "حظر",
        "حظرعام",
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

    # حظر عام
    if command == "حظرعام":

        t = get_target(
            message,
            argument
        )

        if not t:
            bot.reply_to(
                message,
                "❌ استخدم الأمر: حظر عام بالرد أو حظر عام ID أو @username."
            )
            return True

        if target_protected(message, t) or t.id == DEVELOPER_ID:
            bot.reply_to(
                message,
                "❌ لا يمكنك تنفيذ الحظر العام على هذا المستخدم."
            )
            return True

        try:
            success, skipped = global_ban_user(
                t.id,
                message.from_user.id
            )

            log_action(
                chat_id,
                message.from_user.id,
                t.id,
                "حظر عام",
                f"groups={success};skipped={skipped}"
            )

            bot.reply_to(
                message,
                f"🚫 تم الحظر العام لـ {mention(t)}.\n"
                f"تم الحظر في {success} مجموعة، وتعذر التنفيذ في {skipped} مجموعة."
            )

        except Exception as e:
            print("[Global Ban Error]", e)
            bot.reply_to(
                message,
                "❌ فشل تنفيذ الحظر العام."
            )

        return True

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

            if action == "broadcast":
                admin_pending[uid] = "broadcast_message"
                bot.answer_callback_query(call.id)
                bot.send_message(
                    chat_id,
                    "أرسل الآن رسالة الإذاعة بأي نوع يدعمه Telegram.\nسيتم الحفاظ على النص والتنسيق والروابط وPremium Emoji والوسائط."
                )
                return

            if action == "global_reply":
                bot.answer_callback_query(call.id)
                start_global_reply(call.message)
                return

            if action == "export":
                bot.answer_callback_query(call.id, "جاري تجهيز النسخة...")
                export_members_file(chat_id)
                return

            if action == "restore":
                admin_pending[uid] = "restore_members"
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, "أرسل الآن ملف JSON الذي تم تصديره من البوت لاسترجاع الأعضاء.")
                return

            if action == "control":
                bot.answer_callback_query(call.id)
                bot.edit_message_text(admin_control_text(), chat_id, call.message.message_id, reply_markup=admin_control_markup())
                return

            if action == "force_channels":
                bot.answer_callback_query(call.id)
                send_force_channels_admin(chat_id, call.message.message_id)
                return

            if action == "force_add":
                admin_pending[uid] = "force_add"
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, "أرسل @username القناة أو رابطها العام لإضافتها للاشتراك الإجباري.")
                return

            if action == "force_remove":
                bot.answer_callback_query(call.id)
                bot.edit_message_text(force_channels_admin_text(), chat_id, call.message.message_id, reply_markup=force_remove_admin_markup())
                return

            if action.startswith("force_delete:"):
                try:
                    channel_id = int(action.split(":",1)[1])
                    remove_force_channel(channel_id)
                    bot.answer_callback_query(call.id, "تم حذف القناة")
                    send_force_channels_admin(chat_id, call.message.message_id)
                except Exception:
                    bot.answer_callback_query(call.id, "تعذر حذف القناة", show_alert=True)
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

        # إعداد زر شفاف للإذاعة.
        if call.data.startswith("broadcast_btn_yes:"):
            try:
                target_uid = int(call.data.split(":", 1)[1])
            except Exception:
                target_uid = -1
            if uid != DEVELOPER_ID or target_uid != uid or uid not in broadcast_pending:
                bot.answer_callback_query(call.id, "هذه العملية ليست لك أو انتهت.", show_alert=True)
                return
            admin_pending[uid] = "broadcast_button_text"
            bot.answer_callback_query(call.id)
            bot.send_message(chat_id, "أرسل اسم الزر الشفاف.")
            return

        if call.data.startswith("broadcast_btn_no:"):
            try:
                target_uid = int(call.data.split(":", 1)[1])
            except Exception:
                target_uid = -1
            data = broadcast_pending.get(uid)
            if uid != DEVELOPER_ID or target_uid != uid or not data:
                bot.answer_callback_query(call.id, "هذه العملية ليست لك أو انتهت.", show_alert=True)
                return
            admin_pending.pop(uid, None)
            source = data["message"]
            broadcast_pending.pop(uid, None)
            bot.answer_callback_query(call.id, "جاري الإرسال...")
            ok, failed = perform_broadcast(source)
            bot.send_message(chat_id, f"تمت الإذاعة إلى <b>{ok}</b> جهة. تعذر الإرسال إلى <b>{failed}</b>.")
            return

        # فحص الاشتراك الإجباري: نفس الزر يفتح القناة عند عدم الاشتراك، ويتحول للأخضر بعد الاشتراك.
        if call.data.startswith("force_sub_check:"):
            try:
                channel_id = int(call.data.split(":", 1)[1])
                cursor.execute("SELECT * FROM force_sub_channels WHERE id=? AND enabled=1", (channel_id,))
                row = cursor.fetchone()
                if not row:
                    bot.answer_callback_query(call.id, "القناة لم تعد موجودة.", show_alert=True)
                    return
                if user_subscribed_to_channel(uid, row):
                    bot.answer_callback_query(call.id, "تم التحقق من الاشتراك.")
                    try:
                        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=force_sub_markup(uid))
                    except Exception:
                        pass
                else:
                    bot.answer_callback_query(call.id, "لم يتم التحقق بعد. اشترك أولًا ثم اضغط تحقق.", url=row["url"] or None)
                return
            except Exception as e:
                print("[Force Sub Callback]", e)
                bot.answer_callback_query(call.id, "تعذر التحقق الآن.", show_alert=True)
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

        if call.data.startswith("replybtn_more_yes:"):
            token = call.data.split(":", 1)[1]
            p = reply_pending.get(token)
            if not p or p.get("initiator") != uid:
                bot.answer_callback_query(call.id, "❌ هذه العملية ليست لك أو انتهت.", show_alert=True)
                return
            p["step"] = "button_text"
            bot.answer_callback_query(call.id)
            bot.send_message(
                chat_id,
                "🔘 أرسل اسم الزر التالي.\nيمكنك إرسال Premium Emoji داخل الرسالة وسيتم التقاطه تلقائيًا."
            )
            return

        if call.data.startswith("replybtn_more_no:"):
            token = call.data.split(":", 1)[1]
            p = reply_pending.get(token)
            if not p or p.get("initiator") != uid:
                bot.answer_callback_query(call.id, "❌ هذه العملية ليست لك أو انتهت.", show_alert=True)
                return
            _save_pending_reply(token, with_buttons=True)
            bot.answer_callback_query(call.id, "✅ تم حفظ الرد والأزرار")
            try:
                bot.edit_message_text(
                    "✅ تم حفظ الرد وكل الأزرار بنجاح.",
                    chat_id,
                    call.message.message_id
                )
            except Exception:
                pass
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
                "📚 <b>قائمة أوامر البوت</b>\n┈┅⊷━⊷┅┅┈\nاختر القسم الذي تريد أوامره:",
                reply_markup=commands_menu_markup()
            )

            return

        if call.data.startswith("cmdcat:"):
            category = call.data.split(":", 1)[1]
            bot.answer_callback_query(call.id)
            if category == "home":
                bot.edit_message_text(
                    "📚 <b>قائمة أوامر البوت</b>\n┈┅⊷━⊷┅┅┈\nاختر القسم الذي تريد أوامره:",
                    chat_id, call.message.message_id,
                    reply_markup=commands_menu_markup()
                )
                return
            if category == "all":
                text = commands_text(get_owner_user(chat_id))
            else:
                text = command_category_text(category)
            bot.edit_message_text(
                text, chat_id, call.message.message_id,
                reply_markup=commands_back_markup()
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
def setup_default_force_channel():
    # القناة التي طلبها المطور: تضاف افتراضيًا عند أول تشغيل فقط إذا لم توجد أي قناة.
    try:
        cursor.execute("SELECT COUNT(*) AS c FROM force_sub_channels")
        if cursor.fetchone()["c"] == 0:
            ok, result = add_force_channel("@LeaDeR_E")
            print("[Force Sub Default]", result if ok else result)
    except Exception as e:
        print("[Force Sub Default Error]", e)

def run_bot_forever():
    print("===================================")
    print(" Protection Bot Started")
    print(" Bot: @" + BOT_USERNAME)
    print(" Database:", DB_NAME)
    print(" Rank System: ON")
    print(" Custom Emoji: ON")
    print(" Diagnostic Polling: ON")
    print("===================================")

    try:
        setup_default_force_channel()
    except Exception as e:
        print("[Startup Force Sub Error]", repr(e))
        traceback.print_exc()

    # تنظيف الـWebhook مرة واحدة.
    try:
        bot.remove_webhook()
        print("[Webhook] Removed successfully")
    except Exception as e:
        print("[Webhook Cleanup Error]", repr(e))

    time.sleep(1)

    # نستخدم get_updates يدويًا بدل infinity_polling/polling حتى يظهر
    # أي خطأ حقيقي داخل استقبال/معالجة التحديثات في Pydroid.
    offset = None
    conflict_count = 0

    while True:
        try:
            updates = bot.get_updates(
                offset=offset,
                timeout=30,
                long_polling_timeout=30,
                allowed_updates=[
                    "message",
                    "edited_message",
                    "callback_query",
                    "my_chat_member",
                    "chat_member",
                    "chat_join_request"
                ]
            )

            if conflict_count:
                print("[Polling] 409 انتهى وعاد الاتصال بنجاح")
                conflict_count = 0

            for update in updates:
                offset = update.update_id + 1
                try:
                    print(
                        "[UPDATE] id=",
                        update.update_id,
                        "type=",
                        type(update).__name__
                    )
                    bot.process_new_updates([update])
                    print("[UPDATE OK] id=", update.update_id)
                except Exception as update_error:
                    print("[UPDATE PROCESS ERROR]", repr(update_error))
                    traceback.print_exc()

        except KeyboardInterrupt:
            print("Bot stopped.")
            break

        except Exception as e:
            error_text = repr(e)
            print("[POLLING ERROR]", error_text)
            traceback.print_exc()

            if (
                "409" in error_text
                or "Conflict" in error_text
                or "terminated by other getUpdates" in error_text
            ):
                conflict_count += 1
                print(
                    "[POLLING 409] يوجد تشغيل آخر لنفس البوت بنفس التوكن. "
                    "أغلق النسخة الأخرى أو غيّر التوكن من BotFather."
                )
                time.sleep(min(30, 5 + conflict_count * 3))
            else:
                time.sleep(3)

            try:
                bot.remove_webhook()
            except Exception:
                pass


run_bot_forever()
