"""
أدوات الوسائط - Media Tools
إزالة الخلفيات وتحميل الفيديوهات
+ Rembg للإزالة المجانية غير المحدودة
"""

import re
import aiohttp
from io import BytesIO
from PIL import Image
import logging
import asyncio

logger = logging.getLogger(__name__)

# تحميل Rembg بشكل كسول (لتجنب استهلاك الذاكرة عند البدء)
_rembg_session = None

def get_rembg_session():
    """الحصول على جلسة Rembg (تحميل كسول)"""
    global _rembg_session
    if _rembg_session is None:
        try:
            from rembg import new_session
            _rembg_session = new_session("u2net")
            logger.info("✅ Rembg session loaded")
        except Exception as e:
            logger.warning(f"Could not load Rembg: {e}")
    return _rembg_session


# ============== إزالة الخلفية ==============

async def remove_background(image_bytes: bytes) -> BytesIO | None:
    """إزالة الخلفية من الصورة - API أولاً (أخف على السيرفر)"""
    
    # محاولة 1: Remove.bg API المجانية
    result = await remove_bg_removebg_free(image_bytes)
    if result:
        return result
    
    # محاولة 2: PhotoRoom API
    result = await remove_bg_photoroom(image_bytes)
    if result:
        return result
    
    # محاولة 3: Rembg (ثقيل - قد لا يعمل على السيرفرات المجانية)
    result = await remove_bg_rembg(image_bytes)
    if result:
        return result
    
    # محاولة 4: إزالة بسيطة للخلفيات البيضاء
    return simple_white_removal(image_bytes)


async def remove_bg_removebg_free(image_bytes: bytes) -> BytesIO | None:
    """إزالة الخلفية باستخدام API مجانية من erase.bg"""
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('image_file', image_bytes, filename='image.png', content_type='image/png')
            
            # Try erase.bg free API
            async with session.post(
                'https://api.erase.bg/upload',
                data=data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('result_url'):
                        async with session.get(result['result_url']) as img_response:
                            if img_response.status == 200:
                                content = await img_response.read()
                                output = BytesIO(content)
                                output.seek(0)
                                logger.info("✅ Background removed with erase.bg")
                                return output
    except Exception as e:
        logger.warning(f"erase.bg API failed: {e}")
    return None


async def remove_bg_rembg(image_bytes: bytes) -> BytesIO | None:
    """إزالة الخلفية باستخدام Rembg (AI محلي - مجاني وغير محدود)"""
    try:
        session = get_rembg_session()
        if session is None:
            logger.warning("Rembg not available, trying fallback")
            return None
        
        from rembg import remove
        
        # تشغيل في thread منفصل لعدم تجميد البوت
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: remove(image_bytes, session=session)
        )
        
        output = BytesIO(result)
        output.seek(0)
        logger.info("✅ Background removed with Rembg")
        return output
        
    except Exception as e:
        logger.error(f"Rembg failed: {e}")
    return None


async def remove_bg_photoroom(image_bytes: bytes) -> BytesIO | None:
    """استخدام PhotoRoom Sandbox API"""
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('image_file', image_bytes, filename='image.png', content_type='image/png')
            
            async with session.post(
                'https://sdk.photoroom.com/v1/segment',
                data=data,
                headers={'Accept': 'image/png'},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    content = await response.read()
                    output = BytesIO(content)
                    output.seek(0)
                    return output
    except Exception as e:
        logger.warning(f"PhotoRoom API failed: {e}")
    return None


async def remove_bg_preview(image_bytes: bytes) -> BytesIO | None:
    """محاولة الحصول على معاينة من Remove.bg"""
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('image_file', image_bytes, filename='image.png', content_type='image/png')
            data.add_field('size', 'preview')
            
            async with session.post(
                'https://api.remove.bg/v1.0/removebg',
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    content = await response.read()
                    output = BytesIO(content)
                    output.seek(0)
                    return output
    except Exception as e:
        logger.warning(f"Remove.bg preview failed: {e}")
    return None


def simple_white_removal(image_bytes: bytes) -> BytesIO | None:
    """إزالة بسيطة للخلفيات البيضاء"""
    try:
        img = Image.open(BytesIO(image_bytes)).convert('RGBA')
        data = img.getdata()
        
        new_data = []
        for item in data:
            # إذا كان البكسل أبيض أو قريب من الأبيض
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))  # شفاف
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        output = BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Simple removal failed: {e}")
    return None


# ============== إزالة العلامات المائية ==============

async def remove_watermark(image_bytes: bytes) -> BytesIO | None:
    """إزالة العلامات المائية الشفافة/البيضاء من الصورة"""
    try:
        import cv2
        import numpy as np
        
        # تحويل إلى مصفوفة
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None
        
        # تحويل لـ HSV للكشف عن المناطق الفاتحة جداً
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # قناع للعلامات البيضاء/الشفافة
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # توسيع القناع قليلاً
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        # Inpainting لملء المناطق
        result = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        
        # حفظ النتيجة
        _, buffer = cv2.imencode('.png', result)
        output = BytesIO(buffer.tobytes())
        output.seek(0)
        logger.info("✅ Watermark removed")
        return output
        
    except Exception as e:
        logger.error(f"Watermark removal failed: {e}")
    return None


async def remove_text_from_image(image_bytes: bytes) -> BytesIO | None:
    """إزالة الكتابة من الصورة باستخدام Inpainting"""
    try:
        import cv2
        import numpy as np
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None
        
        # تحويل لتدرج الرمادي
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # الكشف عن الحواف (النص عادة له حواف واضحة)
        edges = cv2.Canny(gray, 50, 150)
        
        # توسيع الحواف
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Inpainting
        result = cv2.inpaint(img, dilated, inpaintRadius=5, flags=cv2.INPAINT_NS)
        
        _, buffer = cv2.imencode('.png', result)
        output = BytesIO(buffer.tobytes())
        output.seek(0)
        logger.info("✅ Text removed from image")
        return output
        
    except Exception as e:
        logger.error(f"Text removal failed: {e}")
    return None


async def crop_phone_frame(image_bytes: bytes) -> BytesIO | None:
    """قص إطار الجوال (شريط الحالة والأزرار)"""
    try:
        import cv2
        import numpy as np
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None
        
        height, width = img.shape[:2]
        
        # قص النسب المعتادة لإطارات الجوال
        # شريط الحالة: ~5% من الأعلى
        # شريط التنقل: ~5% من الأسفل
        top_crop = int(height * 0.05)
        bottom_crop = int(height * 0.95)
        
        # قص الصورة
        cropped = img[top_crop:bottom_crop, :]
        
        _, buffer = cv2.imencode('.png', cropped)
        output = BytesIO(buffer.tobytes())
        output.seek(0)
        logger.info("✅ Phone frame cropped")
        return output
        
    except Exception as e:
        logger.error(f"Crop failed: {e}")
    return None


# ============== تحميل الفيديوهات ==============

async def download_video(url: str) -> dict | None:
    """تحميل فيديو من الرابط"""
    url_lower = url.lower()
    
    if 'tiktok' in url_lower:
        return await download_tiktok(url)
    elif 'instagram' in url_lower:
        return await download_instagram(url)
    elif 'pinterest' in url_lower or 'pin.it' in url_lower:
        return await download_pinterest(url)
    elif 'snapchat' in url_lower:
        return await download_snapchat(url)
    
    return None


async def download_tiktok(url: str) -> dict | None:
    """تحميل فيديو تيك توك بدون علامة مائية"""
    try:
        async with aiohttp.ClientSession() as session:
            # API الأولى
            api_url = f"https://www.tikwm.com/api/?url={url}"
            async with session.get(api_url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == 0:
                        video_data = data.get('data', {})
                        video_url = video_data.get('play') or video_data.get('hdplay')
                        if video_url:
                            async with session.get(video_url, timeout=60) as vid_response:
                                if vid_response.status == 200:
                                    content = await vid_response.read()
                                    output = BytesIO(content)
                                    output.seek(0)
                                    output.name = "tiktok_video.mp4"
                                    return {'type': 'video', 'file': output}
            
            # API احتياطية
            backup_url = f"https://api.tikmate.app/api/lookup?url={url}"
            async with session.get(backup_url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    video_url = data.get('video_url')
                    if video_url:
                        async with session.get(video_url, timeout=60) as vid_response:
                            if vid_response.status == 200:
                                content = await vid_response.read()
                                output = BytesIO(content)
                                output.seek(0)
                                output.name = "tiktok_video.mp4"
                                return {'type': 'video', 'file': output}
    except Exception as e:
        logger.error(f"TikTok download error: {e}")
    return None


async def download_instagram(url: str) -> dict | None:
    """تحميل محتوى انستقرام"""
    try:
        async with aiohttp.ClientSession() as session:
            api_url = "https://api.igram.io/api/ig"
            async with session.post(
                api_url,
                json={"url": url},
                headers={'Content-Type': 'application/json'},
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('items', [])
                    if items:
                        item = items[0]
                        media_url = item.get('url')
                        if media_url:
                            async with session.get(media_url, timeout=60) as media_response:
                                if media_response.status == 200:
                                    content = await media_response.read()
                                    output = BytesIO(content)
                                    output.seek(0)
                                    if 'video' in item.get('type', '').lower():
                                        output.name = "instagram_video.mp4"
                                        return {'type': 'video', 'file': output}
                                    else:
                                        output.name = "instagram_photo.jpg"
                                        return {'type': 'photo', 'file': output}
    except Exception as e:
        logger.error(f"Instagram download error: {e}")
    return None


async def download_pinterest(url: str) -> dict | None:
    """تحميل محتوى بنترست"""
    try:
        # استخراج Pin ID
        patterns = [
            r'pin/(\d+)',
            r'pin\.it/(\w+)',
        ]
        pin_id = None
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                pin_id = match.group(1)
                break
        
        if not pin_id:
            return None
            
        async with aiohttp.ClientSession() as session:
            api_url = f"https://api.pinterest.com/v3/pidgets/pins/info/?pin_ids={pin_id}"
            async with session.get(api_url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    pin_data = data.get('data', [{}])[0]
                    images = pin_data.get('images', {})
                    
                    # محاولة الحصول على أعلى دقة
                    image_url = None
                    for key in ['orig', '736x', '564x', '474x']:
                        if key in images:
                            image_url = images[key].get('url')
                            break
                    
                    if image_url:
                        async with session.get(image_url, timeout=60) as img_response:
                            if img_response.status == 200:
                                content = await img_response.read()
                                output = BytesIO(content)
                                output.seek(0)
                                output.name = "pinterest_image.jpg"
                                return {'type': 'photo', 'file': output}
    except Exception as e:
        logger.error(f"Pinterest download error: {e}")
    return None


async def download_snapchat(url: str) -> dict | None:
    """تحميل محتوى سناب شات"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30, allow_redirects=True) as response:
                if response.status == 200:
                    html = await response.text()
                    # البحث عن رابط الفيديو في HTML
                    video_patterns = [
                        r'"media_url":"([^"]+)"',
                        r'source src="([^"]+\.mp4[^"]*)"',
                        r'"url":"(https://[^"]*\.mp4[^"]*)"',
                    ]
                    for pattern in video_patterns:
                        match = re.search(pattern, html)
                        if match:
                            video_url = match.group(1).replace('\\u002F', '/')
                            async with session.get(video_url, timeout=60) as vid_response:
                                if vid_response.status == 200:
                                    content = await vid_response.read()
                                    output = BytesIO(content)
                                    output.seek(0)
                                    output.name = "snapchat_video.mp4"
                                    return {'type': 'video', 'file': output}
    except Exception as e:
        logger.error(f"Snapchat download error: {e}")
    return None


# دالة مساعدة للتحقق من نوع الرابط
def is_supported_url(url: str) -> bool:
    """التحقق إذا كان الرابط مدعوم"""
    supported = ['tiktok', 'instagram', 'pinterest', 'pin.it', 'snapchat']
    url_lower = url.lower()
    return any(domain in url_lower for domain in supported)
