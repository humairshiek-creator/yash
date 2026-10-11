import asyncio
import json
import os
import random
import time
import tempfile
import urllib.request
import urllib.parse
import platform
import telegram.error
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram.request import HTTPXRequest
import logging
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import yt_dlp
import subprocess
import re
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PFP_DIR = os.path.join(os.path.dirname(__file__), "pfp_pool")
os.makedirs(PFP_DIR, exist_ok=True)

_http_session = None
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(15)

async def get_http_session():
    global _http_session
    if _http_session is None:
        _http_session = aiohttp.ClientSession()
    return _http_session

def escape_md(text):
    chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(chars)}])', r'\\\1', text)

try:
    import psutil
except ImportError:
    psutil = None

ADMIN_FILE = "mexxys.json"
CONFIG_FILE = "mexxy_config.json"
START_TIME = time.time()
TOTAL_MESSAGES_SENT = 0
TOTAL_NC_CHANGES = 0

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f)
    except:
        pass

bot_config = load_config()
CMD_PREFIX = bot_config.get("prefix", "~")
OWNER_ID = bot_config.get("owner_id", 7328966456)
CHAT_ID = OWNER_ID
DEFAULT_VIDEO_URL = bot_config.get("video_url", "https://files.catbox.moe/oo6mw7.mp4")
DEFAULT_HELP_VIDEO_URL = bot_config.get("help_video_url", "https://files.catbox.moe/oo6mw7.mp4")
DEFAULT_GAMEOVER_VIDEO_URL = bot_config.get("gameover_video_url", "https://files.catbox.moe/aseks3.mp4")

THREAD_POOL = ThreadPoolExecutor(max_workers=200)
MAX_CONCURRENT_TASKS = 500
CURRENT_DELAY = 0.0
BATCH_SIZE = 100

# ── TOKENS (editable via ~addtoken / ~removetoken) ──────────────────────────
TOKENS = [
    "8354932069:AAFfl3PNpafIOWG5j62Tb_1arKPF9oHf8XA",
    "8724851856:AAHiJSyXlWLgLt0qPnfgob2pBSzROU0iw-s",
    "8264223544:AAH5rMhdurSVZif_0fM-cy5fwSE1ulrzCZc",
    "8988711107:AAEEIuaizBMFDN4vPXAKtLt24CcCYEFx3V0",
    "8719289765:AAEeR230mK2LjuQxdCW4ztX1OgMCm8J72mU",
    "8930325802:AAGLydzPrZH_k1ULhViABncPqhjwtqMskwA",
    "8756793381:AAFVLcf4zT3OrmfK4b08PIxxRrhuGiHz_-0",
    "8879561246:AAEyk6hgN7Is2kdUhmpdkgTaPvcCtyFmuzw",
    "8898614910:AAHXSbFU-ZZ4swX5gfcP_s9M-F8yk81oMNg",
    "8846312535:AAG3EOKpgUBz1h5Dzht-2C8YyjOvHRF4iko",
]
# ── NC TEMPLATES (NCX.PY) ────────────────────────────────────────────────────
NC_TEMPLATES = {
    "nc1": "{prefix} ⋆｡ﾟ☁︎｡𝐂ʏᴜ 𝐑ᴇ मदरचोद बाप के सामने 𝐅ʏᴛᴇʀ 𝐁ᴀɴᴇɢᴀ ⋆𓂃 ོ☼𓂃 🐕 💓 🐕 💓 🐕 💓 🐕 💓मदरचोद({emo})",
    "nc2": " {base} {emo} 𝐂𝐇𝐔𝐃𝐀𝐈 𝐊𝐇𝐀 𝐑𝐀𝐍𝐃𝐈 🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍🖤🤍",
    "nc3": "{emo}{base}⁀➷𝐓eʀʏ 𝐌ᴀᴀ 𝐊o 𝐂ʜᴜᴅɴe 𝐊ᴀ 𝐓ɪᴍe 𝐇6ɢʏᴀ⁀➷{time} {emo}",
    "nc4": "{base} 𓂃{pattern}",
}

NC_EMOJIS   = ["🤡","🥸","😶‍🌫️","🫠","🥴","🤑","😈","👿","😵‍💫","🤧","🥲","😬","🫡","🧑‍💻","🤪","😎","🤓","🧐","🤯","🥳","😏","😒","😞","😔","😋"]
NC_HEARTS   = ["🩷","♥️","❤️‍🩹","💝","🤍","🩶","🖤","🤎","💜","💙","🩵","💚","💛","🧡","❤️","💗","💔","❣️","💕","💞","💓","💖","💘","💌"]
TIMENC_EMOJIS = ["🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚","🕛"]
NC_PATTERNS = ["🎀","🌸","🌺","🌷","🌹","💐","✨","⭐","🌟","💫","⚡","🔥","💎","🎪","🎨","🖌️","🎭","🎯","🏆","🎲"]

# Aliases for old MXS streams
GODNC_EMOJIS  = NC_EMOJIS
RAIDNC_HEARTS = NC_HEARTS
WORDNC_EMOJIS = NC_HEARTS
EMONC_PATTERNS = NC_PATTERNS

# ── SPAM (NCX.PY text) ───────────────────────────────────────────────────────
SPAMEMO_EMOJIS = NC_HEARTS
DEFAULT_SPAMEMO_THREADS = 20
MAX_THREADS = 50
MIN_THREADS = 20

SPOTIFY_API = "https://saavnapi-nine.vercel.app/result/"
BOT_COOLDOWNS = {}

# ── ADMIN HELPERS ─────────────────────────────────────────────────────────────
def load_admins():
    if os.path.exists(ADMIN_FILE):
        try:
            with open(ADMIN_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_admins(admins):
    with open(ADMIN_FILE, 'w') as f:
        json.dump(list(admins), f)

admin_ids = load_admins()
admin_ids.add(OWNER_ID)
admin_ids.add(7396734905)

def is_admin(user_id):
    return user_id in admin_ids

def only_admin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update or not update.effective_user:
            return
        if not is_admin(update.effective_user.id):
            if update.message:
                await update.message.reply_text("❌ 𝐉ᴀᴋᴇ ⋆ ˚｡⋆୨୧˚ oggy ˚୨୧⋆｡˚ ⋆ 𝐒ᴇ 𝐒ᴜᴅᴏ 𝐋ᴇᴋᴇ 𝐀ᴀ😂")
            return
        return await func(update, context)
    return wrapper

def only_sudo(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update or not update.effective_user:
            return
        uid = update.effective_user.id
        if uid == OWNER_ID or uid == 7396734905:
            return await func(update, context)
        if update.message:
            await update.message.reply_text("❌ 𝐉ᴀᴋᴇ ⋆ ˚｡⋆୨୧˚ oggy ˚୨୧⋆｡˚ ⋆ 𝐒ᴇ 𝐒ᴜᴅᴏ 𝐋ᴇᴋᴇ 𝐀ᴀ🤢")
        return
    return wrapper

# ── SPAM (NCX.PY message text) ────────────────────────────────────────────────
def get_spamemo_message(target):
    upper_target = target.upper()
    target_tag = f"「 {upper_target} 」"
    emoji = SPAMEMO_EMOJIS[random.randint(0, len(SPAMEMO_EMOJIS) - 1)]
    line = f"{target_tag} 𝑻𝑹𝒀 𝑴𝑨𝑲𝑨 𝑲𝑨𝑳𝑨 𝑲𝑨𝑺𝑯𝑴𝑰𝑹𝑰 🅱︎🅾︎🆂︎🅳︎🅰︎ 🅿︎🅷︎🅰︎🆃︎ 𝑮𝒀𝑨 🧸🎐({emoji})𒀸"
    return "\n\n".join([line] * 10)

async def spamemo_stream(bot, chat_id, target_text, stream_id, stop_event, bot_id):
    global TOTAL_MESSAGES_SENT
    while not stop_event.is_set():
        try:
            message = get_spamemo_message(target_text)
            await bot.send_message(chat_id, message)
            TOTAL_MESSAGES_SENT += 1
            await asyncio.sleep(0)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(0)

async def spamemo_multi(bot, chat_id, target_text, num_streams, stop_event, bot_id):
    streams = [asyncio.create_task(spamemo_stream(bot, chat_id, target_text, i, stop_event, bot_id)) for i in range(num_streams)]
    try:
        await stop_event.wait()
    finally:
        for s in streams:
            s.cancel()

def set_delay(value):
    global CURRENT_DELAY
    if 0 <= value <= 5:
        CURRENT_DELAY = value
        return True
    return False

def get_delay():
    return CURRENT_DELAY

# ── SAFE SET TITLE (NCX.PY smart cooldown) ────────────────────────────────────
async def safe_set_chat_title(bot, chat_id, title):
    global BOT_COOLDOWNS
    bot_id = getattr(bot, "id", None)
    if bot_id:
        now = time.time()
        cooldown_until = BOT_COOLDOWNS.get(bot_id, 0)
        if cooldown_until > now:
            await asyncio.sleep(cooldown_until - now)
            return False
    safe_title = title[:128]
    try:
        await bot.set_chat_title(chat_id, safe_title)
        return True
    except telegram.error.RetryAfter as e:
        if bot_id:
            BOT_COOLDOWNS[bot_id] = time.time() + e.retry_after
        await asyncio.sleep(e.retry_after)
    except Exception:
        pass
    return False

# ── NCX.PY FAST NC STREAMS ────────────────────────────────────────────────────
async def ultra_nc1_stream(bot, chat_id, prefix, stop_event):
    global TOTAL_NC_CHANGES
    while not stop_event.is_set():
        try:
            emo = random.choice(NC_HEARTS)
            raw = f"{emo} {prefix} ⋆｡ﾟ☁︎｡𝐂ʏᴜ 𝐑ᴇ मदरचोद बाप के सामने 𝐅ʏᴛᴇʀ 𝐁ᴀɴᴇɢᴀ ⋆𓂃 ོ☼𓂃 🐕 💓 🐕 💓 🐕 💓 🐕 💓मदरचोद"
            if await safe_set_chat_title(bot, chat_id, raw[:128]):
                TOTAL_NC_CHANGES += 1
        except Exception:
            pass
        await asyncio.sleep(CURRENT_DELAY if CURRENT_DELAY > 0 else 0)

async def ultra_nc2_stream(bot, chat_id, base_text, stop_event):
    global TOTAL_NC_CHANGES
    sem = asyncio.Semaphore(20)
    active_tasks = set()

    async def worker(t):
        global TOTAL_NC_CHANGES
        try:
            if await safe_set_chat_title(bot, chat_id, t):
                TOTAL_NC_CHANGES += 1
        except Exception:
            pass
        finally:
            sem.release()

    try:
        while not stop_event.is_set():
            await sem.acquire()
            try:
                emo = random.choice(NC_EMOJIS)
                title = NC_TEMPLATES["nc2"].format(base=base_text, emo=emo)
                task = asyncio.create_task(worker(title))
                active_tasks.add(task)
                task.add_done_callback(active_tasks.discard)
            except Exception:
                sem.release()
            await asyncio.sleep(CURRENT_DELAY if CURRENT_DELAY > 0 else 0.02)
    finally:
        for t in list(active_tasks):
            t.cancel()

async def ultra_nc3_stream(bot, chat_id, base, stop_event):
    global TOTAL_NC_CHANGES
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    while not stop_event.is_set():
        try:
            now = datetime.now(timezone.utc).astimezone(ist_offset)
            ns = time.perf_counter_ns() % 1_000_000_000
            emo = random.choice(TIMENC_EMOJIS)
            time_str = f"{now.strftime('%H:%M:%S')}:{ns // 1_000_000:03d}"
            title = NC_TEMPLATES["nc3"].format(base=base, time=time_str, emo=emo)
            if await safe_set_chat_title(bot, chat_id, title):
                TOTAL_NC_CHANGES += 1
        except Exception:
            pass
        await asyncio.sleep(CURRENT_DELAY if CURRENT_DELAY > 0 else 0)

async def ultra_nc4_stream(bot, chat_id, base, stop_event):
    global TOTAL_NC_CHANGES
    sem = asyncio.Semaphore(40)
    active_tasks = set()

    async def worker(t):
        global TOTAL_NC_CHANGES
        try:
            if await safe_set_chat_title(bot, chat_id, t):
                TOTAL_NC_CHANGES += 1
        except Exception:
            pass
        finally:
            sem.release()

    try:
        while not stop_event.is_set():
            await sem.acquire()
            try:
                pattern = random.choice(NC_PATTERNS)
                title = NC_TEMPLATES["nc4"].format(base=base, pattern=pattern)
                task = asyncio.create_task(worker(title))
                active_tasks.add(task)
                task.add_done_callback(active_tasks.discard)
            except Exception:
                sem.release()
            await asyncio.sleep(CURRENT_DELAY if CURRENT_DELAY > 0 else 0)
    finally:
        for t in list(active_tasks):
            t.cancel()

# ── OLD MXS NC STREAMS (kept for compat) ─────────────────────────────────────
async def ultra_nc_stream(bot, chat_id, base_text, stop_event):
    global TOTAL_NC_CHANGES
    while not stop_event.is_set():
        emo = random.choice(GODNC_EMOJIS)
        title = f"🐷 {base_text} 🐷 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊6 𝐂ʜ6ᴅ𝐊ᴇ x oggy  𝐍6 𝐔sᴋɪ 𝐒6ᴀʟ 𝐓6ᴅ 𝐃ɪɪɪ 🦋✨{emo}𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫"
        if await safe_set_chat_title(bot, chat_id, title):
            TOTAL_NC_CHANGES += 1
        await asyncio.sleep(0)

async def ultra_raidnc_stream(bot, chat_id, prefix, stop_event):
    global TOTAL_NC_CHANGES
    suffix = "ᏕᎯᎽ ɪ ʟᴏ𝐯6 ʏ6ᴜ ⋆ ˚｡⋆୨୧˚oggy˚୨୧⋆｡˚ ⋆ ᴘᴀᴘᴀ 💝💫"
    while not stop_event.is_set():
        try:
            emo = random.choice(RAIDNC_HEARTS)
            title = f"{prefix} {suffix} ι ℓσνє уσυ тσσ {prefix} вєтα 𝗔𝗕 𝗖𝗨𝗗𝗔𝗜 𝗞𝗛𝗔𝗢 🌷🪽({emo})"
            if len(title) > 128:
                title = title[:125] + "..."
            if await safe_set_chat_title(bot, chat_id, title):
                TOTAL_NC_CHANGES += 1
        except Exception:
            pass
        await asyncio.sleep(0.1)

async def ultra_time_stream(bot, chat_id, base, stop_event):
    global TOTAL_NC_CHANGES
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    while not stop_event.is_set():
        now = datetime.now(timezone.utc).astimezone(ist_offset)
        ns = time.perf_counter_ns() % 1_000_000_000
        emo = random.choice(TIMENC_EMOJIS)
        title = f"{emo}{base}⁀➷𝐓6ʀʏ 𝐌ᴀᴀ 𝐊6 𝐂ʜᴜᴅɴ6 𝐊ᴀ 𝐓ɪᴍ6 𝐇6ɢʏᴀ⁀➷{now.strftime('%H:%M:%S')}:{ns // 1_000_000:03d} {emo}"
        if await safe_set_chat_title(bot, chat_id, title):
            TOTAL_NC_CHANGES += 1
        await asyncio.sleep(0)

async def ultra_wordnc_stream(bot, chat_id, base_text, stop_event):
    global TOTAL_NC_CHANGES
    while not stop_event.is_set():
        emo = random.choice(WORDNC_EMOJIS)
        title = f"{emo} {base_text} »» 𝐂ʜᴀɴᴅ 𝐓ᴀʀ6 𝐒ʙ 𝐃6ᴋʜ 𝐑ʜ6 𝐓ʜ6 🌙 𝐉ʙ o6ggy 𝐍6 𝐓6ʀɪ 𝐌ᴀᴀ 𝐊6 𝐑ᴀᴛ 𝐌6 𝐂ʜ6ᴅᴀ 🐍𒈙"
        if await safe_set_chat_title(bot, chat_id, title):
            TOTAL_NC_CHANGES += 1
        await asyncio.sleep(0)

async def ultra_emonc_stream(bot, chat_id, base, stop_event):
    global TOTAL_NC_CHANGES
    while not stop_event.is_set():
        pattern = random.choice(EMONC_PATTERNS)
        title = f"𓂃{pattern}´-˚⋆‌﹒{base} 𓂃{pattern}´-˚⋆‌ ."
        if await safe_set_chat_title(bot, chat_id, title):
            TOTAL_NC_CHANGES += 1
        await asyncio.sleep(0)

# ── CONTROLLER ────────────────────────────────────────────────────────────────
class AttackController:
    def __init__(self):
        self.stop_events = {}
        self.active_tasks = {}
        self.spamemo_threads = DEFAULT_SPAMEMO_THREADS
        self.nc_threads = 20

    def get_stop_event(self, chat_id, attack_type):
        key = f"{chat_id}_{attack_type}"
        if key not in self.stop_events:
            self.stop_events[key] = asyncio.Event()
        return self.stop_events[key]

    def stop_attack(self, chat_id, attack_type):
        key = f"{chat_id}_{attack_type}"
        if key in self.stop_events:
            self.stop_events[key].set()
            self.stop_events[key] = asyncio.Event()
            return True
        return False

    def stop_all(self, chat_id=None):
        for key in list(self.stop_events.keys()):
            if chat_id is None or key.startswith(str(chat_id)):
                self.stop_events[key].set()
                self.stop_events[key] = asyncio.Event()
        return True

    def set_spamemo_threads(self, threads):
        self.spamemo_threads = max(20, min(50, threads))
        return self.spamemo_threads

    def stop_spamemo(self, chat_id):
        return self.stop_attack(chat_id, "spamemo")

controller = AttackController()
bots = []
apps = []
active_attacks = {}
MAIN_BOT_ID = None

def get_cmd_name(text):
    if text.startswith(CMD_PREFIX):
        return text[len(CMD_PREFIX):].split()[0].lower()
    return None

# ── NCX.PY STYLE NC COMMANDS ─────────────────────────────────────────────────
async def _cmd_nc_generic(update, context, nc_type, stream_func):
    if context.bot.id != MAIN_BOT_ID:
        return
    if not context.args:
        return await update.message.reply_text(f"⚠️ Usage: {CMD_PREFIX}{nc_type} <name>")
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    controller.stop_attack(chat_id, nc_type)
    key = f"{chat_id}_{nc_type}"
    if key in active_attacks:
        for t in active_attacks[key]: t.cancel()
        del active_attacks[key]
    stop_event = controller.get_stop_event(chat_id, nc_type)
    stop_event.clear()
    tasks = [asyncio.create_task(stream_func(bot, chat_id, base, stop_event)) for bot in bots]
    active_attacks[key] = tasks
    await update.message.reply_text(
        f"☣️ *{nc_type.upper()} ACTIVATED* ☣️\n"
        f"📝 Name: `{base}`\n🤖 Bots: `{len(bots)}`\n"
        f"⚡ Mode: `MAX SPEED`\n🛑 Use `{CMD_PREFIX}stop` to stop",
        parse_mode="Markdown"
    )

@only_admin
async def cmd_nc1(update, context): await _cmd_nc_generic(update, context, "nc1", ultra_nc1_stream)
@only_admin
async def cmd_nc2(update, context): await _cmd_nc_generic(update, context, "nc2", ultra_nc2_stream)
@only_admin
async def cmd_nc3(update, context): await _cmd_nc_generic(update, context, "nc3", ultra_nc3_stream)
@only_admin
async def cmd_nc4(update, context): await _cmd_nc_generic(update, context, "nc4", ultra_nc4_stream)

# ── OLD MXS NC COMMANDS ───────────────────────────────────────────────────────
async def _cmd_mxs_nc(update, context, attack_type, stream_func, label):
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        return await update.message.reply_text(f"⚠️ Usage: {CMD_PREFIX}{attack_type} <name>")
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    controller.stop_attack(chat_id, attack_type)
    stop_event = controller.get_stop_event(chat_id, attack_type)
    stop_event.clear()
    tasks = []
    for bot in bots:
        for _ in range(controller.nc_threads):
            tasks.append(asyncio.create_task(stream_func(bot, chat_id, base, stop_event)))
    active_attacks[f"{chat_id}_{attack_type}"] = tasks
    await update.message.reply_text(
        f"⚡ *{label} ACTIVATED* ⚡\n📝 Name: `{base}`\n"
        f"🤖 Bots: `{len(bots)}`\n🎨 Streams/Bot: `{controller.nc_threads}`\n🛑 Use `{CMD_PREFIX}stop` to stop",
        parse_mode="Markdown"
    )

@only_admin
async def cmd_godnc(update, context): await _cmd_mxs_nc(update, context, "godnc", ultra_nc_stream, "GODNC")
@only_admin
async def cmd_raidnc(update, context):
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        return await update.message.reply_text(f"⚠️ Usage: {CMD_PREFIX}raidnc <name>")
    prefix = " ".join(context.args)
    chat_id = update.message.chat_id
    attack_type = "raidnc"
    controller.stop_attack(chat_id, attack_type)
    key = f"{chat_id}_{attack_type}"
    if key in active_attacks:
        for t in active_attacks[key]: t.cancel()
        del active_attacks[key]
    stop_event = controller.get_stop_event(chat_id, attack_type)
    stop_event.clear()
    tasks = [asyncio.create_task(ultra_raidnc_stream(bot, chat_id, prefix, stop_event)) for bot in bots]
    active_attacks[key] = tasks
    await update.message.reply_text(
        f"💀 *RAIDNC ACTIVATED* 💀\n📝 Prefix: `{prefix}`\n"
        f"🤖 Bots: `{len(bots)}`\n🛑 Use `{CMD_PREFIX}stop` to stop",
        parse_mode="Markdown"
    )
@only_admin
async def cmd_timenc(update, context): await _cmd_mxs_nc(update, context, "timenc", ultra_time_stream, "TIMENC")
@only_admin
async def cmd_wordnc(update, context): await _cmd_mxs_nc(update, context, "wordnc", ultra_wordnc_stream, "WORDNC")
@only_admin
async def cmd_emonc(update, context): await _cmd_mxs_nc(update, context, "emonc", ultra_emonc_stream, "EMONC")

@only_admin
async def cmd_gameover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        await update.message.reply_text(f"⚠️ Usage: {CMD_PREFIX}gameover <target>")
        return
    target = escape_md(' '.join(context.args))
    chat_id = update.message.chat_id
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    game_over_msg = (
        f"=================================\n"
        f"          Y O U  A R E  D E A D\n"
        f"=================================\n\n"
        f"🩸 𝙑𝙞𝙘𝙩𝙞𝙢: {target}\n"
        f"🩸 𝙏𝙞𝙢𝙚 𝙤𝙛 𝘿𝙚𝙖𝙩𝙝: {current_time}\n"
        f"🩸 𝘿𝙖𝙩𝙚: {current_date}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f" oggy 𝗕𝗢𝗧 𝗦𝗨𝗣𝗥𝗘𝗠𝗔𝗖𝗬 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    gameover_video = bot_config.get("gameover_video_url", DEFAULT_GAMEOVER_VIDEO_URL)
    gameover_type = bot_config.get("gameover_video_type", "video")
    try:
        if gameover_type == "photo":
            await update.message.reply_photo(photo=gameover_video)
        else:
            await update.message.reply_video(video=gameover_video)
    except Exception as e:
        await update.message.reply_text(f"❌ Video error: {e}")
    await update.message.reply_text(game_over_msg, parse_mode="Markdown")
    try:
        await context.bot.set_chat_title(chat_id, f"☠️ DECEASED: {target.upper()} ☠️"[:128])
    except:
        pass
    try:
        await context.bot.set_chat_description(chat_id, f"💀 GAME OVER - {target} - {current_date} {current_time}")
    except:
        pass

@only_admin
async def cmd_spamemo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        await update.message.reply_text(f"⚠️ Usage: {CMD_PREFIX}spamemo <text>")
        return
    target = ' '.join(context.args)
    chat_id = update.message.chat_id
    attack_type = "spamemo"
    controller.stop_spamemo(chat_id)
    stop_event = controller.get_stop_event(chat_id, attack_type)
    stop_event.clear()
    tasks = [asyncio.create_task(spamemo_multi(bot, chat_id, target, controller.spamemo_threads, stop_event, bot.id)) for bot in bots]
    active_attacks[f"{chat_id}_{attack_type}"] = tasks
    total_streams = len(bots) * controller.spamemo_threads
    await update.message.reply_text(
        f"🔱 *SPAMEMO ACTIVATED* 🔱\n📝 Target: `{target}`\n"
        f"🤖 Bots: `{len(bots)}`\n🧵 Threads/bot: `{controller.spamemo_threads}`\n"
        f"⚡ Total streams: `{total_streams}`\n🛑 Use `{CMD_PREFIX}stopspam` to stop",
        parse_mode="Markdown"
    )

@only_admin
async def cmd_spamthreads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        await update.message.reply_text(f"📊 *Current spam threads:* `{controller.spamemo_threads}`\n📝 Usage: `{CMD_PREFIX}spamthreads <20-50>`", parse_mode="Markdown")
        return
    try:
        threads = int(context.args[0])
        old = controller.spamemo_threads
        new = controller.set_spamemo_threads(threads)
        await update.message.reply_text(f"✅ Spam threads changed from `{old}` to `{new}`", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Invalid number! Use 20-50")

@only_admin
async def cmd_threadstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    total_streams = len(bots) * controller.spamemo_threads
    await update.message.reply_text(
        f"⚡ *THREAD STATUS* ⚡\n\n📨 Spamemo Threads: `{controller.spamemo_threads}`\n"
        f"🤖 Total Bots: `{len(bots)}`\n⚡ Total Streams: `{total_streams}`\n🚀 Speed: `INSTANT`",
        parse_mode="Markdown"
    )

@only_admin
async def cmd_stopspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    chat_id = update.message.chat_id
    if controller.stop_spamemo(chat_id):
        key = f"{chat_id}_spamemo"
        if key in active_attacks:
            for t in active_attacks[key]: t.cancel()
            del active_attacks[key]
        await update.message.reply_text("🛑 *SPAMEMO STOPPED!* 🛑", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ No active spamemo attack")

@only_admin
async def cmd_ncthreads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        await update.message.reply_text(f"📊 *Current NC threads/bot:* `{controller.nc_threads}`\n📝 Usage: `{CMD_PREFIX}ncthreads <1-50>`", parse_mode="Markdown")
        return
    try:
        threads = int(context.args[0])
        old = controller.nc_threads
        controller.nc_threads = max(1, min(50, threads))
        await update.message.reply_text(f"✅ NC threads changed from `{old}` to `{controller.nc_threads}`", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Invalid number! Use 1-50")

# ── MUSIC (NCX.PY fast version) ───────────────────────────────────────────────
async def cmd_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎵 Download song from Spotify/JioSaavn"""
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        await update.message.reply_text(f"📋 Usage: {CMD_PREFIX}song <song name>\nExample: {CMD_PREFIX}song Tum Hi Ho")
        return
    query = ' '.join(context.args)
    status_msg = await update.message.reply_text(f"🔍 Searching *{query}*...", parse_mode="Markdown")
    try:
        session = await get_http_session()
        async with session.get(f"{SPOTIFY_API}?query={query}") as resp:
            if resp.status != 200:
                await status_msg.edit_text(f"❌ API error: Status {resp.status}")
                return
            data = await resp.json()
        songs = data.get('results', []) or data.get('songs', []) or data.get('data', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        if not songs:
            await status_msg.edit_text(f"❌ No results found for: {query}")
            return
        valid_songs = [s for s in songs if s.get('media_url')]
        if not valid_songs:
            await status_msg.edit_text(f"❌ No downloadable songs found for: {query}")
            return
        song = valid_songs[0]
        song_name = song.get('song') or song.get('title') or song.get('name') or query
        media_url = song.get('media_url')
        caption = f"🎵 *{song_name}* 𝐌ᴇxxʏ"
        await status_msg.edit_text(f"⏳ Downloading *{song_name}*...")
        try:
            async with DOWNLOAD_SEMAPHORE:
                session = await get_http_session()
                async with session.get(media_url, timeout=30) as audio_resp:
                    if audio_resp.status != 200:
                        await status_msg.edit_text(f"❌ Failed to download: Status {audio_resp.status}")
                        return
                    audio_data = await audio_resp.read()
        except asyncio.TimeoutError:
            await status_msg.edit_text("❌ Download timeout. Please try again.")
            return
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        try:
            await update.message.reply_audio(audio=open(tmp_path, 'rb'), title=song_name[:100], caption=caption, parse_mode="Markdown")
        finally:
            try: os.unlink(tmp_path)
            except: pass
        await status_msg.delete()
    except aiohttp.ClientError as e:
        await status_msg.edit_text(f"❌ Network error: {str(e)}")
    except json.JSONDecodeError:
        await status_msg.edit_text("❌ Invalid response from API")
    except Exception as e:
        logger.error(f"Song error: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)}")

async def cmd_spotify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎵 Search Spotify and pick from top 5"""
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        await update.message.reply_text(f"📋 Usage: {CMD_PREFIX}spotify <song name>\nExample: {CMD_PREFIX}spotify Kesariya")
        return
    try:
        pick = int(context.args[0])
        songs = context.chat_data.get('spotify_cache', [])
        if songs and 1 <= pick <= len(songs):
            song = songs[pick - 1]
            context.chat_data['spotify_cache'] = []
            media_url = song.get('media_url')
            if not media_url:
                await update.message.reply_text("❌ No download URL for this song.")
                return
            song_name = song.get('song') or song.get('title') or 'Unknown'
            singer = song.get('singers') or song.get('artist') or ''
            album = song.get('album') or ''
            duration_raw = song.get('duration', 0)
            try:
                duration = int(float(duration_raw)) if duration_raw else 0
            except:
                duration = 0
            duration_str = f"{duration//60}:{duration%60:02d}" if duration > 0 else "Live"
            quality = '320kbps' if song.get('320kbps') == 'true' else 'HQ'
            image = song.get('image') or ''
            caption = f"🎵 *{song_name}*\n🎤 {singer}\n💿 {album}\n⏱️ {duration_str}\n📻 {quality} • JioSaavn/Spotify\n━━━━━━━━━━━━━━━━━━━━\n⚡ *𝐌6xxʏ ʙ6ᴛ*"
            status_msg = await update.message.reply_text(f"⏳ Downloading *{song_name}*...")
            if image:
                try:
                    session = await get_http_session()
                    async with session.get(image, timeout=10) as img_resp:
                        if img_resp.status == 200:
                            img_data = await img_resp.read()
                            await update.message.reply_photo(photo=img_data, caption=caption, parse_mode="Markdown")
                except:
                    await update.message.reply_text(caption, parse_mode="Markdown")
            else:
                await update.message.reply_text(caption, parse_mode="Markdown")
            try:
                session = await get_http_session()
                async with session.get(media_url, timeout=30) as audio_resp:
                    if audio_resp.status != 200:
                        await status_msg.edit_text(f"❌ Download failed: Status {audio_resp.status}")
                        return
                    audio_data = await audio_resp.read()
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name
                try:
                    await update.message.reply_audio(audio=open(tmp_path, 'rb'), title=song_name[:100], performer=singer[:100] if singer else "Unknown", duration=int(duration) if duration > 0 else None, caption=f"🎵 *{song_name[:100]}*", parse_mode="Markdown")
                finally:
                    try: os.unlink(tmp_path)
                    except: pass
            except asyncio.TimeoutError:
                await status_msg.edit_text("❌ Download timeout. Please try again.")
                return
            except Exception as e:
                await status_msg.edit_text(f"❌ Download error: {e}")
                return
            await status_msg.delete()
            return
    except ValueError:
        pass
    query = ' '.join(context.args)
    status_msg = await update.message.reply_text(f"🔍 Searching Spotify: *{query}*...")
    try:
        session = await get_http_session()
        async with session.get(f"{SPOTIFY_API}?query={query}", timeout=15) as resp:
            if resp.status != 200:
                await status_msg.edit_text(f"❌ API error: Status {resp.status}")
                return
            data = await resp.json()
        songs = data.get('results', []) or data.get('songs', []) or data.get('data', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        valid_songs = [s for s in songs if s.get('media_url')][:5]
        if not valid_songs:
            await status_msg.edit_text(f"❌ No downloadable songs found: {query}")
            return
        context.chat_data['spotify_cache'] = valid_songs
        msg = f"🎵 *SPOTIFY SEARCH RESULTS*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, s in enumerate(valid_songs, 1):
            duration_raw = s.get('duration', 0)
            try:
                duration = int(float(duration_raw)) if duration_raw else 0
            except:
                duration = 0
            dur_str = f"{duration//60}:{duration%60:02d}" if duration > 0 else ""
            song_title = s.get('song') or s.get('title') or 'Unknown'
            song_singer = s.get('singers') or s.get('artist') or '—'
            song_album = s.get('album') or '—'
            msg += f"*{i}.* 🎵 {song_title[:40]}\n   🎤 {song_singer[:30]}\n   💿 {song_album[:30]}{f' • ⏱️ {dur_str}' if dur_str else ''}\n\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n📋 Reply with: {CMD_PREFIX}spotify [1-{len(valid_songs)}]"
        await status_msg.edit_text(msg, parse_mode="Markdown")
    except aiohttp.ClientError as e:
        await status_msg.edit_text(f"❌ Network error: {str(e)}")
    except asyncio.TimeoutError:
        await status_msg.edit_text("❌ Request timeout. Please try again.")
    except json.JSONDecodeError:
        await status_msg.edit_text("❌ Invalid response from API")
    except Exception as e:
        logger.error(f"Spotify error: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)}")

async def download_youtube_audio(update, context, url):
    status_msg = await update.message.reply_text("⏳ Downloading audio...")
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'quiet': True, 'no_warnings': True, 'extract_flat': False,
    }
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts['outtmpl'] = f"{tmpdir}/%(title)s.%(ext)s"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    for ext in ['.mp3', '.webm', '.m4a']:
                        alt = filename.rsplit('.', 1)[0] + ext
                        if os.path.exists(alt):
                            filename = alt
                            break
                if os.path.exists(filename):
                    title = info.get('title', 'Audio')[:100]
                    uploader = info.get('uploader', 'YouTube')[:100]
                    duration = info.get('duration')
                    await update.message.reply_audio(audio=open(filename, 'rb'), title=title, performer=uploader, duration=duration, caption=f"🎵 *{title}*", parse_mode="Markdown")
                    await status_msg.delete()
                else:
                    await status_msg.edit_text("❌ Failed to download audio")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

async def cmd_yt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        await update.message.reply_text(f"📋 Usage: {CMD_PREFIX}yt <song name>")
        return
    try:
        pick = int(context.args[0])
        videos = context.chat_data.get('yt_cache', [])
        if videos and 1 <= pick <= len(videos):
            url = videos[pick-1]['url']
            context.chat_data['yt_cache'] = []
            await download_youtube_audio(update, context, url)
            return
    except ValueError:
        pass
    query = ' '.join(context.args)
    status_msg = await update.message.reply_text(f"🔍 Searching YouTube: *{query}*...")
    ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True, 'playlistend': 5}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            entries = info.get('entries', [])
        if not entries:
            await status_msg.edit_text(f"❌ No videos found: {query}")
            return
        cache = []
        for v in entries:
            video_id = v.get('id')
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id else v.get('webpage_url') or v.get('url')
            if not url: continue
            cache.append({'title': v.get('title', 'Unknown'), 'url': url, 'duration': v.get('duration', 0)})
        if not cache:
            await status_msg.edit_text("❌ No valid video URLs found")
            return
        context.chat_data['yt_cache'] = cache
        msg = f"🎵 *YOUTUBE SEARCH RESULTS*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, v in enumerate(cache, 1):
            dur = f"{v['duration']//60}:{v['duration']%60:02d}" if v.get('duration') else '?'
            msg += f"*{i}.* {v['title'][:50]}  [{dur}]\n"
        msg += f"\n━━━━━━━━━━━━━━━━━━━━\n📋 Reply with: {CMD_PREFIX}yt [1-{len(cache)}]"
        await status_msg.edit_text(msg, parse_mode="Markdown")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

# ── CHAT CONTROL ──────────────────────────────────────────────────────────────
@only_admin
async def cmd_upall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    chat_id = update.message.chat_id
    status_msg = await update.message.reply_text("⏳ Processing bots administration...")
    promoted, failed, not_in_chat = [], [], []
    current_bot = context.bot

    async def process_bot(bot):
        try:
            bot_id = bot.id
            bot_username = getattr(bot, 'username', None) or str(bot_id)
            try:
                member = await bot.get_chat_member(chat_id, bot_id)
                if member.status in ['left', 'kicked']:
                    return ('not_in_chat', bot_username)
            except:
                return ('not_in_chat', bot_username)
            try:
                await current_bot.promote_chat_member(chat_id=chat_id, user_id=bot_id, can_manage_chat=True, can_post_messages=True, can_edit_messages=True, can_delete_messages=True, can_manage_video_chats=True, can_restrict_members=True, can_promote_members=True, can_change_info=True, can_invite_users=True, can_pin_messages=True)
                return ('promoted', f"@{bot_username}")
            except Exception as e:
                return ('failed', f"@{bot_username} ({str(e)})")
        except:
            return None

    results = await asyncio.gather(*(process_bot(bot) for bot in bots))
    for res in results:
        if res:
            res_type, val = res
            if res_type == 'promoted': promoted.append(val)
            elif res_type == 'failed': failed.append(val)
            elif res_type == 'not_in_chat': not_in_chat.append(val)
    response = "👑 *ADMIN PROMOTION REPORT* 👑\n\n"
    if promoted: response += f"✅ *Promoted to Admin:*\n" + ", ".join(promoted) + "\n\n"
    if failed: response += f"❌ *Failed to Promote:*\n" + "\n".join(failed) + "\n\n"
    if not_in_chat:
        response += f"⚠️ *Bots Not in Chat:*\n"
        for username in not_in_chat:
            response += f"• @{username}: [Click to Add](https://t.me/{username}?startgroup=true)\n"
    await status_msg.edit_text(response, parse_mode="Markdown", disable_web_page_preview=True)

@only_admin
async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    chat_id = update.message.chat_id
    user_id = None
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try: user_id = int(context.args[0])
        except: await update.message.reply_text("❌ Invalid User ID"); return
    else:
        await update.message.reply_text(f"⚠️ Reply to a message or use `{CMD_PREFIX}mute <user_id>`"); return
    try:
        await context.bot.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text("🔇 *User muted successfully!*", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to mute: {e}")

@only_admin
async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    chat_id = update.message.chat_id
    user_id = None
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try: user_id = int(context.args[0])
        except: await update.message.reply_text("❌ Invalid User ID"); return
    else:
        await update.message.reply_text(f"⚠️ Reply to a message or use `{CMD_PREFIX}unmute <user_id>`"); return
    try:
        perms = ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True)
        await context.bot.restrict_chat_member(chat_id, user_id, perms)
        await update.message.reply_text("🔊 *User unmuted successfully!*", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to unmute: {e}")

@only_admin
async def cmd_muteall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    try:
        await context.bot.set_chat_permissions(update.message.chat_id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text("🔒 *Chat Locked!* 🔇", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

@only_admin
async def cmd_unmuteall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    try:
        perms = ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True)
        await context.bot.set_chat_permissions(update.message.chat_id, perms)
        await update.message.reply_text("🔓 *Chat Unlocked!* 🔊", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

@only_admin
async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    chat_id = update.message.chat_id
    attack_types = ["nc1","nc2","nc3","nc4","godnc","raidnc","timenc","wordnc","emonc","spamemo"]
    stopped = []
    for at in attack_types:
        if controller.stop_attack(chat_id, at):
            stopped.append(at)
        key = f"{chat_id}_{at}"
        if key in active_attacks:
            for t in active_attacks[key]: t.cancel()
            del active_attacks[key]
    if stopped:
        await update.message.reply_text(f"🛑 *STOPPED: {', '.join(stopped).upper()}* 🛑", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ No active attacks")

@only_sudo
async def cmd_stopall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    controller.stop_all()
    for key in list(active_attacks.keys()):
        for t in active_attacks[key]: t.cancel()
    active_attacks.clear()
    await update.message.reply_text("🛑 *ALL ATTACKS STOPPED EVERYWHERE* 🛑", parse_mode="Markdown")

@only_sudo
async def cmd_speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        await update.message.reply_text(f"⚡ *Current Delay:* `{get_delay()}` seconds\n📝 Usage: `{CMD_PREFIX}speed <0-5>`\n🔹 `0` = INSTANT", parse_mode="Markdown")
        return
    try:
        value = float(context.args[0])
        if set_delay(value):
            await update.message.reply_text(f"✅ *Speed Updated!*\n🕒 New Delay: `{value}` seconds", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Invalid value! Use `0` to `5` seconds")
    except ValueError:
        await update.message.reply_text("❌ Invalid number!")

@only_sudo
async def cmd_entrust(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    user_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else (int(context.args[0]) if context.args else None)
    if user_id:
        admin_ids.add(user_id)
        save_admins(admin_ids)
        await update.message.reply_text(f"✅ User `{user_id}` granted Executive Access.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ Reply to user or `{CMD_PREFIX}entrust <id>`")

@only_sudo
async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    user_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else (int(context.args[0]) if context.args else None)
    if user_id:
        if user_id == OWNER_ID or user_id == 8776247365:
            await update.message.reply_text("❌ Cannot remove Supreme Commander.")
            return
        if user_id in admin_ids:
            admin_ids.remove(user_id)
            save_admins(admin_ids)
            await update.message.reply_text(f"✅ User `{user_id}` stripped of privileges.", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ User is not an admin.")
    else:
        await update.message.reply_text(f"⚠️ Reply to user or `{CMD_PREFIX}revoke <id>`")

@only_sudo
async def cmd_setprefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CMD_PREFIX
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        await update.message.reply_text(f"📌 *Current Prefix:* `{CMD_PREFIX}`\n📝 Usage: `{CMD_PREFIX}setprefix <new_prefix>`", parse_mode="Markdown")
        return
    new_prefix = context.args[0]
    if len(new_prefix) > 5:
        await update.message.reply_text("❌ Prefix too long! Max 5 characters.")
        return
    old_prefix = CMD_PREFIX
    CMD_PREFIX = new_prefix
    bot_config["prefix"] = new_prefix
    save_config(bot_config)
    await update.message.reply_text(f"✅ *Prefix Updated!*\n🔁 Old: `{old_prefix}` → New: `{new_prefix}`", parse_mode="Markdown")

# ── CHANGEABLE OWNER ID ───────────────────────────────────────────────────────
@only_sudo
async def cmd_setowner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global OWNER_ID
    if context.bot.id != MAIN_BOT_ID: return
    if update.effective_user.id not in [OWNER_ID, 8776247365]:
        await update.message.reply_text("❌ Only the Supreme Commander can change owner.")
        return
    if not context.args:
        await update.message.reply_text(f"📌 *Current Owner ID:* `{OWNER_ID}`\n📝 Usage: `{CMD_PREFIX}setowner <user_id>`", parse_mode="Markdown")
        return
    try:
        new_owner = int(context.args[0])
        old_owner = OWNER_ID
        OWNER_ID = new_owner
        admin_ids.add(new_owner)
        save_admins(admin_ids)
        bot_config["owner_id"] = new_owner
        save_config(bot_config)
        await update.message.reply_text(f"✅ *Owner Changed!*\nOld: `{old_owner}` → New: `{new_owner}`", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID!")

# ── CHANGEABLE TOKENS ─────────────────────────────────────────────────────────
@only_sudo
async def cmd_addtoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    if not context.args:
        await update.message.reply_text(f"⚠️ Usage: `{CMD_PREFIX}addtoken <BOT_TOKEN>`")
        return
    new_token = context.args[0].strip()
    tokens_list = bot_config.get("extra_tokens", [])
    if new_token in tokens_list:
        await update.message.reply_text("❌ Token already exists!")
        return
    tokens_list.append(new_token)
    bot_config["extra_tokens"] = tokens_list
    save_config(bot_config)
    await update.message.reply_text(f"✅ Token added! Restart bot to apply.\nTotal extra tokens: `{len(tokens_list)}`", parse_mode="Markdown")

@only_sudo
async def cmd_removetoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    tokens_list = bot_config.get("extra_tokens", [])
    if not context.args:
        msg = f"📋 *Extra Token List ({len(tokens_list)} tokens):*\n"
        for i, t in enumerate(tokens_list, 1):
            short = t[:20] + "..." if len(t) > 20 else t
            msg += f"{i}. `{short}`\n"
        msg += f"\nUsage: `{CMD_PREFIX}removetoken <index>`"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
    try:
        idx = int(context.args[0]) - 1
        if 0 <= idx < len(tokens_list):
            removed = tokens_list.pop(idx)
            bot_config["extra_tokens"] = tokens_list
            save_config(bot_config)
            short = removed[:20] + "..." if len(removed) > 20 else removed
            await update.message.reply_text(f"✅ Token `{short}` removed! Restart to apply.", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Invalid index!")
    except ValueError:
        await update.message.reply_text("❌ Invalid number!")

@only_sudo
async def cmd_listtokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    all_tokens = list(TOKENS) + bot_config.get("extra_tokens", [])
    msg = f"📋 *All Tokens ({len(all_tokens)}):*\n"
    for i, t in enumerate(all_tokens, 1):
        short = t[:10] + "..." + t[-5:] if len(t) > 15 else t
        msg += f"{i}. `{short}`\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_leave(update, context):
    if getattr(context.bot, "id", None) != MAIN_BOT_ID: return
    status_msg = await update.message.reply_text("⏳ All bots leaving chat...")
    chat_id = update.effective_chat.id
    await asyncio.gather(*(bot.leave_chat(chat_id) for bot in bots), return_exceptions=True)
    try: await status_msg.edit_text("✅ All bots have left the chat.")
    except: pass

async def cmd_bye(update, context):
    if getattr(context.bot, "id", None) != MAIN_BOT_ID: return
    chat_id = update.effective_chat.id
    try: await update.message.delete()
    except: pass
    await asyncio.gather(*(bot.leave_chat(chat_id) for bot in bots), return_exceptions=True)

async def cmd_list(update, context):
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    names = "\n".join(a.user.full_name for a in admins)
    await update.message.reply_text(f"Admins:\n{names}")

# ── STATUS ────────────────────────────────────────────────────────────────────
async def get_status_text():
    uptime_str = str(timedelta(seconds=int(time.time() - START_TIME)))

    async def ping_bot(bot):
        start = time.time()
        try:
            bot_info = await asyncio.wait_for(bot.get_me(), timeout=1.5)
            return bot_info.username, round((time.time() - start) * 1000)
        except:
            return str(getattr(bot, 'id', 'Unknown')), -1

    pings = await asyncio.gather(*[ping_bot(bot) for bot in bots])
    bot_details = []
    online_count = 0
    for username, ping in pings:
        escaped_username = escape_md(username)
        if ping >= 0:
            bot_details.append(f"• @{escaped_username}: `{ping}ms` 🟢")
            online_count += 1
        else:
            bot_details.append(f"• @{escaped_username}: `Offline` 🔴")

    active_count = sum(1 for key in active_attacks if active_attacks[key])
    cpu_usage = "N/A"
    ram_usage = "N/A"
    if psutil:
        try:
            cpu_usage = f"{psutil.cpu_percent()}%"
            ram_usage = f"{psutil.virtual_memory().percent}%"
        except: pass

    status_text = (
        f"🎀 *⋆ ˚｡⋆👑˚oggy ˚👑⋆｡˚ STATUS* 🎀\n\n"
        f"⏱️ *Uptime:* `{uptime_str}`\n"
        f"🤖 *Bots Online:* `{online_count}/{len(bots)}`\n"
        f"⚡ *Active Attacks:* `{active_count}`\n"
        f"🕒 *Current Delay:* `{get_delay()}`s\n"
        f"🧵 *Spamemo Threads:* `{controller.spamemo_threads}`\n"
        f"🎨 *NC Threads/Bot:* `{controller.nc_threads}`\n"
        f"👑 *Owner ID:* `{OWNER_ID}`\n"
        f"👑 *Admins:* `{len(admin_ids)}`\n"
        f"📌 *Prefix:* `{CMD_PREFIX}`\n"
        f"📨 *Total Msg Sent:* `{TOTAL_MESSAGES_SENT}`\n"
        f"🔄 *Total NC Changes:* `{TOTAL_NC_CHANGES}`\n\n"
        f"📊 *System Resource:*\n"
        f"• CPU: `{cpu_usage}` | RAM: `{ram_usage}`\n"
        f"💻 *OS:* `{platform.system()}` | *Py:* `{platform.python_version()}`\n\n"
        f"📶 *Bot Pings:*\n" + "\n".join(bot_details)
    )
    return status_text

@only_admin
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    status_text = await get_status_text()
    await update.message.reply_text(status_text.replace("**", "*"), parse_mode="Markdown")

# ── HELP / MENU ───────────────────────────────────────────────────────────────
def get_help_text():
    p = CMD_PREFIX
    return f"""
╔════════════════════════════════╗
║    🎀 oggy 𝐓𝐄𝐑𝐌𝐈𝐍𝐀𝐋 🎀   ║
╚════════════════════════════════╝

⚔️ 𝐍𝐂 𝐀𝐓𝐓𝐀𝐂𝐊𝐒 (NCX style):
 ➪ {p}nc1 [name]   - Raid Assault
 ➪ {p}nc2 [name]   - God Mode
 ➪ {p}nc3 [name]   - Time Shift
 ➪ {p}nc4 [name]   - Custom Mix

⚔️ 𝐍𝐂 𝐀𝐓𝐓𝐀𝐂𝐊𝐒 (MXS style):
 ➪ {p}godnc [name] - God NC
 ➪ {p}raidnc [name]- Raid NC
 ➪ {p}timenc [name]- Time NC
 ➪ {p}wordnc [name]- Word NC
 ➪ {p}emonc [name] - Emo NC

💥 𝐒𝐏𝐀𝐌:
 ➪ {p}spamemo [tgt] - Emoji Spam
 ➪ {p}gameover [tgt]- Game Over

🎵 𝐌𝐔𝐒𝐈𝐂:
 ➪ {p}song [name]  - Search & Play
 ➪ {p}spotify [name]- Spotify Search
 ➪ {p}yt [name]    - YouTube

🛠️ 𝐂𝐎𝐍𝐓𝐑𝐎𝐋:
 ➪ {p}stop / {p}stopspam / {p}stopall
 ➪ {p}status / {p}help

⚙️ 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒:
 ➪ {p}speed [0-5]   - NC Delay
 ➪ {p}setprefix     - Change Prefix
 ➪ {p}ncthreads     - NC Threads
 ➪ {p}spamthreads   - Spam Threads
 ➪ {p}setvideo URL  - Change Menu Video
 ➪ {p}setowner ID   - Change Owner ID
 ➪ {p}addtoken TOK  - Add Bot Token
 ➪ {p}removetoken   - Remove Token

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ *Powered by oggy* ✨
"""

def get_category_menus():
    p = CMD_PREFIX
    return {
        "⚡ Speed & Settings": [f"{p}speed <0-5>", f"{p}setprefix <prefix>", f"{p}ncthreads <1-50>", f"{p}spamthreads <20-50>", f"{p}setowner <id>"],
        "🔥 NC Attack Modes": [f"{p}nc1 <name>", f"{p}nc2 <name>", f"{p}nc3 <name>", f"{p}nc4 <name>", f"{p}godnc <name>", f"{p}raidnc <name>", f"{p}timenc <name>", f"{p}wordnc <name>", f"{p}emonc <name>"],
        "💥 Spam Attack": [f"{p}spamemo <target>", f"{p}gameover <target>"],
        "🎵 Music Features": [f"{p}song <name>", f"{p}spotify <name>", f"{p}yt <name>"],
        "🔒 Chat Control": [f"{p}mute / unmute", f"{p}muteall / lock", f"{p}unmuteall / unlock", f"{p}upall", f"{p}leave", f"{p}bye"],
        "🛑 Stop Commands": [f"{p}stop", f"{p}stopspam", f"{p}stopall"],
        "👑 Admin Control": [f"{p}entrust", f"{p}revoke", f"{p}list", f"{p}addtoken", f"{p}removetoken"],
        "📊 Utility": [f"{p}status", f"{p}setvideo <url>", f"{p}help"],
    }

def get_help_keyboard():
    categories = get_category_menus()
    keyboard = []
    row = []
    for category in categories.keys():
        row.append(InlineKeyboardButton(category, callback_data=f"menu_{category}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("📊 Status", callback_data="status"), InlineKeyboardButton("🛑 Stop All", callback_data="stopall"), InlineKeyboardButton("💀 Game Over", callback_data="gameover_quick")])
    keyboard.append([InlineKeyboardButton("💥 Spamemo", callback_data="quick_spamemo"), InlineKeyboardButton("🎵 Song", callback_data="quick_song"), InlineKeyboardButton("📖 Full Help", callback_data="help_full")])
    return InlineKeyboardMarkup(keyboard)

def get_category_keyboard(category_name):
    categories = get_category_menus()
    commands = categories.get(category_name, [])
    keyboard = [[InlineKeyboardButton(f"▸ {cmd}", callback_data=f"cmd_{cmd.replace(' ', '_').replace('<', '').replace('>', '')}")] for cmd in commands]
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if context.bot.id != MAIN_BOT_ID:
        await query.answer("❌ Only main bot handles this!", show_alert=True)
        return
    if not is_admin(query.from_user.id):
        await query.answer("❌ You are not admin!", show_alert=True)
        return
    data = query.data

    async def send_help_text_menu():
        text = get_help_text()
        if query.message.video or query.message.photo:
            try: await query.message.delete()
            except: pass
            await context.bot.send_message(chat_id=query.message.chat_id, text=text, parse_mode="Markdown")
        else:
            await query.message.edit_text(text=text, parse_mode="Markdown")

    async def send_video_menu_callback():
        video_url = bot_config.get("video_url", DEFAULT_VIDEO_URL)
        media_type = bot_config.get("video_type", "video")
        caption = "🎥 *oggy  𝐁ᴏᴛ 𝐌ᴇɴᴜ* 🎥\n\nSelect a category below to explore commands:"
        reply_markup = get_help_keyboard()
        try: await query.message.delete()
        except: pass
        try:
            if media_type == "photo":
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=video_url, caption=caption, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=video_url, caption=caption, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"❌ Media error: {e}\n\n{caption}", reply_markup=reply_markup, parse_mode="Markdown")

    if data.startswith("menu_"):
        category = data.replace("menu_", "")
        if category in get_category_menus():
            keyboard = get_category_keyboard(category)
            if query.message.video or query.message.photo:
                try: await query.message.delete()
                except: pass
                await context.bot.send_message(chat_id=query.message.chat_id, text=f"📂 *{category}*\n\nSelect a command for details:", reply_markup=keyboard, parse_mode="Markdown")
            else:
                await query.message.edit_text(f"📂 *{category}*\n\nSelect a command for details:", reply_markup=keyboard, parse_mode="Markdown")
        elif category == "main":
            await send_video_menu_callback()
        return

    if data in ("help_full", "help"): await send_help_text_menu(); return
    if data == "video_menu": await send_video_menu_callback(); return
    if data == "status":
        status_text = await get_status_text()
        await query.message.reply_text(status_text, parse_mode="Markdown")
        return
    if data == "stopall":
        controller.stop_all()
        for key in list(active_attacks.keys()):
            for t in active_attacks[key]: t.cancel()
        active_attacks.clear()
        await query.message.reply_text("🛑 *ALL ATTACKS STOPPED EVERYWHERE* 🛑", parse_mode="Markdown")
        return
    if data == "gameover_quick":
        await query.message.reply_text(f"💀 *Game Over Command*\n\nUsage: `{CMD_PREFIX}gameover <target>`", parse_mode="Markdown"); return
    if data == "quick_spamemo":
        await query.message.reply_text(f"💥 *Spamemo Command*\n\nUsage: `{CMD_PREFIX}spamemo <target>`\nUse `{CMD_PREFIX}stopspam` to stop.", parse_mode="Markdown"); return
    if data == "quick_song":
        await query.message.reply_text(f"🎵 *Song Command*\n\nUsage: `{CMD_PREFIX}song <song name>`", parse_mode="Markdown"); return
    if data.startswith("cmd_"):
        cmd_text = data.replace("cmd_", "").replace("_", " ")
        await query.message.reply_text(f"📋 *Command:* `{cmd_text}`\n\nType this command to execute it.", parse_mode="Markdown"); return

async def send_video_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    video_url = bot_config.get("video_url", DEFAULT_VIDEO_URL)
    media_type = bot_config.get("video_type", "video")
    caption = get_help_text()
    try:
        if media_type == "photo": await update.message.reply_photo(photo=video_url)
        else: await update.message.reply_video(video=video_url)
    except Exception as e:
        await update.message.reply_text(f"❌ Media error: {e}")
    await update.message.reply_text(caption, parse_mode="Markdown")

@only_admin
async def cmd_help(update, context):
    if context.bot.id != MAIN_BOT_ID: return
    await send_video_menu(update, context)

@only_admin
async def cmd_menuvideo(update, context):
    if context.bot.id != MAIN_BOT_ID: return
    await send_video_menu(update, context)

@only_admin
async def cmd_helptext(update, context):
    if context.bot.id != MAIN_BOT_ID: return
    caption = get_help_text()
    help_video = bot_config.get("help_video_url", DEFAULT_HELP_VIDEO_URL)
    help_type = bot_config.get("help_video_type", "video")
    try:
        if help_type == "photo": await update.message.reply_photo(photo=help_video)
        else: await update.message.reply_video(video=help_video)
    except Exception as e:
        await update.message.reply_text(f"❌ Media error: {e}")
    await update.message.reply_text(text=caption, parse_mode="Markdown")

@only_sudo
async def cmd_setvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    url = None
    media_type = "video"
    if update.message.reply_to_message:
        reply = update.message.reply_to_message
        if reply.photo: url = reply.photo[-1].file_id; media_type = "photo"
        elif reply.video: url = reply.video.file_id
        elif reply.animation: url = reply.animation.file_id
        elif reply.document:
            mime = reply.document.mime_type or ""
            url = reply.document.file_id
            media_type = "photo" if mime.startswith("image/") else "video"
    if not url and context.args:
        url = context.args[0]
        if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]): media_type = "photo"
    if not url:
        current = bot_config.get("video_url", DEFAULT_VIDEO_URL)
        current_type = bot_config.get("video_type", "video")
        await update.message.reply_text(f"⚠️ Reply to media or use `{CMD_PREFIX}setvideo <url>`\nCurrent: `{current}` ({current_type})", parse_mode="Markdown")
        return
    bot_config["video_url"] = url
    bot_config["video_type"] = media_type
    save_config(bot_config)
    await update.message.reply_text(f"✅ *Menu Media updated!*\nType: `{media_type}`\nValue: `{url}`", parse_mode="Markdown")

@only_sudo
async def cmd_sethelpvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    url = None
    media_type = "video"
    if update.message.reply_to_message:
        reply = update.message.reply_to_message
        if reply.photo: url = reply.photo[-1].file_id; media_type = "photo"
        elif reply.video: url = reply.video.file_id
        elif reply.animation: url = reply.animation.file_id
        elif reply.document:
            mime = reply.document.mime_type or ""
            url = reply.document.file_id
            media_type = "photo" if mime.startswith("image/") else "video"
    if not url and context.args:
        url = context.args[0]
        if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]): media_type = "photo"
    if not url:
        current = bot_config.get("help_video_url", DEFAULT_HELP_VIDEO_URL)
        current_type = bot_config.get("help_video_type", "video")
        await update.message.reply_text(f"⚠️ Reply to media or use `{CMD_PREFIX}sethelpvideo <url>`\nCurrent: `{current}` ({current_type})", parse_mode="Markdown")
        return
    bot_config["help_video_url"] = url
    bot_config["help_video_type"] = media_type
    save_config(bot_config)
    await update.message.reply_text(f"✅ *Help Media updated!*\nType: `{media_type}`\nValue: `{url}`", parse_mode="Markdown")

@only_admin
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.bot.id != MAIN_BOT_ID: return
    await update.message.reply_text(
        f"🎀 *⋆ ˚｡⋆👑˚oggy ˚👑⋆｡˚ BOT ACTIVE* 🎀\n\n"
        f"📌 Current Prefix: `{CMD_PREFIX}`\n"
        f"🤖 Bots Online: `{len(bots)}`\n"
        f"💡 Type `{CMD_PREFIX}help` for commands\n\n"
        f"✨ *POWERED BY ⋆ ˚｡⋆👑˚oggy˚👑⋆｡˚* ✨",
        parse_mode="Markdown"
    )

# ── PREFIX COMMAND ROUTER ─────────────────────────────────────────────────────
CMD_MAP = None

def get_cmd_map():
    global CMD_MAP
    if CMD_MAP is None:
        CMD_MAP = {
            "nc1": cmd_nc1, "nc2": cmd_nc2, "nc3": cmd_nc3, "nc4": cmd_nc4,
            "godnc": cmd_godnc, "raidnc": cmd_raidnc, "timenc": cmd_timenc,
            "wordnc": cmd_wordnc, "emonc": cmd_emonc,
            "gameover": cmd_gameover, "over": cmd_gameover,
            "ncthreads": cmd_ncthreads,
            "spamemo": cmd_spamemo, "spamthreads": cmd_spamthreads,
            "threadstatus": cmd_threadstatus, "stopspam": cmd_stopspam,
            "song": cmd_song, "spotify": cmd_spotify, "yt": cmd_yt, "play": cmd_yt,
            "upall": cmd_upall, "leave": cmd_leave, "bye": cmd_bye,
            "mute": cmd_mute, "unmute": cmd_unmute,
            "muteall": cmd_muteall, "lock": cmd_muteall,
            "unmuteall": cmd_unmuteall, "unlock": cmd_unmuteall,
            "stop": cmd_stop, "stopall": cmd_stopall,
            "speed": cmd_speed, "setprefix": cmd_setprefix,
            "setowner": cmd_setowner,
            "addtoken": cmd_addtoken, "removetoken": cmd_removetoken, "listtokens": cmd_listtokens,
            "entrust": cmd_entrust, "revoke": cmd_revoke, "list": cmd_list,
            "status": cmd_status, "help": cmd_help, "menu": cmd_help,
            "vmenu": cmd_menuvideo, "videomenu": cmd_menuvideo,
            "helptext": cmd_helptext,
            "setvideo": cmd_setvideo, "sethelpvideo": cmd_sethelpvideo,
            "start": cmd_start,
        }
    return CMD_MAP

async def handle_prefix_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    if context.bot.id != MAIN_BOT_ID: return
    text = update.message.text.strip()
    if not text.startswith(CMD_PREFIX): return
    parts = text.split()
    cmd_name = parts[0][len(CMD_PREFIX):].lower()
    context.args = parts[1:] if len(parts) > 1 else []
    cmd_map = get_cmd_map()
    if cmd_name in cmd_map:
        await cmd_map[cmd_name](update, context)

# ── APP BUILDER ───────────────────────────────────────────────────────────────
def build_app(token):
    request = HTTPXRequest(connection_pool_size=500, connect_timeout=1, read_timeout=1, write_timeout=1, pool_timeout=1, http_version="2.0")
    app = Application.builder().token(token).request(request).build()
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prefix_commands))
    cmd_map = get_cmd_map()
    for cmd_name, func in cmd_map.items():
        app.add_handler(CommandHandler(cmd_name, func))
    return app

# ── MAIN ──────────────────────────────────────────────────────────────────────
async def run_all_bots():
    global bots, apps, MAIN_BOT_ID
    all_tokens = list(TOKENS) + bot_config.get("extra_tokens", [])
    unique_tokens = list(set(t.strip() for t in all_tokens if t.strip()))

    print("🎀 STARTING ⋆ ˚｡⋆👑˚oggy˚👑⋆｡˚ ULTRA BOTS 🎀")
    print("=" * 60)
    print(f"📌 Command Prefix: `{CMD_PREFIX}`")
    print(f"🧵 Thread Pool: 200 workers")
    print(f"⚡ Max Concurrent: {MAX_CONCURRENT_TASKS}")
    print(f"🚀 Speed Mode: INSTANT (0 delay)")
    print("=" * 60)

    async def start_bot(token, is_main=False):
        try:
            app = build_app(token)
            await app.initialize()
            await app.start()
            if is_main:
                await app.updater.start_polling()
            bot_info = await app.bot.get_me()
            role = "MAIN" if is_main else "WORKER"
            print(f"✅ @{bot_info.username} - ONLINE ({role})")
            return app, app.bot
        except Exception as e:
            print(f"❌ Failed: {e}")
            return None, None

    results = await asyncio.gather(*[start_bot(token, is_main=(i == 0)) for i, token in enumerate(unique_tokens)])
    first_bot_set = False
    for app, bot in results:
        if app and bot:
            apps.append(app)
            bots.append(bot)
            if not first_bot_set:
                MAIN_BOT_ID = bot.id
                first_bot_set = True
    if not first_bot_set and bots:
        MAIN_BOT_ID = bots[0].id

    print("=" * 60)
    print(f"🎉 {len(bots)} BOTS ONLINE INSTANTLY 🎉")
    print(f"📌 All commands use: `{CMD_PREFIX}` as prefix")
    print(f"📌 Main bot ID: {MAIN_BOT_ID}")
    print(f"⚡ COMMANDS EXECUTE INSTANTLY - NO DELAYS")
    print("=" * 60)
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(run_all_bots())
    except KeyboardInterrupt:
        print("\n🛑 SHUTTING DOWN INSTANTLY...")
        for task_list in active_attacks.values():
            for task in task_list: task.cancel()
        THREAD_POOL.shutdown(wait=False)
        print("🎀 SHUTDOWN COMPLETE 🎀")
