import os
import sys
import json
import asyncio
from datetime import datetime

# Fix Windows cp1252 encoding crash on emoji characters
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(BACKEND_DIR)
CV_ROOT = os.path.dirname(APP_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from portal_auto_applier import run_portal_automation
from company_site_applier import run_company_website_and_multi_portal_bot
from llm_job_finder import run_llm_email_job_search_and_apply
CONFIG_PATH = os.path.join(APP_ROOT, "config.json")
DATA_DIR = os.path.join(APP_ROOT, "data")
AUTO_SUMMARY_FILE = os.path.join(DATA_DIR, "all_applications_summary.csv")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

config = load_config()

TARGET_ROLES = config.get("target_roles", [
    "Python Developer",
    "Software Engineer",
    "Frontend Developer",
    "UI UX Designer",
    "AI Automation Engineer",
    "n8n Automation Developer",
    "Network Engineer",
    "Embedded Systems Engineer",
    "IoT Hardware Developer",
    "Electronics & Communication Engineer"
])

async def run_all_in_one_auto_bot(api_key=None, provider="openrouter", headless=False):
    print("=" * 75, flush=True)
    print("       RATNESH KUMAR SINGH - ALL-IN-ONE AUTOMATED JOB ENGINE       ", flush=True)
    print("=" * 75, flush=True)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    resume_path = config.get("resume_path", os.path.join(CV_ROOT, "Resume.pdf"))
    print(f"Target Resume for Application Uploads & Emails: {resume_path}", flush=True)
    mode_str = "Headless (Silent Background)" if headless else "Headed (Visible Browser Window)"
    print(f"Execution Mode: [{mode_str}]", flush=True)
    print("=" * 75, flush=True)
    
    if not os.path.exists(resume_path):
        print(f"CRITICAL WARNING: Resume PDF not found at {resume_path}", flush=True)
        return

    # STEP 1: Run Multi-Role Auto-Applier on Portals (LinkedIn + Indeed + Naukri)
    for idx, role in enumerate(TARGET_ROLES[:6]):
        print(f"\n=======================================================", flush=True)
        print(f"   [STAGE 1/3] PORTAL AUTO-APPLYING FOR: {role.upper()}", flush=True)
        print(f"=======================================================", flush=True)
        try:
            await run_portal_automation(portal_choice="all", keyword=role, headless=headless)
        except Exception as e:
            print(f"Portal automation notice for {role}: {e}", flush=True)

    # STEP 2: Company Careers Websites & Multi-Portal Scraper (Foundit, Monster, Workday, Greenhouse)
    for idx, role in enumerate(TARGET_ROLES[:4]):
        print(f"\n=======================================================", flush=True)
        print(f"   [STAGE 2/3] COMPANY WEBSITE FORM AUTO-FILLER: {role.upper()}", flush=True)
        print(f"=======================================================", flush=True)
        try:
            await run_company_website_and_multi_portal_bot(keyword=role, headless=headless)
        except Exception as e:
            print(f"Company website automation notice for {role}: {e}", flush=True)

    # STEP 3: LLM Unlisted Job Finder & Gmail Direct Email Dispatcher with Resume.pdf
    print(f"\n=======================================================", flush=True)
    print(f"   [STAGE 3/3] LLM UNLISTED JOB FINDER & EMAIL DISPATCHER", flush=True)
    print(f"   (Attaching: Resume.pdf)", flush=True)
    print(f"=======================================================", flush=True)
    try:
        run_llm_email_job_search_and_apply(api_key=api_key, provider=provider)
    except Exception as e:
        print(f"LLM email application engine notice: {e}", flush=True)

    print("\n=======================================================", flush=True)
    print("[DONE] ALL-IN-ONE JOB AUTOMATION CYCLE FULLY COMPLETED!", flush=True)
    print("Check data/applications_db.json and portal_applications_log.csv for full logs.", flush=True)
    print("=======================================================", flush=True)

if __name__ == "__main__":
    asyncio.run(run_all_in_one_auto_bot(headless=False))
