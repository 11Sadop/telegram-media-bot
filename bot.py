#!/usr/bin/env python3
"""
بوت أدوات الوسائط
إزالة الخلفية، تحميل الفيديوهات، والمزيد
"""

import re
import logging
from datetime import datetime

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















