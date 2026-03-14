import poplib
import email
from email.header import decode_header
import requests
import time
import os
import threading
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from config import *
from models import save_email, get_all_emails, mark_all_as_pushed


def decode_str(s):
    if not s:
        return ""
    decoded = decode_header(s)
    result = []
    for part, charset in decoded:
        if isinstance(part, bytes):
            if charset:
                try:
                    result.append(part.decode(charset))
                except:
                    result.append(part.decode('utf-8', errors='ignore'))
            else:
                result.append(part.decode('utf-8', errors='ignore'))
        else:
            result.append(str(part))
    return ''.join(result)


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


def send_pushplus(title, content):
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "topic": "测试"
    }
    try:
        response = requests.post(PUSHPLUS_URL, data=data)
        return response.json()
    except Exception as e:
        print(f"推送失败: {e}")
        return None


def check_emails():
    try:
        print(f"尝试连接到POP3服务器: {POP3_SERVER}")
        pop_conn = poplib.POP3_SSL(POP3_SERVER, POP3_PORT)
        print(f"已连接到POP3服务器: {POP3_SERVER}")
        
        print(f"尝试登录邮箱: {EMAIL_USER}")
        pop_conn.user(EMAIL_USER)
        pop_conn.pass_(EMAIL_PASSWORD)
        print("登录成功")
        
        num_messages = len(pop_conn.list()[1])
        print(f"邮箱共有 {num_messages} 封邮件")
        
        new_saved_count = 0
        
        for i in range(max(1, num_messages - 50), num_messages + 1):
            try:
                print(f"正在检查第 {i} 封邮件...")
                resp, lines, octets = pop_conn.retr(i)
                
                msg_content = b'\r\n'.join(lines)
                msg = email.message_from_bytes(msg_content)
                
                subject = decode_str(msg["subject"])
                from_ = decode_str(msg.get("from"))
                date = msg.get("date")
                message_id = msg.get("Message-ID", "")
                
                if not message_id:
                    message_id = f"auto_id_{i}_{int(time.time())}"
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            try:
                                body = part.get_payload(decode=True).decode()
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        pass
                
                if save_email(message_id, subject, from_, date, body):
                    new_saved_count += 1
                    print(f"发现并保存新邮件: {subject}")
                
            except Exception as e:
                print(f"获取第 {i} 封邮件时出错: {e}")
                continue
        
        pop_conn.quit()
        print(f"检查完成，共保存 {new_saved_count} 封新邮件")
        
        if new_saved_count > 0:
            push_all_emails()
        
    except Exception as e:
        print(f"检查邮件出错: {e}")
        print("\n解决方案：")
        print("1. 登录163邮箱网页版 (mail.163.com)")
        print("2. 进入 设置 → 邮箱安全设置")
        print("3. 开启 POP3/SMTP 服务")
        print("4. 在 登录保护 → 设备管理 中添加信任设备")
        print("5. 关闭 登录保护 → 登录地点保护")
        print("6. 尝试在网页端登录后，再运行此程序")
        print("7. 检查授权码是否正确")
        return False
    
    return True


def push_all_emails():
    all_emails = get_all_emails()
    print(f"开始推送所有 {len(all_emails)} 封邮件")
    
    email_list = []
    for email_data in all_emails:
        email_id, message_id, subject, sender, date, body, created_at, is_pushed = email_data
        
        time_str = parse_email_date(date)
        display_content = parse_email_content(body)
        email_datetime = parse_email_date_to_datetime(date)
        
        email_list.append({
            'time': time_str,
            'content': display_content,
            'datetime': email_datetime
        })
    
    email_list.sort(key=lambda x: x['datetime'], reverse=True)
    
    content_parts = []
    for email_item in email_list:
        content_part = f"{email_item['time']} {email_item['content']}\n"
        content_parts.append(content_part)
    
    full_content = "\n".join(content_parts)
    title = f"📧 新邮件通知 - 共 {len(email_list)} 封"
    
    print(f"推送邮件汇总: {title}")
    result = send_pushplus(title, full_content)
    
    if result:
        mark_all_as_pushed()
        print(f"推送成功，已标记所有邮件为已推送")


def start_flask():
    from app import app
    app.run(debug=False, host='0.0.0.0', port=3000)


def main():
    print(f"开始监听163邮箱: {EMAIL_USER}")
    print(f"检查间隔: {CHECK_INTERVAL} 秒")
    print(f"Web界面地址: http://localhost:3000")
    
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    time.sleep(2)
    
    while True:
        check_emails()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
