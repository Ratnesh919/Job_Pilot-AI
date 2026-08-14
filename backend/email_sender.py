import os
import sys
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Force UTF-8 encoding on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(BACKEND_DIR)
CONFIG_PATH = os.path.join(APP_ROOT, "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

config = load_config()
SENDER_EMAIL = config.get("email", {}).get("sender", os.getenv("GMAIL_SENDER", ""))
APP_PASSWORD = config.get("email", {}).get("app_password", os.getenv("GMAIL_APP_PASSWORD", "")).replace(" ", "")

def send_application_email(recipient_email, subject, body_text, resume_path=None):
    cfg = load_config()
    sender = cfg.get("email", {}).get("sender", SENDER_EMAIL)
    password = cfg.get("email", {}).get("app_password", APP_PASSWORD).replace(" ", "")

    if not sender or not password:
        return {"success": False, "error": "Gmail sender or App Password not configured in Settings."}

    msg = MIMEMultipart()
    msg["From"] = f"{cfg.get('candidate', {}).get('name', 'Job Candidate')} <{sender}>"
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))

    # Attach PDF resume if available
    pdf_path = resume_path or cfg.get("resume_path", os.path.join(APP_ROOT, "Resume.pdf"))
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join(APP_ROOT, pdf_path)

    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
                msg.attach(attach)
        except Exception as e:
            print(f"[ATTACHMENT WARNING] Could not attach {pdf_path}: {e}", file=sys.stderr)

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12)
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return {"success": True, "message": f"Email successfully dispatched to {recipient_email}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_smtp_connection():
    cfg = load_config()
    sender = cfg.get("email", {}).get("sender", SENDER_EMAIL)
    password = cfg.get("email", {}).get("app_password", APP_PASSWORD).replace(" ", "")
    if not sender or not password:
        return False
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8)
        server.login(sender, password)
        server.quit()
        return True
    except Exception:
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        ok = test_smtp_connection()
        print("SMTP_OK" if ok else "SMTP_FAIL")
    else:
        print("Usage: python email_sender.py --test")
