import poplib
import email
from email.header import decode_header
import requests
import time
import os
from config import *


PROCESSED_MESSAGES_FILE = "processed_messages.txt"


def load_processed_messages():
    processed = set()
    try:
        if os.path.exists(PROCESSED_MESSAGES_FILE):
            with open(PROCESSED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        processed.add(line)
    except Exception as e:
        print(f"加载已处理邮件列表时出错: {e}")
    return processed


def save_processed_message(message_id):
    try:
        with open(PROCESSED_MESSAGES_FILE, 'a', encoding='utf-8') as f:
            f.write(message_id + '\n')
    except Exception as e:
        print(f"保存已处理邮件时出错: {e}")


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
    processed_messages = load_processed_messages()
    new_emails = []

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
                
                if message_id in processed_messages:
                    continue
                
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
                
                new_emails.append({
                    "id": i,
                    "subject": subject,
                    "from": from_,
                    "date": date,
                    "body": body,
                    "message_id": message_id
                })
                
                save_processed_message(message_id)
                print(f"发现新邮件: {subject}")
                
            except Exception as e:
                print(f"获取第 {i} 封邮件时出错: {e}")
                continue
        
        pop_conn.quit()
        print("检查完成")
        
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

    if new_emails:
        for mail_info in new_emails:
            title = f"新邮件: {mail_info['subject']}"
            content = f" {mail_info['from']}\n {mail_info['date']}\n\n{mail_info['body'][:500]}"
            print(f"推送邮件: {title}")
            send_pushplus(title, content)
        
        print(f"已处理 {len(new_emails)} 封新邮件")
    
    return True


def main():
    print(f"开始监听163邮箱: {EMAIL_USER}")
    print(f"检查间隔: {CHECK_INTERVAL} 秒")
    print(f"已处理邮件列表保存在: {PROCESSED_MESSAGES_FILE}")
    
    while True:
        check_emails()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
