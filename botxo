# -*- coding: utf-8 -*-
"""
LEADER XO — Telegram Mini App Edition
Single-file / Python standard library only.

Required:
  BOT_TOKEN = Telegram bot token
  OWNER_ID  = Telegram numeric owner ID
  PUBLIC_URL = public HTTPS URL of this same server, e.g. https://your-app.up.railway.app

Optional:
  PORT=8080
  DEV_MODE=0  # set to 1 only for browser testing outside Telegram

The Mini App uses Telegram WebApp initData and validates it server-side.
"""
import os
import re
import json
import time
import hmac
import hashlib
import html
import secrets
import string
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BOT_TOKEN = os.getenv("BOT_TOKEN", "8830531937:AAE12BSnfpPRu5uwxODmVmi7oYbBoWQk4oI").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "8037399518"))
PORT = int(os.getenv("PORT", "8080"))
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
DEV_MODE = os.getenv("DEV_MODE", "0") == "1"
DB_FILE = os.getenv("DB_FILE", "leader_xo_db.json")

GLOBAL_EMOJI = "5359719332542718652"
X_EMOJI = "5855177736082953485"
O_EMOJI = "6163667408545386934"

DEFAULT_CONFIG = {
    "welcome": "LEADER XO\n\nXO رايقة داخل Telegram.\nاعمل غرفة، خذ الكود، وابعتُه لصاحبك.",
    "buttons": {
        "app": "فتح XO",
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
        print(method, "ERROR:", e)
        return {"ok": False, "description": str(e)}


EMOJI_RE = re.compile(
    r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF\u2300-\u23FF\u2B00-\u2BFF]"
)

def clean_bot_text(text):
    """Remove ordinary Unicode emoji so only the configured Premium Emoji is shown."""
    if text is None:
        return ""
    return EMOJI_RE.sub("", str(text)).replace("  ", " ").strip()

def premium_message_data(text):
    """Render the global Premium Emoji as a real custom-emoji entity."""
    clean = clean_bot_text(text)
    marker = "★"
    rendered = marker + " " + clean
    return rendered, [{"type": "custom_emoji", "offset": 0, "length": 1, "custom_emoji_id": str(GLOBAL_EMOJI)}]

def send(chat_id, text, markup=None):
    rendered, entities = premium_message_data(text)
    data = {
        "chat_id": chat_id,
        "text": rendered,
        "entities": json.dumps(entities, ensure_ascii=False),
        "disable_web_page_preview": "true",
    }
    if markup:
        data["reply_markup"] = json.dumps(markup, ensure_ascii=False)
    result = tg("sendMessage", data)
    # If custom emoji is unavailable for this bot/account, retry without any ordinary emoji.
    if not result.get("ok"):
        data.pop("entities", None)
        data["text"] = clean_bot_text(text)
        return tg("sendMessage", data)
    return result

def edit(chat_id, message_id, text, markup=None):
    rendered, entities = premium_message_data(text)
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": rendered,
        "entities": json.dumps(entities, ensure_ascii=False),
    }
    if markup:
        data["reply_markup"] = json.dumps(markup, ensure_ascii=False)
    result = tg("editMessageText", data)
    if not result.get("ok"):
        data.pop("entities", None)
        data["text"] = clean_bot_text(text)
        return tg("editMessageText", data)
    return result


def answer_callback(query_id, text=""):
    return tg("answerCallbackQuery", {"callback_query_id": query_id, "text": text})


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


def button(text, callback=None, url=None, web_app=None, icon=None, style="primary"):
    # Telegram Bot API 9.4+: custom emoji icon + native button color style.
    item = {"text": clean_bot_text(text)[:64], "icon_custom_emoji_id": str(icon or GLOBAL_EMOJI), "style": style}
    if callback:
        item["callback_data"] = callback
    elif url:
        item["url"] = url
    elif web_app:
        item["web_app"] = {"url": web_app}
    return item


def app_url(extra=""):
    if not PUBLIC_URL:
        return ""
    return PUBLIC_URL + extra


def main_keyboard(uid):
    c = DB["config"]["buttons"]
    e = DB["config"].get("button_emojis", {})
    rows = [
        [button(c["app"], web_app=app_url(), icon=e.get("app"))],
        [button(c["create"], "create", icon=e.get("create")), button(c["join"], "join", icon=e.get("join"))],
        [button(c["leaders"], "leaders", icon=e.get("leaders")), button(c["profile"], "profile", icon=e.get("profile"))],
        [button(c["rules"], "rules", icon=e.get("rules"))],
    ]
    if is_owner(uid):
        rows.append([button(c["admin"], "admin", icon=e.get("admin"))])
    return {"inline_keyboard": rows}


def admin_keyboard():
    return {"inline_keyboard": [
        [button("✏️ أسماء الأزرار", "names"), button("✨ إيموجي الأزرار", "buttonemoji")],
        [button("❌ Premium X", "xemoji"), button("⭕ Premium O", "oemoji")],
        [button("📢 إعداد الإذاعة", "broadcastcfg")],
        [button("📊 الإحصائيات", "stats")],
        [button("⬅️ الرئيسية", "home")],
    ]}


def room_keyboard(code):
    rows = []
    if PUBLIC_URL:
        rows.append([button("🎮 افتح الجولة", web_app=app_url("?room=" + urllib.parse.quote(code)))])
    rows.append([button("🔄 تحديث", "refresh:" + code)])
    return {"inline_keyboard": rows}


def new_room(user_id):
    with LOCK:
        while True:
            code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            if code not in DB["rooms"]:
                break
        room = {
            "code": code,
            "x": int(user_id),
            "o": None,
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
        room["o"] = int(user_id)
        room["status"] = "playing"
        room["updated"] = int(time.time())
        save_db()
        return room, "✅ دخلت الغرفة — أنت O."


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
                DB["users"].setdefault(key, {"id": int(key), "name": "Player", "wins": 0, "losses": 0, "draws": 0, "games": 0})
                DB["users"][key]["games"] = int(DB["users"][key].get("games", 0)) + 1
            if win == "X":
                DB["users"][x]["wins"] += 1
                DB["users"][o]["losses"] += 1
            elif win == "O":
                DB["users"][o]["wins"] += 1
                DB["users"][x]["losses"] += 1
            else:
                DB["users"][x]["draws"] += 1
                DB["users"][o]["draws"] += 1
        else:
            room["turn"] = "O" if symbol == "X" else "X"
        room["updated"] = int(time.time())
        save_db()
        return True, "OK", room


def leaderboard_data(limit=50):
    users = list(DB["users"].values())
    users.sort(key=lambda u: (int(u.get("wins", 0)), int(u.get("games", 0))), reverse=True)
    return users[:limit]


def leaderboard_text():
    rows = ["🏆 المتصدرين — الأكثر فوزًا\n"]
    medals = ["🥇", "🥈", "🥉"]
    data = leaderboard_data(20)
    if not data:
        return rows[0] + "لا توجد مباريات حتى الآن."
    for i, u in enumerate(data, 1):
        prefix = medals[i - 1] if i <= 3 else f"{i}."
        rows.append(f"{prefix} {u.get('name','Player')} — 🏆 {u.get('wins',0)} | 🎮 {u.get('games',0)}")
    return "\n".join(rows)


def profile_text(uid):
    u = DB["users"].get(str(int(uid)))
    if not u:
        return "👤 لا توجد إحصائيات بعد."
    return (
        f"👤 {u.get('name','Player')}\n\n"
        f"🎮 المباريات: {u.get('games',0)}\n"
        f"🏆 الفوز: {u.get('wins',0)}\n"
        f"❌ الخسارة: {u.get('losses',0)}\n"
        f"🤝 التعادل: {u.get('draws',0)}"
    )


def room_text(room):
    if room.get("status") == "waiting":
        return f"🎮 غرفة XO\n\n🔐 الكود: {room['code']}\n\nابعت الكود لصاحبك، ثم افتح التطبيق."
    if room.get("status") == "playing":
        return (
            f"🎮 الجولة بدأت!\n\n🔐 {room['code']}\n"
            f"❌ X: {room['x']}\n⭕ O: {room['o']}\n\n🎯 الدور: {room['turn']}"
        )
    result = "🤝 تعادل!" if room.get("winner") == "DRAW" else f"🏆 الفائز: {room.get('winner')}"
    return f"🎮 انتهت الجولة\n\n{result}"


def validate_init_data(init_data):
    """Validate Telegram WebApp initData using Telegram's HMAC scheme."""
    if not init_data or not BOT_TOKEN:
        return None
    try:
        parsed = urllib.parse.parse_qs(init_data, strict_parsing=True)
        received_hash = parsed.get("hash", [""])[0]
        if not received_hash:
            return None
        pairs = []
        for key in sorted(parsed):
            if key == "hash":
                continue
            pairs.append(f"{key}={parsed[key][0]}")
        data_check_string = "\n".join(pairs)
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated, received_hash):
            return None
        auth_date = int(parsed.get("auth_date", ["0"])[0])
        if auth_date <= 0 or time.time() - auth_date > 86400:
            return None
        user_raw = parsed.get("user", [""])[0]
        user = json.loads(user_raw) if user_raw else None
        if not isinstance(user, dict) or not user.get("id"):
            return None
        return user
    except Exception:
        return None


def json_response(handler, payload, status=200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler):
    try:
        n = int(handler.headers.get("Content-Length", "0"))
        if n > 100000:
            return None
        return json.loads(handler.rfile.read(n) or b"{}")
    except Exception:
        return None


def api_user(handler, body=None):
    init_data = handler.headers.get("X-Telegram-Init-Data", "")
    user = validate_init_data(init_data)
    if user:
        upsert_user(user["id"], user.get("first_name") or "Player", user.get("username") or "")
        return user
    if DEV_MODE:
        raw = (body or {}).get("user_id") or urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query).get("user_id", [0])[0]
        try:
            uid = int(raw)
            if uid:
                return {"id": uid, "first_name": "Player", "username": ""}
        except Exception:
            pass
    return None


HTML = r'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
<meta name="theme-color" content="#07111f">
<title>LEADER XO</title>
<style>
:root{--bg:#06101d;--card:#0c1b2c;--card2:#10243a;--line:#1e3b55;--text:#f4f8fc;--muted:#91abc1;--blue:#229ed9;--x:#3aa9ff;--o:#ff4f61;--ok:#36d399}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}body{margin:0;min-height:100vh;background:radial-gradient(circle at 50% -10%,#163b5d 0,#09182a 34%,#040b14 78%);color:var(--text);font-family:Arial,"Noto Sans Arabic",sans-serif}.wrap{max-width:560px;margin:auto;padding:18px 14px 30px}.card{background:rgba(12,27,44,.94);border:1px solid rgba(58,115,153,.35);border-radius:28px;padding:18px;box-shadow:0 25px 80px rgba(0,0,0,.45);backdrop-filter:blur(16px)}.brand{text-align:center;font-size:29px;font-weight:900;letter-spacing:.3px}.sub{text-align:center;color:var(--muted);font-size:14px;margin:7px 0 20px}.pill{display:inline-flex;gap:7px;align-items:center;background:#102941;border:1px solid #1e4766;border-radius:999px;padding:8px 12px;color:#b8d5e9;font-size:13px}.row{display:flex;gap:9px}.row>*{flex:1}.btn{width:100%;border:0;border-radius:17px;padding:15px 13px;margin-top:10px;background:linear-gradient(180deg,#2aa7e0,#1689c0);color:#fff;font-size:16px;font-weight:800;box-shadow:0 9px 24px rgba(22,137,192,.22);cursor:pointer}.btn.alt{background:#122a41;border:1px solid #21445f;box-shadow:none}.btn.danger{background:#52222b}.input{width:100%;border:1px solid #23465f;background:#0a1727;color:#fff;border-radius:16px;padding:15px;margin-top:10px;font-size:17px;outline:none}.screen{display:none}.screen.active{display:block}.status{text-align:center;color:#bad1e3;min-height:25px;margin:13px 0}.code{font-size:32px;font-weight:900;text-align:center;letter-spacing:5px;color:#fff;background:#102942;border:1px dashed #2d668c;border-radius:18px;padding:14px;margin:12px 0}.board{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0}.cell{aspect-ratio:1;border-radius:21px;border:1px solid #25475f;background:linear-gradient(145deg,#102840,#0b1b2c);display:flex;align-items:center;justify-content:center;font-size:58px;font-weight:1000;cursor:pointer;box-shadow:inset 0 1px rgba(255,255,255,.03)}.cell.x{color:var(--x);text-shadow:0 0 28px rgba(58,169,255,.35)}.cell.o{color:var(--o);text-shadow:0 0 28px rgba(255,79,97,.28)}.cell:active{transform:scale(.96)}.turn{padding:12px;text-align:center;border-radius:15px;background:#0b1a2a;color:#bcd6e8}.turn.x{color:var(--x)}.turn.o{color:var(--o)}.leader{display:flex;align-items:center;justify-content:space-between;padding:13px 4px;border-bottom:1px solid #1a3348}.leader:last-child{border-bottom:0}.rank{font-size:14px;color:var(--muted)}.name{font-weight:900}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.stat{background:#0b1a2a;border:1px solid #1a374e;border-radius:15px;padding:12px 5px;text-align:center}.stat b{display:block;font-size:20px}.stat span{color:var(--muted);font-size:11px}.small{color:var(--muted);font-size:12px;text-align:center;line-height:1.7;margin-top:14px}.toast{position:fixed;left:14px;right:14px;bottom:18px;max-width:520px;margin:auto;background:#10273b;border:1px solid #2a5875;padding:13px 15px;border-radius:16px;text-align:center;display:none;z-index:20}.footer{text-align:center;color:#6f8ba1;font-size:11px;margin-top:16px}
</style>
</head>
<body>
<div class="wrap"><div class="card">
<div class="brand"> LEADER XO</div>
<div class="sub">لعبة XO رايقة • غرف خاصة • لعب مباشر</div>

<section id="home" class="screen active">
  <div style="text-align:center"><span class="pill"> Telegram Mini App</span></div>
  <button class="btn" onclick="createRoom()"> إنشاء غرفة</button>
  <input id="roomCode" class="input" maxlength="6" placeholder="اكتب كود الغرفة" autocomplete="off" style="text-transform:uppercase">
  <button class="btn alt" onclick="joinRoom()"> دخول غرفة</button>
  <button class="btn alt" onclick="showLeaderboard()"> المتصدرين</button>
  <button class="btn alt" onclick="showProfile()"> إحصائياتي</button>
  <div id="homeStatus" class="status">أنشئ غرفة أو ادخل كود غرفة.</div>
  <div class="small">X يبدأ أولًا • الفائز يحصل على نقطة فوز • النتائج محفوظة</div>
</section>

<section id="room" class="screen">
  <div id="roomStatus" class="status"></div>
  <div id="roomCodeView" class="code"></div>
  <div id="players"></div>
  <button class="btn" onclick="copyCode()"> نسخ الكود</button>
  <button class="btn alt" onclick="backHome()"> الرئيسية</button>
</section>

<section id="game" class="screen">
  <div id="gameStatus" class="turn"></div>
  <div class="board" id="board"></div>
  <button class="btn alt" onclick="backHome()"> الرئيسية</button>
</section>

<section id="leaders" class="screen">
  <h2 style="margin:5px 0 15px"> المتصدرين</h2>
  <div id="leadersList"></div>
  <button class="btn alt" onclick="backHome()"> الرئيسية</button>
</section>

<section id="profile" class="screen">
  <h2 style="margin:5px 0 15px"> إحصائياتي</h2>
  <div id="profileBox"></div>
  <button class="btn alt" onclick="backHome()"> الرئيسية</button>
</section>

<div class="footer">LEADER XO • Telegram Mini App</div>
</div></div><div id="toast" class="toast"></div>
<script>
const TG = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
if(TG){TG.ready();TG.expand();}
let current=null, poll=null, busy=false;
const initData = TG ? TG.initData : '';
function headers(){return {'Content-Type':'application/json','X-Telegram-Init-Data':initData};}
async function api(path, body=null){
  const opt={method:body?'POST':'GET',headers:headers()};
  if(body)opt.body=JSON.stringify(body);
  const r=await fetch(path,opt); return await r.json();
}
function toast(t){const e=document.getElementById('toast');e.textContent=t;e.style.display='block';setTimeout(()=>e.style.display='none',2200)}
function screen(id){document.querySelectorAll('.screen').forEach(x=>x.classList.remove('active'));document.getElementById(id).classList.add('active')}
function meId(){return TG&&TG.initDataUnsafe&&TG.initDataUnsafe.user?TG.initDataUnsafe.user.id:null}
async function createRoom(){
  if(busy)return;busy=true;
  const j=await api('/api/create',{});busy=false;
  if(!j.ok){toast(j.error||'حدث خطأ');return} current=j.room; renderRoom();
}
async function joinRoom(){
  if(busy)return; const code=document.getElementById('roomCode').value.trim().toUpperCase();
  if(code.length!==6){toast('اكتب كود من 6 خانات');return} busy=true;
  const j=await api('/api/join',{code});busy=false;
  if(!j.ok){toast(j.error||'الكود غير صحيح');return} current=j.room; renderRoom();
}
function renderRoom(){
  screen(current.status==='playing'||current.status==='finished'?'game':'room');
  if(current.status==='waiting'){
    document.getElementById('roomCodeView').textContent=current.code;
    document.getElementById('roomStatus').textContent=' في انتظار اللاعب الثاني...';
    document.getElementById('players').innerHTML='<div class="small">أرسل الكود لصاحبك، ثم انتظر دخوله.</div>';
  }else renderGame();
  startPoll();
}
function renderGame(){
  screen('game');
  const me=meId(); const sym=me===current.x?'X':me===current.o?'O':'';
  let text='';
  if(current.status==='finished') text=current.winner==='DRAW'?' تعادل!':' الفائز: '+current.winner;
  else text='دور '+current.turn+(current.turn===sym?' — دورك':' — انتظر');
  const gs=document.getElementById('gameStatus');gs.textContent=text;gs.className='turn '+(current.turn==='X'?'x':'o');
  const b=document.getElementById('board');b.innerHTML='';
  current.board.forEach((v,i)=>{const c=document.createElement('div');c.className='cell '+(v==='X'?'x':v==='O'?'o':'');c.textContent=v;c.onclick=()=>play(i);b.appendChild(c)});
}
async function play(pos){
  if(busy||!current||current.status!=='playing')return; busy=true;
  const j=await api('/api/move',{code:current.code,position:pos});busy=false;
  if(!j.ok){toast(j.error||'الحركة غير متاحة');return} current=j.room;renderGame();
}
function startPoll(){clearInterval(poll);poll=setInterval(async()=>{
  if(!current||busy)return; const j=await api('/api/room?code='+encodeURIComponent(current.code));
  if(j.ok){current=j.room; if(current.status==='playing'||current.status==='finished')renderGame();else renderRoom();}
},900)}
async function showLeaderboard(){screen('leaders');const j=await api('/api/leaderboard');const box=document.getElementById('leadersList');box.innerHTML='';(j.users||[]).forEach((u,i)=>{box.innerHTML+=`<div class="leader"><div><span class="rank">#${i+1}</span> <span class="name">${escapeHtml(u.name||'Player')}</span></div><div> ${u.wins||0}</div></div>`});if(!box.innerHTML)box.innerHTML='<div class="small">لا توجد مباريات بعد.</div>'}
async function showProfile(){screen('profile');const j=await api('/api/profile');const u=j.user;if(!j.ok){toast(j.error||'خطأ');return}document.getElementById('profileBox').innerHTML=`<h3 style="margin-top:0">${escapeHtml(u.name||'Player')}</h3><div class="stats"><div class="stat"><b>${u.games||0}</b><span>مباريات</span></div><div class="stat"><b>${u.wins||0}</b><span>فوز</span></div><div class="stat"><b>${u.losses||0}</b><span>خسارة</span></div><div class="stat"><b>${u.draws||0}</b><span>تعادل</span></div></div>`}
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function backHome(){clearInterval(poll);current=null;screen('home')}
async function copyCode(){try{await navigator.clipboard.writeText(current.code);toast(' تم نسخ الكود')}catch(e){toast('الكود: '+current.code)}}
const qs=new URLSearchParams(location.search);const initialRoom=qs.get('room');
(async()=>{
  if(!TG||!TG.initData){
    document.getElementById('homeStatus').textContent=' افتح اللعبة من داخل Telegram.';
    if(location.hostname!=='localhost'&&location.hostname!=='127.0.0.1'){
      document.querySelectorAll('.btn').forEach(x=>x.disabled=true);
    }
    return;
  }
  if(initialRoom){document.getElementById('roomCode').value=initialRoom.toUpperCase();await joinRoom();}
})();
</script>
</body></html>'''


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)
        if parsed.path in ("/", "/index.html"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/health":
            json_response(self, {"ok": True, "service": "LEADER XO", "time": int(time.time())})
            return
        if parsed.path == "/api/room":
            user = api_user(self)
            if not user:
                json_response(self, {"ok": False, "error": "Telegram authorization required."}, 401); return
            code = q.get("code", [""])[0].upper()
            room = DB["rooms"].get(code)
            if not room:
                json_response(self, {"ok": False, "error": "ROOM_NOT_FOUND"}, 404); return
            if int(user["id"]) not in (int(room["x"]), int(room.get("o") or 0)):
                json_response(self, {"ok": False, "error": "NOT_A_PLAYER"}, 403); return
            json_response(self, {"ok": True, "room": room}); return
        if parsed.path == "/api/leaderboard":
            json_response(self, {"ok": True, "users": leaderboard_data(50)}); return
        if parsed.path == "/api/profile":
            user = api_user(self)
            if not user:
                json_response(self, {"ok": False, "error": "Telegram authorization required."}, 401); return
            u = upsert_user(user["id"], user.get("first_name") or "Player", user.get("username") or "")
            json_response(self, {"ok": True, "user": u}); return
        json_response(self, {"ok": False, "error": "NOT_FOUND"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        body = read_json(self)
        if body is None:
            json_response(self, {"ok": False, "error": "BAD_JSON"}, 400); return
        user = api_user(self, body)
        if not user:
            json_response(self, {"ok": False, "error": "افتح Mini App من داخل Telegram."}, 401); return
        uid = int(user["id"])
        if parsed.path == "/api/create":
            room = find_active_room(uid)
            if not room:
                room = new_room(uid)
            json_response(self, {"ok": True, "room": room}); return
        if parsed.path == "/api/join":
            room, msg = join_room(body.get("code", ""), uid)
            if not room:
                json_response(self, {"ok": False, "error": msg}, 400); return
            json_response(self, {"ok": True, "room": room}); return
        if parsed.path == "/api/move":
            ok, msg, room = make_move(body.get("code", ""), uid, body.get("position", -1))
            json_response(self, {"ok": ok, "error": None if ok else msg, "room": room}, 200 if ok else 400); return
        json_response(self, {"ok": False, "error": "NOT_FOUND"}, 404)


def configure_bot_menu():
    if not PUBLIC_URL:
        print("PUBLIC_URL is empty — Mini App button/menu cannot be configured.")
        return
    result = tg("setChatMenuButton", {
        "menu_button": json.dumps({
            "type": "web_app",
            "text": "XO",
            "web_app": {"url": PUBLIC_URL},
        }, ensure_ascii=False)
    })
    print("setChatMenuButton:", result.get("ok"), result.get("description", ""))


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
            send(chat_id, "اكتب: المفتاح|الاسم\napp | create | join | leaders | profile | rules | admin | broadcast"); return True
        key, name = [x.strip() for x in text.split("|", 1)]
        if key not in DB["config"]["buttons"]:
            send(chat_id, "❌ المفتاح غير صحيح."); return True
        DB["config"]["buttons"][key] = name[:64]
        PENDING.pop(uid, None); save_db(); send(chat_id, "✅ تم تغيير اسم الزر."); return True
    if mode == "broadcast_url":
        if not text.startswith(("http://", "https://", "tg://")):
            send(chat_id, "❌ أرسل رابطًا يبدأ بـ http:// أو https:// أو tg://"); return True
        DB["config"]["broadcast_url"] = text.strip(); PENDING.pop(uid, None); save_db(); send(chat_id, "✅ تم حفظ رابط الإذاعة."); return True
    if mode == "broadcast":
        PENDING.pop(uid, None); count = broadcast(text); send(chat_id, f"✅ تمت الإذاعة إلى {count} مستخدم."); return True
    return False


def handle_callback(query):
    uid = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    mid = query["message"]["message_id"]
    data = query.get("data", "")
    answer_callback(query["id"])
    if data == "home":
        edit(chat_id, mid, DB["config"]["welcome"], main_keyboard(uid)); return
    if data == "create":
        room = find_active_room(uid) or new_room(uid)
        send(chat_id, room_text(room), room_keyboard(room["code"])); return
    if data == "join":
        send(chat_id, "🔑 أرسل الكود بهذا الشكل:\n/room ABC123"); return
    if data == "leaders":
        edit(chat_id, mid, leaderboard_text(), {"inline_keyboard": [[button("⬅️ الرئيسية", "home")]]}); return
    if data == "profile":
        edit(chat_id, mid, profile_text(uid), {"inline_keyboard": [[button("⬅️ الرئيسية", "home")]]}); return
    if data == "rules":
        edit(chat_id, mid, "📖 طريقة اللعب\n\n1️⃣ إنشاء غرفة\n2️⃣ إرسال الكود لصاحبك\n3️⃣ اللاعب الثاني يدخل بالكود\n4️⃣ افتح Mini App والعبوا مباشرة\n\n❌ X يبدأ أولًا\n⭕ O ثانيًا", {"inline_keyboard": [[button("⬅️ الرئيسية", "home")]]}); return
    if data == "admin" and is_owner(uid):
        edit(chat_id, mid, "⚙️ لوحة الإدارة\n\nPremium Emoji يتم التقاطه تلقائيًا من الرسالة — بدون كتابة ID.", admin_keyboard()); return
    if not is_owner(uid): return
    if data == "xemoji": PENDING[uid] = "xemoji"; send(chat_id, "❌ أرسل Premium Emoji الذي تريد استخدامه لـ X."); return
    if data == "oemoji": PENDING[uid] = "oemoji"; send(chat_id, "⭕ أرسل Premium Emoji الذي تريد استخدامه لـ O."); return
    if data == "names": PENDING[uid] = "names"; send(chat_id, "✏️ اكتب: المفتاح|اسم الزر"); return
    if data == "buttonemoji": PENDING[uid] = "buttonemoji"; send(chat_id, "✨ اكتب مفتاح الزر وأرفق معه Premium Emoji؛ سألتقط الـID تلقائيًا."); return
    if data == "broadcastcfg": send(chat_id, "📢 الإذاعة\n\n/broadcast_url ثم أرسل الرابط\n/broadcast ثم أرسل نص الإذاعة\n\nالزر رابط حقيقي ويدعم Telegram والروابط الخارجية."); return
    if data == "stats": send(chat_id, f"📊 المستخدمون: {len(DB['users'])}\n🎮 الغرف: {len(DB['rooms'])}\n🌐 Mini App: {'جاهز' if PUBLIC_URL else 'يحتاج PUBLIC_URL'}"); return
    if data.startswith("refresh:"):
        code = data.split(":", 1)[1]; room = DB["rooms"].get(code)
        if room: edit(chat_id, mid, room_text(room), room_keyboard(code))


def handle_command(message):
    text = message.get("text", "")
    uid = message["from"]["id"]
    chat_id = message["chat"]["id"]
    upsert_user(uid, message["from"].get("first_name") or "Player", message["from"].get("username") or "")
    if text.startswith("/start"):
        extra = "\n\n⚠️ Mini App يحتاج PUBLIC_URL إذا لم يظهر زر فتح XO." if not PUBLIC_URL else ""
        send(chat_id, DB["config"]["welcome"] + extra, main_keyboard(uid)); return True
    if text.startswith("/room "):
        room, msg = join_room(text.split(None, 1)[1], uid)
        send(chat_id, msg)
        if room: send(chat_id, room_text(room), room_keyboard(room["code"]))
        return True
    if text == "/panel" and is_owner(uid):
        send(chat_id, "⚙️ لوحة الإدارة", admin_keyboard()); return True
    if text == "/broadcast_url" and is_owner(uid):
        PENDING[uid] = "broadcast_url"; send(chat_id, "🔗 أرسل الرابط الآن."); return True
    if text == "/broadcast" and is_owner(uid):
        PENDING[uid] = "broadcast"; send(chat_id, "📢 أرسل نص الإذاعة الآن."); return True
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


def run_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), AppHandler)
    print(f"Mini App server listening on 0.0.0.0:{PORT}")
    server.serve_forever()


def main():
    load_db()
    threading.Thread(target=run_server, daemon=True).start()
    if BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        print("BOT_TOKEN is not configured. Mini App server is still running.")
        return
    if PUBLIC_URL:
        configure_bot_menu()
    bot_loop()


if __name__ == "__main__":
    main()
