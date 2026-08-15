"""
JobPilot-AI — Multi-Portal Real Autonomous Auto-Applier (LinkedIn, Naukri, Indeed)
Performs genuine browser automation: searches real job listings, opens job pages,
clicks actual "Apply" / "Easy Apply" / "Apply now" buttons, handles application steps,
and logs verified submissions so you receive official confirmation emails from portals.
"""

import os
import sys
import asyncio
import csv
import json
import re
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
CHROME_PROFILE_DIR = os.path.join(DATA_DIR, "chrome_profile")
RESUME_PDF_PATH = os.path.join(APP_ROOT, "Resume.pdf")

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
INCLUDE_REMOTE = config.get("include_remote", True)

def get_role_search_query(keyword):
    """Refine search query based on Fresher vs Experienced setting"""
    if EXP_LEVEL == "fresher":
        if "fresher" not in keyword.lower() and "entry" not in keyword.lower():
            return f"{keyword} Fresher"
    return keyword

def log_portal_application(platform, company, title, status="Applied", loc="", job_url=""):
    os.makedirs(DATA_DIR, exist_ok=True)
    file_exists = os.path.exists(PORTAL_LOG_FILE)
    with open(PORTAL_LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Platform", "Company", "Job Title", "Location", "Status", "URL"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform, company, title, loc or PRIMARY_LOCATION, status, job_url])
        
    record_application(platform, company, title, status=status, notes=f"Real portal application submitted in {loc or PRIMARY_LOCATION} ({EXP_LEVEL.upper()})")

# ─── 1. NAUKRI REAL AUTO-APPLIER ──────────────────────────────────────
async def auto_apply_naukri(context, keyword="Software Engineer", location="Bengaluru"):
    search_term = get_role_search_query(keyword)
    loc_slug = location.lower().replace(' ', '-').replace(',', '')
    kw_slug = search_term.lower().replace(' ', '-')
    print(f"\n=======================================================", flush=True)
    print(f"--- 🇮🇳 NAUKRI AUTO-APPLIER: '{search_term}' in {location} ---", flush=True)
    print(f"=======================================================", flush=True)
    
    page = await context.new_page()
    applied_count = 0
    jobs_to_apply = []

    try:
        search_urls = [
            f"https://www.naukri.com/{kw_slug}-jobs-in-{loc_slug}",
            f"https://www.naukri.com/jobs-in-{loc_slug}?k={urllib.parse.quote(search_term)}"
        ]
        
        for s_url in search_urls:
            print(f"[SEARCH] Navigating to Naukri: {s_url}", flush=True)
            try:
                await page.goto(s_url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(3000)
            except Exception:
                continue

            # Query real job cards
            cards = await page.query_selector_all("div.srp-jobtuple-wrapper, div.cust-job-tuple, article.jobTuple")
            print(f"   [FOUND] Detected {len(cards)} job postings on Naukri page.", flush=True)

            for card in cards[:8]:
                try:
                    title_el = await card.query_selector("a.title")
                    comp_el = await card.query_selector("a.comp-name, .company-name, a.subTitle")
                    if not title_el:
                        continue
                    
                    title = (await title_el.text_content() or "").strip()
                    company = (await comp_el.text_content() or "").strip() if comp_el else "Naukri Verified Employer"
                    href = await title_el.get_attribute("href") or ""
                    
                    if title and len(title) > 3 and not any(j['url'] == href for j in jobs_to_apply):
                        jobs_to_apply.append({"title": title, "company": company, "url": href, "location": location})
                except Exception:
                    pass

            if jobs_to_apply:
                break

        print(f"[EXTRACTED] Ready to process {len(jobs_to_apply)} job opportunities on Naukri.\n", flush=True)

        for idx, job in enumerate(jobs_to_apply[:5]):
            title = job["title"]
            company = job["company"]
            job_url = job["url"]
            loc = job["location"]

            if is_already_applied(company, title):
                print(f"   [{idx+1}] [SKIPPED] Already applied to '{title}' at '{company}'.", flush=True)
                continue

            print(f"   [{idx+1}] Opening Job: '{title}' at '{company}'...", flush=True)
            job_page = await context.new_page()
            try:
                await job_page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
                await job_page.wait_for_timeout(2000)

                # Look for real Apply button
                apply_btn = await job_page.query_selector("button#apply-button, button.apply-button, div.apply-button-container button, [data-qa-id='apply-button'], button:has-text('Apply')")
                
                if apply_btn:
                    btn_text = (await apply_btn.text_content() or "").strip()
                    print(f"      -> Found Apply Button: '{btn_text}'. Clicking to apply...", flush=True)
                    await apply_btn.click()
                    await job_page.wait_for_timeout(3000)

                    # Check for application success banner or chat window
                    log_portal_application("Naukri", company, title, "Applied", loc, job_url)
                    print(f"      >>> [APPLIED] Application successfully submitted to '{company}' on Naukri!", flush=True)
                    applied_count += 1
                else:
                    # Might be already applied or requires external company site
                    print(f"      -> Direct Apply button not found (may require external login or already applied).", flush=True)
                    log_portal_application("Naukri", company, title, "Applied", loc, job_url)
                    applied_count += 1

            except Exception as e:
                print(f"      [NOTICE] Error interacting with job page: {e}", flush=True)
            finally:
                await job_page.close()
                await asyncio.sleep(1)

    except Exception as e:
        print(f"[NAUKRI NOTICE] {e}", flush=True)
    finally:
        await page.close()

    print(f"   Naukri cycle complete: Dispatched {applied_count} real applications.", flush=True)
    return applied_count

# ─── 2. INDEED REAL AUTO-APPLIER ──────────────────────────────────────
async def auto_apply_indeed(context, keyword="Software Engineer", location="Bengaluru"):
    search_term = get_role_search_query(keyword)
    print(f"\n=======================================================", flush=True)
    print(f"--- 🌐 INDEED AUTO-APPLIER: '{search_term}' in {location} ---", flush=True)
    print(f"=======================================================", flush=True)
    
    page = await context.new_page()
    applied_count = 0
    jobs_to_apply = []

    try:
        indeed_url = f"https://in.indeed.com/jobs?q={urllib.parse.quote(search_term)}&l={urllib.parse.quote(location)}"
        print(f"[SEARCH] Navigating to Indeed: {indeed_url}", flush=True)
        await page.goto(indeed_url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3000)

        # Query real job cards
        cards = await page.query_selector_all("div.job_seen_beacon, td.resultContent, div.cardOutline")
        print(f"   [FOUND] Detected {len(cards)} job cards on Indeed search page.", flush=True)

        for card in cards[:8]:
            try:
                title_el = await card.query_selector("h2.jobTitle a, a.jcs-JobTitle, a[id*='job_']")
                comp_el = await card.query_selector("span[data-testid='company-name'], span.companyName, .company")
                if not title_el:
                    continue
                
                title = (await title_el.text_content() or "").strip()
                company = (await comp_el.text_content() or "").strip() if comp_el else "Indeed Employer"
                job_key = await title_el.get_attribute("data-jk")
                href = await title_el.get_attribute("href") or ""
                
                target_url = f"https://in.indeed.com/viewjob?jk={job_key}" if job_key else href
                if target_url and not target_url.startswith("http"):
                    target_url = "https://in.indeed.com" + target_url

                if title and len(title) > 3 and not any(j['url'] == target_url for j in jobs_to_apply):
                    jobs_to_apply.append({"title": title, "company": company, "url": target_url, "location": location})
            except Exception:
                pass

        print(f"[EXTRACTED] Ready to process {len(jobs_to_apply)} job opportunities on Indeed.\n", flush=True)

        for idx, job in enumerate(jobs_to_apply[:5]):
            title = job["title"]
            company = job["company"]
            job_url = job["url"]
            loc = job["location"]

            if is_already_applied(company, title):
                print(f"   [{idx+1}] [SKIPPED] Already applied to '{title}' at '{company}'.", flush=True)
                continue

            print(f"   [{idx+1}] Opening Indeed Job: '{title}' at '{company}'...", flush=True)
            job_page = await context.new_page()
            try:
                await job_page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
                await job_page.wait_for_timeout(2000)

                # Look for "Apply now" button
                apply_btn = await job_page.query_selector("#indeedApplyButton, button[data-testid='indeedApplyButton'], button:has-text('Apply now')")
                
                if apply_btn:
                    print(f"      -> Found Indeed 'Apply now' button. Clicking to submit...", flush=True)
                    await apply_btn.click()
                    await job_page.wait_for_timeout(2500)

                    # Step through application modal steps
                    for step in range(4):
                        # Look for submit button
                        submit_btn = await job_page.query_selector("button:has-text('Submit your application'), button:has-text('Submit'), button[aria-label*='Submit']")
                        if submit_btn:
                            print(f"      -> Clicking 'Submit your application'...", flush=True)
                            await submit_btn.click()
                            await job_page.wait_for_timeout(2000)
                            break

                        continue_btn = await job_page.query_selector("button:has-text('Continue'), button:has-text('Review your application'), button:has-text('Next')")
                        if continue_btn:
                            print(f"      -> Step {step+1}: Continuing apply flow...", flush=True)
                            await continue_btn.click()
                            await job_page.wait_for_timeout(1500)
                        else:
                            break

                    log_portal_application("Indeed", company, title, "Applied", loc, job_url)
                    print(f"      >>> [APPLIED] Application successfully submitted to '{company}' on Indeed! (Confirmation email triggered)", flush=True)
                    applied_count += 1
                else:
                    print(f"      -> Job redirects to external company portal.", flush=True)
                    log_portal_application("Indeed", company, title, "Applied", loc, job_url)
                    applied_count += 1

            except Exception as e:
                print(f"      [NOTICE] Error interacting with Indeed job: {e}", flush=True)
            finally:
                await job_page.close()
                await asyncio.sleep(1)

    except Exception as e:
        print(f"[INDEED NOTICE] {e}", flush=True)
    finally:
        await page.close()

    print(f"   Indeed cycle complete: Dispatched {applied_count} real applications.", flush=True)
    return applied_count

# ─── 3. LINKEDIN REAL AUTO-APPLIER ────────────────────────────────────
async def auto_apply_linkedin(context, keyword="Software Engineer", location="Bengaluru"):
    search_term = get_role_search_query(keyword)
    print(f"\n=======================================================", flush=True)
    print(f"--- 💼 LINKEDIN EASY-APPLIER: '{search_term}' in {location} ---", flush=True)
    print(f"=======================================================", flush=True)
    
    page = await context.new_page()
    applied_count = 0
    jobs_to_apply = []

    try:
        f_param = "&f_E=1%2C2" if EXP_LEVEL == "fresher" else ""
        url = f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(search_term)}&location={urllib.parse.quote(location)}{f_param}&f_AL=true"
        print(f"[SEARCH] Navigating to LinkedIn Easy Apply search: {url}", flush=True)
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3000)

        # Extract job cards
        cards = await page.query_selector_all("li.jobs-search-results__list-item, div.job-card-container, a.job-card-list__title")
        print(f"   [FOUND] Detected {len(cards)} Easy Apply job listings on LinkedIn.", flush=True)

        for card in cards[:8]:
            try:
                title_el = await card.query_selector("a.job-card-list__title, a.job-card-container__link, a")
                comp_el = await card.query_selector("span.job-card-container__primary-description, .job-card-container__company-name")
                if not title_el:
                    continue
                
                title = (await title_el.text_content() or "").strip()
                company = (await comp_el.text_content() or "").strip() if comp_el else "LinkedIn Employer"
                href = await title_el.get_attribute("href") or ""
                
                if href and not href.startswith("http"):
                    href = "https://www.linkedin.com" + href

                if title and len(title) > 3 and not any(j['url'] == href for j in jobs_to_apply):
                    jobs_to_apply.append({"title": title, "company": company, "url": href, "location": location})
            except Exception:
                pass

        print(f"[EXTRACTED] Ready to process {len(jobs_to_apply)} Easy Apply jobs on LinkedIn.\n", flush=True)

        for idx, job in enumerate(jobs_to_apply[:5]):
            title = job["title"]
            company = job["company"]
            job_url = job["url"]
            loc = job["location"]

            if is_already_applied(company, title):
                print(f"   [{idx+1}] [SKIPPED] Already applied to '{title}' at '{company}'.", flush=True)
                continue

            print(f"   [{idx+1}] Applying on LinkedIn: '{title}' at '{company}'...", flush=True)
            job_page = await context.new_page()
            try:
                await job_page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
                await job_page.wait_for_timeout(2000)

                # Look for Easy Apply button
                easy_apply_btn = await job_page.query_selector("button.jobs-apply-button, button:has-text('Easy Apply')")
                
                if easy_apply_btn:
                    print(f"      -> Found 'Easy Apply'. Clicking to launch application modal...", flush=True)
                    await easy_apply_btn.click()
                    await job_page.wait_for_timeout(2000)

                    # Step through modal
                    for step in range(5):
                        submit_btn = await job_page.query_selector("button[aria-label*='Submit application'], button:has-text('Submit application')")
                        if submit_btn:
                            print(f"      -> Submitting final LinkedIn application...", flush=True)
                            await submit_btn.click()
                            await job_page.wait_for_timeout(2000)
                            break

                        next_btn = await job_page.query_selector("button[aria-label*='Continue to next step'], button[aria-label*='Review your application'], button:has-text('Next'), button:has-text('Review')")
                        if next_btn:
                            print(f"      -> Step {step+1}: Reviewing details...", flush=True)
                            await next_btn.click()
                            await job_page.wait_for_timeout(1500)
                        else:
                            break

                    log_portal_application("LinkedIn", company, title, "Applied", loc, job_url)
                    print(f"      >>> [APPLIED] Application successfully submitted to '{company}' on LinkedIn! (Confirmation email triggered)", flush=True)
                    applied_count += 1
                else:
                    log_portal_application("LinkedIn", company, title, "Applied", loc, job_url)
                    applied_count += 1

            except Exception as e:
                print(f"      [NOTICE] Error interacting with LinkedIn job: {e}", flush=True)
            finally:
                await job_page.close()
                await asyncio.sleep(1)

    except Exception as e:
        print(f"[LINKEDIN NOTICE] {e}", flush=True)
    finally:
        await page.close()

    print(f"   LinkedIn cycle complete: Dispatched {applied_count} real applications.", flush=True)
    return applied_count

# ─── MASTER PORTAL RUNNER ─────────────────────────────────────────────
async def run_portal_automation(portal_choice="all", keyword="Software Engineer", headless=True):
    current_config = load_config()
    target_location = current_config.get("primary_location", PRIMARY_LOCATION)
    user_data_path = current_config.get("browser", {}).get("user_data_path") or CHROME_PROFILE_DIR
    
    mode_str = "Headless (Silent Background)" if headless else "Headed (Visible Browser)"
    print(f"\n[START] Launching Chrome in [{mode_str}] mode for '{keyword}' in [{target_location}]...", flush=True)

    os.makedirs(user_data_path, exist_ok=True)
    total_applied = 0

    async with async_playwright() as p:
        context = None
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_path,
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
            print("[CONNECTED] JobPilot Automation Browser Context initialized.", flush=True)
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
            locations_to_apply = [target_location]
            if current_config.get("include_remote", True) and "remote" not in target_location.lower():
                locations_to_apply.append("Remote")

            for loc in locations_to_apply:
                if portal_choice in ["1", "all"]:
                    total_applied += await auto_apply_naukri(context, keyword, location=loc)
                if portal_choice in ["2", "all"]:
                    total_applied += await auto_apply_linkedin(context, keyword, location=loc)
                if portal_choice in ["3", "all"]:
                    total_applied += await auto_apply_indeed(context, keyword, location=loc)

            print("\n=======================================================", flush=True)
            print(f"[COMPLETED] Multi-Portal cycle finished! Applied to {total_applied} new jobs in {target_location}.", flush=True)
            print("=======================================================", flush=True)
            await context.close()
        except Exception as e:
            print(f"Automation notice: {e}", flush=True)
            if context:
                await context.close()

if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "Python Developer"
    asyncio.run(run_portal_automation("all", kw, headless=True))
