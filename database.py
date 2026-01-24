import sqlite3
import os
from datetime import datetime

DATABASE_FILE = "offers.db"


def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS download_stats (
            id INTEGER PRIMARY KEY,
            platform TEXT,
            success INTEGER DEFAULT 0,
            timestamp TEXT
        )
    """)
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


def record_download(platform, success):
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO download_stats (platform, success, timestamp) VALUES (?, ?, ?)",
            (platform, 1 if success else 0, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error recording download: {e}")


def get_download_stats():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM download_stats WHERE success = 1")
        success = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM download_stats WHERE success = 0")
        failed = c.fetchone()[0]
        conn.close()
        return {"success": success, "failed": failed, "total": success + failed}
    except:
        return {"success": 0, "failed": 0, "total": 0}


def track_user(user_id, username=None, first_name=None):
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            first_seen TEXT, last_seen TEXT, message_count INTEGER DEFAULT 1)""")
        now = datetime.now().isoformat()
        c.execute("SELECT message_count FROM users WHERE user_id = ?", (user_id,))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE users SET username=?, first_name=?, last_seen=?, message_count=message_count+1 WHERE user_id=?",
                (username, first_name, now, user_id))
        else:
            c.execute("INSERT INTO users (user_id, username, first_name, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, first_name, now, now))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error tracking user: {e}")


def get_user_stats():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total = c.fetchone()[0]
        today = datetime.now().date().isoformat()
        c.execute("SELECT COUNT(*) FROM users WHERE last_seen LIKE ?", (f"{today}%",))
        today_active = c.fetchone()[0]
        c.execute("SELECT username, first_name, message_count FROM users ORDER BY last_seen DESC LIMIT 5")
        recent = c.fetchall()
        conn.close()
        return {"total": total, "today_active": today_active, "recent": recent}
    except:
        return {"total": 0, "today_active": 0, "recent": []}


def save_offer(title, link, price=None, category=None, source=None, image_url=None, description=None):
    if not link:
        return False
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO offers (title, link, price, category, source, image_url, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, link, price, category, source, image_url, description))
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
