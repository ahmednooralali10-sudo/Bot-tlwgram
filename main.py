import os
import httpx
import asyncio
import threading
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ============================================================
#  ✅ CONFIG
# ============================================================
# ⚠️ ضع التوكن الجديد هنا من @BotFather
TELEGRAM_BOT_TOKEN = "8230350157:AAGRh2yxff0XymkwxsFabWQAXqM7bHdaipY"

# سيرفر السبام (لا تغيره)
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

async def fetch_status():
    try:
        r = client.get(f"{API_BASE_URL}/status", timeout=90)
        if r.status_code != 200: return {"error": f"HTTP {r.status_code}"}
        if "application/json" not in r.headers.get("content-type", ""):
            return {"error": "السيرفر نايم، جاري إيقاظه..."}
        return r.json()
    except Exception as e: return {"error": f"فشل الاتصال: {str(e)}"}

async def fetch_start(uid: str):
    try:
        r = client.get(f"{API_BASE_URL}/start", params={"uid": uid}, timeout=150)
        if r.status_code != 200: return {"ok": False, "error": f"HTTP {r.status_code}"}
        if "application/json" not in r.headers.get("content-type", ""):
            return {"ok": False, "error": "السيرفر نايم، يرجى المحاولة بعد دقيقة"}
        return r.json()
    except Exception as e: return {"ok": False, "error": f"تعذر البدء: {str(e)}"}

async def fetch_stop():
    try:
        r = client.get(f"{API_BASE_URL}/stop", timeout=90)
        if r.status_code != 200: return {"ok": False, "error": f"HTTP {r.status_code}"}
        if "application/json" not in r.headers.get("content-type", ""):
            return {"ok": False, "error": "السيرفر نايم، يرجى المحاولة بعد دقيقة"}
        return r.json()
    except Exception as e: return {"ok": False, "error": f"تعذر الإيقاف: {str(e)}"}

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

def build_status_text(s: dict):
    if "error" in s: return f"❌ {s['error']}"
    running = s.get("running", False); online = s.get("online_bots", [])
    first = s.get("first_online", False); target = s.get("target_uid") or "—"
    txt = (f"<b>📡 حالة السيرفر</b>\n━━━━━━━━━━━━━━━\n"
           f"{'🟢' if running else '🔴'} الحالة: <b>{'شغال' if running else 'متوقف'}</b>\n"
           f"🎯 التارجت: <code>{target}</code>\n"
           f"👥 الأونلاين: <b>{len(online)}</b>\n"
           f"⚡ أول بوت: <b>{'نعم' if first else 'لا'}</b>\n")
    if online:
        txt += "\n<b>▸ البوتات (أول 15):</b>\n"
        for b in online[:15]: txt += f"  • <code>{b['uid']}</code>\n"
        if len(online) > 15: txt += f"  … و {len(online)-15} آخرين\n"
    return txt + "\n━━━━━━━━━━━━━━━"

async def send_video(bot, chat_id, caption, keyboard):
    return await bot.send_video(
        chat_id=chat_id, video=VIDEO_URL, caption=caption,
        parse_mode="HTML", reply_markup=keyboard, supports_streaming=True,
    )

async def edit_video(q, caption, keyboard):
    try:
        await q.edit_message_media(
            media=InputMediaVideo(media=VIDEO_URL, caption=caption, parse_mode="HTML"),
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
    await send_video(ctx.bot, update.effective_chat.id,
                     build_main_caption(update.effective_user.first_name or ""), main_keyboard())

async def cmd_devs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id): return
    caption = ("<b>👨‍💻 المطورون</b>\n━━━━━━━━━━━━━━━\n"
               "تواصل مع أي مطور عبر الأزرار ⬇️\n\n• @Hmza645\n• @dljyta\n• @xsaudi96\n━━━━━━━━━━━━━━━")
    await send_video(ctx.bot, update.effective_chat.id, caption, devs_keyboard())

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id): return
    s = await fetch_status()
    await send_video(ctx.bot, update.effective_chat.id, build_status_text(s), main_keyboard())

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id): return
    j = await fetch_stop()
    txt = "⏹ <b>تم إيقاف السيرفر</b>" if j.get("ok") else f"❌ {j.get('error','فشل')}"
    await send_video(ctx.bot, update.effective_chat.id, txt, main_keyboard())

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_allowed(q.from_user.id): return
    data = q.data
    if data == "menu_status":
        await edit_video(q, build_status_text(await fetch_status()), main_keyboard())
    elif data == "menu_stop":
        j = await fetch_stop()
        await edit_video(q, "⏹ <b>تم إيقاف السيرفر</b>" if j.get("ok") else f"❌ {j.get('error','فشل')}", main_keyboard())
    elif data == "menu_start":
        awaiting_uid.add(q.from_user.id)
        await edit_video(q, "🎯 <b>أرسل الـ UID</b> (أرقام فقط):",
                         InlineKeyboardMarkup([[_make_button("🔙 رجوع", callback_data="menu_back", style="primary")]]))
    elif data == "menu_devs":
        caption = ("<b>👨‍💻 المطورون</b>\n━━━━━━━━━━━━━━━\n• @Hmza645\n• @dljyta\n• @xsaudi96\n━━━━━━━━━━━━━━━")
        await edit_video(q, caption, devs_keyboard())
    elif data == "menu_back":
        awaiting_uid.discard(q.from_user.id)
        await edit_video(q, build_main_caption(q.from_user.first_name or ""), main_keyboard())

async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in awaiting_uid: return
    text = (update.message.text or "").strip()
    if not text.isdigit():
        await update.message.reply_text("⚠️ أرقام فقط."); return
    awaiting_uid.discard(uid)
    msg = await send_video(ctx.bot, update.effective_chat.id,
                           f"⏳ <b>جاري البدء على</b> <code>{text}</code>...\n<i>قد يستغرق حتى دقيقتين.</i>",
                           InlineKeyboardMarkup([[_make_button("🔙 رجوع", callback_data="menu_back", style="primary")]]))
    j = await fetch_start(text)
    if not j.get("ok"):
        try: await msg.edit_caption(caption=f"❌ {j.get('error','فشل')}", parse_mode="HTML", reply_markup=main_keyboard())
        except Exception: pass
        return
    s = await fetch_status()
    result = (f"✅ <b>{j.get('message','تم')}</b>\n🎯 <code>{j.get('target_uid')}</code>\n"
              f"👥 أونلاين: <b>{j.get('online_bots',0)}</b>\n\n" + build_status_text(s))
    try: await msg.edit_caption(caption=result, parse_mode="HTML", reply_markup=main_keyboard())
    except Exception: pass

# ============================================================
#  FASTAPI & POLLING
# ============================================================
app = FastAPI()

@app.get("/")
@app.get("/health")
async def health():
    return {"status": "ok", "bot": "Ariyan V-Badge Polling Mode"}

def run_bot_polling():
    """تشغيل البوت بوضع Polling في Thread منفصل"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # بناء البوت
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # إضافة الأوامر
    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("status", cmd_status))
    bot_app.add_handler(CommandHandler("stop", cmd_stop))
    bot_app.add_handler(CommandHandler("devs", cmd_devs))
    bot_app.add_handler(CallbackQueryHandler(on_callback))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    
    print("🤖 Bot is running in Polling mode...")
    bot_app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

@app.on_event("startup")
async def startup():
    # تشغيل البوت في الخلفية بمجرد إقلاع السيرفر
    t = threading.Thread(target=run_bot_polling, daemon=True)
    t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
