from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler








from config import BOT_TOKEN, CHANNEL_ID, ADMIN_IDS, RSS_FEEDS, MESSAGES, SCRAPE_INTERVAL
from database import init_db, save_offer, mark_as_sent, get_unsent_offers, get_stats, clear_database, record_download, get_download_stats, track_user, get_user_stats
from utils import create_offer_image
from handlers.media_tools import (
    remove_background, download_video, is_supported_url,
    remove_watermark, remove_text_from_image, crop_phone_frame
)








# Setup logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)








# حالة المستخدم (لتتبع الوضع المختار)
user_mode = {}
















# ============== القائمة الرئيسية ==============








def get_main_menu():
    """إنشاء القائمة الرئيسية"""
    keyboard = [
        [
            InlineKeyboardButton("📹 TikTok", callback_data="info_tiktok"),
            InlineKeyboardButton("📸 Instagram", callback_data="info_instagram"),
            InlineKeyboardButton("▶️ YouTube", callback_data="info_youtube"),
        ],
        [
            InlineKeyboardButton("🐦 Twitter/X", callback_data="info_twitter"),
            InlineKeyboardButton("📘 Facebook", callback_data="info_facebook"),
            InlineKeyboardButton("📌 Pinterest", callback_data="info_pinterest"),
        ],
        [
            InlineKeyboardButton("👻 Snapchat", callback_data="info_snapchat"),
            InlineKeyboardButton("💖 Likee", callback_data="info_likee"),
            InlineKeyboardButton("🎬 Kwai", callback_data="info_kwai"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)\n\n
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات المستخدمين للأدمن"""
    if update.effective_user.id not in ADMIN_IDS:
        return


    stats = get_user_stats()
    text = f"""
👥 *إحصائيات المستخدمين*


📊 إجمالي المستخدمين: {stats['total_users']}
🟢 نشطين اليوم: {stats['active_today']}
📅 نشطين هذا الأسبوع: {stats['active_this_week']}


📈 *إحصائيات التحميل:*
✅ ناجح: {stats['downloads']['success']}
❌ فشل: {stats['downloads']['failed']}
"""
    await update.message.reply_text(text, parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات التحميل"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    stats = get_download_stats()
    if not stats:
        await update.message.reply_text("❌ لا توجد إحصائيات بعد")
        return
        
    text = "📊 *إحصائيات التحميل حسب المنصة:*\n\n"
    for s in stats:
        platform = s['platform']
        count = s['count']
        text += f"🔹 *{platform}*: {count} التحميلات\n"
        
    await update.message.reply_text(text, parse_mode='Markdown')


















async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية مع القائمة"""
    welcome_text = """
🎬 *بوت تحميل الفيديوهات*








📥 *أرسل رابط الفيديو مباشرة وأحمّله لك!*








✨ *المنصات المدعومة:*







