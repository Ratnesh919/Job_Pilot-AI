import os
import sys
import asyncio
import json
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

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

config = load_config()
target_roles = config.get("target_roles", ["Software Engineer", "Python Developer", "Frontend Developer"])
headless_mode = config.get("browser", {}).get("headless", True)
exp_mode = config.get("experience_level", "fresher")
prim_loc = config.get("primary_location", "Remote")

async def run_master_agent():
    print("=======================================================", flush=True)
    print(f"      🚀 JOBPILOT-AI AUTONOMOUS APPLICATION AGENT 🚀", flush=True)
    print(f"   Mode: [{exp_mode.upper()}]  |  Primary Location: [{prim_loc}]", flush=True)
    print(f"   Browser: [{'Headless Background' if headless_mode else 'Headed Visible'}]", flush=True)
    print("=======================================================\n", flush=True)

    try:
        from portal_auto_applier import run_portal_automation
        from company_site_applier import run_company_website_and_multi_portal_bot
        from llm_job_finder import run_llm_email_job_search_and_apply
    except ImportError:
        from .portal_auto_applier import run_portal_automation
        from .company_site_applier import run_company_website_and_multi_portal_bot
        from .llm_job_finder import run_llm_email_job_search_and_apply

    roles_to_run = target_roles[:3] if target_roles else ["Software Engineer"]

    for idx, role in enumerate(roles_to_run):
        print(f"\n>>>>>>>>>>>>>>> [STAGE 1/3: JOB BOARD AUTO-APPLIER] ({role}) <<<<<<<<<<<<<<<", flush=True)
        try:
            await run_portal_automation("all", keyword=role, headless=headless_mode)
        except Exception as e:
            print(f"[STAGE 1 NOTICE] {e}", flush=True)

        print(f"\n>>>>>>>>>>>>>>> [STAGE 2/3: COMPANY CAREERS FORM AUTO-FILLER] ({role}) <<<<<<<<<<<<<<<", flush=True)
        try:
            await run_company_website_and_multi_portal_bot(keyword=role, headless=headless_mode)
        except Exception as e:
            print(f"[STAGE 2 NOTICE] {e}", flush=True)

        await asyncio.sleep(1)

    print("\n>>>>>>>>>>>>>>> [STAGE 3/3: LLM RECRUITER & COLD EMAIL DISPATCHER] <<<<<<<<<<<<<<<", flush=True)
    try:
        run_llm_email_job_search_and_apply()
    except Exception as e:
        print(f"[STAGE 3 NOTICE] {e}", flush=True)

    print("\n=======================================================", flush=True)
    print("   🎉 ALL APPLICATION CHANNELS EXECUTED SUCCESSFULLY! 🎉", flush=True)
    print("=======================================================", flush=True)

if __name__ == "__main__":
    asyncio.run(run_master_agent())
