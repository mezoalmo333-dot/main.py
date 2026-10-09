# -*- coding: utf-8 -*-
"""
BLACK LINK — تواصل مع صاحب البوت فقط
ملف واحد مناسب لـ Pydroid 3، دون مكتبات خارجية.
"""
import json, os, time, html, urllib.parse, urllib.request, urllib.error, traceback

# عدّل الإعدادين التاليين:
BOT_TOKEN = "8645431584:AAHKFa1N6TrVOIqByCoNKlUx_Fcd3w9KiCU"
OWNER_ID = 803002143  # رقم حساب الأدمن الرقمي
DB_FILE = "black_link_contact_db.json"
POLL_TIMEOUT = 25

# معرّفات الإيموجي المخصص التي طلبها صاحب البوت
EMOJI_MESSAGE = "5282843764451195532"
EMOJI_ID = "6298398604180588232"
EMOJI_TEXT = "5877536313623711363"
EMOJI_PROFILE = "5416117059207572332"
EMOJI_SEND = "5206607081334906820"
EMOJI_SEND_AGAIN = "5395444784611480792"
EMOJI_CANCEL = "5210952531676504517"
EMOJI_WELCOME = "5931415565955503486"
EMOJI_HELP = "6048434449605989564"
EMOJI_ADMIN = "5934033357112348687"
EMOJI_REPLY_GREEN = "5861665979968262792"

# Inline keyboards فقط؛ Telegram Bot API لا يتيح فرض ألوان success/danger على الأزرار.
def custom_emoji(emoji_id):
    return {"type": "custom_emoji", "custom_emoji_id": str(emoji_id)}

def button(text, callback_data=None, url=None, style=None, emoji_id=None):
    b = {"text": text}
    if callback_data is not None:
        b["callback_data"] = callback_data
    if url is not None:
        b["url"] = url
    if style in ("primary", "success", "danger"):
        b["style"] = style
    if emoji_id:
        b["icon_custom_emoji_id"] = str(emoji_id)
    return b

def main_keyboard():
    return {"inline_keyboard": [
        [button("إرسال رسالة", "send", style="success", emoji_id=EMOJI_SEND)],
        [button("طريقة الاستخدام", "help", style="primary", emoji_id=EMOJI_HELP)]
    ]}

def cancel_keyboard():
    return {"inline_keyboard": [
        [button("إلغاء", "cancel", style="danger", emoji_id=EMOJI_CANCEL)]
    ]}

def reply_batch_keyboard(count):
    return {"inline_keyboard": [
        [button("تم إرسال الردود", "reply_done", style="success", emoji_id=EMOJI_SEND)],
        [button("إلغاء", "cancel", style="danger", emoji_id=EMOJI_CANCEL)]
    ]}

def sent_keyboard():
    return {"inline_keyboard": [
        [button("إرسال رسالة مرة أخرى", "send", style="success", emoji_id=EMOJI_SEND_AGAIN)]
    ]}

def received_reply_keyboard():
    return {"inline_keyboard": [
        [button("رد على الرسالة", "send", style="success", emoji_id=EMOJI_REPLY_GREEN)]
    ]}

def default_db():
    return {"users": {}, "blocked_users": [], "stats": {"received": 0, "replied": 0, "broadcasts": 0}, "states": {}}

def load_db():
    if not os.path.exists(DB_FILE): return default_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        base = default_db()
        for k, v in base.items(): data.setdefault(k, v)
        return data
    except Exception:
        print("تعذر قراءة قاعدة البيانات؛ احتفظ بنسخة احتياطية منها.")
        return default_db()

DB = load_db()
def save_db():
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(DB, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DB_FILE)

API = "https://api.telegram.org/bot" + BOT_TOKEN + "/"
def api(method, data=None, timeout=40):
    form = {}
    for k, v in (data or {}).items():
        if v is None: continue
        form[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list, bool)) else str(v)
    req = urllib.request.Request(API + method, data=urllib.parse.urlencode(form).encode("utf-8"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: out = json.loads(r.read().decode("utf-8"))
        if not out.get("ok"): print("Telegram API:", method, out.get("description", "error"))
        return out
    except urllib.error.HTTPError as e:
        try: print("HTTP error:", method, e.read().decode("utf-8", "replace")[:400])
        except Exception: print("HTTP error:", method, str(e))
    except Exception as e: print("Network error:", method, repr(e))
    return {"ok": False, "result": None}

def send(chat_id, text, keyboard=None, parse_mode="HTML", entities=None):
    payload = {"chat_id": chat_id, "text": text,
               "reply_markup": keyboard, "disable_web_page_preview": True}
    if entities is not None:
        payload["entities"] = entities
    elif parse_mode:
        payload["parse_mode"] = parse_mode
    return api("sendMessage", payload)

def utf16_len(value):
    return len(value.encode("utf-16-le")) // 2

def send_welcome(uid, tg_user):
    name = tg_user.get("first_name") or "صديقي"
    line1 = "اهلا يـ " + name + " ⭐"
    line2 = "نورت بوت تواصل محظورين مدام هند ⭐"
    text = line1 + "\n" + line2
    entities = [
        {"type": "bold", "offset": 0, "length": utf16_len(line1)},
        {"type": "text_link", "offset": utf16_len("اهلا يـ "), "length": utf16_len(name),
         "url": "tg://user?id=" + str(uid)},
        {"type": "custom_emoji", "offset": utf16_len(line1) - 1, "length": 1,
         "custom_emoji_id": EMOJI_WELCOME},
        {"type": "bold", "offset": utf16_len(line1) + 1, "length": utf16_len(line2)},
        {"type": "custom_emoji", "offset": utf16_len(text) - 1, "length": 1,
         "custom_emoji_id": EMOJI_WELCOME},
        {"type": "blockquote", "offset": 0, "length": utf16_len(text)}
    ]
    return send(uid, text, main_keyboard(), parse_mode=None, entities=entities)

def copy_message(to_id, from_id, message_id, keyboard=None):
    return api("copyMessage", {"chat_id": to_id, "from_chat_id": from_id,
                               "message_id": message_id, "reply_markup": keyboard})

def answer(qid, text="", alert=False):
    return api("answerCallbackQuery", {"callback_query_id": qid, "text": text, "show_alert": alert})

def get_user(uid, tg=None):
    key = str(uid)
    if key not in DB["users"]:
        DB["users"][key] = {"id": int(uid), "first_name": "مستخدم", "username": "", "messages": 0}
    if tg:
        DB["users"][key]["first_name"] = tg.get("first_name", "مستخدم")
        DB["users"][key]["username"] = tg.get("username", "")
    save_db()
    return DB["users"][key]

def set_state(uid, state): DB["states"][str(uid)] = state; save_db()
def clear_state(uid): DB["states"].pop(str(uid), None); save_db()
def is_blocked(uid): return int(uid) in [int(x) for x in DB["blocked_users"]]
def esc(v): return html.escape(str(v or ""), quote=False)

def profile_url(uid):
    u = DB["users"].get(str(uid), {})
    if u.get("username"): return "https://t.me/" + u["username"]
    # رابط tg://user?id= صالح لفتح الحساب في العملاء الداعمة له، ولا يضمن إظهار الملف للجميع.
    return "tg://user?id=" + str(uid)

def owner_message_keyboard(uid):
    return {"inline_keyboard": [
        [button("دخول حساب الشخص", url=profile_url(uid), style="danger", emoji_id=EMOJI_PROFILE)],
        [button("رد على الرسالة", callback_data="reply:" + str(uid), style="danger", emoji_id=EMOJI_SEND)]
    ]}

def user_menu_text():
    return ("╔══════════════════════╗\n"
            "       <b>𝐁𝐋𝐀𝐂𝐊 𝐋𝐈𝐍𝐊</b>\n"
            "╚══════════════════════╝\n\n"
            "<blockquote>مركز التواصل الخاص</blockquote>\n"
            "ابعت رسالتك لصاحب البوت، وهتوصله مباشرة ويقدر يرد عليك من هنا.")

def send_to_owner(uid, msg):
    if not OWNER_ID:
        send(uid, "البوت لم يتم إعداده بعد. ضع OWNER_ID في الملف.")
        return
    if is_blocked(uid):
        send(uid, "لا يمكنك إرسال رسائل إلى صاحب البوت عبر هذه الخدمة.")
        return
    txt = msg.get("text") or msg.get("caption") or "رسالة وسائط"
    notice = (
        "شخص ارسل رسالة لك\n\n"
        f"ايـدي | <code>{uid}</code>\n\n"
        "الرسالة |\n"
        "<blockquote><b>" + esc(txt) + "</b></blockquote>"
    )
    sent = send(OWNER_ID, notice, owner_message_keyboard(uid))
    if not sent.get("ok"):
        send(uid, "تعذر تسليم رسالتك حاليًا. حاول مرة أخرى.")
        return
    if not msg.get("text"):
        copied = copy_message(OWNER_ID, uid, msg["message_id"])
        if not copied.get("ok"):
            send(OWNER_ID, "<i>تعذر نسخ نوع الوسائط المرفقة.</i>")
    DB["stats"]["received"] = int(DB["stats"].get("received", 0)) + 1
    DB["users"][str(uid)]["messages"] = int(DB["users"][str(uid)].get("messages", 0)) + 1
    save_db()
    send(uid, "تـم ارسـل رسـالـتـك لـ مـامـا هـنـد", sent_keyboard())

def find_user(text):
    target = (text or "").strip().lstrip("@")
    if target.isdigit() and target in DB["users"]: return int(target)
    for uid, u in DB["users"].items():
        if u.get("username", "").lower() == target.lower(): return int(uid)
    return None

def broadcast(owner_id, msg):
    ok = fail = 0
    for target in list(DB["users"]):
        tid = int(target)
        if is_blocked(tid): continue
        res = copy_message(tid, owner_id, msg["message_id"])
        if res.get("ok"): ok += 1
        else: fail += 1
        time.sleep(0.04)
    DB["stats"]["broadcasts"] += 1
    save_db()
    send(owner_id, f"انتهت الإذاعة.\n✓ وصل: <b>{ok}</b>\n✗ تعذر: <b>{fail}</b>", admin_keyboard())

def admin_keyboard():
    # كل أزرار لوحة الإدارة باللون الأزرق مع الإيموجي المخصص المطلوب.
    return {"inline_keyboard": [
        [button("الإحصائيات", "admin:stats", style="primary", emoji_id=EMOJI_ADMIN)],
        [button("حظر مرسل", "admin:ban", style="primary", emoji_id=EMOJI_ADMIN),
         button("فك الحظر", "admin:unban", style="primary", emoji_id=EMOJI_ADMIN)],
        [button("إذاعة رسالة", "admin:broadcast", style="primary", emoji_id=EMOJI_ADMIN)]
    ]}

def handle_message(msg):
    chat = msg.get("chat", {})
    if chat.get("type") != "private": return
    tg = msg.get("from", {})
    uid = tg.get("id")
    if not uid: return
    get_user(uid, tg)
    text = msg.get("text", "")
    state = DB["states"].get(str(uid))

    if text == "/start":
        send_welcome(uid, tg)
        if uid == OWNER_ID: send(uid, "لوحة الإدارة:", admin_keyboard())
        return
    if text == "/admin":
        send(uid, "لوحة الإدارة:" if uid == OWNER_ID else "الأمر خاص بالأدمن.", admin_keyboard() if uid == OWNER_ID else None)
        return
    if text in ("/cancel", "❌ إلغاء"):
        clear_state(uid); send(uid, "تم الإلغاء.", main_keyboard()); return

    if state:
        step = state.get("step")
        if step == "compose":
            # احتفظ بالنص/التعليق قبل طلب التأكيد أو المعالجة، لكي يظهر تنسيق الإشعار للأدمن.
            send_to_owner(uid, msg)
            clear_state(uid)
            return
        if uid == OWNER_ID and step == "reply_batch":
            state.setdefault("messages", []).append(int(msg["message_id"]))
            set_state(uid, state)
            count = len(state["messages"])
            send(uid, f"<b>الرسائل الموجودة:</b> <code>{count}</code>\nأرسل رسالة أو وسيطًا آخر، أو اضغط «تم إرسال الردود» عند الانتهاء.", reply_batch_keyboard(count))
            return
        if uid == OWNER_ID and step in ("ban", "unban"):
            target_id = find_user(text)
            if not target_id and text.strip().isdigit(): target_id = int(text.strip())
            if not target_id:
                send(uid, "لم أجد المستخدم. أرسل ID أو @username لمستخدم بدأ البوت.")
                return
            if step == "ban":
                if target_id not in DB["blocked_users"]: DB["blocked_users"].append(target_id)
                send(uid, f"تم حظر <code>{target_id}</code>.")
                send(target_id, "تم منعك من مراسلة صاحب البوت.")
            else:
                DB["blocked_users"] = [int(x) for x in DB["blocked_users"] if int(x) != target_id]
                send(uid, f"تم فك الحظر عن <code>{target_id}</code>.")
            clear_state(uid); save_db(); send(uid, "لوحة الإدارة:", admin_keyboard()); return
        if uid == OWNER_ID and step == "broadcast":
            clear_state(uid); broadcast(uid, msg); return

    if text == "✉️ إرسال رسالة" or text == "/send":
        if is_blocked(uid): send(uid, "لا يمكنك مراسلة صاحب البوت."); return
        set_state(uid, {"step": "compose"})
        send(uid, "اكتب رسالتك أو أرسل الصورة/الفيديو/الملف الذي تريد إيصاله للأدمن.", cancel_keyboard())
        return
    if text in ("ℹ️ طريقة الاستخدام", "/help"):
        send(uid, "اضغط «إرسال رسالة»، ثم اكتب رسالتك. ستصل مباشرة إلى صاحب البوت، ويمكنه الرد عليك من خلال البوت.", main_keyboard())
        return
    if text.startswith("/"):
        send(uid, "أمر غير معروف. استخدم الأزرار.", main_keyboard()); return
    send(uid, "اضغط «إرسال رسالة» أولًا لبدء التواصل.", main_keyboard())

def handle_callback(q):
    qid = q.get("id"); data = q.get("data", ""); actor = q.get("from", {}).get("id")
    if not actor: return
    get_user(actor, q.get("from"))
    if data == "send":
        if is_blocked(actor): answer(qid, "لا يمكنك مراسلة صاحب البوت.", True); return
        set_state(actor, {"step": "compose"})
        answer(qid, "اكتب رسالتك الآن.")
        send(actor, "اكتب رسالتك أو أرسل وسائطك للأدمن.", cancel_keyboard()); return
    if data == "help":
        answer(qid)
        send(actor, "أرسل رسالتك عبر زر «إرسال رسالة». ستصل لصاحب البوت ويمكنه الرد عليك من هنا.")
        return
    if data == "cancel":
        clear_state(actor); answer(qid, "تم الإلغاء."); send(actor, "تم الإلغاء.", main_keyboard()); return
    if data.startswith("reply:"):
        if actor != OWNER_ID: answer(qid, "هذا الزر خاص بالأدمن.", True); return
        target = int(data.split(":", 1)[1])
        if is_blocked(target): answer(qid, "هذا المرسل محظور؛ فك الحظر أولًا.", True); return
        set_state(actor, {"step": "reply_batch", "target": target, "messages": []})
        answer(qid, "أرسل ردودك بالترتيب.")
        send(actor, f"اكتب ردك إلى <code>{target}</code>.\nيمكنك إرسال عدة رسائل أو وسائط متتالية، ثم اضغط «تم إرسال الردود».", reply_batch_keyboard(0)); return
    if data == "reply_done":
        if actor != OWNER_ID:
            answer(qid, "هذا الزر خاص بالأدمن.", True)
            return
        state = DB["states"].get(str(actor), {})
        if state.get("step") != "reply_batch":
            answer(qid, "لا توجد مجموعة ردود نشطة.", True)
            return
        target = int(state["target"])
        message_ids = list(state.get("messages", []))
        if not message_ids:
            answer(qid, "أرسل ردًا واحدًا على الأقل أولًا.", True)
            return
        answer(qid, "جارٍ إرسال الردود بالترتيب…")
        intro = send(target, "<b>وصلتك رسالة من ماما هند</b>")
        if not intro.get("ok"):
            answer(qid, "تعذر التواصل مع هذا المستخدم.", True)
            return
        delivered = 0
        last_delivered_message_id = None
        reply_button_attached = False
        for index, mid in enumerate(message_ids):
            # أرفق زر الرد بآخر رسالة تم نسخها حتى يظهر أسفل محتوى الرد، لا فوقه.
            markup = received_reply_keyboard() if index == len(message_ids) - 1 else None
            result = copy_message(target, actor, mid, markup)
            if result.get("ok"):
                delivered += 1
                copied = result.get("result") or {}
                last_delivered_message_id = copied.get("message_id")
                if index == len(message_ids) - 1:
                    reply_button_attached = True
            time.sleep(0.05)
        # إذا فشل نسخ آخر رسالة أو كل الرسائل، اعرض الزر برسالة مستقلة حتى يظل الرد ممكنًا.
        if delivered and not reply_button_attached:
            send(target, "يمكنك الرد على ماما هند من هنا.", received_reply_keyboard())
        elif delivered == 0:
            send(target, "تعذر إرسال محتوى الرد. يمكنك المحاولة بإرسال رسالة جديدة.", received_reply_keyboard())
        clear_state(actor)
        DB["stats"]["replied"] += delivered
        save_db()
        send(actor, f"تم إنهاء الردود.\n<b>الرسائل المرسلة:</b> <code>{delivered}/{len(message_ids)}</code>", admin_keyboard())
        return

    if data.startswith("admin:"):
        if actor != OWNER_ID: answer(qid, "غير مصرح لك.", True); return
        action = data.split(":", 1)[1]; answer(qid)
        if action == "stats":
            send(actor, f"<b>إحصائيات BLACK LINK</b>\nالمستخدمون: <b>{len(DB['users'])}</b>\nالرسائل: <b>{DB['stats']['received']}</b>\nالردود: <b>{DB['stats']['replied']}</b>\nالمحظورون: <b>{len(DB['blocked_users'])}</b>\nالإذاعات: <b>{DB['stats']['broadcasts']}</b>", admin_keyboard())
        elif action == "ban":
            set_state(actor, {"step": "ban"}); send(actor, "أرسل ID أو @username لحظره.", cancel_keyboard())
        elif action == "unban":
            set_state(actor, {"step": "unban"}); send(actor, "أرسل ID أو @username لفك الحظر.", cancel_keyboard())
        elif action == "broadcast":
            set_state(actor, {"step": "broadcast"}); send(actor, "أرسل الرسالة أو الوسائط التي تريد إذاعتها.", cancel_keyboard())
        return
    answer(qid, "زر غير معروف.")

def main():
    if BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE" or not BOT_TOKEN:
        print("ضع توكن @BotFather في BOT_TOKEN."); return
    if not OWNER_ID:
        print("ضع رقم حساب الأدمن في OWNER_ID."); return
    print("BLACK LINK contact bot is running.")
    offset = None
    while True:
        try:
            params = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message", "callback_query"]}
            if offset is not None: params["offset"] = offset
            result = api("getUpdates", params, timeout=POLL_TIMEOUT + 15)
            if not result.get("ok"): time.sleep(3); continue
            for upd in result.get("result", []):
                offset = upd["update_id"] + 1
                try:
                    if "callback_query" in upd: handle_callback(upd["callback_query"])
                    elif "message" in upd: handle_message(upd["message"])
                except Exception: traceback.print_exc()
            save_db()
        except KeyboardInterrupt:
            print("تم إيقاف البوت."); break
        except Exception:
            traceback.print_exc(); time.sleep(3)

if __name__ == "__main__":
    main()
