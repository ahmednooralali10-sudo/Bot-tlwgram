import os
import httpx
import asyncio
import uvicorn
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ============================================================
#  ✅ CONFIG — كل شيء هنا مباشرة (بدّل التوكن فقط)
# ============================================================
TELEGRAM_BOT_TOKEN = "8230350157:AAEXpUPDdrXXGbZnugmFeKyBHc-KzpRLbEI"          # ← غيّر هذا فقط
API_BASE_URL       = "https://spam-visit.onrender.com"
RENDER_URL         = "https://bot-tlwgram.onrender.com"  # ← غيّره لاحقًا بعد النشر
ADMIN_IDS          = set()                         # اتركه فارغًا ليستخدمه الجميع، أو ضع {123456789}
VIDEO_URL          = "https://files.catbox.moe/etnyuf.mp4"

DEVELOPERS = [
    ("@Hmza645",  "https://t.me/Hmza645"),
    ("@dljyta",   "https://t.me/dljyta"),
    ("@xsaudi96", "https://t.me/xsaudi96"),
]

client = httpx.Client(timeout=120.0, verify=False)
awaiting_uid = set()

# ============================================================
#  APP INIT
# ============================================================
ptb_app = Application.builder().token(TELEGRAM_BOT_TOKEN).updater(None).build()

# ============================================================
#  HELPERS
# ============================================================
def is_allowed(user_id: int) -> bool:
    return (not ADMIN_IDS) or (user_id in ADMIN_IDS)

async def fetch_status():
    try: return client.get(f"{API_BASE_URL}/status").json()
    except Exception as e: return {"error": str(e)}

async def fetch_start(uid: str):
    try: return client.get(f"{API_BASE_URL}/start", params={"uid": uid}).json()
    except Exception as e: return {"ok": False, "error": str(e)}

async def fetch_stop():
    try: return client.get(f"{API_BASE_URL}/stop").json()
    except Exception as e: return {"ok": False, "error": str(e)}

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ تشغيل", callback_data="menu_start"),
         InlineKeyboardButton("⏹ إيقاف", callback_data="menu_stop")],
        [InlineKeyboardButton("📊 الحالة", callback_data="menu_status")],
        [InlineKeyboardButton("👨‍💻 المطورون", callback_data="menu_devs")],
    ])

def devs_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👨‍💻 {name}", url=url) for name, url in DEVELOPERS],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")],
    ])

def build_main_caption(username: str = ""):
    hello = f"أهلاً {username}" if username else "أهلاً بك"
    return (f"<b>🔥 Ariyan V-Badge Bot 🔥</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"{hello} في لوحة التحكم 🎛\n\n"
            f"<b>▸ الخيارات المتاحة:</b>\n"
            f"  ▶️ تشغيل السبام\n  ⏹ إيقاف السبام\n  📊 عرض الحالة\n  👨‍💻 المطورون\n\n"
            f"━━━━━━━━━━━━━━━━━━\n<i>⚡ Powered by Ariyan Team</i>")

def build_status_text(s: dict):
    if "error" in s: return f"❌ تعذر الاتصال:\n<code>{s['error']}</code>"
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
        chat_id=chat_id,
        video=VIDEO_URL,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard,
        supports_streaming=True,
    )

async def edit_video(q, caption, keyboard):
    try:
        await q.edit_message_media(
            media=InputMediaVideo(media=VIDEO_URL, caption=caption, parse_mode="HTML"),
            reply_markup=keyboard,
        )
    except Exception:
        try:
            await q.edit_message_caption(caption=caption, parse_mode="HTML", reply_markup=keyboard)
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
    txt = "⏹ <b>تم إيقاف السيرفر</b>" if j.get("ok") else f"❌ فشل:\n<code>{j}</code>"
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
        await edit_video(q, "⏹ <b>تم إيقاف السيرفر</b>" if j.get("ok") else f"❌ فشل:\n<code>{j}</code>", main_keyboard())
    elif data == "menu_start":
        awaiting_uid.add(q.from_user.id)
        await edit_video(q, "🎯 <b>أرسل الـ UID</b> (أرقام فقط):",
                         InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]))
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
                           f"⏳ <b>جاري البدء على</b> <code>{text}</code>...\n<i>قد يستغرق 90 ثانية.</i>",
                           InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]))
    j = await fetch_start(text)
    if not j.get("ok"):
        try:
            await msg.edit_caption(caption=f"❌ فشل:\n<code>{j}</code>", parse_mode="HTML", reply_markup=main_keyboard())
        except Exception: pass
        return
    s = await fetch_status()
    result = (f"✅ <b>{j.get('message','تم')}</b>\n🎯 <code>{j.get('target_uid')}</code>\n"
              f"👥 أونلاين: <b>{j.get('online_bots',0)}</b>\n\n" + build_status_text(s))
    try:
        await msg.edit_caption(caption=result, parse_mode="HTML", reply_markup=main_keyboard())
    except Exception: pass

ptb_app.add_handler(CommandHandler("start", cmd_start))
ptb_app.add_handler(CommandHandler("status", cmd_status))
ptb_app.add_handler(CommandHandler("stop", cmd_stop))
ptb_app.add_handler(CommandHandler("devs", cmd_devs))
ptb_app.add_handler(CallbackQueryHandler(on_callback))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

# ============================================================
#  FASTAPI
# ============================================================
app = FastAPI()

@app.on_event("startup")
async def startup():
    await ptb_app.initialize()
    await ptb_app.start()
    if RENDER_URL and "onrender.com" in RENDER_URL:
        webhook_url = f"{RENDER_URL}/webhook/{TELEGRAM_BOT_TOKEN}"
        try:
            await ptb_app.bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook set: {webhook_url}")
        except Exception as e:
            print(f"❌ Webhook error: {e}")
    asyncio.create_task(self_ping())

@app.on_event("shutdown")
async def shutdown():
    await ptb_app.stop()

async def self_ping():
    await asyncio.sleep(10)
    while True:
        try:
            if RENDER_URL:
                async with httpx.AsyncClient() as c:
                    await c.get(f"{RENDER_URL}/health", timeout=10)
        except: pass
        await asyncio.sleep(14 * 60)

@app.get("/")
async def root(): return {"status": "ok", "bot": "Ariyan V-Badge"}

@app.get("/health")
async def health(): return {"status": "ok"}

@app.post("/webhook/{token}")
async def webhook(token: str, request: Request):
    if token != TELEGRAM_BOT_TOKEN:
        return Response(status_code=403)
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.update_queue.put(update)
    return {"ok": True}

# ============================================================
#  RUN (هذا السطر اللي كان ناقص — سبب الخروج المبكر)
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
