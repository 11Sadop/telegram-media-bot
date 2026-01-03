import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# قائمة روابط خطوط بديلة
FONT_URLS = [
    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Bold.ttf",
    "https://github.com/alif-type/amiri/raw/main/Amiri-Bold.ttf",
    "https://raw.githubusercontent.com/AO-Design-Inc/openZJL/main/Fonts/Arabic/DIN%20Next%20LT%20Arabic%20Bold.ttf",
]
FONT_FILE = "arabic_font.ttf"

# متغير عام للخط
FONT_LOADED = None


def download_font():
    """تحميل الخط من مصادر متعددة"""
    global FONT_LOADED
    
    if os.path.exists(FONT_FILE):
        try:
            FONT_LOADED = ImageFont.truetype(FONT_FILE, 40)
            print("✅ الخط موجود ويعمل")
            return True
        except:
            os.remove(FONT_FILE)
    
    for url in FONT_URLS:
        try:
            print(f"⬇️ تحميل الخط من: {url[:50]}...")
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(FONT_FILE, "wb") as f:
                    f.write(resp.content)
                # اختبار الخط
                FONT_LOADED = ImageFont.truetype(FONT_FILE, 40)
                print("✅ تم تحميل الخط بنجاح")
                return True
        except Exception as e:
            print(f"❌ فشل: {e}")
            continue
    
    print("⚠️ لم يتم تحميل الخط - سيتم تخطي تصميم الصور")
    return False


def load_font(size):
    """تحميل الخط بحجم معين"""
    if os.path.exists(FONT_FILE):
        try:
            return ImageFont.truetype(FONT_FILE, size)
        except:
            pass
    return None


def process_arabic(text):
    """معالجة النص العربي"""
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except:
        return text


def create_offer_image(image_url, title, price, store_name, category=""):
    """تصميم صورة العرض - يرجع None إذا فشل"""
    
    # محاولة تحميل الخط إذا لم يكن موجود
    if not os.path.exists(FONT_FILE):
        if not download_font():
            return None  # تخطي التصميم
    
    try:
        # تحميل الخط
        font_big = load_font(50)
        font_med = load_font(35)
        font_small = load_font(25)
        
        if not font_big:
            print("⚠️ الخط غير متاح")
            return None
        
        # أبعاد الصورة
        width, height = 800, 500
        
        # إنشاء الصورة
        img = Image.new('RGB', (width, height), '#0f0f23')
        draw = ImageDraw.Draw(img)
        
        # ========== الخلفية ==========
        # تدرج علوي
        for i in range(100):
            alpha = int(255 * (1 - i/100))
            draw.rectangle((0, i, width, i+1), fill=(30, 30, 80))
        
        # ========== اسم المتجر (أعلى) ==========
        store_text = process_arabic(store_name or "عرض خاص")
        draw.text((width//2, 50), store_text, font=font_big, fill='#FFD700', anchor="mm")
        
        # ========== خط فاصل ==========
        draw.line((100, 90, width-100, 90), fill='#333366', width=2)
        
        # ========== العنوان ==========
        title_text = title[:40] if title else "عرض مميز"
        title_processed = process_arabic(title_text)
        draw.text((width//2, 160), title_processed, font=font_med, fill='#FFFFFF', anchor="mm")
        
        # ========== السعر/الخصم ==========
        if price:
            price_text = process_arabic(price)
            # مستطيل ملون
            box_w, box_h = 200, 80
            box_x = (width - box_w) // 2
            box_y = 220
            draw.rounded_rectangle((box_x, box_y, box_x+box_w, box_y+box_h), 
                                   radius=15, fill='#e63946')
            draw.text((width//2, box_y + box_h//2), price_text, 
                     font=font_big, fill='#FFFFFF', anchor="mm")
        
        # ========== التصنيف ==========
        if category:
            cat_text = process_arabic(category)
            draw.text((width//2, 350), cat_text, font=font_small, fill='#888899', anchor="mm")
        
        # ========== شعار القناة ==========
        draw.rectangle((0, height-50, width, height), fill='#1a1a2e')
        channel_text = "عروض المواقع"
        draw.text((width//2, height-25), process_arabic(channel_text), 
                 font=font_small, fill='#666688', anchor="mm")
        
        # ========== حفظ ==========
        output = BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        return output
        
    except Exception as e:
        print(f"❌ خطأ التصميم: {e}")
        return None


# تحميل الخط عند بدء التشغيل
print("🔤 فحص الخط...")
download_font()
