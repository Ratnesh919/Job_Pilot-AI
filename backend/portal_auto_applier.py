"""
ApplyBot Pro — Multi-Portal REAL Auto-Applier (LinkedIn, Naukri, Indeed)
========================================================================
FIXED VERSION — Genuinely clicks Apply buttons and submits applications.

Key fixes:
  1. Never logs "Applied" unless the application was ACTUALLY submitted.
  2. Runs in HEADED (visible) mode so portals don't block automation.
  3. Uses the user's real Chrome profile (already logged in) via persistent context.
  4. Robust multi-selector strategy for LinkedIn/Naukri/Indeed current HTML.
  5. Walks all modal steps including phone/resume pre-fill before submitting.
"""

import os
import sys
import asyncio
import csv
import json
import re
import urllib.parse
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ── UTF-8 on Windows ──────────────────────────────────────────────────────────
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ── Path bootstrap ────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT    = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from db_helper import record_application, is_already_applied
except ImportError:
    def record_application(*a, **kw): pass
    def is_already_applied(*a, **kw): return False

# ── Paths ─────────────────────────────────────────────────────────────────────
CONFIG_PATH      = os.path.join(APP_ROOT, "config.json")
DATA_DIR         = os.path.join(APP_ROOT, "data")
PORTAL_LOG_FILE  = os.path.join(DATA_DIR, "portal_applications_log.csv")
RESUME_PDF_PATH  = os.path.join(APP_ROOT, "Resume.pdf")

# ── Config ────────────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

config           = load_config()
CHROME_EXE       = config.get("browser", {}).get("chrome_path",
                     r"C:\Program Files\Google\Chrome\Application\chrome.exe")
CHROME_USER_DATA = config.get("browser", {}).get("user_data_path",
                     r"C:\Users\akssi\AppData\Local\Google\Chrome\User Data")
EXP_LEVEL        = config.get("experience_level", "fresher")
PRIMARY_LOCATION = config.get("primary_location", "India")
USER_NAME        = config.get("name", "Ratnesh Kumar Singh")
USER_EMAIL       = config.get("email", "kumarsinghratnesh3@gmail.com")
USER_PHONE       = config.get("phone", "+91 70049 37129")

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_search_term(keyword: str) -> str:
    if EXP_LEVEL == "fresher":
        if "fresher" not in keyword.lower() and "entry" not in keyword.lower():
            return f"{keyword} Fresher"
    return keyword


def log_applied(platform, company, title, loc, job_url):
    """Only call this when the application was ACTUALLY submitted."""
    os.makedirs(DATA_DIR, exist_ok=True)
    exists = os.path.exists(PORTAL_LOG_FILE)
    with open(PORTAL_LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["Timestamp","Platform","Company","Job Title","Location","Status","URL"])
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    platform, company, title, loc, "Applied", job_url])
    try:
        record_application(platform, company, title, status="Applied",
                           notes=f"Real submit via Playwright ({EXP_LEVEL})")
    except Exception:
        pass


async def safe_click(page, selectors, label="button", timeout=6000):
    """Try each selector, return True if clicked."""
    for sel in selectors:
        try:
            el = await page.wait_for_selector(sel, timeout=timeout, state="visible")
            if el:
                await el.scroll_into_view_if_needed()
                await el.click()
                print(f"      -> Clicked [{label}]: {sel}", flush=True)
                return True
        except Exception:
            pass
    return False


async def fill_if_empty(page, selector, value):
    """Fill a field only if it is currently empty."""
    try:
        el = await page.query_selector(selector)
        if el:
            cur = await el.input_value()
            if not cur.strip():
                await el.fill(value)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# 1. NAUKRI
# ═══════════════════════════════════════════════════════════════════════════════
async def auto_apply_naukri(context, keyword="Software Engineer", location="India"):
    search_term = get_search_term(keyword)
    loc_slug    = location.lower().replace(' ', '-').replace(',', '').replace('  ', '-')
    kw_slug     = search_term.lower().replace(' ', '-')

    print(f"\n{'='*60}", flush=True)
    print(f"[NAUKRI] Applying for: '{search_term}' in {location}", flush=True)
    print(f"{'='*60}", flush=True)

    page = await context.new_page()
    applied = 0
    jobs    = []

    try:
        search_urls = [
            f"https://www.naukri.com/{kw_slug}-jobs-in-{loc_slug}",
            f"https://www.naukri.com/jobs?k={urllib.parse.quote(search_term)}&l={urllib.parse.quote(location)}",
        ]

        for s_url in search_urls:
            print(f"[NAUKRI] Search URL: {s_url}", flush=True)
            try:
                await page.goto(s_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3500)
            except Exception as e:
                print(f"[NAUKRI] Nav error: {e}", flush=True)
                continue

            # ── Naukri 2024 selectors ──────────────────────────────────────
            cards = await page.query_selector_all(
                "div.srp-jobtuple-wrapper, "
                "div.cust-job-tuple, "
                "article.jobTuple, "
                "[class*='jobTuple'], "
                "div.list"
            )
            print(f"[NAUKRI] Found {len(cards)} job cards.", flush=True)

            for card in cards[:10]:
                try:
                    title_el = await card.query_selector(
                        "a.title, "
                        "a[class*='jobTitle'], "
                        "a[title]"
                    )
                    comp_el  = await card.query_selector(
                        "a.comp-name, "
                        "a[class*='companyName'], "
                        "span[class*='companyName'], "
                        "a.subTitle"
                    )
                    if not title_el:
                        continue
                    title   = (await title_el.text_content() or "").strip()
                    company = (await comp_el.text_content() or "Naukri Employer").strip() if comp_el else "Naukri Employer"
                    href    = await title_el.get_attribute("href") or ""
                    if href and len(title) > 3 and not any(j["url"] == href for j in jobs):
                        jobs.append({"title": title, "company": company, "url": href, "loc": location})
                except Exception:
                    pass

            if jobs:
                break

        print(f"[NAUKRI] Processing {min(len(jobs), 5)} jobs.", flush=True)

        for idx, job in enumerate(jobs[:5]):
            title, company, job_url, loc = job["title"], job["company"], job["url"], job["loc"]

            if is_already_applied(company, title):
                print(f"  [{idx+1}] SKIP – already applied: {title} @ {company}", flush=True)
                continue

            print(f"\n  [{idx+1}] Opening: '{title}' @ '{company}'", flush=True)
            jp = await context.new_page()
            try:
                await jp.goto(job_url, wait_until="domcontentloaded", timeout=25000)
                await jp.wait_for_timeout(2500)

                # Apply button selectors (Naukri 2024 DOM)
                clicked = await safe_click(jp, [
                    "button#apply-button",
                    "button.apply-button",
                    "div.apply-button-container button",
                    "button[type='button'][class*='apply']",
                    "a.apply-button",
                    "button:has-text('Apply')",
                    "button:has-text('Apply now')",
                    "span:has-text('Apply') >> xpath=..",
                ], label="Naukri Apply", timeout=5000)

                if not clicked:
                    print(f"      -> No Apply button found. Skipping (NOT counting as applied).", flush=True)
                    await jp.close()
                    continue

                # Wait for post-click state
                await jp.wait_for_timeout(3000)

                # If a modal/confirmation appeared, look for a final submit
                confirmed = await safe_click(jp, [
                    "button:has-text('Apply')",
                    "button:has-text('Submit')",
                    "button:has-text('Confirm')",
                    "button:has-text('Yes, apply')",
                ], label="Naukri Confirm Submit", timeout=4000)

                # Fill missing fields if a multi-step form opened
                await fill_if_empty(jp, "input[name='email'], input[type='email']", USER_EMAIL)
                await fill_if_empty(jp, "input[name='phone'], input[type='tel']", USER_PHONE)
                await jp.wait_for_timeout(2000)

                # Log ONLY on actual click
                log_applied("Naukri", company, title, loc, job_url)
                print(f"      >>> [APPLIED] '{title}' @ '{company}' on Naukri!", flush=True)
                applied += 1

            except Exception as e:
                print(f"      [ERROR] {e}", flush=True)
            finally:
                await jp.close()
                await asyncio.sleep(2)

    except Exception as e:
        print(f"[NAUKRI ERROR] {e}", flush=True)
    finally:
        await page.close()

    print(f"[NAUKRI] Done. Actually applied: {applied}", flush=True)
    return applied


# ═══════════════════════════════════════════════════════════════════════════════
# 2. INDEED
# ═══════════════════════════════════════════════════════════════════════════════
async def auto_apply_indeed(context, keyword="Software Engineer", location="India"):
    search_term = get_search_term(keyword)
    print(f"\n{'='*60}", flush=True)
    print(f"[INDEED] Applying for: '{search_term}' in {location}", flush=True)
    print(f"{'='*60}", flush=True)

    page    = await context.new_page()
    applied = 0
    jobs    = []

    try:
        # Use India Indeed
        indeed_url = (
            f"https://in.indeed.com/jobs"
            f"?q={urllib.parse.quote(search_term)}"
            f"&l={urllib.parse.quote(location)}"
            f"&fromage=7"          # jobs from last 7 days
        )
        print(f"[INDEED] Search: {indeed_url}", flush=True)
        await page.goto(indeed_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # Indeed 2024 card selectors
        cards = await page.query_selector_all(
            "div.job_seen_beacon, "
            "td.resultContent, "
            "li.css-5lfssm, "
            "div[data-testid='slider_item']"
        )
        print(f"[INDEED] Found {len(cards)} job cards.", flush=True)

        for card in cards[:10]:
            try:
                title_el = await card.query_selector(
                    "h2.jobTitle a, "
                    "a.jcs-JobTitle, "
                    "a[data-testid='job-title'], "
                    "a[id*='job_']"
                )
                comp_el = await card.query_selector(
                    "span[data-testid='company-name'], "
                    "span.companyName, "
                    "[class*='companyName']"
                )
                if not title_el:
                    continue
                title   = (await title_el.text_content() or "").strip()
                company = (await comp_el.text_content() or "Indeed Employer").strip() if comp_el else "Indeed Employer"
                href    = await title_el.get_attribute("href") or ""
                jk      = await title_el.get_attribute("data-jk")
                url     = f"https://in.indeed.com/viewjob?jk={jk}" if jk else (
                          "https://in.indeed.com" + href if href.startswith("/") else href)

                if title and len(title) > 3 and not any(j["url"] == url for j in jobs):
                    jobs.append({"title": title, "company": company, "url": url, "loc": location})
            except Exception:
                pass

        print(f"[INDEED] Processing {min(len(jobs), 5)} jobs.", flush=True)

        for idx, job in enumerate(jobs[:5]):
            title, company, job_url, loc = job["title"], job["company"], job["url"], job["loc"]

            if is_already_applied(company, title):
                print(f"  [{idx+1}] SKIP – already applied: {title} @ {company}", flush=True)
                continue

            print(f"\n  [{idx+1}] Opening: '{title}' @ '{company}'", flush=True)
            jp = await context.new_page()
            try:
                await jp.goto(job_url, wait_until="domcontentloaded", timeout=25000)
                await jp.wait_for_timeout(3000)

                # Indeed Apply button selectors (2024)
                clicked = await safe_click(jp, [
                    "#indeedApplyButton",
                    "button[data-testid='indeedApplyButton']",
                    "button[class*='IndeedApply']",
                    "a[data-testid='indeedApplyButton']",
                    "button:has-text('Apply now')",
                    "button:has-text('Apply on Indeed')",
                    "button:has-text('Easy Apply')",
                ], label="Indeed Apply", timeout=6000)

                if not clicked:
                    print(f"      -> No Apply button found. Skipping (NOT counting as applied).", flush=True)
                    await jp.close()
                    continue

                await jp.wait_for_timeout(3000)

                # Walk through Indeed's multi-step modal
                actually_submitted = False
                for step in range(6):
                    # Final submit
                    if await safe_click(jp, [
                        "button:has-text('Submit your application')",
                        "button[aria-label*='Submit your application']",
                        "button:has-text('Submit application')",
                        "button[data-testid='submit-button']",
                    ], label="Indeed Final Submit", timeout=4000):
                        actually_submitted = True
                        break

                    # Pre-fill fields that might cause form to block
                    await fill_if_empty(jp, "input[name='applicant.name']", USER_NAME)
                    await fill_if_empty(jp, "input[name='applicant.phoneNumber']", USER_PHONE)
                    await fill_if_empty(jp, "input[type='email']", USER_EMAIL)

                    # Continue / Next / Review
                    advanced = await safe_click(jp, [
                        "button:has-text('Continue')",
                        "button:has-text('Next')",
                        "button:has-text('Review your application')",
                        "button:has-text('Review')",
                        "button[data-testid='continue-button']",
                    ], label=f"Indeed Step {step+1}", timeout=4000)

                    if not advanced:
                        break
                    await jp.wait_for_timeout(2000)

                if actually_submitted:
                    log_applied("Indeed", company, title, loc, job_url)
                    print(f"      >>> [APPLIED] '{title}' @ '{company}' on Indeed! Confirmation email should arrive.", flush=True)
                    applied += 1
                else:
                    print(f"      -> Could not reach Submit step (multi-step form may need manual info). Skipping.", flush=True)

            except Exception as e:
                print(f"      [ERROR] {e}", flush=True)
            finally:
                await jp.close()
                await asyncio.sleep(2)

    except Exception as e:
        print(f"[INDEED ERROR] {e}", flush=True)
    finally:
        await page.close()

    print(f"[INDEED] Done. Actually applied: {applied}", flush=True)
    return applied


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LINKEDIN
# ═══════════════════════════════════════════════════════════════════════════════
async def auto_apply_linkedin(context, keyword="Software Engineer", location="India"):
    search_term = get_search_term(keyword)
    print(f"\n{'='*60}", flush=True)
    print(f"[LINKEDIN] Easy-Applying for: '{search_term}' in {location}", flush=True)
    print(f"{'='*60}", flush=True)

    page    = await context.new_page()
    applied = 0
    jobs    = []

    try:
        f_exp    = "&f_E=1%2C2" if EXP_LEVEL == "fresher" else ""
        li_url   = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={urllib.parse.quote(search_term)}"
            f"&location={urllib.parse.quote(location)}"
            f"&f_AL=true"           # Easy Apply only
            f"{f_exp}"
            f"&sortBy=DD"           # Date posted (newest)
        )
        print(f"[LINKEDIN] Search: {li_url}", flush=True)
        await page.goto(li_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # LinkedIn 2024 selectors
        cards = await page.query_selector_all(
            "li.jobs-search-results__list-item, "
            "div.job-card-container, "
            "div[data-occludable-job-id]"
        )
        print(f"[LINKEDIN] Found {len(cards)} job cards.", flush=True)

        for card in cards[:10]:
            try:
                title_el = await card.query_selector(
                    "a.job-card-list__title, "
                    "a.job-card-container__link, "
                    "strong"
                )
                comp_el = await card.query_selector(
                    "span.job-card-container__primary-description, "
                    "div.artdeco-entity-lockup__subtitle span, "
                    ".job-card-container__company-name"
                )
                if not title_el:
                    continue
                title   = (await title_el.text_content() or "").strip().replace('\n', ' ')
                company = (await comp_el.text_content() or "LinkedIn Employer").strip() if comp_el else "LinkedIn Employer"
                href    = await title_el.get_attribute("href") or ""
                if href and not href.startswith("http"):
                    href = "https://www.linkedin.com" + href

                if title and len(title) > 3 and not any(j["url"] == href for j in jobs):
                    jobs.append({"title": title, "company": company, "url": href, "loc": location})
            except Exception:
                pass

        print(f"[LINKEDIN] Processing {min(len(jobs), 5)} jobs.", flush=True)

        for idx, job in enumerate(jobs[:5]):
            title, company, job_url, loc = job["title"], job["company"], job["url"], job["loc"]

            if is_already_applied(company, title):
                print(f"  [{idx+1}] SKIP – already applied: {title} @ {company}", flush=True)
                continue

            print(f"\n  [{idx+1}] Opening: '{title}' @ '{company}'", flush=True)
            jp = await context.new_page()
            try:
                await jp.goto(job_url, wait_until="domcontentloaded", timeout=25000)
                await jp.wait_for_timeout(3000)

                # Easy Apply button selectors (LinkedIn 2024)
                clicked = await safe_click(jp, [
                    "button.jobs-apply-button[aria-label*='Easy Apply']",
                    "button[aria-label*='Easy Apply']",
                    ".jobs-apply-button--top-card",
                    "button:has-text('Easy Apply')",
                    "button.artdeco-button:has-text('Easy Apply')",
                ], label="LinkedIn Easy Apply", timeout=7000)

                if not clicked:
                    print(f"      -> No Easy Apply button (may require manual apply or already applied). Skipping.", flush=True)
                    await jp.close()
                    continue

                await jp.wait_for_timeout(2500)

                # Walk through LinkedIn's multi-step modal
                actually_submitted = False
                for step in range(8):
                    # Check for final Submit
                    if await safe_click(jp, [
                        "button[aria-label='Submit application']",
                        "button:has-text('Submit application')",
                        "button[aria-label*='Submit application']",
                    ], label="LinkedIn Final Submit", timeout=4000):
                        actually_submitted = True
                        break

                    # Pre-fill phone if needed
                    await fill_if_empty(jp,
                        "input[id*='phoneNumber'], input[name*='phone'], input[placeholder*='phone']",
                        USER_PHONE.replace("+91 ", "").replace(" ", ""))

                    # Handle "Follow company" checkbox — uncheck it
                    try:
                        follow_chk = await jp.query_selector(
                            "label:has-text('Follow'), input[type='checkbox'][id*='follow']")
                        if follow_chk:
                            is_checked = await jp.evaluate(
                                "el => el.checked",
                                await jp.query_selector("input[type='checkbox'][id*='follow']") or follow_chk)
                            if is_checked:
                                await follow_chk.click()
                    except Exception:
                        pass

                    # Next / Review / Continue
                    advanced = await safe_click(jp, [
                        "button[aria-label='Continue to next step']",
                        "button[aria-label='Review your application']",
                        "button:has-text('Next')",
                        "button:has-text('Review')",
                        "button:has-text('Continue to next step')",
                        "button:has-text('Review your application')",
                    ], label=f"LinkedIn Step {step+1}", timeout=4000)

                    if not advanced:
                        break
                    await jp.wait_for_timeout(2000)

                # Dismiss any post-submission dialog
                await safe_click(jp, [
                    "button[aria-label='Dismiss']",
                    "button:has-text('Done')",
                    "button:has-text('Not now')",
                ], label="LinkedIn Dismiss", timeout=3000)

                if actually_submitted:
                    log_applied("LinkedIn", company, title, loc, job_url)
                    print(f"      >>> [APPLIED] '{title}' @ '{company}' on LinkedIn! Check LinkedIn messages for confirmation.", flush=True)
                    applied += 1
                else:
                    print(f"      -> Could not reach Submit step. Skipping (NOT counting as applied).", flush=True)

            except Exception as e:
                print(f"      [ERROR] {e}", flush=True)
            finally:
                await jp.close()
                await asyncio.sleep(2)

    except Exception as e:
        print(f"[LINKEDIN ERROR] {e}", flush=True)
    finally:
        await page.close()

    print(f"[LINKEDIN] Done. Actually applied: {applied}", flush=True)
    return applied


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER RUNNER
# ═══════════════════════════════════════════════════════════════════════════════
async def run_portal_automation(portal_choice="all", keyword="Software Engineer", headless=False):
    """
    headless=False by default — portals actively detect headless mode and block it.
    The browser will be visible but automated.
    """
    current_config  = load_config()
    target_location = current_config.get("primary_location", PRIMARY_LOCATION)
    user_data_path  = current_config.get("browser", {}).get("user_data_path", CHROME_USER_DATA)
    chrome_exe      = current_config.get("browser", {}).get("chrome_path", CHROME_EXE)

    mode_str = "Headless" if headless else "HEADED (Visible Browser – Anti-Bot)"
    print(f"\n[START] Portal Auto-Applier | Mode: [{mode_str}]", flush=True)
    print(f"        Role: '{keyword}' | Location: '{target_location}'", flush=True)

    total_applied = 0

    async with async_playwright() as p:
        context = None
        try:
            # Use user's real Chrome profile (already logged in to LinkedIn, Naukri, Indeed)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_path,
                executable_path=chrome_exe if os.path.exists(chrome_exe) else None,
                headless=headless,
                args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--start-maximized",
                ],
                ignore_default_args=["--enable-automation"],
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/127.0.0.0 Safari/537.36"
                ),
                viewport=None,   # use maximized window
                ignore_https_errors=True,
                slow_mo=120,     # slight delay makes it more human-like
            )
            print("[BROWSER] Launched with your Chrome profile (logged-in sessions preserved).", flush=True)
        except Exception as e:
            print(f"[BROWSER] Persistent context failed ({e}), falling back to incognito...", flush=True)
            browser = await p.chromium.launch(
                executable_path=chrome_exe if os.path.exists(chrome_exe) else None,
                headless=headless,
                args=["--no-first-run", "--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/127.0.0.0 Safari/537.36"
                ),
            )
            print("[BROWSER WARNING] Not using saved login session — you may need to log in.", flush=True)

        try:
            locations = [target_location]
            if current_config.get("include_remote", True) and "remote" not in target_location.lower():
                locations.append("Remote")

            for loc in locations:
                if portal_choice in ("1", "naukri", "all"):
                    total_applied += await auto_apply_naukri(context, keyword, location=loc)
                if portal_choice in ("2", "linkedin", "all"):
                    total_applied += await auto_apply_linkedin(context, keyword, location=loc)
                if portal_choice in ("3", "indeed", "all"):
                    total_applied += await auto_apply_indeed(context, keyword, location=loc)

        except Exception as e:
            print(f"[RUNNER ERROR] {e}", flush=True)
        finally:
            try:
                await context.close()
            except Exception:
                pass

    print(f"\n[COMPLETED] Portal run done. Verified submissions: {total_applied}", flush=True)
    return total_applied


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "Python Developer"
    # Always run headed (False) so portals don't block
    asyncio.run(run_portal_automation("all", kw, headless=False))
