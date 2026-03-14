from flask import Flask, render_template, request
from models import get_emails_count, get_all_emails_for_stats, get_all_emails_sorted
from datetime import datetime
import re
from email.utils import parsedate_to_datetime
import math

app = Flask(__name__)
PER_PAGE = 100


def parse_email_content(body):
    try:
        cleaned_body = re.sub(r'<img[^>]*>', '', body, flags=re.IGNORECASE)
        cleaned_body = re.sub(r'https?://[^\s]+', '', cleaned_body)
        cleaned_body = cleaned_body.strip()
        
        pattern = r'Hello,\s*(Vessel\s*(.*?))\s*is\s*passing\s*through\s*(.*?)(?:,|\.|\s*triggering time:)'
        match = re.search(pattern, cleaned_body, re.IGNORECASE)
        
        if match:
            vessel_part = match.group(1).strip()
            location_part = match.group(3).strip()
            
            time_pattern = r'triggering time:(\d{4})-(\d{2})-(\d{2})\s*(\d{2}):(\d{2})'
            time_match = re.search(time_pattern, cleaned_body)
            
            if time_match:
                month = time_match.group(2)
                day = time_match.group(3)
                hour = time_match.group(4)
                minute = time_match.group(5)
                time_str = f"{month}-{day} {hour}:{minute}"
                return f"{vessel_part}通过{location_part}（{time_str}）"
            else:
                return f"{vessel_part}通过{location_part}"
        
        return cleaned_body[:100]
    except Exception as e:
        return body[:100]


def parse_email_date_to_datetime(date_str):
    try:
        dt = parsedate_to_datetime(date_str)
        return dt
    except:
        try:
            dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
            return dt
        except:
            return datetime.now()


def parse_email_date(date_str):
    try:
        dt = parse_email_date_to_datetime(date_str)
        today = datetime.now().date()
        email_date = dt.date()
        
        if email_date == today:
            return dt.strftime('%H:%M')
        else:
            return dt.strftime('%m-%d %H:%M')
    except:
        return date_str


def get_daily_stats(emails):
    stats = {}
    for email_data in emails:
        email_id, message_id, subject, sender, date, body, created_at, is_pushed = email_data
        try:
            dt = parse_email_date_to_datetime(date)
            date_key = dt.strftime('%m.%d')
            if date_key in stats:
                stats[date_key] += 1
            else:
                stats[date_key] = 1
        except:
            try:
                dt = datetime.fromisoformat(created_at)
                date_key = dt.strftime('%m.%d')
                if date_key in stats:
                    stats[date_key] += 1
                else:
                    stats[date_key] = 1
            except:
                continue
    
    sorted_stats = sorted(stats.items(), key=lambda x: x[0], reverse=True)
    return sorted_stats


@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    total_count = get_emails_count()
    total_pages = math.ceil(total_count / PER_PAGE)
    
    if page < 1:
        page = 1
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    all_emails_raw = get_all_emails_sorted()
    email_list_all = []
    
    for email_data in all_emails_raw:
        email_id, message_id, subject, sender, date, body, created_at, is_pushed = email_data
        
        time_str = parse_email_date(date)
        display_content = parse_email_content(body)
        email_datetime = parse_email_date_to_datetime(date)
        
        email_list_all.append({
            'id': email_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': display_content,
            'time': time_str,
            'is_pushed': bool(is_pushed),
            'datetime': email_datetime
        })
    
    email_list_all.sort(key=lambda x: x['datetime'], reverse=True)
    
    start_idx = (page - 1) * PER_PAGE
    end_idx = start_idx + PER_PAGE
    email_list = email_list_all[start_idx:end_idx]
    
    all_emails = get_all_emails_for_stats()
    daily_stats = get_daily_stats(all_emails)
    
    pagination = {
        'current_page': page,
        'total_pages': total_pages,
        'total_count': total_count,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1,
        'next_page': page + 1
    }
    
    return render_template('index.html', emails=email_list, daily_stats=daily_stats, pagination=pagination)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
