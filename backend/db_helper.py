import os
import sys
import json
import uuid
from datetime import datetime, timedelta

# Force UTF-8 encoding on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(APP_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "applications_db.json")

def load_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_db(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_already_applied(company, role, recruiter_email=None, days_threshold=30):
    """
    Returns True if an application has already been submitted to the same company
    and role (or recruiter email) within the last `days_threshold` days.
    """
    if not company and not recruiter_email:
        return False
        
    db = load_db()
    now = datetime.now()
    c_clean = company.strip().lower() if company else ""
    r_clean = role.strip().lower() if role else ""
    e_clean = recruiter_email.strip().lower() if recruiter_email else ""

    for app in db:
        app_comp = (app.get("company") or "").strip().lower()
        app_role = (app.get("role") or "").strip().lower()
        app_email = (app.get("recruiter_email") or "").strip().lower()
        app_date_str = app.get("applied_date", "")

        # Check by recruiter email match
        if e_clean and app_email and e_clean == app_email:
            return True

        # Check by company and role match
        if c_clean and app_comp and (c_clean in app_comp or app_comp in c_clean):
            # If role also matches or overlaps
            if not r_clean or not app_role or (r_clean in app_role or app_role in r_clean):
                if app_date_str:
                    try:
                        app_dt = datetime.strptime(app_date_str[:10], "%Y-%m-%d")
                        if (now - app_dt) < timedelta(days=days_threshold):
                            return True
                    except Exception:
                        return True
                else:
                    return True

    return False

def record_application(platform, company, role, status="Applied", recruiter_email=None, notes=None):
    db = load_db()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y-%m-%d")

    entry = {
        "id": f"app_{uuid.uuid4().hex[:8]}",
        "company": company,
        "role": role,
        "platform": platform,
        "applied_date": date_str,
        "status": status,
        "recruiter_email": recruiter_email or "",
        "notes": notes or f"Application submitted via {platform}",
        "history": [
            {
                "status": status,
                "date": timestamp,
                "note": notes or f"Initial application dispatched via {platform}"
            }
        ]
    }

    db.insert(0, entry)
    save_db(db)
    return entry

if __name__ == "__main__":
    db = load_db()
    print(f"Applications Database ready. Total records: {len(db)}")
