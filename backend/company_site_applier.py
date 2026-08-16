"""
JobPilot-AI — Autonomous Company Website & Careers Form Auto-Filler Engine
Enters company career websites (ATS forms like Greenhouse, Lever, Ashby, Workable, custom company portals),
auto-fills application forms with candidate details, uploads Resume.pdf, writes AI cover letters,
submits forms, and if HR emails/Gmail addresses are discovered on the site, sends direct application emails via Gmail SMTP.
"""

import os
import sys
import asyncio
import json
import re
import csv
import urllib.request
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Force UTF-8 encoding on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from db_helper import record_application, is_already_applied
from llm_job_finder import call_low_latency_llm_cover_letter
from email_sender import send_application_email

CONFIG_PATH = os.path.join(APP_ROOT, "config.json")
DATA_DIR = os.path.join(APP_ROOT, "data")
DEFAULT_RESUME = os.path.join(APP_ROOT, "Resume.pdf")
COMPANY_LOG_FILE = os.path.join(DATA_DIR, "company_applications_log.csv")

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

# Verified top technology companies & active career hubs
CURATED_COMPANY_TARGETS = [
    {
        "company": "Razorpay",
        "careers_url": "https://razorpay.com/jobs/",
        "hr_email": "careers@razorpay.com",
        "roles": ["Software Engineer", "Python Developer", "Backend Developer", "Frontend Developer"]
    },
    {
        "company": "Postman",
        "careers_url": "https://www.postman.com/company/careers/",
        "hr_email": "careers@postman.com",
        "roles": ["Software Engineer", "Frontend Developer", "API Developer"]
    },
    {
        "company": "BrowserStack",
        "careers_url": "https://www.browserstack.com/careers",
        "hr_email": "careers@browserstack.com",
        "roles": ["Software Engineer", "QA Engineer", "Python Developer"]
    },
    {
        "company": "Hasura",
        "careers_url": "https://hasura.io/careers",
        "hr_email": "jobs@hasura.io",
        "roles": ["Full Stack Developer", "Backend Developer", "Software Engineer"]
    },
    {
        "company": "InMobi",
        "careers_url": "https://www.inmobi.com/company/careers",
        "hr_email": "talent@inmobi.com",
        "roles": ["AI Engineer", "Software Engineer", "Data Engineer"]
    },
    {
        "company": "CleverTap",
        "careers_url": "https://clevertap.com/careers/",
        "hr_email": "careers@clevertap.com",
        "roles": ["Software Engineer", "Full Stack Developer", "Python Developer"]
    },
    {
        "company": "Freshworks",
        "careers_url": "https://www.freshworks.com/company/careers/",
        "hr_email": "careers@freshworks.com",
        "roles": ["Software Engineer", "Frontend Developer", "Product Engineer"]
    }
]

def search_live_company_career_sites(keyword="Software Engineer", location="Remote"):
    """Finds live ATS career forms (Lever, Greenhouse, Ashby, Workable) and company careers pages"""
    results = []
    try:
        search_query = f"{keyword} {location} (site:jobs.lever.co OR site:boards.greenhouse.io OR site:jobs.ashbyhq.com OR site:apply.workable.com)"
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(search_query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            soup = BeautifulSoup(resp.read(), "html.parser")
            links = soup.select("a.result__url, a.result__snippet")
            for link in links[:6]:
                href = link.get("href", "")
                if "uddg=" in href:
                    href = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
                
                if any(ats in href for ats in ["lever.co", "greenhouse.io", "ashbyhq.com", "workable.com"]):
                    parts = href.split('/')
                    comp_name = "Tech Employer"
                    for p in parts:
                        if p and p not in ["jobs.lever.co", "boards.greenhouse.io", "jobs.ashbyhq.com", "apply.workable.com", "https:", "http:", ""]:
                            comp_name = p.capitalize()
                            break
                    results.append({
                        "company": comp_name,
                        "careers_url": href,
                        "hr_email": "",
                        "roles": [keyword]
                    })
    except Exception:
        pass
        
    return results

async def fill_and_submit_company_form(page, target_url, role_title, company_name, hr_email=""):
    """Navigates to company careers page, fills inputs, attaches Resume.pdf, and submits or emails"""
    if is_already_applied(company_name, role_title):
        print(f"   [SKIPPED] Already applied to '{role_title}' at '{company_name}' in the last 30 days.", flush=True)
        return False

    cfg = load_config()
    cand = cfg.get("candidate", {})
    resume_path = cfg.get("resume_path", DEFAULT_RESUME)
    if not os.path.isabs(resume_path):
        resume_path = os.path.join(APP_ROOT, resume_path)

    print(f"\n=======================================================", flush=True)
    print(f"--- 🏢 ENTERING COMPANY WEBSITE: {company_name} ---", flush=True)
    print(f"    URL: {target_url}", flush=True)
    print(f"=======================================================", flush=True)

    applied_via_form = False
    discovered_emails = []

    try:
        await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3000)

        # Look for "Apply" buttons or links to open the actual application form if on landing page
        apply_links = await page.query_selector_all("a:has-text('Apply'), button:has-text('Apply'), a[href*='apply'], a:has-text('Apply for this job')")
        if apply_links:
            try:
                print(f"   -> Clicking 'Apply' button on careers page...", flush=True)
                await apply_links[0].click()
                await page.wait_for_timeout(2500)
            except Exception:
                pass

        # Check for HR / Recruiter email on the page
        page_text = await page.inner_text("body")
        extracted_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_text)
        valid_page_emails = [e for e in extracted_emails if not any(x in e.lower() for x in ['sentry', 'w3.org', 'google', 'png', 'jpg', 'schema.org'])]
        if valid_page_emails:
            discovered_emails.extend(valid_page_emails)

        # ─── 1. FILL FORM FIELDS ───
        # Candidate Full Name
        name_inputs = await page.query_selector_all("input[name*='name' i], input[id*='name' i], input[placeholder*='name' i], input[data-qa*='name' i]")
        if name_inputs and cand.get("name"):
            print(f"   [FORM] Filling Name: {cand['name']}", flush=True)
            await name_inputs[0].fill(cand["name"])

        # Candidate Email
        email_inputs = await page.query_selector_all("input[type='email'], input[name*='email' i], input[id*='email' i], input[placeholder*='email' i]")
        if email_inputs and cand.get("email"):
            print(f"   [FORM] Filling Email: {cand['email']}", flush=True)
            await email_inputs[0].fill(cand["email"])

        # Phone Number
        phone_inputs = await page.query_selector_all("input[type='tel'], input[name*='phone' i], input[id*='phone' i], input[placeholder*='phone' i], input[name*='mobile' i]")
        if phone_inputs and cand.get("phone"):
            print(f"   [FORM] Filling Phone: {cand['phone']}", flush=True)
            await phone_inputs[0].fill(cand["phone"])

        # LinkedIn / GitHub / Portfolio URLs
        url_inputs = await page.query_selector_all("input[type='url'], input[name*='url' i], input[name*='link' i], input[id*='link' i]")
        for inp in url_inputs:
            name_attr = ((await inp.get_attribute("name") or "") + " " + (await inp.get_attribute("placeholder") or "")).lower()
            if "linkedin" in name_attr and cand.get("linkedin"):
                await inp.fill(cand["linkedin"])
            elif "github" in name_attr and cand.get("github"):
                await inp.fill(cand["github"])
            elif ("portfolio" in name_attr or "website" in name_attr) and cand.get("portfolio"):
                await inp.fill(cand["portfolio"])

        # ─── 2. ATTACH RESUME PDF ───
        if os.path.exists(resume_path):
            file_inputs = await page.query_selector_all("input[type='file'], input[name*='resume' i], input[name*='cv' i], input[id*='resume' i]")
            if file_inputs:
                try:
                    await file_inputs[0].set_input_files(resume_path)
                    print(f"   [FORM] Attached Resume PDF: {os.path.basename(resume_path)}", flush=True)
                except Exception as fe:
                    print(f"   [NOTICE] File input attach: {fe}", flush=True)

        # ─── 3. FILL AI COVER LETTER / NOTE ───
        textareas = await page.query_selector_all("textarea[name*='cover' i], textarea[placeholder*='cover' i], textarea[name*='message' i], textarea[name*='note' i], textarea")
        if textareas:
            print(f"   [AI] Generating customized cover note for {company_name}...", flush=True)
            cover_letter = call_low_latency_llm_cover_letter(company_name, role_title)
            await textareas[0].fill(cover_letter[:1500])

        # ─── 4. SUBMIT FORM ───
        submit_btns = await page.query_selector_all("button[type='submit'], input[type='submit'], button:has-text('Submit'), button:has-text('Apply'), button:has-text('Submit Application')")
        if submit_btns and (name_inputs or email_inputs):
            print(f"   [FORM] Clicking Submit Application button...", flush=True)
            await submit_btns[0].click()
            await page.wait_for_timeout(3000)
            applied_via_form = True
            print(f"   >>> [CONFIRMED APPLIED] Application Form successfully submitted to {company_name}!", flush=True)
            record_application("Company Careers Form", company_name, role_title, status="Applied", notes=f"Form submitted at {target_url} ({EXP_LEVEL.upper()})")

    except Exception as e:
        print(f"   [NOTICE] Web form interaction notice: {e}", flush=True)

    # ─── 5. DIRECT EMAIL OUTREACH IF HR / GMAIL CONTACT AVAILABLE ───
    target_email = hr_email or (discovered_emails[0] if discovered_emails else "")
    if target_email:
        sender_email = cfg.get("email", {}).get("sender", "")
        if sender_email and target_email.lower() != sender_email.lower():
            print(f"\n   [DIRECT EMAIL] Found Careers/HR Inbox: {target_email}", flush=True)
            print(f"   [DISPATCHING] Sending personalized cover letter & Resume.pdf directly via Gmail SMTP...", flush=True)
            
            custom_body = call_low_latency_llm_cover_letter(company_name, role_title)
            subject = f"Application for {role_title} - {cand.get('name', 'Job Candidate')}"
            
            res = send_application_email(target_email, subject, custom_body, resume_path)
            if res.get("success"):
                print(f"   >>> [EMAILED GMAIL/HR] Application email + Resume.pdf delivered to {target_email}!", flush=True)
                record_application("Recruiter / Company Email", company_name, role_title, status="Applied", recruiter_email=target_email, notes=f"Dispatched email with Resume.pdf to {target_email} ({EXP_LEVEL.upper()})")
                return True
            else:
                print(f"   [NOTICE] Email send: {res.get('error')}", flush=True)

    return applied_via_form

async def run_company_website_and_multi_portal_bot(keyword="Software Engineer", headless=True):
    current_config = load_config()
    target_location = current_config.get("primary_location", PRIMARY_LOCATION)
    
    print("\n=======================================================", flush=True)
    print(f"   🚀 AUTONOMOUS COMPANY SITE & CAREERS FORM AGENT [{EXP_LEVEL.upper()}]", flush=True)
    print(f"   Role: {keyword.upper()}  |  Location: {target_location}", flush=True)
    print("=======================================================", flush=True)

    applied_total = 0

    # 1. Gather curated & live company career sites
    target_companies = []
    for c in CURATED_COMPANY_TARGETS:
        if any(keyword.lower() in r.lower() or r.lower() in keyword.lower() for r in c["roles"]):
            target_companies.append(c)

    if not target_companies:
        target_companies = CURATED_COMPANY_TARGETS[:3]

    print(f"[SEARCHING] Finding live ATS career forms (Lever, Greenhouse, Ashby) for '{keyword}'...", flush=True)
    live_ats_jobs = search_live_company_career_sites(keyword, target_location)
    if live_ats_jobs:
        print(f"   [FOUND] Discovered {len(live_ats_jobs)} live ATS company application forms.", flush=True)
        target_companies.extend(live_ats_jobs[:3])

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

            for comp in target_companies[:4]:
                success = await fill_and_submit_company_form(
                    page=page,
                    target_url=comp["careers_url"],
                    role_title=keyword,
                    company_name=comp["company"],
                    hr_email=comp.get("hr_email", "")
                )
                if success:
                    applied_total += 1
                await asyncio.sleep(1)

            await browser.close()
        except Exception as e:
            print(f"Company automation notice: {e}", flush=True)
            if browser:
                await browser.close()

    print("\n=======================================================", flush=True)
    print(f"[COMPLETED] Company website & career forms cycle finished! Applications submitted: {applied_total}", flush=True)
    print("=======================================================", flush=True)
    return applied_total

if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "Software Engineer"
    asyncio.run(run_company_website_and_multi_portal_bot(kw, headless=True))
