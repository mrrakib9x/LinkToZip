
# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════╗
# ║   🌐 𝐒ᴍᴀʀᴛ 𝐏ʀᴇᴍɪᴜᴍ 𝐋ɪɴᴋ 𝐓ᴏ 𝐂ᴏᴅᴇ 𝐁ᴏᴛ 🌐                   ║
# ║   Developer: @rtcadmin9x                                  ║
# ║   Final Edition — No History + Custom ZIP Name               ║
# ╚══════════════════════════════════════════════════════════════╝

import os
import sqlite3
import shutil
import zipfile
import requests
import telebot
import json
import random
import re
import emoji
import time
import io
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from datetime import datetime
from telebot import types

# ═══════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "8606854890:AAGX8_SjR1o8c0o5oht45JRUP0dWgsLbMNs").strip()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "7474870354").split(",") if x.strip().isdigit()]
BASE_DIR = "bot_data"
TEMP_DIR = os.path.join(BASE_DIR, "temp")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)

# ✅ Custom ZIP filename — এখানে চাইলে পরিবর্তন করুন
ZIP_FILENAME = "RtcWebTo.zip"

if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise RuntimeError("BOT_TOKEN সেট করুন।")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", num_threads=1)

user_states = {}
temp_data = {}

def set_state(uid, state): user_states[uid] = state
def get_state(uid): return user_states.get(uid)
def clear_state(uid):
    if uid in user_states: del user_states[uid]

def is_admin(uid): return uid in ADMIN_IDS

# ═══════════════════════════════════════
# ✨ PREMIUM EMOJI ENGINE
# ═══════════════════════════════════════
MAIN_EMOJI_ID = "6010060634803148161"
PLACEHOLDER = "🌟"
PREMIUM_EMOJI_DB_FILE = os.path.join(BASE_DIR, "premium_emojis.json")

def load_json(filepath, default_type=dict):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass
    return default_type()

def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception: pass

def load_premium_emoji_db():
    db = {}
    data = load_json(PREMIUM_EMOJI_DB_FILE, dict)
    def _add(emj, cid):
        if str(cid).isdigit() and emoji.is_emoji(emj):
            db.setdefault(emj, []).append(str(cid))
    if isinstance(data, dict):
        if "combined_packs" in data:
            for pack in data["combined_packs"]:
                for item in pack.get("emojis", []):
                    _add(item.get("emoji"), item.get("id") or item.get("custom_emoji_id"))
        else:
            for emj, val in data.items():
                if isinstance(val, list):
                    for cid in val: _add(emj, cid)
                else: _add(emj, val)
    return db

EMOJI_TO_PREMIUM = load_premium_emoji_db()
PREMIUM_EMOJIS = [i for sub in EMOJI_TO_PREMIUM.values() for i in sub] or [MAIN_EMOJI_ID]

def premium_id_for(char: str) -> str:
    if char == PLACEHOLDER: return MAIN_EMOJI_ID
    ids = EMOJI_TO_PREMIUM.get(char)
    if ids:
        valid = [i for i in ids if i.isdigit()]
        if valid: return random.choice(valid)
    pool = [i for i in PREMIUM_EMOJIS if str(i).isdigit()]
    return random.choice(pool) if pool else MAIN_EMOJI_ID

def format_pe(text: str) -> str:
    if not text: return ""
    def replace_emj(char, _d):
        eid = premium_id_for(char)
        return f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>' if eid and eid.isdigit() else char
    return emoji.replace_emoji(text, replace=replace_emj)

_EXU_LINE_RE = re.compile(r'^\s*\d+\.\s+(\d+)\s+\[(.+)\]\s*$')

def parse_emoji_pack(raw_bytes: bytes, filename: str) -> dict:
    text = raw_bytes.decode("utf-8", errors="ignore")
    result = {}
    def _add(emj, cid):
        if str(cid).isdigit() and emoji.is_emoji(emj):
            result.setdefault(emj, []).append(str(cid))
    if filename.lower().endswith(".json"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                if "combined_packs" in data:
                    for pack in data["combined_packs"]:
                        for item in pack.get("emojis", []):
                            _add(item.get("emoji"), item.get("id") or item.get("custom_emoji_id"))
                else:
                    for emj, val in data.items():
                        if isinstance(val, list):
                            for cid in val: _add(emj, cid)
                        else: _add(emj, val)
        except Exception: pass
    else:
        for line in text.splitlines():
            m = _EXU_LINE_RE.match(line.strip())
            if m: _add(m.group(2), m.group(1))
    return result

def merge_emoji_pack(new_data: dict):
    global EMOJI_TO_PREMIUM, PREMIUM_EMOJIS
    added_ids, added_keys = 0, 0
    for emj, ids in new_data.items():
        existing = EMOJI_TO_PREMIUM.setdefault(emj, [])
        if not existing: added_keys += 1
        for cid in ids:
            if cid not in existing:
                existing.append(cid)
                added_ids += 1
    save_json(PREMIUM_EMOJI_DB_FILE, EMOJI_TO_PREMIUM)
    PREMIUM_EMOJIS = [i for sub in EMOJI_TO_PREMIUM.values() for i in sub] or [MAIN_EMOJI_ID]
    return added_ids, added_keys

# ═══════════════════════════════════════
# 🛡️ ANTI-CRASH HTML SENDER
# ═══════════════════════════════════════
def create_header(title: str) -> str:
    return (
        f"➿➿➿➿➿➿➿➿➿➿➿\n"
        f"        <b>{title}</b>        \n"
        f"➿➿➿➿➿➿➿➿➿➿➿\n\n"
    )

def strip_html(text):
    clean = re.sub(r'<tg-emoji emoji-id="[^"]+">([^<]+)</tg-emoji>', r'\1', text or "")
    return re.sub(r'<[^>]+>', '', clean)

def safe_send(chat_id, text, reply_markup=None, **kwargs):
    formatted = format_pe(text)
    try:
        return bot.send_message(chat_id, formatted, parse_mode="HTML",
                                reply_markup=reply_markup,
                                disable_web_page_preview=True, **kwargs)
    except Exception:
        return bot.send_message(chat_id, strip_html(formatted), parse_mode=None,
                                reply_markup=reply_markup,
                                disable_web_page_preview=True, **kwargs)

def safe_send_doc(chat_id, file_path, filename, caption=""):
    """Send a document with a custom filename."""
    try:
        with open(file_path, "rb") as f:
            return bot.send_document(
                chat_id, f,
                visible_file_name=filename,
                caption=format_pe(caption),
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"send_document error: {e}")
        return None

# ═══════════════════════════════════════
# 🎨 STYLED BUTTONS
# ═══════════════════════════════════════
class StyledInlineButton(types.InlineKeyboardButton):
    def __init__(self, text, url=None, callback_data=None,
                 style=None, icon_custom_emoji_id=None):
        super().__init__(text=text, url=url, callback_data=callback_data)
        self.style = style
        self.icon_custom_emoji_id = icon_custom_emoji_id
    def to_dict(self):
        d = super().to_dict()
        if self.style: d['style'] = self.style
        if self.icon_custom_emoji_id: d['icon_custom_emoji_id'] = self.icon_custom_emoji_id
        return d

def btn(text, cb=None, url=None, style=None, icon=None):
    eid = premium_id_for(icon) if icon else None
    return StyledInlineButton(text, url=url, callback_data=cb,
                              style=style, icon_custom_emoji_id=eid)

def _kb_btn(text, icon_emoji, style):
    eid = premium_id_for(icon_emoji)
    d = {"text": text, "style": style}
    if eid and eid.isdigit():
        d["icon_custom_emoji_id"] = eid
    return d

def _build_reply_keyboard(buttons, row_width=2):
    rows, row = [], []
    for text, icon_emoji, style in buttons:
        row.append(_kb_btn(text, icon_emoji, style))
        if len(row) == row_width:
            rows.append(row); row = []
    if row: rows.append(row)
    return json.dumps({"keyboard": rows, "resize_keyboard": True, "is_persistent": False})

# ━━━ User Button Text (My History Removed) ━━━
BTN_GET_SRC = "𝐆ᴇᴛ 𝐒ᴏᴜʀᴄᴇ"
BTN_STATS   = "𝐌ʏ 𝐒ᴛᴀᴛs"
BTN_PREMIUM = "𝐏ʀᴇᴍɪᴜᴍ"
BTN_HOW_TO  = "𝐇ᴏᴡ 𝐓ᴏ 𝐔sᴇ"
BTN_SUPPORT = "𝐒ᴜᴘᴘᴏʀᴛ"
BTN_ADMIN   = "𝐀ᴅᴍɪɴ 𝐏ᴀɴᴇʟ"
BTN_CANCEL  = "𝐂ᴀɴᴄᴇʟ"

# ━━━ Admin Button Text ━━━
A_DASH     = "𝐃ᴀsʜʙᴏᴀʀᴅ"
A_ALLFILES = "𝐀ʟʟ 𝐅ɪʟᴇs"
A_ALLUSERS = "𝐀ʟʟ 𝐔sᴇʀs"
A_HISTORY  = "𝐀ʟʟ 𝐇ɪsᴛᴏʀʏ"
A_BCAST    = "𝐁ʀᴏᴀᴅᴄᴀsᴛ"
A_SETTINGS = "𝐒ᴇᴛᴛɪɴɢs"
A_EMOJIS   = "𝐄ᴍᴏᴊɪ 𝐌ᴀɴᴀɢᴇʀ"
A_USERMODE = "𝐔sᴇʀ 𝐌ᴏᴅᴇ"

def main_menu(uid):
    """✅ My History removed — clean layout."""
    btns = [
        (BTN_GET_SRC, "🌐", "success"),
        (BTN_STATS,   "📊", "primary"),
        (BTN_PREMIUM, "💎", "success"),
        (BTN_HOW_TO,  "❓", "primary"),
        (BTN_SUPPORT, "📞", "danger"),
    ]
    if is_admin(uid): btns.append((BTN_ADMIN, "👑", "danger"))
    return _build_reply_keyboard(btns)

def admin_menu():
    return _build_reply_keyboard([
        (A_DASH,     "📊", "success"),
        (A_ALLFILES, "📁", "primary"),
        (A_ALLUSERS, "👥", "primary"),
        (A_HISTORY,  "📜", "primary"),
        (A_BCAST,    "📢", "danger"),
        (A_SETTINGS, "⚙️", "primary"),
        (A_EMOJIS,   "✨", "success"),
        (A_USERMODE, "👤", "primary"),
    ])

def cancel_menu():
    return _build_reply_keyboard([(BTN_CANCEL, "❌", "danger")], row_width=1)

def match_btn(text, target):
    if not text: return False
    return text.strip() == target.strip()

# ═══════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════
def execute_query(query, params=(), commit=True, fetchone=False, fetchall=False, lastrowid=False):
    try:
        with sqlite3.connect("bot_database.db", timeout=20) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(query, params)
            res = None
            if commit: conn.commit()
            if fetchone: res = c.fetchone()
            if fetchall: res = c.fetchall()
            if lastrowid: res = c.lastrowid
            return res
    except Exception as e:
        print(f"Database Error: {e}")
        return None

def init_db():
    execute_query('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT, name TEXT,
        join_date TEXT, extractions INTEGER DEFAULT 0, is_premium INTEGER DEFAULT 0)''')
    execute_query('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        url TEXT, extracted_at TEXT, zip_path TEXT)''')
    execute_query('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    execute_query("INSERT OR IGNORE INTO settings (key, value) VALUES ('support_link', '@rtcadmin9x')")
    execute_query("INSERT OR IGNORE INTO settings (key, value) VALUES ('premium_price', '99')")
    execute_query("INSERT OR IGNORE INTO settings (key, value) VALUES ('free_limit', '20')")

def get_setting(key, default=""):
    row = execute_query("SELECT value FROM settings WHERE key=?", (key,), fetchone=True)
    return row["value"] if row else default

def set_setting(key, value):
    execute_query("INSERT INTO settings(key,value) VALUES (?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

def get_free_limit():
    try: return int(get_setting("free_limit", "20"))
    except Exception: return 20

# ═══════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════
def is_safe_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ['http', 'https']: return False
    host = parsed.hostname
    if not host: return False
    if host in ['localhost', '127.0.0.1', '0.0.0.0']: return False
    if host.startswith(('192.168.', '10.', '172.16.', '172.17.', '172.18.', '172.19.',
                        '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.',
                        '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.')): return False
    return True

def user_zip_dir(uid):
    path = os.path.join(STORAGE_DIR, str(uid))
    os.makedirs(path, exist_ok=True)
    return path

def user_zip_path(uid, hist_id):
    """Internal storage path — always .zip extension."""
    return os.path.join(user_zip_dir(uid), f"source_{hist_id}.zip")

def check_user_limit(uid):
    """Return (allowed, remaining, limit, is_premium)."""
    u = execute_query("SELECT is_premium, extractions FROM users WHERE id=?", (uid,), fetchone=True)
    if not u:
        return (True, 0, 0, False)
    is_prem = int(u["is_premium"] or 0) == 1
    used = int(u["extractions"] or 0)
    limit = get_free_limit()
    if is_prem:
        return (True, -1, limit, True)
    remaining = max(0, limit - used)
    return (remaining > 0, remaining, limit, False)

# ═══════════════════════════════════════
# /start
# ═══════════════════════════════════════
@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    execute_query("INSERT OR IGNORE INTO users (id, username, name, join_date) VALUES (?, ?, ?, ?)",
                  (uid, message.from_user.username or "",
                   message.from_user.first_name or "",
                   datetime.now().strftime("%Y-%m-%d")))

    u = execute_query("SELECT is_premium, extractions FROM users WHERE id=?", (uid,), fetchone=True)
    is_prem = int(u["is_premium"] or 0) == 1 if u else False
    used = int(u["extractions"] or 0) if u else 0
    limit = get_free_limit()

    if is_prem:
        quota_text = "💎 <b>Premium:</b> Unlimited extractions"
    else:
        remaining = max(0, limit - used)
        quota_text = f"📦 <b>Free Limit:</b> {remaining}/{limit} extractions remaining"

    text = create_header("🌐 𝐋ɪɴᴋ 𝐓ᴏ 𝐂ᴏᴅᴇ") + (
        "🚀 <b>𝐂ᴏɴᴠᴇʀᴛ 𝐖ᴇʙsɪᴛᴇs 𝐈ɴᴛᴏ 𝐂ᴏᴅᴇ</b>\n\n"
        "🔗 Send a public website URL\n"
        "📦 Get organized frontend source\n"
        "⚡ Fast ZIP generation\n\n"
        f"{quota_text}\n\n"
        "➿➿➿➿➿➿➿➿➿➿➿\n"
        "💡 <b>𝐍ᴏᴛᴇ:</b> Only public frontend resources."
    )
    safe_send(message.chat.id, text, reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: match_btn(m.text, BTN_CANCEL) or m.text == '/cancel')
def handle_cancel(message):
    uid = message.from_user.id
    clear_state(uid)
    if uid in temp_data: del temp_data[uid]
    kb = admin_menu() if is_admin(uid) else main_menu(uid)
    safe_send(uid, "🚫 <b>𝐀ᴄᴛɪᴏɴ 𝐂ᴀɴᴄᴇʟʟᴇᴅ.</b>", reply_markup=kb)

# ═══════════════════════════════════════
# 🌐 GET SOURCE
# ═══════════════════════════════════════
@bot.message_handler(func=lambda m: match_btn(m.text, BTN_GET_SRC))
def ask_url(message):
    uid = message.from_user.id
    allowed, remaining, limit, is_prem = check_user_limit(uid)

    if not allowed:
        support = get_setting("support_link", "@rtcadmin9x")
        price = get_setting("premium_price", "99")
        text = create_header("🔒 𝐅ʀᴇᴇ 𝐋ɪᴍɪᴛ 𝐑ᴇᴀᴄʜᴇᴅ") + (
            f"📦 <b>আপনি আপনার Free limit ({limit}) শেষ করেছেন।</b>\n\n"
            f"💎 <b>Unlimited access</b> পেতে Premium নিন।\n"
            f"💰 <b>Price:</b> {price} BDT\n\n"
            f"📞 <b>Contact:</b> {support}"
        )
        markup = types.InlineKeyboardMarkup().add(
            btn("📞 𝐂ᴏɴᴛᴀᴄᴛ 𝐀ᴅᴍɪɴ",
                url=f"https://t.me/{support.lstrip('@')}",
                style="success", icon="📞"))
        return safe_send(uid, text, reply_markup=markup)

    set_state(uid, "wait_url")

    if is_prem:
        quota = "💎 Premium — Unlimited"
    else:
        quota = f"📦 Free — {remaining}/{limit} remaining"

    safe_send(message.chat.id,
        create_header("🌐 𝐆ᴇᴛ 𝐒ᴏᴜʀᴄᴇ") +
        f"{quota}\n\n"
        "🔗 <b>𝐒ᴇɴᴅ 𝐘ᴏᴜʀ 𝐖ᴇʙsɪᴛᴇ 𝐔𝐑𝐋</b>\n\n"
        "📌 Example: <code>https://example.com</code>\n\n"
        "🔙 /cancel দিয়ে বাতিল করুন।",
        reply_markup=cancel_menu())

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "wait_url")
def process_extraction(message):
    uid = message.from_user.id
    if match_btn(message.text, BTN_CANCEL) or message.text == '/cancel':
        return handle_cancel(message)

    allowed, remaining, limit, is_prem = check_user_limit(uid)
    if not allowed:
        clear_state(uid)
        return ask_url(message)

    url = (message.text or "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if not is_safe_url(url):
        return safe_send(uid, "❌ <b>𝐈ɴᴠᴀʟɪᴅ 𝐔𝐑𝐋</b>\n\nRestricted or invalid host.",
                         reply_markup=cancel_menu())

    safe_send(uid, "🔍 <b>𝐀ɴᴀʟʏᴢɪɴɢ 𝐖ᴇʙsɪᴛᴇ...</b>")

    try:
        response = requests.get(url, timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        soup = BeautifulSoup(response.text, 'html.parser')

        user_folder = os.path.join(TEMP_DIR, str(uid))
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder, ignore_errors=True)
        os.makedirs(user_folder, exist_ok=True)

        with open(os.path.join(user_folder, "index.html"), "w", encoding="utf-8") as f:
            f.write(soup.prettify())

        # 1) Save history
        hist_id = execute_query(
            "INSERT INTO history (user_id, url, extracted_at, zip_path) VALUES (?, ?, ?, ?)",
            (uid, url, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ""),
            lastrowid=True)

        # 2) Create ZIP on disk
        final_zip = user_zip_path(uid, hist_id)
        base_no_ext = final_zip[:-4] if final_zip.endswith(".zip") else final_zip
        if os.path.exists(final_zip):
            try: os.remove(final_zip)
            except Exception: pass
        shutil.make_archive(base_no_ext, 'zip', user_folder)

        if not os.path.isfile(final_zip):
            raise RuntimeError("ZIP creation failed")

        # 3) Update DB
        execute_query("UPDATE history SET zip_path=? WHERE id=?", (final_zip, hist_id))
        execute_query("UPDATE users SET extractions = extractions + 1 WHERE id = ?", (uid,))

        # 4) Send ZIP with custom filename
        u_after = execute_query("SELECT is_premium, extractions FROM users WHERE id=?", (uid,), fetchone=True)
        used_after = int(u_after["extractions"] or 0) if u_after else 0
        prem_after = int(u_after["is_premium"] or 0) == 1 if u_after else False

        if prem_after:
            quota_line = "💎 <b>Premium — Unlimited</b>"
        else:
            rem_after = max(0, limit - used_after)
            quota_line = f"📦 <b>Free — {rem_after}/{limit} remaining</b>"

        safe_send_doc(
            uid,
            final_zip,
            ZIP_FILENAME,   # ✅ Custom filename
            caption=(
                create_header("✅ 𝐒ᴏᴜʀᴄᴇ 𝐑ᴇᴀᴅʏ!") +
                f"🔗 <b>URL:</b> <code>{url[:80]}</code>\n"
                f"📦 <b>Package:</b> {ZIP_FILENAME}\n\n"
                f"{quota_line}\n\n"
                f"💡 Thank you for using our service!"
            )
        )

        clear_state(uid)
        shutil.rmtree(user_folder, ignore_errors=True)
        safe_send(uid, "🏠 <b>𝐌ᴀɪɴ 𝐌ᴇɴᴜ</b>", reply_markup=main_menu(uid))

    except Exception as e:
        clear_state(uid)
        safe_send(uid, f"⚠️ <b>𝐄ʀʀᴏʀ:</b>\n<code>{str(e)[:200]}</code>",
                  reply_markup=main_menu(uid))

# ═══════════════════════════════════════
# 📊 MY STATS
# ═══════════════════════════════════════
@bot.message_handler(func=lambda m: match_btn(m.text, BTN_STATS))
def my_stats(message):
    uid = message.from_user.id
    u = execute_query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
    if not u:
        return safe_send(uid, "❌ <b>User not found.</b> /start করুন।")

    is_prem = int(u["is_premium"] or 0) == 1
    used = int(u["extractions"] or 0)
    limit = get_free_limit()

    if is_prem:
        quota_line = "💎 <b>Premium — Unlimited</b>"
    else:
        remaining = max(0, limit - used)
        quota_line = f"📦 <b>Free — {remaining}/{limit} remaining</b>"

    text = create_header("📊 𝐌ʏ 𝐒ᴛᴀᴛs") + (
        f"🆔 <b>𝐔𝐬𝐞𝐫 𝐈𝐃:</b> <code>{uid}</code>\n"
        f"👤 <b>𝐍𝐚𝐦𝐞:</b> {u['name']}\n"
        f"🔗 <b>𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞:</b> @{u['username'] or '—'}\n\n"
        f"📦 <b>𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐢𝐨𝐧𝐬:</b> {used}\n"
        f"💎 <b>𝐏𝐫𝐞𝐦𝐢𝐮𝐦:</b> {'✅ Active' if is_prem else '❌ Free'}\n"
        f"{quota_line}\n"
        f"📅 <b>𝐉𝐨𝐢𝐧𝐞𝐝:</b> {u['join_date']}"
    )
    safe_send(uid, text, reply_markup=main_menu(uid))

# ═══════════════════════════════════════
# 💎 PREMIUM
# ═══════════════════════════════════════
@bot.message_handler(func=lambda m: match_btn(m.text, BTN_PREMIUM))
def premium_info(message):
    uid = message.from_user.id
    support = get_setting("support_link", "@rtcadmin9x")
    price = get_setting("premium_price", "99")
    limit = get_free_limit()

    text = create_header("💎 𝐏ʀᴇᴍɪᴜᴍ") + (
        "🚀 <b>𝐔𝐧𝐥𝐨𝐜𝐤 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬</b>\n\n"
        f"📦 <b>Free Limit:</b> {limit} extractions\n"
        "💎 <b>Premium:</b> ♾ Unlimited extractions\n"
        "✅ <b>Faster Processing</b>\n"
        "✅ <b>Priority Support</b>\n\n"
        f"💰 <b>Price:</b> {price} BDT\n\n"
        "➿➿➿➿➿➿➿➿➿➿➿\n"
        f"📞 <b>Contact:</b> {support}"
    )
    markup = types.InlineKeyboardMarkup().add(
        btn("𝐂ᴏɴᴛᴀᴄᴛ 𝐀ᴅᴍɪɴ", url=f"https://t.me/{support.lstrip('@')}",
            style="success", icon="📞"))
    safe_send(uid, text, reply_markup=markup)

# ═══════════════════════════════════════
# ❓ HOW TO USE
# ═══════════════════════════════════════
@bot.message_handler(func=lambda m: match_btn(m.text, BTN_HOW_TO))
def how_to_use(message):
    uid = message.from_user.id
    limit = get_free_limit()
    text = create_header("❓ 𝐇ᴏᴡ 𝐓ᴏ 𝐔sᴇ") + (
        "1️⃣ <b>Click</b> 🌐 𝐆ᴇᴛ 𝐒ᴏᴜʀᴄᴇ\n"
        "2️⃣ <b>Send</b> a public website URL\n"
        "3️⃣ <b>Wait</b> for extraction\n"
        "4️⃣ <b>Download</b> the ZIP file\n\n"
        f"📦 <b>Free Limit:</b> {limit} extractions\n"
        "💎 <b>Premium:</b> Unlimited\n\n"
        "➿➿➿➿➿➿➿➿➿➿➿\n"
        "💡 <b>𝐓ɪᴘs:</b>\n"
        "• Only public frontend resources\n"
        "• Large sites may take longer\n"
        "• Some sites block extraction"
    )
    safe_send(uid, text, reply_markup=main_menu(uid))

# ═══════════════════════════════════════
# 📞 SUPPORT
# ═══════════════════════════════════════
@bot.message_handler(func=lambda m: match_btn(m.text, BTN_SUPPORT))
def support(message):
    uid = message.from_user.id
    link = get_setting("support_link", "@rtcadmin9x")
    text = create_header("📞 𝐒ᴜᴘᴘᴏʀᴛ") + (
        f"💬 <b>Contact:</b> {link}\n\n"
        "🚀 <b>Response Time:</b> 24 hours\n"
        "🛡️ <b>Safe & Friendly Support</b>"
    )
    markup = types.InlineKeyboardMarkup().add(
        btn("𝐎ᴘᴇɴ 𝐒ᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{link.lstrip('@')}",
            style="success", icon="💬"))
    safe_send(uid, text, reply_markup=markup)

# ═══════════════════════════════════════
# 👑 ADMIN PANEL
# ═══════════════════════════════════════
@bot.message_handler(func=lambda m: match_btn(m.text, BTN_ADMIN))
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    safe_send(message.chat.id,
        create_header("👑 𝐀ᴅᴍɪɴ 𝐏ᴀɴᴇʟ") +
        "📊 𝐌ᴀɴᴀɢᴇ 𝐘ᴏᴜʀ 𝐁ᴏᴛ:",
        reply_markup=admin_menu())

@bot.message_handler(func=lambda m: match_btn(m.text, A_USERMODE))
def back_user(message):
    if not is_admin(message.from_user.id): return
    clear_state(message.from_user.id)
    safe_send(message.chat.id, "🏠 <b>𝐔𝐬𝐞𝐫 𝐌ᴏᴅᴇ 𝐀ᴄᴛɪᴠᴇ.</b>",
              reply_markup=main_menu(message.from_user.id))

# ━━━ 📊 Dashboard ━━━
@bot.message_handler(func=lambda m: match_btn(m.text, A_DASH) and is_admin(m.from_user.id))
def admin_dashboard(message):
    total_users = execute_query("SELECT COUNT(*) as c FROM users", fetchone=True)["c"]
    total_extr = execute_query("SELECT COALESCE(SUM(extractions),0) as c FROM users", fetchone=True)["c"]
    prem_count = execute_query("SELECT COUNT(*) as c FROM users WHERE is_premium=1", fetchone=True)["c"]
    hist_count = execute_query("SELECT COUNT(*) as c FROM history", fetchone=True)["c"]
    limit = get_free_limit()

    safe_send(message.chat.id,
        create_header("📊 𝐃ᴀsʜʙᴏᴀʀᴅ") +
        f"👥 <b>Total Users:</b> {total_users}\n"
        f"📦 <b>Total Extractions:</b> {total_extr}\n"
        f"💎 <b>Premium Users:</b> {prem_count}\n"
        f"📜 <b>History Records:</b> {hist_count}\n"
        f"🔒 <b>Free Limit:</b> {limit}\n"
        f"✨ <b>Premium Emojis:</b> {len(PREMIUM_EMOJIS)}"
    )

# ━━━ 📁 All User Files ━━━
@bot.message_handler(func=lambda m: match_btn(m.text, A_ALLFILES) and is_admin(m.from_user.id))
def admin_all_files(message):
    rows = execute_query(
        "SELECT h.id, h.user_id, h.url, h.extracted_at, h.zip_path, u.name "
        "FROM history h LEFT JOIN users u ON u.id = h.user_id "
        "ORDER BY h.id DESC LIMIT 20",
        fetchall=True
    ) or []

    if not rows:
        return safe_send(message.chat.id,
            create_header("📁 𝐀ʟʟ 𝐅ɪʟᴇs") +
            "📭 <b>এখনো কোনো file নেই।</b>",
            reply_markup=admin_menu())

    text = create_header("📁 𝐀ʟʟ 𝐅ɪʟᴇs") + f"📊 <b>শেষ 20টি file</b>\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)

    for r in rows:
        uname = r["name"] or f"User {r['user_id']}"
        url_short = (r["url"] or "")[:50]
        text += (f"🆔 <code>#{r['id']}</code> | 👤 {uname}\n"
                 f"   🔗 <code>{url_short}</code>\n"
                 f"   📅 {r['extracted_at']}\n\n")

        zip_path = r["zip_path"] or ""
        zip_ok = bool(zip_path) and os.path.isfile(zip_path)
        if zip_ok:
            markup.add(btn(f"📥 𝐃ᴏᴡɴʟᴏᴀᴅ #{r['id']} — {uname[:15]}",
                           cb=f"adm_dl_{r['id']}", style="success", icon="📥"))
            markup.add(btn(f"🗑️ 𝐑ᴇᴍᴏᴠᴇ #{r['id']}",
                           cb=f"adm_rm_{r['id']}", style="danger", icon="🗑️"))
        else:
            markup.add(btn(f"❌ 𝐍ᴏ ꜰɪʟᴇ #{r['id']}",
                           cb="adm_no_file", style="danger", icon="❌"))

    markup.add(btn("🔄 𝐑ᴇꜰʀᴇꜱʜ", cb="adm_refresh_files",
                   style="primary", icon="🔄"))
    markup.add(btn("🗑️ 𝐂ʟᴇᴀʀ ᴏʟᴅ ꜰɪʟᴇs", cb="adm_clear_files",
                   style="danger", icon="🗑️"))

    safe_send(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "adm_refresh_files" and is_admin(c.from_user.id))
def adm_refresh_files(call):
    bot.answer_callback_query(call.id, "🔄 Refreshed!")
    rows = execute_query(
        "SELECT h.id, h.user_id, h.url, h.extracted_at, h.zip_path, u.name "
        "FROM history h LEFT JOIN users u ON u.id = h.user_id "
        "ORDER BY h.id DESC LIMIT 20",
        fetchall=True
    ) or []
    if not rows:
        return bot.edit_message_text(format_pe(create_header("📁 𝐀ʟʟ 𝐅ɪʟᴇs") +
                                               "📭 <b>কোনো file নেই।</b>"),
                                     call.message.chat.id, call.message.message_id,
                                     parse_mode="HTML")

    text = create_header("📁 𝐀ʟʟ 𝐅ɪʟᴇs") + f"📊 <b>শেষ 20টি file</b>\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        uname = r["name"] or f"User {r['user_id']}"
        text += (f"🆔 <code>#{r['id']}</code> | 👤 {uname}\n"
                 f"   🔗 <code>{(r['url'] or '')[:50]}</code>\n"
                 f"   📅 {r['extracted_at']}\n\n")
        zip_ok = bool(r["zip_path"]) and os.path.isfile(r["zip_path"])
        if zip_ok:
            markup.add(btn(f"📥 𝐃ᴏᴡɴʟᴏᴀᴅ #{r['id']} — {uname[:15]}",
                           cb=f"adm_dl_{r['id']}", style="success", icon="📥"))
            markup.add(btn(f"🗑️ 𝐑ᴇᴍᴏᴠᴇ #{r['id']}",
                           cb=f"adm_rm_{r['id']}", style="danger", icon="🗑️"))
        else:
            markup.add(btn(f"❌ 𝐍ᴏ ꜰɪʟᴇ #{r['id']}",
                           cb="adm_no_file", style="danger", icon="❌"))
    markup.add(btn("🔄 𝐑ᴇꜰʀᴇꜱʜ", cb="adm_refresh_files", style="primary", icon="🔄"))
    markup.add(btn("🗑️ 𝐂ʟᴇᴀʀ ᴏʟᴅ ꜰɪʟᴇs", cb="adm_clear_files", style="danger", icon="🗑️"))

    try:
        bot.edit_message_text(format_pe(text), call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode="HTML")
    except Exception: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_dl_") and is_admin(c.from_user.id))
def adm_download_file(call):
    try:
        hist_id = int(call.data.split("_")[2])
    except Exception:
        return bot.answer_callback_query(call.id, "❌ Invalid ID", show_alert=True)

    row = execute_query("SELECT * FROM history WHERE id=?", (hist_id,), fetchone=True)
    if not row:
        return bot.answer_callback_query(call.id, "❌ File not found!", show_alert=True)

    zip_path = row["zip_path"]
    if not zip_path or not os.path.isfile(zip_path):
        return bot.answer_callback_query(call.id,
            "❌ ZIP file server-এ নেই।", show_alert=True)

    user_row = execute_query("SELECT name, username FROM users WHERE id=?", (row["user_id"],), fetchone=True)
    uname = user_row["name"] if user_row else f"User {row['user_id']}"
    tg_user = f"@{user_row['username']}" if (user_row and user_row["username"]) else "—"

    # ✅ Send with custom filename
    safe_send_doc(
        call.from_user.id,
        zip_path,
        ZIP_FILENAME,
        caption=(
            create_header(f"📥 𝐅ɪʟᴇ #{hist_id}") +
            f"👤 <b>User:</b> {uname}\n"
            f"🔗 <b>TG:</b> {tg_user}\n"
            f"🆔 <b>User ID:</b> <code>{row['user_id']}</code>\n"
            f"🌐 <b>URL:</b> <code>{row['url'][:80]}</code>\n"
            f"📅 <b>Date:</b> {row['extracted_at']}"
        )
    )
    bot.answer_callback_query(call.id, "✅ File sent!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_rm_") and is_admin(c.from_user.id))
def adm_remove_file(call):
    try:
        hist_id = int(call.data.split("_")[2])
    except Exception:
        return bot.answer_callback_query(call.id, "❌ Invalid ID", show_alert=True)

    row = execute_query("SELECT * FROM history WHERE id=?", (hist_id,), fetchone=True)
    if not row:
        return bot.answer_callback_query(call.id, "❌ Already removed", show_alert=True)

    if row["zip_path"] and os.path.isfile(row["zip_path"]):
        try: os.remove(row["zip_path"])
        except Exception: pass

    execute_query("DELETE FROM history WHERE id=?", (hist_id,))
    bot.answer_callback_query(call.id, f"🗑️ File #{hist_id} removed!", show_alert=True)

    call.data = "adm_refresh_files"
    adm_refresh_files(call)

@bot.callback_query_handler(func=lambda c: c.data == "adm_no_file" and is_admin(c.from_user.id))
def adm_no_file(call):
    bot.answer_callback_query(call.id, "❌ File server-এ নেই।", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "adm_clear_files" and is_admin(c.from_user.id))
def adm_clear_files(call):
    rows = execute_query("SELECT id, zip_path FROM history ORDER BY id DESC", fetchall=True) or []
    deleted = 0
    for i, r in enumerate(rows):
        if i >= 5:
            if r["zip_path"] and os.path.isfile(r["zip_path"]):
                try:
                    os.remove(r["zip_path"])
                    deleted += 1
                except Exception: pass
            execute_query("UPDATE history SET zip_path='' WHERE id=?", (r["id"],))
    bot.answer_callback_query(call.id, f"🗑️ Purged {deleted} old files (kept latest 5).", show_alert=True)

# ━━━ 👥 All Users ━━━
@bot.message_handler(func=lambda m: match_btn(m.text, A_ALLUSERS) and is_admin(m.from_user.id))
def admin_all_users(message):
    rows = execute_query(
        "SELECT id, name, username, extractions, is_premium, join_date "
        "FROM users ORDER BY id DESC LIMIT 30",
        fetchall=True
    ) or []

    if not rows:
        return safe_send(message.chat.id,
            create_header("👥 𝐀ʟʟ 𝐔sᴇʀs") + "📭 No users yet.",
            reply_markup=admin_menu())

    text = create_header("👥 𝐀ʟʟ 𝐔sᴇʀs") + f"📊 <b>শেষ 30 জন User</b>\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)

    for r in rows:
        prem = "💎" if r["is_premium"] else "👤"
        text += (f"{prem} <b>{r['name']}</b> | <code>{r['id']}</code>\n"
                 f"   @{r['username'] or '—'} | 📦 {r['extractions']}\n\n")

        markup.add(btn(f"⚙️ 𝐌ᴀɴᴀɢᴇ — {r['name'][:15]}",
                       cb=f"adm_user_{r['id']}", style="primary", icon="⚙️"))

    safe_send(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_user_") and is_admin(c.from_user.id))
def adm_user_manage(call):
    try:
        uid = int(call.data.split("_")[2])
    except Exception:
        return bot.answer_callback_query(call.id, "❌ Invalid ID", show_alert=True)

    u = execute_query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
    if not u:
        return bot.answer_callback_query(call.id, "❌ User not found!", show_alert=True)

    hist_count = execute_query("SELECT COUNT(*) as c FROM history WHERE user_id=?", (uid,), fetchone=True)["c"]

    text = create_header(f"👤 𝐔sᴇʀ 𝐃ᴇᴛᴀɪʟs") + (
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"🏷 <b>Name:</b> {u['name']}\n"
        f"🔗 <b>Username:</b> @{u['username'] or '—'}\n"
        f"📅 <b>Joined:</b> {u['join_date']}\n\n"
        f"📦 <b>Extractions:</b> {u['extractions']}\n"
        f"📜 <b>History Records:</b> {hist_count}\n"
        f"💎 <b>Premium:</b> {'✅ Yes' if u['is_premium'] else '❌ No'}"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    if u["is_premium"]:
        markup.add(btn("❌ 𝐑ᴇᴍᴏᴠᴇ 𝐏ʀᴇᴍɪᴜᴍ", cb=f"adm_rmprem_{uid}",
                       style="danger", icon="❌"))
    else:
        markup.add(btn("💎 𝐆ɪᴠᴇ 𝐏ʀᴇᴍɪᴜᴍ", cb=f"adm_addprem_{uid}",
                       style="success", icon="💎"))
    markup.add(btn("📜 𝐕ɪᴇᴡ 𝐅ɪʟᴇs", cb=f"adm_userfiles_{uid}",
                   style="primary", icon="📜"))
    markup.add(btn("🗑️ 𝐃ᴇʟᴇᴛᴇ 𝐔sᴇʀ", cb=f"adm_deluser_{uid}",
                   style="danger", icon="🗑️"))
    markup.add(btn("🔙 𝐁ᴀᴄᴋ", cb="adm_back_users",
                   style="primary", icon="🔙"))

    try:
        bot.edit_message_text(format_pe(text), call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode="HTML")
    except Exception:
        safe_send(call.from_user.id, text, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_addprem_") and is_admin(c.from_user.id))
def adm_add_prem(call):
    uid = int(call.data.split("_")[2])
    execute_query("UPDATE users SET is_premium=1 WHERE id=?", (uid,))
    bot.answer_callback_query(call.id, "💎 Premium enabled!", show_alert=True)
    call.data = f"adm_user_{uid}"
    adm_user_manage(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_rmprem_") and is_admin(c.from_user.id))
def adm_rm_prem(call):
    uid = int(call.data.split("_")[2])
    execute_query("UPDATE users SET is_premium=0 WHERE id=?", (uid,))
    bot.answer_callback_query(call.id, "❌ Premium removed!", show_alert=True)
    call.data = f"adm_user_{uid}"
    adm_user_manage(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_deluser_") and is_admin(c.from_user.id))
def adm_del_user(call):
    uid = int(call.data.split("_")[2])
    rows = execute_query("SELECT zip_path FROM history WHERE user_id=?", (uid,), fetchall=True) or []
    for r in rows:
        if r["zip_path"] and os.path.isfile(r["zip_path"]):
            try: os.remove(r["zip_path"])
            except Exception: pass
    execute_query("DELETE FROM history WHERE user_id=?", (uid,))
    execute_query("DELETE FROM users WHERE id=?", (uid,))
    bot.answer_callback_query(call.id, "🗑️ User deleted!", show_alert=True)
    call.data = "adm_back_users"
    adm_back_users(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_userfiles_") and is_admin(c.from_user.id))
def adm_user_files(call):
    uid = int(call.data.split("_")[2])
    rows = execute_query("SELECT id, url, extracted_at, zip_path FROM history WHERE user_id=? ORDER BY id DESC LIMIT 20",
                         (uid,), fetchall=True) or []
    if not rows:
        return bot.answer_callback_query(call.id, "📭 No files found.", show_alert=True)

    text = create_header(f"📜 𝐅ɪʟᴇs ᴏꜰ 𝐔sᴇʀ {uid}")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        ok = r["zip_path"] and os.path.isfile(r["zip_path"])
        text += f"🆔 <code>#{r['id']}</code> — {r['extracted_at']}\n"
        if ok:
            markup.add(btn(f"📥 𝐃ᴏᴡɴʟᴏᴀᴅ #{r['id']}", cb=f"adm_dl_{r['id']}",
                           style="success", icon="📥"))
    markup.add(btn("🔙 𝐁ᴀᴄᴋ", cb=f"adm_user_{uid}", style="primary", icon="🔙"))
    safe_send(call.from_user.id, text, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "adm_back_users" and is_admin(c.from_user.id))
def adm_back_users(call):
    rows = execute_query(
        "SELECT id, name, username, extractions, is_premium FROM users ORDER BY id DESC LIMIT 30",
        fetchall=True
    ) or []
    text = create_header("👥 𝐀ʟʟ 𝐔sᴇʀs") + f"📊 <b>শেষ 30 জন</b>\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        prem = "💎" if r["is_premium"] else "👤"
        text += f"{prem} <b>{r['name']}</b> | <code>{r['id']}</code> | 📦 {r['extractions']}\n"
        markup.add(btn(f"⚙️ 𝐌ᴀɴᴀɢᴇ — {r['name'][:15]}",
                       cb=f"adm_user_{r['id']}", style="primary", icon="⚙️"))
    try:
        bot.edit_message_text(format_pe(text), call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode="HTML")
    except Exception:
        safe_send(call.from_user.id, text, reply_markup=markup)
    bot.answer_callback_query(call.id)

# ━━━ 📜 All History ━━━
@bot.message_handler(func=lambda m: match_btn(m.text, A_HISTORY) and is_admin(m.from_user.id))
def admin_all_history(message):
    total = execute_query("SELECT COUNT(*) as c FROM history", fetchone=True)["c"]

    if total == 0:
        return safe_send(message.chat.id,
            create_header("📜 𝐀ʟʟ 𝐇ɪsᴛᴏʀʏ") +
            "📭 <b>এখনো কোনো record নেই।</b>",
            reply_markup=admin_menu())

    rows = execute_query(
        "SELECT h.id, h.user_id, h.url, h.extracted_at, h.zip_path, "
        "       COALESCE(u.name, 'Unknown') as uname, "
        "       COALESCE(u.username, '') as unick "
        "FROM history h LEFT JOIN users u ON u.id = h.user_id "
        "ORDER BY h.id DESC LIMIT 15",
        fetchall=True
    ) or []

    text = create_header("📜 𝐀ʟʟ 𝐇ɪsᴛᴏʀʏ") + (
        f"📊 <b>Total Records:</b> {total}\n"
        f"📄 <b>Showing:</b> Last {len(rows)}\n\n"
        "➿➿➿➿➿➿➿➿➿➿➿\n\n"
    )

    for i, r in enumerate(rows, 1):
        url_short = (r["url"] or "")[:50]
        uname = r["uname"] or "Unknown"
        unick = f"@{r['unick']}" if r["unick"] else "—"
        zip_ok = bool(r["zip_path"]) and os.path.isfile(r["zip_path"])
        status = "✅" if zip_ok else "❌"

        text += (
            f"<b>{i}.</b> 🆔 <code>#{r['id']}</code>  {status}\n"
            f"   👤 {uname} ({unick})\n"
            f"   🔗 <code>{url_short}</code>\n"
            f"   📅 {r['extracted_at']}\n\n"
        )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(btn("📁 𝐆ᴏ ᴛᴏ 𝐀ʟʟ 𝐅ɪʟᴇs", cb="adm_goto_files",
                   style="success", icon="📁"))
    markup.add(btn("🔄 𝐑ᴇꜰʀᴇꜱʜ", cb="adm_refresh_history",
                   style="primary", icon="🔄"))

    safe_send(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "adm_goto_files" and is_admin(c.from_user.id))
def adm_goto_files(call):
    bot.answer_callback_query(call.id, "📁 Opening All Files...")
    rows = execute_query(
        "SELECT h.id, h.user_id, h.url, h.extracted_at, h.zip_path, u.name "
        "FROM history h LEFT JOIN users u ON u.id = h.user_id "
        "ORDER BY h.id DESC LIMIT 20",
        fetchall=True
    ) or []

    text = create_header("📁 𝐀ʟʟ 𝐅ɪʟᴇs") + f"📊 <b>শেষ 20টি file</b>\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        uname = r["name"] or f"User {r['user_id']}"
        text += (f"🆔 <code>#{r['id']}</code> | 👤 {uname}\n"
                 f"   🔗 <code>{(r['url'] or '')[:50]}</code>\n"
                 f"   📅 {r['extracted_at']}\n\n")
        zip_ok = bool(r["zip_path"]) and os.path.isfile(r["zip_path"])
        if zip_ok:
            markup.add(btn(f"📥 𝐃ᴏᴡɴʟᴏᴀᴅ #{r['id']} — {uname[:15]}",
                           cb=f"adm_dl_{r['id']}", style="success", icon="📥"))
            markup.add(btn(f"🗑️ 𝐑ᴇᴍᴏᴠᴇ #{r['id']}",
                           cb=f"adm_rm_{r['id']}", style="danger", icon="🗑️"))
    markup.add(btn("🔄 𝐑ᴇꜰʀᴇꜱʜ", cb="adm_refresh_files", style="primary", icon="🔄"))

    try:
        bot.edit_message_text(format_pe(text), call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode="HTML")
    except Exception:
        safe_send(call.from_user.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "adm_refresh_history" and is_admin(c.from_user.id))
def adm_refresh_history(call):
    bot.answer_callback_query(call.id, "🔄 Refreshed!")
    total = execute_query("SELECT COUNT(*) as c FROM history", fetchone=True)["c"]
    rows = execute_query(
        "SELECT h.id, h.user_id, h.url, h.extracted_at, h.zip_path, "
        "       COALESCE(u.name, 'Unknown') as uname, "
        "       COALESCE(u.username, '') as unick "
        "FROM history h LEFT JOIN users u ON u.id = h.user_id "
        "ORDER BY h.id DESC LIMIT 15",
        fetchall=True
    ) or []

    text = create_header("📜 𝐀ʟʟ 𝐇ɪsᴛᴏʀʏ") + (
        f"📊 <b>Total Records:</b> {total}\n"
        f"📄 <b>Showing:</b> Last {len(rows)}\n\n"
        "➿➿➿➿➿➿➿➿➿➿➿\n\n"
    )
    for i, r in enumerate(rows, 1):
        uname = r["uname"] or "Unknown"
        unick = f"@{r['unick']}" if r["unick"] else "—"
        zip_ok = bool(r["zip_path"]) and os.path.isfile(r["zip_path"])
        status = "✅" if zip_ok else "❌"
        text += (f"<b>{i}.</b> 🆔 <code>#{r['id']}</code>  {status}\n"
                 f"   👤 {uname} ({unick})\n"
                 f"   🔗 <code>{(r['url'] or '')[:50]}</code>\n"
                 f"   📅 {r['extracted_at']}\n\n")

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(btn("📁 𝐆ᴏ ᴛᴏ 𝐀ʟʟ 𝐅ɪʟᴇs", cb="adm_goto_files",
                   style="success", icon="📁"))
    markup.add(btn("🔄 𝐑ᴇꜰʀᴇꜱʜ", cb="adm_refresh_history",
                   style="primary", icon="🔄"))

    try:
        bot.edit_message_text(format_pe(text), call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode="HTML")
    except Exception: pass

# ━━━ 📢 Broadcast ━━━
@bot.message_handler(func=lambda m: match_btn(m.text, A_BCAST) and is_admin(m.from_user.id))
def bcast_start(message):
    set_state(message.from_user.id, "WAIT_BCAST")
    safe_send(message.chat.id, "📢 <b>Send broadcast message:</b>", reply_markup=cancel_menu())

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "WAIT_BCAST")
def handle_bcast(message):
    if match_btn(message.text, BTN_CANCEL): return handle_cancel(message)
    uid = message.from_user.id
    users = execute_query("SELECT id FROM users", fetchall=True)
    safe_send(uid, "⏳ <b>Broadcasting...</b>", reply_markup=admin_menu())

    succ, fail = 0, 0
    for (u_id,) in users:
        try:
            bot.copy_message(u_id, uid, message.message_id)
            succ += 1
        except Exception:
            fail += 1
        time.sleep(0.05)

    clear_state(uid)
    safe_send(uid, f"✅ <b>Broadcast Complete!</b>\n\n✔️ Success: {succ}\n❌ Failed: {fail}",
              reply_markup=admin_menu())

# ━━━ ⚙️ Settings ━━━
@bot.message_handler(func=lambda m: match_btn(m.text, A_SETTINGS) and is_admin(m.from_user.id))
def admin_settings(message):
    support = get_setting("support_link", "@rtcadmin9x")
    price = get_setting("premium_price", "99")
    limit = get_free_limit()
    text = create_header("⚙️ 𝐒ᴇᴛᴛɪɴɢs") + (
        f"📞 <b>Support:</b> {support}\n"
        f"💰 <b>Premium Price:</b> {price} BDT\n"
        f"🔒 <b>Free Limit:</b> {limit} extractions\n\n"
        "👇 যেটা পরিবর্তন করতে চান সেটি সিলেক্ট করুন:"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(btn("📞 𝐒ᴇᴛ 𝐒ᴜᴘᴘᴏʀᴛ", cb="adm_set_support",
                   style="primary", icon="📞"))
    markup.add(btn("💰 𝐒ᴇᴛ 𝐏ʀᴇᴍɪᴜᴍ 𝐏ʀɪᴄᴇ", cb="adm_set_price",
                   style="success", icon="💰"))
    markup.add(btn("🔒 𝐒ᴇᴛ 𝐅ʀᴇᴇ 𝐋ɪᴍɪᴛ", cb="adm_set_limit",
                   style="primary", icon="🔒"))
    safe_send(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_support" and is_admin(c.from_user.id))
def adm_set_support(call):
    clear_state(call.from_user.id)
    set_state(call.from_user.id, "WAIT_SET_SUPPORT")
    bot.answer_callback_query(call.id, "📞 Send new support link")
    safe_send(call.from_user.id,
        create_header("📞 𝐒ᴇᴛ 𝐒ᴜᴘᴘᴏʀᴛ") +
        "📌 Send new support link\n\n"
        "Example: <code>@rtcadmin9x</code>\n\n"
        "🔙 /cancel দিয়ে বাতিল করুন।",
        reply_markup=cancel_menu())

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "WAIT_SET_SUPPORT" and is_admin(m.from_user.id))
def save_support(message):
    if match_btn(message.text, BTN_CANCEL) or message.text == '/cancel':
        return handle_cancel(message)
    val = (message.text or "").strip()
    if not val:
        return safe_send(message.chat.id, "❌ Empty value!", reply_markup=cancel_menu())
    set_setting("support_link", val)
    clear_state(message.from_user.id)
    safe_send(message.chat.id, f"✅ <b>Support link updated!</b>\n\n📞 <b>New:</b> {val}",
              reply_markup=admin_menu())

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_price" and is_admin(c.from_user.id))
def adm_set_price(call):
    clear_state(call.from_user.id)
    set_state(call.from_user.id, "WAIT_SET_PRICE")
    bot.answer_callback_query(call.id, "💰 Send new premium price")
    safe_send(call.from_user.id,
        create_header("💰 𝐒ᴇᴛ 𝐏ʀᴇᴍɪᴜᴍ 𝐏ʀɪᴄᴇ") +
        "📌 Send new premium price\n\n"
        "Example: <code>199</code>\n\n"
        "🔙 /cancel দিয়ে বাতিল করুন।",
        reply_markup=cancel_menu())

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "WAIT_SET_PRICE" and is_admin(m.from_user.id))
def save_price(message):
    if match_btn(message.text, BTN_CANCEL) or message.text == '/cancel':
        return handle_cancel(message)
    try:
        val = float((message.text or "").strip())
        if val < 0: raise ValueError
        set_setting("premium_price", str(val))
        clear_state(message.from_user.id)
        safe_send(message.chat.id, f"✅ <b>Premium price set to {val} BDT</b>",
                  reply_markup=admin_menu())
    except Exception:
        safe_send(message.chat.id, "❌ Invalid number! Positive number পাঠান।",
                  reply_markup=cancel_menu())

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_limit" and is_admin(c.from_user.id))
def adm_set_limit(call):
    clear_state(call.from_user.id)
    set_state(call.from_user.id, "WAIT_SET_LIMIT")
    bot.answer_callback_query(call.id, "🔒 Send new free limit")
    safe_send(call.from_user.id,
        create_header("🔒 𝐒ᴇᴛ 𝐅ʀᴇᴇ 𝐋ɪᴍɪᴛ") +
        "📌 Send new free limit\n\n"
        "Example: <code>20</code>\n\n"
        "💡 এই সংখ্যাটি free users এর maximum extractions হবে।\n\n"
        "🔙 /cancel দিয়ে বাতিল করুন।",
        reply_markup=cancel_menu())

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "WAIT_SET_LIMIT" and is_admin(m.from_user.id))
def save_limit(message):
    if match_btn(message.text, BTN_CANCEL) or message.text == '/cancel':
        return handle_cancel(message)
    try:
        val = int((message.text or "").strip())
        if val < 0: raise ValueError
        set_setting("free_limit", str(val))
        clear_state(message.from_user.id)
        safe_send(message.chat.id, f"✅ <b>Free limit set to {val} extractions</b>",
                  reply_markup=admin_menu())
    except Exception:
        safe_send(message.chat.id, "❌ Invalid number! Positive integer পাঠান।",
                  reply_markup=cancel_menu())

# ━━━ ✨ Emoji Manager ━━━
@bot.message_handler(func=lambda m: match_btn(m.text, A_EMOJIS) and is_admin(m.from_user.id))
def emoji_mgr(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(btn("𝐔ᴘʟᴏᴀᴅ 𝐏ᴀᴄᴋ", cb="emj_json", style="success", icon="📥"))
    markup.add(btn("𝐂ʟᴇᴀʀ 𝐀ʟʟ", cb="emj_clear", style="danger", icon="🗑️"))
    safe_send(message.chat.id, create_header("✨ 𝐄ᴍᴏᴊɪ 𝐌ᴀɴᴀɢᴇʀ"), reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "emj_json" and is_admin(c.from_user.id))
def cb_emj_json(call):
    clear_state(call.from_user.id)
    set_state(call.from_user.id, "WAIT_EMOJI_PACK")
    bot.answer_callback_query(call.id, "📥 Send pack file")
    safe_send(call.from_user.id,
              "📁 <b>Send the .json or .txt Emoji Pack file.</b>",
              reply_markup=cancel_menu())

@bot.message_handler(content_types=["document"],
                     func=lambda m: get_state(m.from_user.id) == "WAIT_EMOJI_PACK")
def handle_emoji_file(message):
    if match_btn(message.text, BTN_CANCEL): return handle_cancel(message)
    uid = message.from_user.id
    try:
        file_info = bot.get_file(message.document.file_id)
        raw = bot.download_file(file_info.file_path)
        parsed = parse_emoji_pack(raw, message.document.file_name)
        if not parsed:
            clear_state(uid)
            return safe_send(uid, "⚠️ No valid entries found.", reply_markup=admin_menu())
        added_ids, added_keys = merge_emoji_pack(parsed)
        clear_state(uid)
        safe_send(uid,
            create_header("✅ 𝐄ᴍᴏᴊɪ 𝐏ᴀᴄᴋ 𝐀ᴅᴅᴇᴅ") +
            f"📁 <b>File:</b> {message.document.file_name}\n"
            f"🆔 <b>New IDs:</b> {added_ids}\n"
            f"🤩 <b>New Emojis:</b> {added_keys}\n"
            f"📊 <b>Total Pool:</b> {len(PREMIUM_EMOJIS)}",
            reply_markup=admin_menu())
    except Exception as e:
        clear_state(uid)
        safe_send(uid, f"❌ <b>Error:</b> {e}", reply_markup=admin_menu())

@bot.callback_query_handler(func=lambda c: c.data == "emj_clear" and is_admin(c.from_user.id))
def cb_emj_clear(call):
    global EMOJI_TO_PREMIUM, PREMIUM_EMOJIS
    EMOJI_TO_PREMIUM = {}
    PREMIUM_EMOJIS = [MAIN_EMOJI_ID]
    save_json(PREMIUM_EMOJI_DB_FILE, {})
    bot.answer_callback_query(call.id, "✅ All custom emojis cleared!", show_alert=True)

# ═══════════════════════════════════════
# BOOTSTRAP
# ═══════════════════════════════════════
if __name__ == "__main__":
    init_db()
    print("╔══════════════════════════════════════╗")
    print("║   🌐 𝐋ɪɴᴋ 𝐓ᴏ 𝐂ᴏᴅᴇ 𝐁ᴏᴛ 🌐           ║")
    print("║                                      ║")
    print("║   🚀 𝐁ᴏᴛ 𝐒ᴛᴀʀᴛᴇᴅ                  ║")
    print("║   💾 𝐃ᴀᴛᴀʙᴀsᴇ 𝐑ᴇᴀᴅʏ               ║")
    print("║   ✅ 𝐅ɪɴᴀʟ — 𝐍ᴏ 𝐇ɪsᴛᴏʀʏ 𝐁ᴜᴛᴛᴏɴ     ║")
    print("║   📦 𝐙𝐈𝐏: " + ZIP_FILENAME.ljust(23) + " ║")
    print("╚══════════════════════════════════════╝")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
