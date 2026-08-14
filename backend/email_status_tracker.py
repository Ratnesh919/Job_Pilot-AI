import os
import sys
import imaplib
import email
from email.header import decode_header
import json
import re
from datetime import datetime

# Force UTF-8 encoding on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(BACKEND_DIR)
CONFIG_PATH = os.path.join(APP_ROOT, "config.json")
DATA_DIR = os.path.join(APP_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "applications_db.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def load_db():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_db(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def decode_mime_words(s):
    if not s:
        return ""
    decoded_fragments = decode_header(s)
    result = []
    for text, charset in decoded_fragments:
        if isinstance(text, bytes):
            try:
                result.append(text.decode(charset or 'utf-8', errors='replace'))
            except Exception:
                result.append(text.decode('latin1', errors='replace'))
        else:
            result.append(str(text))
    return " ".join(result)

def check_gmail_inbox_updates():
    cfg = load_config()
    sender = cfg.get("email", {}).get("sender", "")
    password = cfg.get("email", {}).get("app_password", "").replace(" ", "")

    if not sender or not password:
        return {
            "success": False,
            "message": "Gmail sender email or App Password not configured in Settings.",
            "updates": []
        }

    db = load_db()
    detected_updates = []

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(sender, password)
        mail.select("inbox")

        # Search for recent hiring related messages
        status, messages = mail.search(None, '(OR OR OR (SUBJECT "interview") (SUBJECT "application") (SUBJECT "assessment") (SUBJECT "offer"))')
        if status != "OK":
            return {"success": True, "message": "No relevant recruiter emails found.", "updates": []}

        msg_ids = messages[0].split()
        recent_ids = msg_ids[-25:] if len(msg_ids) > 25 else msg_ids

        for m_id in reversed(recent_ids):
            res, msg_data = mail.fetch(m_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_mime_words(msg.get("Subject", ""))
                    from_header = decode_mime_words(msg.get("From", ""))
                    date_header = msg.get("Date", "")

                    subj_lower = subject.lower()
                    from_lower = from_header.lower()

                    # Classify status
                    new_status = None
                    note = ""

                    if any(k in subj_lower for k in ["interview", "invitation to interview", "round", "discussion", "schedule"]):
                        new_status = "Interview Scheduled"
                        note = f"Recruiter invite received: '{subject}'"
                    elif any(k in subj_lower for k in ["assessment", "coding test", "hackerrank", "online test", "screening test"]):
                        new_status = "Assessment / Test"
                        note = f"Technical assessment link received: '{subject}'"
                    elif any(k in subj_lower for k in ["offer", "selected", "letter of intent", "congratulations"]):
                        new_status = "Selected / Offered"
                        note = f"Offer notification: '{subject}'"
                    elif any(k in subj_lower for k in ["not moving forward", "unfortunate", "regret", "rejected", "other candidates"]):
                        new_status = "Rejected"
                        note = f"Status update notice: '{subject}'"

                    if new_status:
                        # Match with database
                        for app in db:
                            comp = (app.get("company") or "").lower()
                            if comp and len(comp) > 2 and (comp in from_lower or comp in subj_lower):
                                if app.get("status") != new_status:
                                    app["status"] = new_status
                                    if "history" not in app:
                                        app["history"] = []
                                    app["history"].append({
                                        "status": new_status,
                                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "note": note
                                    })
                                    detected_updates.append({
                                        "company": app.get("company"),
                                        "newStatus": new_status,
                                        "note": note
                                    })

        save_db(db)
        mail.close()
        mail.logout()

        return {
            "success": True,
            "message": f"Inbox scan completed. Found {len(detected_updates)} status changes.",
            "updates": detected_updates
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Gmail scan error: {str(e)}",
            "updates": []
        }

if __name__ == "__main__":
    res = check_gmail_inbox_updates()
    print(json.dumps(res, indent=2))
