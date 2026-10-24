# ملف: main.py
import os
import httpx
import asyncio
import threading
import uvicorn
from fastapi import FastAPI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaAnimation
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

import checker 

# ============================================================
#  ✅ CONFIG
# ============================================================
TELEGRAM_BOT_TOKEN = "8230350157:AAGRh2yxff0XymkwxsFabWQAXqM7bHdaipY"
API_BASE_URL = "https://spam-visit.onrender.com"
ADMIN_IDS = set() 
VIDEO_URL = "https://files.catbox.moe/etnyuf.mp4"

DEVELOPERS = [
    ("@Hmza645",  "https://t.me/Hmza645"),
    ("@dljyta",   "https://t.me/dljyta"),
    ("@xsaudi96", "https://t.me/xsaudi96"),
]

client = httpx.Client(timeout=150.0, verify=False)
awaiting_uid = set()

# ============================================================
#  HELPERS
# ============================================================
def is_allowed(user_id: int) -> bool:
    return (not ADMIN_IDS) or (user_id in ADMIN_IDS)

def _make_button(text, callback_data=None, url=None, style=None):
    kwargs = {"text": text}
    if callback_data: kwargs["callback_data"] = callback_data
    if url: kwargs["url"] = url
    if style:
        try: return InlineKeyboardButton(style=style, **kwargs)
        except TypeError: pass
    return InlineKeyboardButton(**kwargs)

async def fetch_start(uid: str):
    try:
        r = client.get(f"{API_BASE_URL}/start", params={"uid": uid}, timeout=150)
        if r.status_code != 200: return {"ok": False}
        return r.json()
    except Exception: return {"ok": False}

async def fetch_stop():
    try:
        r = client.get(f"{API_BASE_URL}/stop", timeout=90)
        if r.status_code != 200: return {"ok": False}
        return r.json()
    except Exception: return {"ok": False}

async def get_status():
    try:
        r = client.get(f"{API_BASE_URL}/status", timeout=10)
        return r.json()
    except Exception: return {}

def main_keyboard():
    return InlineKeyboardMarkup([
        [_make_button("▶️ تشغيل", callback_data="menu_start", style="success"),
         _make_button("⏹ إيقاف", callback_data="menu_stop", style="danger")],
        [_make_button("📊 الحالة", callback_data="menu_status", style="primary")],
        [_make_button("👨‍💻 المطورون", callback_data="menu_devs")],
    ])

def devs_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👨‍💻 {name}", url=url) for name, url in DEVELOPERS],
        [_make_button("🔙 رجوع", callback_data="menu_back", style="primary")],
    ])

def build_main_caption(username: str = ""):
    hello = f"أهلاً {username}" if username else "أهلاً بك"
    return (f"<b>🔥 Ariyan V-Badge Bot 🔥</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"{hello} في لوحة التحكم 🎛\n\n"
            f"<b>▸ الخيارات المتاحة:</b>\n"
            f"  ▶️ تشغيل السبام\n  ⏹ إيقاف السبام\n  📊 عرض الحالة\n  👨‍💻 المطورون\n\n"
            f"━━━━━━━━━━━━━━━━━━\n<i>⚡ Powered by Ariyan Team</i>")

async def send_anim(bot, chat_id, caption, keyboard):
    return await bot.send_animation(
        chat_id=chat_id, animation=VIDEO_URL, caption=caption,
        parse_mode="HTML", reply_markup=keyboard
    )

async def edit_anim(q, caption, keyboard):
    try:
        await q.edit_message_media(
            media=InputMediaAnimation(media=VIDEO_URL, caption=caption, parse_mode="HTML"),
            reply_markup=keyboard,
        )
    except Exception:
        try: await q.edit_message_caption(caption=caption, parse_mode="HTML", reply_markup=keyboard)
        except Exception: pass

# ============================================================
#  HANDLERS
# ============================================================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id): return
    await send_anim(ctx.bot, update.effective_chat.id,
                    build_main_caption(update.effective_user.first_name or ""), main_keyboard())

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_allowed(q.from_user.id): return
    data = q.data
    
    if data == "menu_stop":
        await fetch_stop()
        await edit_anim(q, "⏹ <b>تم إيقاف السيرفر</b>", main_keyboard())
        
    elif data == "menu_start":
        awaiting_uid.add(q.from_user.id)
        await edit_anim(q, "🎯 <b>أرسل الـ UID</b> (أرقام فقط):",
                        InlineKeyboardMarkup([[_make_button("🔙 رجوع", callback_data="menu_back", style="primary")]]))
                         
    elif data == "menu_devs":
        caption = ("<b>👨‍💻 المطورون</b>\n━━━━━━━━━━━━━━━\n• @Hmza645\n• @dljyta\n• @xsaudi96\n━━━━━━━━━━━━━━━")
        await edit_anim(q, caption, devs_keyboard())
        
    elif data == "menu_back":
        awaiting_uid.discard(q.from_user.id)
        await edit_anim(q, build_main_caption(q.from_user.first_name or ""), main_keyboard())

async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in awaiting_uid: return
    text = (update.message.text or "").strip()
    if not text.isdigit():
        await update.message.reply_text("⚠️ أرقام فقط."); return
    
    awaiting_uid.discard(uid)
    
    msg = await send_anim(ctx.bot, update.effective_chat.id,
                          f"⏳ <b>جاري جلب البيانات وبدء السبام...</b>\n<i>يرجى الانتظار حتى يتم الاتصال باللعبة.</i>",
                          InlineKeyboardMarkup([[_make_button("🔙 رجوع", callback_data="menu_back", style="primary")]]))
    
    info = checker.get_player_info(text)
    
    await fetch_start(text)
    
    max_retries = 15
    bot_online = False
    
    for _ in range(max_retries):
        await asyncio.sleep(2)
        status = await get_status()
        if status.get("online_bots_count", 0) > 0:
            bot_online = True
            break
            
    if bot_online:
        result = (
            f"<b>✅ تم بدء السبام بنجاح (البوتات متصلة)</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>الاسم:</b> <code>{info['name']}</code>\n"
            f"📈 <b>اللفل:</b> <code>{info['level']}</code>\n"
            f"🆔 <b>الايدي:</b> <code>{text}</code>\n"
            f"━━━━━━━━━━━━━━━"
        )
    else:
        result = (
            f"<b>⚠️ تأخر الاتصال باللعبة</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>الاسم:</b> <code>{info['name']}</code>\n"
            f"📈 <b>اللفل:</b> <code>{info['level']}</code>\n"
            f"🆔 <b>الايدي:</b> <code>{text}</code>\n"
            f"<i>(البوتات ما زالت تحاول الدخول في الخلفية..)</i>\n"
            f"━━━━━━━━━━━━━━━"
        )
        
    try: await msg.edit_caption(caption=result, parse_mode="HTML", reply_markup=main_keyboard())
    except Exception: pass

# ============================================================
#  MAIN THREAD
# ============================================================
bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", cmd_start))
bot_app.add_handler(CallbackQueryHandler(on_callback))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

# ============================================================
#  WEB SERVER
# ============================================================
web_app = FastAPI()

@web_app.get("/")
@web_app.get("/health")
async def health():
    return {"status": "ok"}

def run_web_server():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(web_app, host="0.0.0.0", port=port, log_level="warning")

if __name__ == "__main__":
    t = threading.Thread(target=run_web_server, daemon=True)
    t.start()
    print("🤖 Bot is running...")
    bot_app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
