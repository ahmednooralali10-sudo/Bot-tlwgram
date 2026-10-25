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
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_BASE_URL = "https://info-and-spam-xdhr.onrender.com"
ADMIN_IDS = set() 
VIDEO_URL = "https://files.catbox.moe/etnyuf.mp4"

DEVELOPERS = [
    ("@Hmza645",  "https://t.me/Hmza645"),
    ("@dljyta",   "https://t.me/dljyta"),
    ("@xsaudi96", "https://t.me/xsaudi96"),
]

client = httpx.Client(timeout=150.0, verify=False)
awaiting_uid = set()

# تخزين الأيدي النشطة حالياً عشان يظهر في رسالة الإيقاف
active_uids = {}  # {chat_id: {"uid": uid, "name": name, "level": level}}

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

async def fetch_stop(uid: str = None):
    try:
        url = f"{API_BASE_URL}/stop"
        params = {"uid": uid} if uid else None
        r = client.get(url, params=params, timeout=90)
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
#  CORE PROCESS FUNCTION
# ============================================================
async def process_start_spam(bot, chat_id, uid_text, message_to_edit=None):
    info = checker.get_player_info(uid_text)
    name = info.get("name", "غير معروف")
    level = info.get("level", "0")
    
    active_uids[chat_id] = {"uid": uid_text, "name": name, "level": level}
    
    await fetch_start(uid_text)
    
    max_retries = 15
    bot_online = False
    
    for _ in range(max_retries):
        await asyncio.sleep(2)
        status = await get_status()
        if status.get("online_bots", 0) > 0:
            bot_online = True
            break
            
    if bot_online:
        result = (
            f"<b>✅ تم بدء السبام بنجاح (البوتات متصلة)</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>الاسم:</b> <code>{name}</code>\n"
            f"📈 <b>اللفل:</b> <code>{level}</code>\n"
            f"🆔 <b>الايدي:</b> <code>{uid_text}</code>\n"
            f"━━━━━━━━━━━━━━━"
        )
    else:
        result = (
            f"<b>⚠️ تأخر الاتصال باللعبة</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>الاسم:</b> <code>{name}</code>\n"
            f"📈 <b>اللفل:</b> <code>{level}</code>\n"
            f"🆔 <code>{uid_text}</code>\n"
            f"<i>(البوتات ما زالت تحاول الدخول في الخلفية..)</i>\n"
            f"━━━━━━━━━━━━━━━"
        )
        
    if message_to_edit:
        try:
            await message_to_edit.edit_caption(caption=result, parse_mode="HTML", reply_markup=main_keyboard())
        except Exception:
            await send_anim(bot, chat_id, result, main_keyboard())
    else:
        await send_anim(bot, chat_id, result, main_keyboard())

# ============================================================
#  HANDLERS (Commands & Callbacks)
# ============================================================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id): return
    await send_anim(ctx.bot, update.effective_chat.id,
                    build_main_caption(update.effective_user.first_name or ""), main_keyboard())

async def cmd_spam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id): return
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("⚠️ يرجى كتابة الأمر بشكل صحيح، مثال:\n<code>/spam 123456789</code>", parse_mode="HTML")
        return
    
    uid = args[0]
    msg = await send_anim(ctx.bot, update.effective_chat.id,
                          f"⏳ <b>جاري جلب البيانات وبدء السبام للايدي: {uid}...</b>",
                          InlineKeyboardMarkup([[_make_button("🔙 رجوع", callback_data="menu_back", style="primary")]]))
    await process_start_spam(ctx.bot, update.effective_chat.id, uid, msg)

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id): return
    chat_id = update.effective_chat.id
    
    target_uid = None
    if chat_id in active_uids:
        target_uid = active_uids[chat_id]["uid"]
        
    await fetch_stop(target_uid)
    
    if chat_id in active_uids:
        data = active_uids.pop(chat_id)
        result = (
            f"<b>⏹ تم إيقاف السبام بنجاح</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>الاسم:</b> <code>{data['name']}</code>\n"
            f"📈 <b>اللفل:</b> <code>{data['level']}</code>\n"
            f"🆔 <b>الايدي:</b> <code>{data['uid']}</code>\n"
            f"━━━━━━━━━━━━━━━"
        )
    else:
        result = (
            f"<b>⏹ تم إيقاف السيرفر والعمليات بنجاح</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<i>(لم يتم رصد أيدي نشط محفوظ في هذه الجلسة)</i>\n"
            f"━━━━━━━━━━━━━━━"
        )
    await send_anim(ctx.bot, chat_id, result, main_keyboard())

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_allowed(q.from_user.id): return
    data = q.data
    chat_id = q.message.chat.id
    
    if data == "menu_stop":
        target_uid = active_uids[chat_id]["uid"] if chat_id in active_uids else None
        await fetch_stop(target_uid)
        
        if chat_id in active_uids:
            item = active_uids.pop(chat_id)
            caption = (
                f"<b>⏹ تم إيقاف السبام بنجاح</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 <b>الاسم:</b> <code>{item['name']}</code>\n"
                f"📈 <b>اللفل:</b> <code>{item['level']}</code>\n"
                f"🆔 <b>الايدي:</b> <code>{item['uid']}</code>\n"
                f"━━━━━━━━━━━━━━━"
            )
        else:
            caption = (
                f"<b>⏹ تم إيقاف السيرفر والعمليات بنجاح</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"<i>(لم يتم رصد أيدي نشط محفوظ في هذه الجلسة)</i>\n"
                f"━━━━━━━━━━━━━━━"
            )
        await edit_anim(q, caption, main_keyboard())
        
    elif data == "menu_start":
        awaiting_uid.add(q.from_user.id)
        await edit_anim(q, "🎯 <b>أرسل الـ UID الآن</b> (أرقام فقط):",
                        InlineKeyboardMarkup([[_make_button("🔙 رجوع", callback_data="menu_back", style="primary")]]))
                         
    elif data == "menu_status":
        status = await get_status()
        online_count = status.get("online_bots", 0)
        current_t = status.get("current_target")
        item = active_uids.get(chat_id)
        
        status_text = (
            f"<b>📊 حالة السيرفر والسبام</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🟢 <b>البوتات المتصلة:</b> <code>{online_count}</code>\n"
            f"🎯 <b>الهدف الحالي بالـ API:</b> <code>{current_t if current_t else 'لا توجد'}</code>\n"
        )
        if item:
            status_text += (
                f"👤 <b>اسمك بالجلسة:</b> <code>{item['name']}</code>\n"
                f"🆔 <b>الايدي الشغال:</b> <code>{item['uid']}</code>\n"
            )
        status_text += f"━━━━━━━━━━━━━━━"
        await edit_anim(q, status_text, main_keyboard())

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
    
    await process_start_spam(ctx.bot, update.effective_chat.id, text, msg)

# ============================================================
#  MAIN THREAD
# ============================================================
bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", cmd_start))
bot_app.add_handler(CommandHandler("spam", cmd_spam))
bot_app.add_handler(CommandHandler("stop", cmd_stop))
bot_app.add_handler(CallbackQueryHandler(on_callback))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

# ============================================================
#  WEB SERVER
# ============================================================
web_app = FastAPI()

@web_app.get("/")
@web_app.get("/health")
async def health():
    status = await get_status()
    return {"status": "ok", "bot_status": status}

def run_web_server():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(web_app, host="0.0.0.0", port=port, log_level="warning")

if __name__ == "__main__":
    t = threading.Thread(target=run_web_server, daemon=True)
    t.start()
    print("🤖 Bot is running...")
    bot_app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
