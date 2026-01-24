import sqlite3
import os
from datetime import datetime

DATABASE_FILE = "offers.db"


def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    # Create offers table
    c.execute("""
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY,
            title TEXT,
            link TEXT UNIQUE,
            price TEXT,
            category TEXT,
            source TEXT,
            image_url TEXT,
            description TEXT,
            is_sent INTEGER DEFAULT 0
        )
    """)
    
    # Create download_stats table for tracking downloads
    c.execute("""
        CREATE TABLE IF NOT EXISTS download_stats (
            id INTEGER PRIMARY KEY,
            platform TEXT,
            success INTEGER DEFAULT 0,
            timestamp TEXT
        )
    """)
    
    # Attempt to add new columns if they don't exist (migrations)
    try:
        c.execute("ALTER TABLE offers ADD COLUMN image_url TEXT")
    except:
        pass
        
    try:
        c.execute("ALTER TABLE offers ADD COLUMN description TEXT")
    except:
        pass
        
    conn.commit()
    conn.close()
    print("Database ready")


def record_download(platform: str, success: bool):
    """Record download attempt"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute(
            "INSERT INTO download_stats (platform, success, timestamp) VALUES (?, ?, ?)",
            (platform, 1 if success else 0, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error recording download: {e}")


def get_download_stats():
    """Get download statistics"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        
        # Total success/fail
        c.execute("SELECT COUNT(*) FROM download_stats WHERE success = 1")
        success = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM download_stats WHERE success = 0")
        failed = c.fetchone()[0]
        
        # By platform
        c.execute("""
            SELECT platform, 
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
                   SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
            FROM download_stats 
            GROUP BY platform
        """)
        by_platform = {row[0]: {"success": row[1], "failed": row[2]} for row in c.fetchall()}
        
        conn.close()
        return {
            "success": success,
            "failed": failed,
            "total": success + failed,
            "by_platform": by_platform
        }
    except:
        return {"success": 0, "failed": 0, "total": 0, "by_platform": {}}


def save_offer(title, link, price=None, category=None, source=None, image_url=None, description=None):
    if not link:
        return False
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO offers 
            (title, link, price, category, source, image_url, description) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, link, price, category, source, image_url, description))
        conn.commit()
        inserted = c.rowcount > 0
        conn.close()
        return inserted
    except Exception as e:
        print(f"Error saving offer: {e}")
        return False


def get_unsent_offers(limit=10):
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM offers WHERE is_sent = 0 LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def mark_as_sent(link):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("UPDATE offers SET is_sent = 1 WHERE link = ?", (link,))
    conn.commit()
    conn.close()


def get_stats():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM offers")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM offers WHERE is_sent = 1")
    sent = c.fetchone()[0]
    conn.close()
    return {"total": total, "sent": sent, "pending": total - sent}


def clear_database():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM offers")
    conn.commit()
    conn.close()
    print("Database cleared")
