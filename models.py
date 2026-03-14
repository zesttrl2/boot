import sqlite3
from datetime import datetime


def init_db():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            subject TEXT,
            sender TEXT,
            date TEXT,
            body TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_pushed INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()


def save_email(message_id, subject, sender, date, body):
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO emails (message_id, subject, sender, date, body)
            VALUES (?, ?, ?, ?, ?)
        ''', (message_id, subject, sender, date, body))
        conn.commit()
        
        if cursor.rowcount > 0:
            return True
        return False
    except Exception as e:
        print(f"保存邮件到数据库时出错: {e}")
        return False
    finally:
        conn.close()


def get_recent_emails(limit=100):
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, message_id, subject, sender, date, body, created_at, is_pushed
        FROM emails
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    
    emails = cursor.fetchall()
    conn.close()
    
    return emails


def get_emails_count():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM emails')
    count = cursor.fetchone()[0]
    conn.close()
    
    return count


def get_emails_page(page=1, per_page=100):
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    offset = (page - 1) * per_page
    
    cursor.execute('''
        SELECT id, message_id, subject, sender, date, body, created_at, is_pushed
        FROM emails
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    
    emails = cursor.fetchall()
    conn.close()
    
    return emails


def get_all_emails_for_stats():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, message_id, subject, sender, date, body, created_at, is_pushed
        FROM emails
        ORDER BY id DESC
    ''')
    
    emails = cursor.fetchall()
    conn.close()
    
    return emails


def get_all_emails_sorted():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, message_id, subject, sender, date, body, created_at, is_pushed
        FROM emails
    ''')
    
    emails = cursor.fetchall()
    conn.close()
    
    return emails


def mark_as_pushed(email_id):
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE emails SET is_pushed = 1 WHERE id = ?', (email_id,))
        conn.commit()
    finally:
        conn.close()


def get_unpushed_emails():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, message_id, subject, sender, date, body, created_at
        FROM emails
        WHERE is_pushed = 0
        ORDER BY created_at DESC
    ''')
    
    emails = cursor.fetchall()
    conn.close()
    
    return emails


def get_all_emails():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, message_id, subject, sender, date, body, created_at, is_pushed
        FROM emails
        ORDER BY created_at DESC
    ''')
    
    emails = cursor.fetchall()
    conn.close()
    
    return emails


def mark_all_as_pushed():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE emails SET is_pushed = 1 WHERE is_pushed = 0')
        conn.commit()
    finally:
        conn.close()


init_db()
