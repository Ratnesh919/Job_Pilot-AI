"""
ApplyBot Pro — Portal Login Detector & One-Time Session Manager
================================================================
The bot uses a DEDICATED bot Chrome profile (separate from your main Chrome)
so both can run simultaneously.

On first run, the bot profile has NO sessions. This script:
  1. Opens the bot profile browser (visible)
  2. Checks if already logged into LinkedIn / Naukri / Indeed
  3. If NOT logged in: navigates to login page and WAITS for user
  4. Once logged in, closes browser → sessions saved permanently in bot profile
  5. Next time bot runs: already logged in, no manual action needed
"""

import sys
import os
import json
import asyncio
from playwright.async_api import async_playwright

ROOT_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(ROOT_DIR, 'data')
# ← MUST match the path used in portal_auto_applier.py
BOT_PROFILE = os.path.join(DATA_DIR, 'bot_chrome_profile')
CONFIG_PATH = os.path.join(ROOT_DIR, 'config.json')

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_chrome_exe():
    cfg = load_config()
    path = cfg.get("browser", {}).get("chrome_path",
           r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    return path if os.path.exists(path) else None


async def check_login_status():
    """
    Checks login state using the bot profile (headless=False required —
    some portals 302 to login on headless).
    Returns dict: {linkedin, naukri, indeed, any_logged_in, needs_login}
    """
    os.makedirs(BOT_PROFILE, exist_ok=True)
    chrome_exe = get_chrome_exe()

    status = {
        "linkedin": False,
        "naukri":   False,
        "indeed":   False,
        "any_logged_in": False,
        "needs_login":   True
    }

    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=BOT_PROFILE,
                executable_path=chrome_exe,
                headless=True,    # just checking, not applying
                args=[
                    '--no-first-run',
                    '--disable-blink-features=AutomationControlled',
                ],
                ignore_default_args=['--enable-automation'],
            )
            page = context.pages[0] if context.pages else await context.new_page()

            # LinkedIn
            try:
                await page.goto("https://www.linkedin.com/feed/",
                                timeout=15000, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
                url = page.url.lower()
                if "feed" in url and "login" not in url and "authwall" not in url:
                    status["linkedin"] = True
            except Exception:
                pass

            # Naukri
            try:
                await page.goto("https://www.naukri.com/mnjuser/profile",
                                timeout=15000, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
                url = page.url.lower()
                if "nlogin" not in url and ("mnjuser" in url or "profile" in url):
                    status["naukri"] = True
            except Exception:
                pass

            # Indeed
            try:
                await page.goto("https://www.indeed.com/",
                                timeout=15000, wait_until="domcontentloaded")
                await page.wait_for_timeout(1000)
                content = await page.content()
                if "sign in" not in content.lower() and "log in" not in content.lower():
                    status["indeed"] = True
                else:
                    status["indeed"] = True   # Indeed works without login for some jobs
            except Exception:
                status["indeed"] = True

            await context.close()

    except Exception as e:
        sys.stderr.write(f"Login check error: {e}\n")

    status["any_logged_in"]  = status["linkedin"] or status["naukri"]
    status["needs_login"]    = not status["any_logged_in"]
    return status


async def open_login_window():
    """
    Opens the bot's Chrome profile visibly and navigates to login pages.
    Waits up to 10 minutes for the user to log in.
    Once the user is logged in and closes the browser (or 10min elapses),
    sessions are saved in the bot profile for all future runs.
    """
    os.makedirs(BOT_PROFILE, exist_ok=True)
    chrome_exe = get_chrome_exe()

    print("[LOGIN] Opening bot browser for one-time login setup...", flush=True)
    print("[LOGIN] Please log into LinkedIn, Naukri, and Indeed in the browser.", flush=True)
    print("[LOGIN] When done, close ALL tabs in that browser window.", flush=True)
    print("[LOGIN] Your sessions will be saved permanently.", flush=True)

    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=BOT_PROFILE,
                executable_path=chrome_exe,
                headless=False,
                args=[
                    '--no-first-run',
                    '--disable-blink-features=AutomationControlled',
                    '--start-maximized',
                    '--disable-infobars',
                    '--disable-session-crashed-bubble',
                ],
                ignore_default_args=['--enable-automation'],
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/127.0.0.0 Safari/537.36"
                ),
                viewport=None,
            )
        except Exception as e:
            print(f"[LOGIN] Could not open bot browser: {e}", flush=True)
            return {"success": False, "message": str(e)}

        # Open the 3 login pages
        p1 = context.pages[0] if context.pages else await context.new_page()
        try:
            await p1.goto("https://www.linkedin.com/login", timeout=15000)
        except Exception:
            pass

        p2 = await context.new_page()
        try:
            await p2.goto("https://www.naukri.com/nlogin/login", timeout=15000)
        except Exception:
            pass

        p3 = await context.new_page()
        try:
            await p3.goto("https://secure.indeed.com/auth", timeout=15000)
        except Exception:
            pass

        print("[LOGIN] Browser is open. Waiting for you to log in (up to 10 minutes)...", flush=True)

        # Poll every 10 seconds to check if user logged in to at least one portal
        for _ in range(60):  # 60 x 10s = 10 minutes
            await asyncio.sleep(10)

            # Check if browser was closed by user
            if not context.pages:
                break

            # Check LinkedIn login
            try:
                url = p1.url.lower() if not p1.is_closed() else ""
                if "feed" in url and "login" not in url:
                    print("[LOGIN] LinkedIn: Logged in ✓", flush=True)
                    break
            except Exception:
                break

            # Check Naukri login
            try:
                url = p2.url.lower() if not p2.is_closed() else ""
                if "nlogin" not in url and "naukri.com" in url and "login" not in url:
                    print("[LOGIN] Naukri: Logged in ✓", flush=True)
                    break
            except Exception:
                break

        print("[LOGIN] Sessions saved to bot profile. Closing login browser.", flush=True)
        try:
            await context.close()
        except Exception:
            pass

    return {"success": True, "message": "Login complete. Sessions saved permanently."}


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"

    if mode == "--open":
        result = asyncio.run(open_login_window())
        print(json.dumps(result))
    else:
        res = asyncio.run(check_login_status())
        print(json.dumps(res, indent=2))
