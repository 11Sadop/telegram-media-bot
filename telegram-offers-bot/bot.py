#!/usr/bin/env python3
"""
بوت عروض تيليجرام - للسعودية
+ أدوات الوسائط (إزالة الخلفية، تحميل الفيديوهات)
"""

import re
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import BOT_TOKEN, CHANNEL_ID, ADMIN_IDS, RSS_FEEDS, MESSAGES, SCRAPE_INTERVAL
from database import init_db, save_offer, mark_as_sent, get_unsent_offers, get_stats, clear_database
from utils import create_offer_image
from handlers.media_tools import (
    remove_background, download_video, is_supported_url,
    remove_watermark, remove_text_from_image, crop_phone_frame
)

# Setup logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# ============== COMMANDS ==============

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص المصادر"""
    await update.message.reply_text("🔍 جاري الفحص...")
    results = []
    try:
        from scrapers.rss_scraper import scrape_almowafir_deals
        r = scrape_almowafir_deals()
        results.append(f"الموفر: {len(r)}")
    except Exception as e:
        results.append(f"الموفر خطأ: {e}")
    try:
        from scrapers.rss_scraper import scrape_delivery_apps
        r = scrape_delivery_apps()
        results.append(f"توصيل: {len(r)}")
    except Exception as e:
        results.append(f"توصيل خطأ: {e}")
    await update.message.reply_text("\n".join(results) if results else "لا نتائج")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية"""
    await update.message.reply_text(MESSAGES["welcome"], parse_mode='Markdown')


async def offers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض آخر العروض"""
    offers = get_unsent_offers(5)
    if not offers:
        await update.message.reply_text(MESSAGES["no_offers"])
        return
    
    for offer in offers:
        await send_offer_message(update.message, dict(offer))


async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحديث العروض يدوياً"""
    await update.message.reply_text(MESSAGES["updating"])
    await perform_scrape(context)
    await update.message.reply_text("✅ تم التحديث!")


async def perform_scrape(context: ContextTypes.DEFAULT_TYPE):
    """وظيفة السحب والنشر المشتركة (للتحديث اليدوي والتلقائي)"""
    try:
        from scrapers import fetch_all_rss_feeds
        offers = fetch_all_rss_feeds(RSS_FEEDS)
        
        count = 0
        for offer in offers:
            if save_offer(offer['title'], offer['link'], offer.get('price'), offer.get('category'), offer.get('source'), offer.get('image_url'), offer.get('description')):
                count += 1
        
        if count > 0:
            await post_to_channel(context.application)
            return count
    except Exception as e:
        logger.error(f"Scrape error: {e}")
    return 0


async def scheduled_scrape_job(context: ContextTypes.DEFAULT_TYPE):
    """وظيفة الجدولة التلقائية"""
    logger.info("Running scheduled scrape...")
    await perform_scrape(context)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات البوت"""
    stats = get_stats()
    msg = f"""
📊 *إحصائيات البوت*

📦 إجمالي العروض: {stats['total']}
✅ تم نشرها: {stats['sent']}
⏳ في الانتظار: {stats['pending']}
"""
    await update.message.reply_text(msg, parse_mode='Markdown')


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسح العروض القديمة"""
    clear_database()
    await update.message.reply_text(MESSAGES["cleared"])


async def add_offer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إضافة عرض يدوياً"""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text(MESSAGES["admin_only"])
        return
    
    text = update.message.text
    for cmd in ['/اضافة', '/add', 'اضافة', 'add']:
        if text.startswith(cmd):
            text = text[len(cmd):].strip()
            break
    
    if not text:
        await update.message.reply_text(MESSAGES["add_format"], parse_mode='Markdown')
        return
    
    # Parse lines
    lines = text.split('\n')
    if len(lines) < 2:
        await update.message.reply_text("❌ البيانات ناقصة")
        return
    
    title = lines[0].strip()
    link = lines[1].strip()
    category = lines[2].strip() if len(lines) > 2 else "عروض متنوعة"
    
    if save_offer(title, link, "", category, "يدوي"):
        await update.message.reply_text(MESSAGES["offer_added"])
        offer = {"title": title, "link": link, "category": category, "source": "يدوي"}
        await send_offer_to_chat(context.bot, CHANNEL_ID, offer)
        mark_as_sent(link)
    else:
        await update.message.reply_text("❌ العرض موجود")


# ============== MESSAGES & IMAGES ==============

def format_caption(offer: dict) -> str:
    """تنسيق رسالة العرض"""
    title = offer.get('title', 'عرض')
    link = offer.get('link', '')
    price = offer.get('price', '')
    desc = offer.get('description', '')
    source = offer.get('source', '')
    category = offer.get('category', '')
    
    # بناء الرسالة
    msg = f"🎁 *{title}*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if desc:
        msg += f"{desc}\n\n"
    
    if price:
        msg += f"💰 *الخصم:* {price}\n"
    
    if source:
        msg += f"🏪 *المتجر:* {source}\n"
        
    if category:
        msg += f"📂 *التصنيف:* {category}\n"
    
    msg += "\n━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🔗 [اضغط هنا للعرض]({link})\n"
    msg += f"\n📢 {CHANNEL_ID}"
    
    return msg


async def send_offer_to_chat(bot, chat_id, offer: dict):
    """إرسال العرض مع صورة مصممة"""
    caption = format_caption(offer)
    
    # Generate custom image
    image_io = create_offer_image(
        offer.get('image_url'), 
        offer.get('title'), 
        offer.get('price'), 
        offer.get('source')
    )
    
    try:
        if image_io:
            await bot.send_photo(chat_id=chat_id, photo=image_io, caption=caption, parse_mode='Markdown')
        elif offer.get('image_url'):
            await bot.send_photo(chat_id=chat_id, photo=offer['image_url'], caption=caption, parse_mode='Markdown')
        else:
            await bot.send_message(chat_id=chat_id, text=caption, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Send error: {e}")
        # Fallback
        await bot.send_message(chat_id=chat_id, text=caption, parse_mode='Markdown')


async def send_offer_message(message_object, offer: dict):
    """للرد على المستخدم"""
    caption = format_caption(offer)
    # لا نستخدم تصميم الصور في الردود السريعة لتوفير الوقت، فقط الصور الأصلية
    try:
        if offer.get('image_url'):
            await message_object.reply_photo(photo=offer['image_url'], caption=caption, parse_mode='Markdown')
        else:
            await message_object.reply_text(caption, parse_mode='Markdown')
    except:
        await message_object.reply_text(caption, parse_mode='Markdown')


async def post_to_channel(app: Application):
    """نشر العروض للقناة"""
    offers = get_unsent_offers(5)
    for offer in offers:
        await send_offer_to_chat(app.bot, CHANNEL_ID, dict(offer))
        mark_as_sent(offer['link'])


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصور - إزالة الخلفية/العلامات/الكتابة/الإطار"""
    caption = (update.message.caption or "").lower().strip()
    
    # تحديد نوع المعالجة من التعليق
    if any(x in caption for x in ['علامة', 'ووتر', 'watermark', 'شعار', 'لوقو']):
        mode = 'watermark'
        msg = "🔄 جاري إزالة العلامة المائية..."
    elif any(x in caption for x in ['كتابة', 'نص', 'text', 'كلام']):
        mode = 'text'
        msg = "🔄 جاري إزالة الكتابة..."
    elif any(x in caption for x in ['قص', 'اطار', 'crop', 'frame', 'شريط']):
        mode = 'crop'
        msg = "🔄 جاري قص الإطار..."
    else:
        mode = 'background'
        msg = "🔄 جاري إزالة الخلفية..."
    
    await update.message.reply_text(msg)
    
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        
        # تطبيق المعالجة المناسبة
        if mode == 'watermark':
            result = await remove_watermark(bytes(photo_bytes))
            filename = "no_watermark.png"
            success_msg = "✅ تم إزالة العلامة المائية!"
        elif mode == 'text':
            result = await remove_text_from_image(bytes(photo_bytes))
            filename = "no_text.png"
            success_msg = "✅ تم إزالة الكتابة!"
        elif mode == 'crop':
            result = await crop_phone_frame(bytes(photo_bytes))
            filename = "cropped.png"
            success_msg = "✅ تم قص الإطار!"
        else:
            result = await remove_background(bytes(photo_bytes))
            filename = "no_background.png"
            success_msg = "✅ تم إزالة الخلفية!"
        
        if result:
            await update.message.reply_document(
                document=result,
                filename=filename,
                caption=success_msg
            )
        else:
            await update.message.reply_text("❌ فشلت العملية - جرب صورة أخرى")
    except Exception as e:
        logger.error(f"Photo error: {e}")
        await update.message.reply_text("❌ حدث خطأ")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأوامر النصية والروابط"""
    text = update.message.text
    if not text: return
    
    # التحقق من وجود رابط فيديو مدعوم
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    
    if urls:
        url = urls[0]
        if is_supported_url(url):
            await update.message.reply_text("📥 جاري التحميل...")
            try:
                result = await download_video(url)
                if result:
                    if result['type'] == 'video':
                        await update.message.reply_video(
                            video=result['file'],
                            caption="✅ تم التحميل بدون علامة مائية!"
                        )
                    else:
                        await update.message.reply_photo(
                            photo=result['file'],
                            caption="✅ تم التحميل!"
                        )
                else:
                    await update.message.reply_text("❌ فشل التحميل - جرب مرة ثانية")
            except Exception as e:
                logger.error(f"Download error: {e}")
                await update.message.reply_text("❌ حدث خطأ في التحميل")
            return
    
    # الأوامر النصية العادية
    t = text.lower().strip()
    if t.startswith('/'): t = t[1:]
    
    if t in ['عروض', 'latest']: await offers_command(update, context)
    elif t in ['تحديث', 'refresh']: await refresh_command(update, context)
    elif t in ['مسح', 'clear']: await clear_command(update, context)
    elif t.startswith('اضافة') or t.startswith('add'): await add_offer_command(update, context)
    elif t in ['مساعدة', 'help', 'start']: await start_command(update, context)


def main():
    print("🚀 Bot Starting...")
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    
    # --- DEBUG & ADMIN ---
    app.add_handler(CommandHandler("debug", debug_command))
    
    # FORCE CLEAR ON STARTUP (Fix for "Nothing Changed")
    # This ensures we start fresh every restart
    clear_database()
    print("🧹 Database force cleared on startup.")
    
    # Media Tools Handlers
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Job Queue (Automation)
    if app.job_queue:
        # Run every 30 minutes (1800 seconds)
        app.job_queue.run_repeating(scheduled_scrape_job, interval=1800, first=60)
        print("✅ Automation scheduled (every 30 mins)")
    else:
        print("⚠️ JobQueue not available")
        
    app.run_polling()


if __name__ == "__main__":
    main()
