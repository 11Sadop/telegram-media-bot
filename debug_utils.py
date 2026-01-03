from telegram import Update
from telegram.ext import ContextTypes


async def debug_scrape_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to test scrapers one by one"""
    await update.message.reply_text("🕵️ جاري فحص المصادر... انتظر")
    
    results = []
    
    # Test 1: Almowafir
    try:
        from scrapers.rss_scraper import scrape_almowafir_deals
        almowafir = scrape_almowafir_deals()
        results.append(f"✅ الموفر: {len(almowafir)} عرض")
    except Exception as e:
        results.append(f"❌ الموفر: {e}")

    # Test 2: Ilofo
    try:
        from scrapers.rss_scraper import scrape_ilofo_deals
        ilofo = scrape_ilofo_deals()
        results.append(f"✅ Ilofo: {len(ilofo)} عرض")
    except Exception as e:
        results.append(f"❌ Ilofo: {e}")

    # Test 3: Cobone
    try:
        from scrapers.rss_scraper import scrape_cobone_deals
        cobone = scrape_cobone_deals()
        results.append(f"✅ كوبون: {len(cobone)} عرض")
    except Exception as e:
        results.append(f"❌ كوبون: {e}")

    # Test 4: Delivery Apps
    try:
        from scrapers.rss_scraper import scrape_delivery_apps
        delivery = scrape_delivery_apps()
        results.append(f"✅ تطبيقات التوصيل: {len(delivery)} عرض")
    except Exception as e:
        results.append(f"❌ تطبيقات التوصيل: {e}")

    await update.message.reply_text("\n".join(results))
