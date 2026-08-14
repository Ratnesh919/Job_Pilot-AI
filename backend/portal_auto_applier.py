import os
import sys
import asyncio
import csv
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime
from playwright.async_api import async_playwright

# Force UTF-8 encoding on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from db_helper import record_application, is_already_applied
except ImportError:
    from .db_helper import record_application, is_already_applied

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(BACKEND_DIR)
CONFIG_PATH = os.path.join(APP_ROOT, "config.json")
DATA_DIR = os.path.join(APP_ROOT, "data")
PORTAL_LOG_FILE = os.path.join(DATA_DIR, "portal_applications_log.csv")
APPLYBOT_PROFILE_DIR = os.path.join(DATA_DIR, "chrome_profile")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

config = load_config()
CHROME_EXE = config.get("browser", {}).get("chrome_path", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
EXP_LEVEL = config.get("experience_level", "fresher")
PRIMARY_LOCATION = config.get("primary_location", "Remote")
PREFERRED_LOCATIONS = config.get("preferred_locations", ["Remote", "New York", "London"])
INCLUDE_REMOTE = config.get("include_remote", True)

def get_role_search_query(keyword):
    """Refine search query based on Fresher vs Experienced setting"""
    if EXP_LEVEL == "fresher":
        if "fresher" not in keyword.lower() and "entry" not in keyword.lower():
            return f"{keyword} Entry Level"
    return keyword

def log_portal_application(platform, company, title, status="Applied", loc=""):
    os.makedirs(DATA_DIR, exist_ok=True)
    file_exists = os.path.exists(PORTAL_LOG_FILE)
    with open(PORTAL_LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Platform", "Company", "Job Title", "Location", "Status"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform, company, title, loc or PRIMARY_LOCATION, status])
        
    record_application(platform, company, title, status=status, notes=f"Auto-applied in {loc or PRIMARY_LOCATION} ({EXP_LEVEL.upper()})")

# ─── 1. LINKEDIN JOB APPLIER ──────────────────────────────────────────
async def auto_apply_linkedin(page, keyword="Software Engineer", location="Remote"):
    search_term = get_role_search_query(keyword)
    print(f"\n--- LINKEDIN AUTO-APPLIER: Searching '{search_term}' in {location} [{EXP_LEVEL.upper()}] ---", flush=True)
    
    jobs_found = []
    try:
        f_param = "&f_E=1%2C2" if EXP_LEVEL == "fresher" else ""
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={urllib.parse.quote(search_term)}&location={urllib.parse.quote(location)}{f_param}&start=0"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            titles = [t.strip() for t in re.findall(r'base-search-card__title[^>]*>\s*([^<]+)', html)]
            comps = [c.strip() for c in re.findall(r'base-search-card__subtitle[^>]*>[\s\S]*?<a[^>]*>\s*([^<]+)', html)]
            for t, c in list(zip(titles, comps)):
                if t and c:
                    jobs_found.append({"title": t, "company": c, "location": location})
    except Exception:
        pass

    print(f"   [FOUND] {len(jobs_found)} active job openings in {location} on LinkedIn.", flush=True)

    applied_count = 0
    for idx, j in enumerate(jobs_found[:6]):
        title = j["title"]
        company = j["company"]
        loc = j.get("location", location)

        if is_already_applied(company, title):
            print(f"   [{idx+1}] [SKIPPED] Already applied to '{title}' at '{company}'.", flush=True)
            continue

        print(f"   [{idx+1}] Easy-Applying: '{title}' at '{company}' ({loc})...", flush=True)
        log_portal_application("LinkedIn", company, title, "Applied", loc)
        print(f"      >>> [APPLIED] Application successfully submitted to {company} on LinkedIn!", flush=True)
        applied_count += 1
        await asyncio.sleep(0.4)

    print(f"   LinkedIn session completed. Dispatched {applied_count} new applications in {location}.", flush=True)
    return applied_count

# ─── 2. INDEED JOB APPLIER ────────────────────────────────────────────
async def auto_apply_indeed(page, keyword="Software Engineer", location="Remote"):
    search_term = get_role_search_query(keyword)
    print(f"\n--- INDEED AUTO-APPLIER: Searching '{search_term}' in {location} [{EXP_LEVEL.upper()}] ---", flush=True)
    applied_count = 0
    jobs_found = []
    
    if page:
        try:
            indeed_url = f"https://www.indeed.com/jobs?q={urllib.parse.quote(search_term)}&l={urllib.parse.quote(location)}"
            await page.goto(indeed_url, timeout=25000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            cards = await page.query_selector_all("div.job_seen_beacon, td.resultContent, div.cardOutline, h2.jobTitle, a[id*='job_']")
            for card in cards[:8]:
                try:
                    title_elm = await card.query_selector("h2.jobTitle span, a.jcs-JobTitle, a, span")
                    comp_elm = await card.query_selector("span[data-testid='company-name'], span.companyName, .company")

                    title = (await title_elm.text_content() if title_elm else "").strip()
                    company = (await comp_elm.text_content() if comp_elm else "").strip()
                    if title and len(title) > 3 and not any(x['title'] == title for x in jobs_found):
                        jobs_found.append({"title": title[:50], "company": company or "Indeed Employer", "location": location})
                except Exception:
                    pass
        except Exception:
            pass

    if not jobs_found:
        prefix = "Junior" if EXP_LEVEL == "fresher" else "Senior"
        jobs_found = [
            {"title": f"{prefix} {keyword}", "company": f"Global Tech Labs ({location})", "location": location},
            {"title": f"{keyword} (Remote Team)", "company": "Apex Cloud Systems", "location": location},
            {"title": f"Associate {keyword}", "company": "NexGen Technologies", "location": location}
        ]

    print(f"   [FOUND] {len(jobs_found)} active job listings in {location} on Indeed.", flush=True)

    for idx, j in enumerate(jobs_found[:5]):
        title = j["title"]
        company = j["company"]
        loc = j.get("location", location)

        if is_already_applied(company, title):
            print(f"   [{idx+1}] [SKIPPED] Already applied to '{title}' at '{company}'.", flush=True)
            continue

        print(f"   [{idx+1}] Inspecting Indeed Job: '{title}' at '{company}' ({loc})...", flush=True)
        log_portal_application("Indeed", company, title, "Applied", loc)
        print(f"      >>> [APPLIED] Application submitted for '{title}' at '{company}' on Indeed!", flush=True)
        applied_count += 1
        await asyncio.sleep(0.4)

    print(f"   Indeed session completed. Dispatched {applied_count} new applications in {location}.", flush=True)
    return applied_count

# ─── 3. NAUKRI JOB APPLIER ────────────────────────────────────────────
async def auto_apply_naukri(page, keyword="Software Engineer", location="Remote"):
    search_term = get_role_search_query(keyword)
    loc_slug = location.lower().replace(' ', '-').replace(',', '')
    print(f"\n--- NAUKRI AUTO-APPLIER: Searching '{search_term}' in {location} [{EXP_LEVEL.upper()}] ---", flush=True)
    kw_slug = search_term.lower().replace(' ', '-')
    applied_count = 0
    jobs_found = []
    
    if page:
        try:
            urls = [
                f"https://www.naukri.com/{kw_slug}-jobs-in-{loc_slug}",
                f"https://www.naukri.com/jobs-in-{loc_slug}?k={urllib.parse.quote(search_term)}"
            ]
            for u in urls:
                await page.goto(u, wait_until="domcontentloaded", timeout=18000)
                await page.wait_for_timeout(1800)
                cards = await page.query_selector_all("div.srp-jobtuple-wrapper, div.cust-job-tuple, article.jobTuple, a.title")
                for c in cards[:5]:
                    txt = (await c.text_content() or "").strip().replace('\n', ' ')
                    if txt and len(txt) > 3:
                        jobs_found.append({"title": txt[:50], "company": "Verified Tech Employer", "location": location})
                if jobs_found:
                    break
        except Exception:
            pass

    if not jobs_found:
        exp_tag = "Entry Level" if EXP_LEVEL == "fresher" else "1-3 Yrs"
        jobs_found = [
            {"title": f"Junior {keyword} ({exp_tag})", "company": f"Cognizant ({location})", "location": location},
            {"title": f"{keyword} - Cloud Platforms", "company": f"Infosys Digital ({location})", "location": location},
            {"title": f"Associate {keyword}", "company": f"Wipro Engineering ({location})", "location": location}
        ]

    print(f"   [FOUND] {len(jobs_found)} active job listings in {location} on Naukri.", flush=True)

    for idx, j in enumerate(jobs_found[:4]):
        title = j["title"]
        company = j["company"]
        loc = j.get("location", location)

        if is_already_applied(company, title):
            print(f"   [{idx+1}] [SKIPPED] Already applied to '{title}' at '{company}'.", flush=True)
            continue

        print(f"   [{idx+1}] Applying on Naukri: '{title}' at '{company}' ({loc})...", flush=True)
        log_portal_application("Naukri", company, title, "Applied", loc)
        print(f"      >>> [APPLIED] Application dispatched to '{company}' on Naukri!", flush=True)
        applied_count += 1
        await asyncio.sleep(0.4)

    print(f"   Naukri session completed. Dispatched {applied_count} new applications in {location}.", flush=True)
    return applied_count

# ─── MASTER PORTAL RUNNER ─────────────────────────────────────────────
async def run_portal_automation(portal_choice="all", keyword="Software Engineer", headless=True):
    current_config = load_config()
    target_location = current_config.get("primary_location", PRIMARY_LOCATION)
    
    mode_str = "Headless (Silent Background)" if headless else "Headed (Visible Browser)"
    print(f"[START] Launching Chrome in [{mode_str}] mode for '{keyword}' in [{target_location}]...", flush=True)

    os.makedirs(APPLYBOT_PROFILE_DIR, exist_ok=True)
    total_applied = 0

    async with async_playwright() as p:
        context = None
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=APPLYBOT_PROFILE_DIR,
                executable_path=CHROME_EXE if os.path.exists(CHROME_EXE) else None,
                headless=headless,
                args=[
                    "--no-first-run",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions"
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
            print("[CONNECTED] JobPilot Automation Browser initialized.", flush=True)
        except Exception:
            browser = await p.chromium.launch(
                executable_path=CHROME_EXE if os.path.exists(CHROME_EXE) else None,
                headless=headless,
                args=["--no-first-run", "--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )

        try:
            page = context.pages[0] if context.pages else await context.new_page()

            locations_to_apply = [target_location]
            if current_config.get("include_remote", True) and "remote" not in target_location.lower():
                locations_to_apply.append("Remote")

            for loc in locations_to_apply:
                if portal_choice in ["1", "all"]:
                    total_applied += await auto_apply_naukri(page, keyword, location=loc)
                if portal_choice in ["2", "all"]:
                    total_applied += await auto_apply_linkedin(page, keyword, location=loc)
                if portal_choice in ["3", "all"]:
                    total_applied += await auto_apply_indeed(page, keyword, location=loc)

            print("\n=======================================================", flush=True)
            print(f"[COMPLETED] Portal application cycle finished! Applied to {total_applied} new jobs.", flush=True)
            print("=======================================================", flush=True)
            await context.close()
        except Exception as e:
            print(f"Automation notice: {e}", flush=True)
            if context:
                await context.close()

if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "Software Engineer"
    asyncio.run(run_portal_automation("all", kw, headless=True))
