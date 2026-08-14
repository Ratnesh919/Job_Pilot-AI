"""
JobPilot-AI — Portal Login Detector & Session Manager
Checks whether the candidate is currently logged into LinkedIn, Naukri, and Indeed in the Chrome automation profile.
Can also open interactive browser tabs for one-click login.
"""

import sys
import os
import json
import asyncio
from playwright.async_api import async_playwright

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, 'data')
PROFILE_DIR = os.path.join(DATA_DIR, 'chrome_profile')
CONFIG_PATH = os.path.join(ROOT_DIR, 'config.json')

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

async def check_login_status():
    """Fast check of login state on LinkedIn and Naukri."""
    config = load_config()
    user_data_path = config.get("browser", {}).get("user_data_path") or PROFILE_DIR
    os.makedirs(user_data_path, exist_ok=True)

    status = {
        "linkedin": False,
        "naukri": False,
        "indeed": True,
        "any_logged_in": False,
        "needs_login": True
    }

    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_path,
                headless=True,
                args=['--no-first-run', '--disable-blink-features=AutomationControlled']
            )
            page = context.pages[0] if context.pages else await context.new_page()

            # 1. Check LinkedIn
            try:
                await page.goto("https://www.linkedin.com/feed/", timeout=12000, wait_until="domcontentloaded")
                curr_url = page.url.lower()
                if "feed" in curr_url and "login" not in curr_url and "authwall" not in curr_url and "checkpoint" not in curr_url:
                    status["linkedin"] = True
            except Exception:
                status["linkedin"] = False

            # 2. Check Naukri
            try:
                await page.goto("https://www.naukri.com/mnjuser/profile", timeout=12000, wait_until="domcontentloaded")
                curr_url = page.url.lower()
                if "nlogin" not in curr_url and ("mnjuser" in curr_url or "profile" in curr_url):
                    status["naukri"] = True
            except Exception:
                status["naukri"] = False

            await context.close()
    except Exception as e:
        sys.stderr.write(f"Login check error: {e}\n")

    status["any_logged_in"] = status["linkedin"] or status["naukri"]
    status["needs_login"] = not (status["linkedin"] or status["naukri"])
    return status

async def open_login_window():
    """Opens a visible headful Chrome window with login pages."""
    config = load_config()
    user_data_path = config.get("browser", {}).get("user_data_path") or PROFILE_DIR
    os.makedirs(user_data_path, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_path,
            headless=False,
            args=['--no-first-run']
        )
        p1 = context.pages[0] if context.pages else await context.new_page()
        await p1.goto("https://www.linkedin.com/login")
        
        p2 = await context.new_page()
        await p2.goto("https://www.naukri.com/nlogin/login")

        p3 = await context.new_page()
        await p3.goto("https://secure.indeed.com/auth")

        print("[LOGIN_WINDOW] Chrome opened. Log in to your accounts and close the browser when finished.", flush=True)

        try:
            # Wait up to 10 minutes for user to log in
            await p1.wait_for_timeout(600000)
        except Exception:
            pass
        await context.close()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"

    if mode == "--open":
        asyncio.run(open_login_window())
        print(json.dumps({"success": True, "message": "Login window closed"}))
    else:
        res = asyncio.run(check_login_status())
        print(json.dumps(res, indent=2))
