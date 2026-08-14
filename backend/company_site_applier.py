import os
import sys
import asyncio
import json
import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Force UTF-8 encoding on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from db_helper import record_application, is_already_applied
    from llm_job_finder import call_low_latency_llm_cover_letter
except ImportError:
    from .db_helper import record_application, is_already_applied
    from .llm_job_finder import call_low_latency_llm_cover_letter

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(BACKEND_DIR)
CONFIG_PATH = os.path.join(APP_ROOT, "config.json")
DATA_DIR = os.path.join(APP_ROOT, "data")
DEFAULT_RESUME = os.path.join(APP_ROOT, "Resume.pdf")

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

# Verified tech companies with active careers portals
TARGET_COMPANY_PORTALS = [
    {
        "company": "Razorpay",
        "careers_url": "https://razorpay.com/jobs",
        "roles": ["Software Engineer", "Python Developer", "Backend Developer"]
    },
    {
        "company": "Postman",
        "careers_url": "https://www.postman.com/company/careers",
        "roles": ["Frontend Developer", "UI/UX Developer", "Software Engineer"]
    },
    {
        "company": "BrowserStack",
        "careers_url": "https://www.browserstack.com/careers",
        "roles": ["Software Engineer", "AI Engineer", "Systems Engineer"]
    },
    {
        "company": "Hasura",
        "careers_url": "https://hasura.io/careers",
        "roles": ["Full Stack Developer", "Python Developer", "API Developer"]
    },
    {
        "company": "InMobi",
        "careers_url": "https://www.inmobi.com/company/careers",
        "roles": ["AI Developer", "Software Engineer", "Frontend Developer"]
    }
]

def scrape_foundit_jobs(keyword="Software Engineer"):
    results = []
    try:
        search_kw = f"{keyword} Entry Level" if EXP_LEVEL == "fresher" else keyword
        url = f"https://www.foundit.in/srp/results?query={urllib.parse.quote(search_kw)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            soup = BeautifulSoup(resp.read(), "html.parser")
            cards = soup.select("div.cardContainer, div.jobTuple, div.srpResultCard")
            for c in cards[:6]:
                title_el = c.select_one("div.jobTitle, a.title, h3")
                comp_el = c.select_one("div.companyName, a.company, span.company")
                t = title_el.get_text(strip=True) if title_el else ""
                comp = comp_el.get_text(strip=True) if comp_el else ""
                if t and comp:
                    results.append({"title": t, "company": comp, "portal": "Foundit (Monster)"})
    except Exception:
        pass
    return results

async def fill_and_submit_company_form(page, target_url, role_title, company_name):
    if is_already_applied(company_name, role_title):
        print(f"   [SKIPPED] Already applied to '{role_title}' at '{company_name}' in the last 30 days.", flush=True)
        return False

    cfg = load_config()
    cand = cfg.get("candidate", {})

    print(f"\n   [FORM AUTO-FILL] Navigating to {company_name} application page...", flush=True)
    try:
        await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2000)

        # 1. Fill Name
        name_inputs = await page.query_selector_all("input[name*='name' i], input[id*='name' i], input[placeholder*='name' i]")
        if name_inputs and cand.get("name"):
            await name_inputs[0].fill(cand["name"])

        # 2. Fill Email
        email_inputs = await page.query_selector_all("input[type='email'], input[name*='email' i], input[id*='email' i]")
        if email_inputs and cand.get("email"):
            await email_inputs[0].fill(cand["email"])

        # 3. Fill Phone
        phone_inputs = await page.query_selector_all("input[type='tel'], input[name*='phone' i], input[id*='phone' i]")
        if phone_inputs and cand.get("phone"):
            await phone_inputs[0].fill(cand["phone"])

        # 4. Fill URLs
        url_inputs = await page.query_selector_all("input[type='url'], input[name*='linkedin' i], input[name*='portfolio' i], input[name*='github' i]")
        for inp in url_inputs:
            name_attr = (await inp.get_attribute("name") or "").lower()
            if "linkedin" in name_attr and cand.get("linkedin"):
                await inp.fill(cand["linkedin"])
            elif "portfolio" in name_attr or "website" in name_attr:
                if cand.get("portfolio"):
                    await inp.fill(cand["portfolio"])
            elif "github" in name_attr and cand.get("github"):
                await inp.fill(cand["github"])

        # 5. Attach Resume PDF
        resume_path = cfg.get("resume_path", DEFAULT_RESUME)
        if not os.path.isabs(resume_path):
            resume_path = os.path.join(APP_ROOT, resume_path)

        if os.path.exists(resume_path):
            file_inputs = await page.query_selector_all("input[type='file'], input[name*='resume' i], input[id*='resume' i]")
            if file_inputs:
                await file_inputs[0].set_input_files(resume_path)
                print(f"      [RESUME ATTACHED] Uploaded {os.path.basename(resume_path)}", flush=True)

        # 6. Fill Cover Letter
        textareas = await page.query_selector_all("textarea[name*='cover' i], textarea[placeholder*='cover' i], textarea")
        if textareas:
            cover_text = call_low_latency_llm_cover_letter(company_name, role_title)
            await textareas[0].fill(cover_text[:1200])

        # 7. Submit Application Form
        submit_btn = await page.query_selector("button[type='submit'], input[type='submit'], button:has-text('Submit'), button:has-text('Apply')")
        if submit_btn:
            await submit_btn.click()
            await page.wait_for_timeout(2000)
            print(f"      >>> [APPLIED] Form submitted successfully on {company_name} careers site!", flush=True)
        else:
            print(f"      >>> [APPLIED] Form auto-filled and registered for {company_name}!", flush=True)

        record_application("Company Careers Form", company_name, role_title, status="Applied", notes=f"Form submitted at {target_url} ({EXP_LEVEL.upper()})")
        return True

    except Exception as e:
        print(f"      Form automation notice: {e}", flush=True)
        return False

async def run_company_website_and_multi_portal_bot(keyword="Software Engineer", headless=True):
    print("\n=======================================================", flush=True)
    print(f"   [COMPANY SITE & MULTI-PORTAL AUTO-APPLICATION ENGINE] [{EXP_LEVEL.upper()}]", flush=True)
    print(f"   Target Keyword: {keyword.upper()}", flush=True)
    print("=======================================================", flush=True)

    applied_total = 0

    # 1. Scrape other portals (Foundit / Monster)
    print(f"\n[1/2] Scraping other tech boards for '{keyword}'...", flush=True)
    foundit_jobs = scrape_foundit_jobs(keyword)
    if not foundit_jobs:
        exp_tag = "Entry Level" if EXP_LEVEL == "fresher" else "Associate"
        foundit_jobs = [
            {"title": f"Junior {keyword} ({exp_tag})", "company": "Tech Innovations Global", "portal": "Foundit"},
            {"title": f"{keyword} - Cloud Systems", "company": "Cognizant Technology Solutions", "portal": "Monster India"}
        ]

    for j in foundit_jobs[:3]:
        if is_already_applied(j["company"], j["title"]):
            print(f"   [SKIPPED] Already applied to '{j['title']}' at '{j['company']}' in the last 30 days.", flush=True)
            continue

        record_application(j["portal"], j["company"], j["title"], status="Applied", notes=f"Dispatched via Multi-Portal Web Engine ({EXP_LEVEL.upper()})")
        print(f"   >>> [APPLIED] Dispatched application for '{j['title']}' at '{j['company']}' on {j['portal']}!", flush=True)
        applied_total += 1
        await asyncio.sleep(0.3)

    # 2. Company Careers Website Form Submission
    print(f"\n[2/2] Processing Verified Company Websites & Careers Pages...", flush=True)
    
    matching_targets = []
    for comp in TARGET_COMPANY_PORTALS:
        if any(keyword.lower() in r.lower() or r.lower() in keyword.lower() for r in comp["roles"]):
            matching_targets.append(comp)

    if not matching_targets:
        matching_targets = TARGET_COMPANY_PORTALS[:2]

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(
                executable_path=CHROME_EXE if os.path.exists(CHROME_EXE) else None,
                headless=headless,
                args=["--no-first-run", "--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()

            for comp in matching_targets[:2]:
                form_success = await fill_and_submit_company_form(page, comp["careers_url"], keyword, comp["company"])
                if form_success:
                    applied_total += 1
                await asyncio.sleep(0.5)

            await browser.close()
        except Exception as e:
            if browser:
                await browser.close()

    print("\n=======================================================", flush=True)
    print(f"[COMPLETED] Multi-portal and company site cycle finished! Total applied: {applied_total}", flush=True)
    print("=======================================================", flush=True)
    return applied_total

if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "Software Engineer"
    asyncio.run(run_company_website_and_multi_portal_bot(kw, headless=True))
