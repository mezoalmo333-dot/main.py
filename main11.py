# -*- coding: utf-8 -*-
"""
LEADER XO — Telegram XO Bot Edition
Single-file / Python standard library only.

Required:
  BOT_TOKEN = Telegram bot token
  OWNER_ID  = Telegram numeric owner ID
"""
import os
import re
import json
import time
import secrets
import string
import threading
import urllib.parse
import urllib.request

BOT_TOKEN = os.getenv("BOT_TOKEN", "8830531937:AAE12BSnfpPRu5uwxODmVmi7oYbBoWQk4oI").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "8037399518"))
DB_FILE = os.getenv("DB_FILE", "leader_xo_db.json")

GLOBAL_EMOJI = "5359719332542718652"
X_EMOJI = "5855177736082953485"
O_EMOJI = "6163667408545386934"

DEFAULT_CONFIG = {
    "welcome": "LEADER XO\n\nXO رايقة داخل Telegram.\nاعمل غرفة، خذ الكود، وابعتُه لصاحبك.",
    "buttons": {
        "create": "إنشاء غرفة",
        "join": "دخول غرفة",
        "leaders": "المتصدرين",
        "profile": "إحصائياتي",
        "rules": "طريقة اللعب",
        "admin": "الإدارة",
        "broadcast": "إذاعة",
    },
    "button_emojis": {},
    "x_emoji": X_EMOJI,
    "o_emoji": O_EMOJI,
    "broadcast_url": "",
    "broadcast_button": "فتح الرابط",
    "force_sub_enabled": True,
    "required_channels": ["https://t.me/LeaDeR_E", "https://t.me/kon_ze_athar"],
    "win_points": 1,
    "leave_points": 1,
    "empty_cell": "⠀",
    "leave_button": "خروج من الغرفة",
}

DB = {"config": {}, "users": {}, "rooms": {}}
LOCK = threading.RLock()
PENDING = {}


def clone_default():
    return json.loads(json.dumps(DEFAULT_CONFIG, ensure_ascii=False))


def save_db():
    with LOCK:
        tmp = DB_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(DB, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DB_FILE)


def load_db():
    with LOCK:
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    DB.update(loaded)
            except Exception as e:
                print("DB load error:", e)
        base = clone_default()
        DB.setdefault("config", {})
        for k, v in base.items():
            if k not in DB["config"]:
                DB["config"][k] = v
        DB["config"].setdefault("buttons", {}).update({
            k: v for k, v in base["buttons"].items()
            if k not in DB["config"].get("buttons", {})
        })
        DB["config"].setdefault("button_emojis", {})
        # Every Telegram button uses the requested global Premium Emoji by default.
        for _key in DB["config"].get("buttons", {}):
            DB["config"]["buttons"][_key] = clean_bot_text(DB["config"]["buttons"][_key])
            DB["config"]["button_emojis"][_key] = GLOBAL_EMOJI
        DB["config"].setdefault("x_emoji", X_EMOJI)
        DB["config"].setdefault("o_emoji", O_EMOJI)
        DB["config"].setdefault("broadcast_url", "")
        DB["config"].setdefault("broadcast_button", "فتح الرابط")
        DB["config"].setdefault("force_sub_enabled", True)
        DB["config"].setdefault("required_channels", ["https://t.me/LeaDeR_E", "https://t.me/kon_ze_athar"])
        DB["config"].setdefault("win_points", 1)
        DB["config"].setdefault("leave_points", 1)
        DB["config"].setdefault("empty_cell", "⠀")
        DB["config"].setdefault("leave_button", "خروج من الغرفة")
        DB["config"].setdefault("rules_text", "[[CE:6163305411521809988]] إنشاء غرفة\n[[CE:6163690420980159099]] إرسال الكود لصاحبك\n[[CE:6163281479964037804]] اللاعب الثاني يدخل بالكود\n[[CE:6163364742200038523]] العبوا مباشرة\n\n[[CE:5855177736082953485]] يبدأ أولًا\n[[CE:6163667408545386934]] ثانيًا")
        DB["config"].setdefault("room_text", "")
        DB.setdefault("users", {})
        DB.setdefault("rooms", {})
        save_db()


def tg(method, data=None):
    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        return {"ok": False, "description": "BOT_TOKEN is not configured"}
    try:
        body = urllib.parse.urlencode(data or {}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            data=body,
            headers={"User-Agent": "LEADER-XO/1.0"},
        )
        with urllib.request.urlopen(req, timeout=35) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        if hasattr(e, "read"):
            try:
                raw = e.read().decode("utf-8", errors="replace")
                try:
                    err = json.loads(raw)
                    desc = err.get("description", raw)
                except Exception:
                    desc = raw
                print(method, "ERROR:", desc)
                return {"ok": False, "description": desc}
            except Exception:
                pass
        print(method, "ERROR:", e)
        return {"ok": False, "description": str(e)}


EMOJI_RE = re.compile(
    r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF\u2300-\u23FF\u2B00-\u2BFF]"
)

def clean_bot_text(text):
    """Remove ordinary Unicode emoji from bot text."""
    if text is None:
        return ""
    return EMOJI_RE.sub("", str(text)).replace("  ", " ").strip()

def _utf16_len(text):
    return len(str(text).encode("utf-16-le")) // 2

CUSTOM_EMOJI_ALTS = {}
CUSTOM_EMOJI_LOADED = False


def load_custom_emoji_alts(ids):
    """Resolve each custom-emoji ID to its real Telegram alternative emoji.
    Telegram requires a custom_emoji entity to wrap exactly the emoji stored as
    the custom emoji's alternative text; using an arbitrary character such as ★
    can cause HTTP 400. The result is cached.
    """
    global CUSTOM_EMOJI_LOADED
    wanted = [str(x) for x in ids if x]
    missing = [x for x in wanted if x not in CUSTOM_EMOJI_ALTS]
    if not missing:
        return
    try:
        result = tg("getCustomEmojiStickers", {
            "custom_emoji_ids": json.dumps(missing, ensure_ascii=False)
        })
        if result.get("ok"):
            for sticker in result.get("result", []):
                sid = str(sticker.get("custom_emoji_id") or sticker.get("file_unique_id") or "")
                alt = sticker.get("emoji") or "🙂"
                if sid:
                    CUSTOM_EMOJI_ALTS[sid] = alt
    except Exception as e:
        print("custom emoji lookup error:", e)
    CUSTOM_EMOJI_LOADED = True


def premium_message_data(text):
    raw = str(text or "")
    pattern = re.compile(r"\[\[CE:([0-9]+)\]\]")
    ids = [m.group(1) for m in pattern.finditer(raw)]
    if not ids:
        ids = [str(GLOBAL_EMOJI)]
    load_custom_emoji_alts(ids)

    out = []
    entities = []
    offset16 = 0
    last = 0
    for m in pattern.finditer(raw):
        before = clean_bot_text(raw[last:m.start()])
        out.append(before)
        offset16 += _utf16_len(before)

        emoji_id = m.group(1)
        # IMPORTANT: Telegram requires the entity to wrap the emoji that is the
        # alternative text of that exact custom emoji.
        alt = CUSTOM_EMOJI_ALTS.get(emoji_id, "🙂")
        out.append(alt)
        entities.append({
            "type": "custom_emoji",
            "offset": offset16,
            "length": _utf16_len(alt),
            "custom_emoji_id": emoji_id,
        })
        offset16 += _utf16_len(alt)
        last = m.end()

    tail = clean_bot_text(raw[last:])
    out.append(tail)
    rendered = "".join(out).strip()

    if not entities:
        emoji_id = str(GLOBAL_EMOJI)
        alt = CUSTOM_EMOJI_ALTS.get(emoji_id, "🙂")
        rendered = alt + ((" " + rendered) if rendered else "")
        entities = [{
            "type": "custom_emoji",
            "offset": 0,
            "length": _utf16_len(alt),
            "custom_emoji_id": emoji_id,
        }]
    return rendered, entities

def _strip_custom_emoji_markers(text):
    return re.sub(r"\[\[CE:[0-9]+\]\]", '', str(text or ''))

def _plain_fallback_text(text):
    return clean_bot_text(_strip_custom_emoji_markers(text))

def _plain_markup(markup):
    if not markup: return markup
    copied=json.loads(json.dumps(markup,ensure_ascii=False))
    for row in copied.get('inline_keyboard',[]):
        for item in row: item.pop('icon_custom_emoji_id',None)
    return copied


def send(chat_id, text, markup=None):
    # Send Premium Custom Emoji as Telegram entities. Never expose [[CE:...]] markers.
    rendered, entities = premium_message_data(text)
    data = {
        "chat_id": chat_id,
        "text": rendered,
        "entities": json.dumps(entities, ensure_ascii=False, separators=(",", ":")),
        "disable_web_page_preview": "true",
    }
    if markup:
        data["reply_markup"] = json.dumps(markup, ensure_ascii=False, separators=(",", ":"))
    result = tg("sendMessage", data)
    if result.get("ok"):
        return result

    # A bad custom-emoji button must not break the whole message. Retry the same
    # message WITH its Custom Emoji entities but without button icon IDs.
    if markup:
        data["reply_markup"] = json.dumps(_plain_markup(markup), ensure_ascii=False, separators=(",", ":"))
        result2 = tg("sendMessage", data)
        if result2.get("ok"):
            return result2

    # Last-resort compatibility fallback: remove only the internal markers, not
    # the surrounding text. This prevents [[CE:...]] from ever reaching users.
    plain = _plain_fallback_text(text)
    data.pop("entities", None)
    data["text"] = plain or "LEADER XO"
    if markup:
        data["reply_markup"] = json.dumps(_plain_markup(markup), ensure_ascii=False, separators=(",", ":"))
    return tg("sendMessage", data)


def edit(chat_id, message_id, text, markup=None):
    rendered, entities = premium_message_data(text)
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": rendered,
        "entities": json.dumps(entities, ensure_ascii=False, separators=(",", ":")),
    }
    if markup:
        data["reply_markup"] = json.dumps(markup, ensure_ascii=False, separators=(",", ":"))
    result = tg("editMessageText", data)
    if result.get("ok"):
        return result

    if markup:
        data["reply_markup"] = json.dumps(_plain_markup(markup), ensure_ascii=False, separators=(",", ":"))
        result2 = tg("editMessageText", data)
        if result2.get("ok"):
            return result2

    plain = _plain_fallback_text(text)
    data.pop("entities", None)
    data["text"] = plain or "LEADER XO"
    if markup:
        data["reply_markup"] = json.dumps(_plain_markup(markup), ensure_ascii=False, separators=(",", ":"))
    return tg("editMessageText", data)

def answer_callback(query_id, text=""):
    # Callback queries can expire while the bot is reconnecting.
    # Never let an expired/invalid callback break the actual button action.
    try:
        result = tg("answerCallbackQuery", {"callback_query_id": query_id, "text": text})
        if not result.get("ok"):
            print("answerCallbackQuery ignored:", result.get("description", "unknown error"))
        return result
    except Exception as e:
        print("answerCallbackQuery ignored:", e)
        return {"ok": False, "description": str(e)}


def is_owner(uid):
    try:
        return OWNER_ID != 0 and int(uid) == OWNER_ID
    except Exception:
        return False


def upsert_user(user_id, name="Player", username=""):
    key = str(int(user_id))
    with LOCK:
        u = DB["users"].setdefault(key, {
            "id": int(user_id),
            "name": name or "Player",
            "username": username or "",
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "games": 0,
            "points": 0,
            "created": int(time.time()),
        })
        if name:
            u["name"] = name[:100]
        if username is not None:
            u["username"] = username[:100]
        save_db()
        return u


def custom_emoji_id(message):
    for key in ("entities", "caption_entities"):
        for ent in message.get(key, []) or []:
            if ent.get("type") == "custom_emoji" and ent.get("custom_emoji_id"):
                return str(ent["custom_emoji_id"])
    return None


def button(text, callback=None, url=None, icon=None, style="primary", copy_text=None):
    # Native Telegram inline button with Premium Custom Emoji icon.
    item = {"text": clean_bot_text(text)[:64], "icon_custom_emoji_id": str(icon or GLOBAL_EMOJI), "style": style}
    if callback:
        item["callback_data"] = callback
    elif url:
        item["url"] = url
    elif copy_text is not None:
        item["copy_text"] = {"text": str(copy_text)}
    return item


def channel_name_from_url(url):
    m = re.search(r"t\.me/([^/?#]+)", str(url or ""))
    return ("@" + m.group(1).lstrip("@")) if m else str(url or "")

def subscription_keyboard():
    rows=[]
    for url in DB["config"].get("required_channels", []):
        rows.append([button("الاشتراك في " + channel_name_from_url(url), url=url)])
    rows.append([button("تحقق من الاشتراك", "checksub")])
    return {"inline_keyboard": rows}

def subscription_text():
    return "[[CE:%s]] يجب الاشتراك في القنوات التالية أولًا:\n\n%s\n\nبعد الاشتراك اضغط تحقق من الاشتراك." % (GLOBAL_EMOJI, "\n".join(channel_name_from_url(x) for x in DB["config"].get("required_channels", [])))

def is_subscribed(uid):
    if not DB["config"].get("force_sub_enabled", True) or is_owner(uid): return True
    for url in DB["config"].get("required_channels", []):
        result=tg("getChatMember", {"chat_id": channel_name_from_url(url), "user_id": int(uid)})
        if not result.get("ok"): return False
        m=result.get("result") or {}; status=m.get("status", "")
        if status not in ("creator","administrator","member") and not (status=="restricted" and m.get("is_member")): return False
    return True

def require_subscription(uid, chat_id, edit_message=None):
    if is_subscribed(uid): return True
    if edit_message: edit(chat_id, edit_message, subscription_text(), subscription_keyboard())
    else: send(chat_id, subscription_text(), subscription_keyboard())
    return False

def game_config_keyboard():
    c=DB["config"]
    return {"inline_keyboard":[[button("نقاط الفوز: "+str(c.get("win_points",1)),"setwin"),button("نقاط الانسحاب: "+str(c.get("leave_points",1)),"setleave")],[button("اسم زر الخروج","setleavebtn"),button("الخانة الفارغة","setempty")],[button("الرئيسية","admin")]]}

def sub_config_keyboard():
    state="مفعّل" if DB["config"].get("force_sub_enabled",True) else "متوقف"
    return {"inline_keyboard":[[button("الإجباري: "+state,"togglesub")],[button("تغيير القنوات","setchannels")],[button("الرئيسية","admin")]]}

def main_keyboard(uid):
    c = DB["config"]["buttons"]
    e = DB["config"].get("button_emojis", {})
    rows = [
        [button(c["create"], "create", icon=e.get("create")), button(c["join"], "join", icon=e.get("join"))],
        [button(c["leaders"], "leaders", icon=e.get("leaders")), button(c["profile"], "profile", icon=e.get("profile"))],
        [button(c["rules"], "rules", icon=e.get("rules"))],
    ]
    if is_owner(uid):
        rows.append([button(c["admin"], "admin", icon=e.get("admin"))])
    return {"inline_keyboard": rows}


def admin_keyboard():
    return {"inline_keyboard": [
        [button("أسماء الأزرار", "names"), button("إيموجي الأزرار", "buttonemoji")],
        [button("Premium X", "xemoji"), button("Premium O", "oemoji")],
        [button("تعديل الرسائل", "messages"), button("إعداد الإذاعة", "broadcastcfg")],
        [button("إعدادات اللعب", "gamecfg"), button("الاشتراك الإجباري", "subcfg")],
        [button("الإحصائيات", "stats"), button("إعادة الإعدادات", "resetcfg")],
        [button("الرئيسية", "home")],
    ]}

def messages_admin_keyboard():
    return {"inline_keyboard": [
        [button("رسالة البداية", "editwelcome")],
        [button("طريقة اللعب", "editrules")],
        [button("رسالة الغرفة", "editroommsg")],
        [button("الرئيسية", "admin")],
    ]}


def room_keyboard(code):
    return {"inline_keyboard": [
        [button("X", "choose:X:" + code, icon=DB["config"].get("x_emoji", X_EMOJI), style="primary"),
         button("O", "choose:O:" + code, icon=DB["config"].get("o_emoji", O_EMOJI), style="danger")],
        [button("نسخ الكود", copy_text=code)]
    ]}


def xo_board_keyboard(room):
    code = room["code"]
    board = room.get("board", [""] * 9)
    rows = []
    for i in range(9):
        value = board[i]
        if value == "X":
            label, icon, style = "X", DB["config"].get("x_emoji", X_EMOJI), "primary"
        elif value == "O":
            label, icon, style = "O", DB["config"].get("o_emoji", O_EMOJI), "danger"
        else:
            label, icon, style = DB["config"].get("empty_cell", "⠀"), GLOBAL_EMOJI, "primary"
        if i % 3 == 0:
            rows.append([])
        rows[-1].append(button(label, "move:" + code + ":" + str(i), icon=icon, style=style))
    rows.append([button("نسخ الكود", copy_text=code), button(DB["config"].get("leave_button","خروج من الغرفة"),"leave:"+code,style="danger")])
    return {"inline_keyboard": rows}


def game_text(room):
    if room.get("status") == "waiting":
        choice = room.get("x_choice")
        return ("[[CE:%s]] غرفة XO\n\nالكود: %s\n%s\n\nأرسل الكود لصاحبك."
                % (GLOBAL_EMOJI, room["code"], "اختيارك: " + choice if choice else "اختر X أو O أولًا."))
    if room.get("status") == "playing":
        return ("[[CE:%s]] الجولة بدأت\n\nX: %s\nO: %s\n\nالدور: %s\n\n"
                "أول لاعب يضع 3 متتالية في صف أو عمود أو قطر يفوز."
                % (GLOBAL_EMOJI, room.get("x"), room.get("o"), room.get("turn")))
    winner = room.get("winner")
    return "[[CE:%s]] انتهت الجولة\n\n%s" % (
        GLOBAL_EMOJI, "تعادل." if winner == "DRAW" else "الفائز: " + str(winner)
    )


def generate_room_code():
    """Generate a fresh 6-character code that is not used by any room."""
    with LOCK:
        while True:
            code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            if code not in DB["rooms"]:
                return code


def new_room(user_id):
    with LOCK:
        code = generate_room_code()
        room = {
            "code": code,
            "x": int(user_id),
            "o": None,
            "x_choice": None,
            "board": [""] * 9,
            "turn": "X",
            "status": "waiting",
            "winner": None,
            "created": int(time.time()),
            "updated": int(time.time()),
        }
        DB["rooms"][code] = room
        save_db()
        return room


def refresh_room_code(old_code, user_id):
    """Replace the current room code with a brand-new unique code."""
    old_code = str(old_code or "").strip().upper()
    uid = int(user_id)
    with LOCK:
        room = DB["rooms"].get(old_code)
        if not room:
            return None, "الغرفة غير موجودة."
        if int(room.get("x", 0)) != uid:
            return None, "أنت لست صاحب الغرفة."
        new_code = generate_room_code()
        room = dict(room)
        room["code"] = new_code
        room["updated"] = int(time.time())
        DB["rooms"].pop(old_code, None)
        DB["rooms"][new_code] = room
        save_db()
        return room, "تم تغيير كود الغرفة."


def find_active_room(user_id):
    uid = int(user_id)
    with LOCK:
        for room in DB["rooms"].values():
            if room.get("status") in ("waiting", "playing") and (room.get("x") == uid or room.get("o") == uid):
                return room
    return None


def join_room(code, user_id):
    code = str(code or "").strip().upper()
    with LOCK:
        room = DB["rooms"].get(code)
        if not room:
            return None, "❌ كود الغرفة غير صحيح."
        if room.get("status") != "waiting":
            return None, "❌ الغرفة بدأت بالفعل أو انتهت."
        if int(room["x"]) == int(user_id):
            return None, "❌ أنت صاحب الغرفة."
        if find_active_room(user_id):
            return None, "❌ أنت داخل غرفة أخرى."
        if not room.get("x_choice"):
            return None, "❌ صاحب الغرفة يجب أن يختار X أو O أولًا."
        room["o"] = int(user_id)
        room["status"] = "playing"
        room["turn"] = room["x_choice"]
        room["updated"] = int(time.time())
        save_db()
        other = "O" if room["x_choice"] == "X" else "X"
        return room, "✅ دخلت الغرفة — أنت " + other + "."


def choose_symbol(code, user_id, symbol):
    code = str(code or "").strip().upper()
    symbol = str(symbol or "").upper()
    with LOCK:
        room = DB["rooms"].get(code)
        if not room or room.get("status") != "waiting":
            return None, "❌ الغرفة غير متاحة."
        if int(room.get("x", 0)) != int(user_id):
            return None, "❌ اختيار X أو O لصاحب الغرفة فقط."
        if symbol not in ("X", "O"):
            return None, "❌ اختيار غير صحيح."
        room["x_choice"] = symbol
        room["turn"] = symbol
        room["updated"] = int(time.time())
        save_db()
        return room, "تم اختيار " + symbol + ". أرسل الكود لصاحبك."


def winning_symbol(board):
    lines = (
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6),
    )
    for a, b, c in lines:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def make_move(code, user_id, position):
    code = str(code or "").strip().upper()
    uid = int(user_id)
    try:
        position = int(position)
    except Exception:
        return False, "❌ حركة غير صحيحة.", None
    with LOCK:
        room = DB["rooms"].get(code)
        if not room or room.get("status") != "playing":
            return False, "❌ الغرفة ليست في مباراة الآن.", room
        symbol = "X" if int(room["x"]) == uid else "O" if int(room["o"]) == uid else None
        if not symbol:
            return False, "❌ أنت لست لاعبًا في هذه الغرفة.", room
        if room.get("turn") != symbol:
            return False, "⏳ ليس دورك الآن.", room
        if position < 0 or position > 8 or room["board"][position]:
            return False, "❌ هذه الخانة محجوزة.", room
        room["board"][position] = symbol
        win = winning_symbol(room["board"])
        if win or all(room["board"]):
            room["winner"] = win or "DRAW"
            room["status"] = "finished"
            x = str(room["x"])
            o = str(room["o"])
            for key in (x, o):
                DB["users"].setdefault(key, {"id": int(key), "name": "Player", "wins": 0, "losses": 0, "draws": 0, "games": 0, "points": 0})
                DB["users"][key]["games"] = int(DB["users"][key].get("games", 0)) + 1
            if win == "X":
                DB["users"][x]["wins"] += 1
                DB["users"][x]["points"] = int(DB["users"][x].get("points",0)) + int(DB["config"].get("win_points",1))
                DB["users"][o]["losses"] += 1
            elif win == "O":
                DB["users"][o]["wins"] += 1
                DB["users"][o]["points"] = int(DB["users"][o].get("points",0)) + int(DB["config"].get("win_points",1))
                DB["users"][x]["losses"] += 1
            else:
                DB["users"][x]["draws"] += 1
                DB["users"][o]["draws"] += 1
        else:
            room["turn"] = "O" if symbol == "X" else "X"
        room["updated"] = int(time.time())
        save_db()
        return True, "OK", room


def leave_room(user_id):
    uid=int(user_id)
    with LOCK:
        room=find_active_room(uid)
        if not room:
            return None,None,"❌ أنت لست داخل غرفة."

        x_id = int(room.get("x", 0) or 0)
        o_raw = room.get("o")
        o_id = int(o_raw) if o_raw else None
        opponent = o_id if x_id == uid else (x_id if o_id == uid else None)

        # Finish the old room and explicitly detach both players from its
        # active state. This guarantees that the leaver can create/join a
        # brand-new room immediately, even if an old Telegram message remains.
        room["status"] = "finished"
        room["winner_user_id"] = opponent
        room["updated"] = int(time.time())
        room["left_user_id"] = uid
        room["x"] = None
        room["o"] = None

        if opponent:
            key=str(opponent)
            DB["users"].setdefault(key,{"id":opponent,"name":"Player","wins":0,"losses":0,"draws":0,"games":0,"points":0})
            DB["users"][key]["points"] = int(DB["users"][key].get("points",0)) + int(DB["config"].get("leave_points",1))

        save_db()
        return room,opponent,"تم الخروج من الغرفة."

def room_control_keyboard(room, uid):
    if room.get("status") in ("waiting","playing") and (int(room.get("x",0))==int(uid) or int(room.get("o") or 0)==int(uid)):
        return {"inline_keyboard":[[button(DB["config"].get("leave_button","خروج من الغرفة"),"leave:"+room["code"],style="danger")]]}
    return None

def leaderboard_data(limit=50):
    users = list(DB["users"].values())
    users.sort(key=lambda u: (int(u.get("points", 0)), int(u.get("wins", 0)), int(u.get("games", 0))), reverse=True)
    return users[:limit]


def leaderboard_text():
    rows = ["[[CE:%s]] المتصدرين — بالنقاط\n" % GLOBAL_EMOJI]
    medals = ["🥇", "🥈", "🥉"]
    data = leaderboard_data(20)
    if not data:
        return rows[0] + "لا توجد مباريات حتى الآن."
    for i, u in enumerate(data, 1):
        prefix = medals[i - 1] if i <= 3 else f"{i}."
        rows.append(f"{prefix} {u.get('name','Player')} — [[CE:{GLOBAL_EMOJI}]] {u.get('points',0)} نقطة | فوز: {u.get('wins',0)}")
    return "\n".join(rows)


def profile_text(uid):
    u = DB["users"].get(str(int(uid)))
    if not u:
        return "👤 لا توجد إحصائيات بعد."
    return (
        f"[[CE:{GLOBAL_EMOJI}]] {u.get('name','Player')}\n\n"
        f"[[CE:{GLOBAL_EMOJI}]] المباريات: {u.get('games',0)}\n"
        f"[[CE:{GLOBAL_EMOJI}]] النقاط: {u.get('points',0)}\n"
        f"[[CE:{GLOBAL_EMOJI}]] الفوز: {u.get('wins',0)}\n"
        f"[[CE:{GLOBAL_EMOJI}]] الخسارة: {u.get('losses',0)}\n"
        f"[[CE:{GLOBAL_EMOJI}]] التعادل: {u.get('draws',0)}"
    )


def room_text(room):
    if room.get("status") == "waiting":
        return (DB["config"].get("room_text") or f"[[CE:{GLOBAL_EMOJI}]] غرفة XO") + f"\n\nالكود: {room['code']}\n\nأرسل الكود لصاحبك، ثم يكتبه في المحادثة مباشرة للدخول."
    if room.get("status") == "playing":
        return (
            f"[[CE:{GLOBAL_EMOJI}]] الجولة بدأت\n\n"
            f"الكود: {room['code']}\n"
            f"X: {room['x']}\nO: {room['o']}\n\n"
            f"الدور: {room['turn']}"
        )
    result = "تعادل" if room.get("winner") == "DRAW" else f"الفائز: {room.get('winner')}"
    return f"[[CE:{GLOBAL_EMOJI}]] انتهت الجولة\n\n{result}"


def broadcast(text):
    url = DB["config"].get("broadcast_url", "")
    markup = None
    if url:
        markup = {"inline_keyboard": [[button(DB["config"].get("broadcast_button", "🔗 فتح الرابط"), url=url)]]}
    sent = 0
    for u in list(DB["users"].values()):
        try:
            result = send(u["id"], text, markup)
            if result.get("ok"):
                sent += 1
            time.sleep(0.04)
        except Exception:
            pass
    return sent


def process_admin_message(message):
    uid = message.get("from", {}).get("id")
    if not is_owner(uid):
        return False
    text = message.get("text", "")
    chat_id = message["chat"]["id"]
    mode = PENDING.get(uid)
    cid = custom_emoji_id(message)
    if mode in ("xemoji", "oemoji") and cid:
        DB["config"]["x_emoji" if mode == "xemoji" else "o_emoji"] = cid
        PENDING.pop(uid, None); save_db()
        send(chat_id, "✅ تم حفظ Premium Emoji تلقائيًا."); return True
    if mode == "buttonemoji":
        key = text.strip().split()[0].lower() if text.strip() else ""
        if cid and key in DB["config"]["buttons"]:
            DB["config"]["button_emojis"][key] = cid
            PENDING.pop(uid, None); save_db()
            send(chat_id, "✅ تم حفظ Premium Emoji للزر تلقائيًا."); return True
        send(chat_id, "اكتب مفتاح الزر ثم أرسل Premium Emoji معه، مثل: app + الإيموجي المميز."); return True
    if mode == "names":
        if "|" not in text:
            send(chat_id, "اكتب: المفتاح|الاسم\ncreate | join | leaders | profile | rules | admin | broadcast"); return True
        key, name = [x.strip() for x in text.split("|", 1)]
        if key not in DB["config"]["buttons"]:
            send(chat_id, "❌ المفتاح غير صحيح."); return True
        DB["config"]["buttons"][key] = name[:64]
        PENDING.pop(uid, None); save_db(); send(chat_id, "✅ تم تغيير اسم الزر."); return True
    if mode == "setwin":
        try: DB["config"]["win_points"]=max(0,int(text.strip())); PENDING.pop(uid,None); save_db(); send(chat_id,"تم حفظ نقاط الفوز.")
        except: send(chat_id,"أرسل رقمًا صحيحًا.")
        return True
    if mode == "setleave":
        try: DB["config"]["leave_points"]=max(0,int(text.strip())); PENDING.pop(uid,None); save_db(); send(chat_id,"تم حفظ نقاط الانسحاب.")
        except: send(chat_id,"أرسل رقمًا صحيحًا.")
        return True
    if mode == "setleavebtn": DB["config"]["leave_button"]=text.strip()[:64] or "خروج من الغرفة"; PENDING.pop(uid,None); save_db(); send(chat_id,"تم الحفظ."); return True
    if mode == "setempty": DB["config"]["empty_cell"]=text[:4] or "⠀"; PENDING.pop(uid,None); save_db(); send(chat_id,"تم الحفظ."); return True
    if mode == "setchannels":
        vals=[x.strip() for x in text.split("|") if x.strip()]
        if not vals: send(chat_id,"أرسل رابطًا واحدًا على الأقل."); return True
        DB["config"]["required_channels"]=vals; PENDING.pop(uid,None); save_db(); send(chat_id,"تم حفظ القنوات."); return True
    if mode == "broadcast_url":
        if not text.startswith(("http://", "https://", "tg://")):
            send(chat_id, "❌ أرسل رابطًا يبدأ بـ http:// أو https:// أو tg://"); return True
        DB["config"]["broadcast_url"] = text.strip(); PENDING.pop(uid, None); save_db(); send(chat_id, "✅ تم حفظ رابط الإذاعة."); return True
    if mode == "broadcast":
        PENDING.pop(uid, None); count = broadcast(text); send(chat_id, f"[[CE:{GLOBAL_EMOJI}]] تمت الإذاعة إلى {count} مستخدم."); return True
    if mode in ("editwelcome", "editrules", "editroommsg"):
        key = {"editwelcome":"welcome", "editrules":"rules_text", "editroommsg":"room_text"}[mode]
        DB["config"][key] = text
        PENDING.pop(uid, None); save_db(); send(chat_id, "تم حفظ التعديل."); return True
    return False


def handle_callback(query):
    uid = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    mid = query["message"]["message_id"]
    data = query.get("data", "")
    answer_callback(query["id"])
    if data == "checksub":
        if is_subscribed(uid): edit(chat_id,mid,DB["config"]["welcome"],main_keyboard(uid))
        else: answer_callback(query["id"],"لم يكتمل الاشتراك بعد."); edit(chat_id,mid,subscription_text(),subscription_keyboard())
        return
    if not require_subscription(uid,chat_id,mid): return
    if data == "home":
        edit(chat_id, mid, DB["config"]["welcome"], main_keyboard(uid)); return
    if data == "create":
        active=find_active_room(uid)
        if active:
            edit(chat_id,mid,"[[CE:%s]] أنت داخل غرفة أخرى.\n\nالكود: %s\nالطرف الآخر: %s" % (GLOBAL_EMOJI,active.get("code"),active.get("o") or "في انتظار لاعب"),room_control_keyboard(active,uid)); return
        room=new_room(uid)
        send(chat_id, game_text(room), room_keyboard(room["code"])); return
    if data == "join":
        active=find_active_room(uid)
        if active:
            send(chat_id,"[[CE:%s]] أنت داخل غرفة أخرى.\n\nالكود: %s\nالطرف الآخر: %s" % (GLOBAL_EMOJI,active.get("code"),active.get("o") or "في انتظار لاعب"),room_control_keyboard(active,uid)); return
        send(chat_id,"أرسل كود الغرفة فقط، مثل: ABC123. لا تحتاج إلى كتابة /room."); return
    if data == "leaders":
        edit(chat_id, mid, leaderboard_text(), {"inline_keyboard": [[button("⬅️ الرئيسية", "home")]]}); return
    if data == "profile":
        edit(chat_id, mid, profile_text(uid), {"inline_keyboard": [[button("⬅️ الرئيسية", "home")]]}); return
    if data == "rules":
        edit(chat_id, mid, DB["config"].get("rules_text", "[[CE:6163305411521809988]] إنشاء غرفة\n[[CE:6163690420980159099]] إرسال الكود لصاحبك\n[[CE:6163281479964037804]] اللاعب الثاني يدخل بالكود\n[[CE:6163364742200038523]] العبوا مباشرة\n\n[[CE:5855177736082953485]] يبدأ أولًا\n[[CE:6163667408545386934]] ثانيًا"), {"inline_keyboard": [[button("الرئيسية", "home")]]}); return
    if data == "admin" and is_owner(uid):
        edit(chat_id, mid, "⚙️ لوحة الإدارة\n\nPremium Emoji يتم التقاطه تلقائيًا من الرسالة — بدون كتابة ID.", admin_keyboard()); return
    if data.startswith("leave:"):
        code=data.split(":",1)[1].strip().upper(); room=DB["rooms"].get(code)
        if not room or room.get("status") not in ("waiting","playing"): answer_callback(query["id"],"الغرفة غير متاحة."); return
        if int(room.get("x",0))!=uid and int(room.get("o") or 0)!=uid: answer_callback(query["id"],"أنت لست داخل هذه الغرفة."); return
        room2,opponent,msg=leave_room(uid)
        # The old room is finished locally before any Telegram request is made.
        # So even if editMessageText fails because Telegram is temporarily
        # unreachable, the player is already free to create a new room.
        edit(chat_id,mid,"[[CE:%s]] %s\n\nيمكنك إنشاء غرفة جديدة الآن." % (GLOBAL_EMOJI,msg),{"inline_keyboard":[[button("إنشاء غرفة جديدة","create")],[button("الرئيسية","home")]]})
        if opponent:
            send(opponent,"[[CE:%s]] انسحب اللاعب الآخر من الغرفة.\nلقد حصلت على %s نقطة." % (GLOBAL_EMOJI,DB["config"].get("leave_points",1)),{"inline_keyboard":[[button("إنشاء غرفة جديدة","create")],[button("الرئيسية","home")]]})
        return

    if data.startswith("choose:"):
        parts = data.split(":")
        if len(parts) == 3:
            room, msg = choose_symbol(parts[2], uid, parts[1])
            if room:
                edit(chat_id, mid, game_text(room), room_keyboard(room["code"]))
            else:
                answer_callback(query["id"], msg)
        return

    if data.startswith("move:"):
        parts = data.split(":")
        if len(parts) == 3:
            ok, msg, room = make_move(parts[1], uid, parts[2])
            if room:
                if room.get("status") == "playing":
                    edit(chat_id, mid, game_text(room), xo_board_keyboard(room))
                else:
                    edit(chat_id, mid, game_text(room), {"inline_keyboard": [
                        [button("نسخ الكود", copy_text=room["code"])],
                        [button("الرئيسية", "home")]
                    ]})
            elif not ok:
                answer_callback(query["id"], msg)
        return

    if not is_owner(uid): return
    if data == "gamecfg": edit(chat_id,mid,"إعدادات اللعب\n\nالنقاط والزر والخانات قابلة للتعديل.",game_config_keyboard()); return
    if data == "subcfg": edit(chat_id,mid,"الاشتراك الإجباري\n\n"+"\n".join(DB["config"].get("required_channels",[])),sub_config_keyboard()); return
    if data == "togglesub": DB["config"]["force_sub_enabled"]=not DB["config"].get("force_sub_enabled",True); save_db(); edit(chat_id,mid,"تم تغيير حالة الاشتراك الإجباري.",sub_config_keyboard()); return
    if data == "setwin": PENDING[uid]="setwin"; send(chat_id,"أرسل عدد نقاط الفوز."); return
    if data == "setleave": PENDING[uid]="setleave"; send(chat_id,"أرسل عدد نقاط الانسحاب."); return
    if data == "setleavebtn": PENDING[uid]="setleavebtn"; send(chat_id,"أرسل اسم زر الخروج."); return
    if data == "setempty": PENDING[uid]="setempty"; send(chat_id,"أرسل الرمز الذي سيظهر للخانة الفارغة."); return
    if data == "setchannels": PENDING[uid]="setchannels"; send(chat_id,"أرسل الروابط مفصولة بـ |."); return
    if data == "xemoji": PENDING[uid] = "xemoji"; send(chat_id, "❌ أرسل Premium Emoji الذي تريد استخدامه لـ X."); return
    if data == "oemoji": PENDING[uid] = "oemoji"; send(chat_id, "⭕ أرسل Premium Emoji الذي تريد استخدامه لـ O."); return
    if data == "names": PENDING[uid] = "names"; send(chat_id, "✏️ اكتب: المفتاح|اسم الزر"); return
    if data == "buttonemoji": PENDING[uid] = "buttonemoji"; send(chat_id, "✨ اكتب مفتاح الزر وأرفق معه Premium Emoji؛ سألتقط الـID تلقائيًا."); return
    if data == "broadcastcfg": send(chat_id, "الإذاعة\n\n/broadcast_url ثم أرسل الرابط\n/broadcast ثم أرسل نص الإذاعة\n\nالزر رابط حقيقي ويدعم Telegram والروابط الخارجية."); return
    if data == "messages": edit(chat_id, mid, "تحكم الرسائل", messages_admin_keyboard()); return
    if data == "editwelcome": PENDING[uid] = "editwelcome"; send(chat_id, "أرسل رسالة البداية الجديدة."); return
    if data == "editrules": PENDING[uid] = "editrules"; send(chat_id, "أرسل طريقة اللعب الجديدة. يمكنك استخدام [[CE:رقم_الإيموجي]] للإيموجي المميز."); return
    if data == "editroommsg": PENDING[uid] = "editroommsg"; send(chat_id, "أرسل رسالة الغرفة الجديدة. يمكنك استخدام [[CE:رقم_الإيموجي]]."); return
    if data == "resetcfg":
        DB["config"] = clone_default();
        for k in DB["config"]["buttons"]: DB["config"]["button_emojis"][k] = GLOBAL_EMOJI
        save_db(); edit(chat_id, mid, "تمت إعادة إعدادات البوت الأساسية.", admin_keyboard()); return
    if data == "stats": send(chat_id, f"[[CE:{GLOBAL_EMOJI}]] المستخدمون: {len(DB['users'])}\n[[CE:{GLOBAL_EMOJI}]] الغرف: {len(DB['rooms'])}"); return
    if data.startswith("refresh:"):
        code = data.split(":", 1)[1].strip().upper()
        room, msg = refresh_room_code(code, uid)
        if room:
            markup = xo_board_keyboard(room) if room.get("status") == "playing" else room_keyboard(room["code"])
            edit(chat_id, mid, game_text(room), markup)
        else:
            answer_callback(query["id"], msg)


def handle_command(message):
    text = message.get("text", "")
    uid = message["from"]["id"]
    chat_id = message["chat"]["id"]
    upsert_user(uid, message["from"].get("first_name") or "Player", message["from"].get("username") or "")
    if text.startswith("/start") or text.startswith("/استارت"):
        if not require_subscription(uid,chat_id): return True
        send(chat_id,DB["config"]["welcome"],main_keyboard(uid)); return True
    if not require_subscription(uid,chat_id): return True
    if text.startswith("/room "):
        active=find_active_room(uid)
        if active:
            send(chat_id,"[[CE:%s]] أنت داخل غرفة أخرى.\n\nالكود: %s\nالطرف الآخر: %s" % (GLOBAL_EMOJI,active.get("code"),active.get("o") or "في انتظار لاعب"),room_control_keyboard(active,uid)); return True
        room,msg=join_room(text.split(None,1)[1],uid)
        send(chat_id, msg)
        if room: send(chat_id, game_text(room), xo_board_keyboard(room))
        return True
    if (text == "/panel" or text == "/لوحة الادمن") and is_owner(uid):
        send(chat_id, "لوحة الإدارة", admin_keyboard()); return True
    if text == "/broadcast_url" and is_owner(uid):
        PENDING[uid] = "broadcast_url"; send(chat_id, "🔗 أرسل الرابط الآن."); return True
    if text == "/broadcast" and is_owner(uid):
        PENDING[uid] = "broadcast"; send(chat_id, "أرسل نص الإذاعة الآن."); return True
    # Joining a room requires only the code; no /room command is needed.
    code = re.sub(r"[^A-Z0-9]", "", text.strip().upper())
    if re.fullmatch(r"[A-Z0-9]{6}", code) and code in DB["rooms"]:
        active=find_active_room(uid)
        if active:
            send(chat_id,"[[CE:%s]] أنت داخل غرفة أخرى.\n\nالكود: %s\nالطرف الآخر: %s" % (GLOBAL_EMOJI,active.get("code"),active.get("o") or "في انتظار لاعب"),room_control_keyboard(active,uid)); return True
        room,msg=join_room(code,uid)
        send(chat_id, msg)
        if room:
            send(chat_id, game_text(room), xo_board_keyboard(room))
            # Notify the room creator that the second player joined.
            if int(room.get("x", 0)) != uid:
                send(room["x"], game_text(room), xo_board_keyboard(room))
        return True
    return False


def bot_loop():
    offset = 0
    while True:
        result = tg("getUpdates", {
            "offset": offset,
            "timeout": 25,
            "allowed_updates": json.dumps(["message", "callback_query"]),
        })
        if not result.get("ok"):
            time.sleep(3); continue
        for update in result.get("result", []):
            offset = update["update_id"] + 1
            try:
                if "callback_query" in update:
                    handle_callback(update["callback_query"]); continue
                message = update.get("message")
                if not message: continue
                upsert_user(message["from"]["id"], message["from"].get("first_name") or "Player", message["from"].get("username") or "")
                if process_admin_message(message): continue
                if handle_command(message): continue
                cid = custom_emoji_id(message)
                if cid and is_owner(message["from"]["id"]):
                    send(message["chat"]["id"], f"✨ Premium Emoji ID detected automatically.\n{cid}")
            except Exception as e:
                print("update error:", e)


def main():
    load_db()
    if BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        print("BOT_TOKEN is not configured.")
        return
    bot_loop()


if __name__ == "__main__":
    main()
