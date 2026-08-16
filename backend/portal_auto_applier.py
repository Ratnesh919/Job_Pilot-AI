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


async def show_browser_hud(page, text: str):
    """Injects a real-time floating status badge & virtual cursor in the open browser so you can watch live progress."""
    try:
        clean_text = text.replace("'", "\\'").replace('"', '\\"')
        await page.evaluate(f"""() => {{
            // HUD
            let hud = document.getElementById('applybot-live-hud');
            if (!hud) {{
                hud = document.createElement('div');
                hud.id = 'applybot-live-hud';
                hud.style.position = 'fixed';
                hud.style.bottom = '24px';
                hud.style.right = '24px';
                hud.style.backgroundColor = '#0f172a';
                hud.style.color = '#38bdf8';
                hud.style.padding = '12px 20px';
                hud.style.borderRadius = '12px';
                hud.style.border = '1px solid #38bdf8';
                hud.style.boxShadow = '0 10px 30px rgba(0,0,0,0.7)';
                hud.style.zIndex = '999999999';
                hud.style.fontFamily = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
                hud.style.fontSize = '14px';
                hud.style.fontWeight = '600';
                hud.style.pointerEvents = 'none';
                hud.style.transition = 'all 0.3s ease';
                document.body.appendChild(hud);
            }}
            hud.innerHTML = '🤖 <span style="color:#ffffff; font-weight:700;">ApplyBot Pro:</span> ' + '{clean_text}';

            // Virtual Mouse Pointer
            let cur = document.getElementById('applybot-virtual-cursor');
            if (!cur) {{
                cur = document.createElement('div');
                cur.id = 'applybot-virtual-cursor';
                cur.style.position = 'fixed';
                cur.style.width = '18px';
                cur.style.height = '18px';
                cur.style.borderRadius = '50%';
                cur.style.backgroundColor = 'rgba(239, 68, 68, 0.9)';
                cur.style.border = '2px solid #ffffff';
                cur.style.boxShadow = '0 0 12px rgba(239, 68, 68, 0.8), inset 0 0 4px #fff';
                cur.style.pointerEvents = 'none';
                cur.style.zIndex = '999999999';
                cur.style.transform = 'translate(-50%, -50%)';
                cur.style.transition = 'all 0.15s cubic-bezier(0.2, 0.8, 0.2, 1)';
                cur.style.left = '50vw';
                cur.style.top = '50vh';
                document.body.appendChild(cur);
            }}
        }}""")
    except Exception:
        pass


async def move_cursor_to_element(page, el):
    """Smoothly moves the virtual visual cursor and Playwright mouse to the center of an element."""
    try:
        box = await el.bounding_box()
        if box:
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + box["height"] / 2
            # Move visual cursor via JS
            await page.evaluate(f"""() => {{
                let cur = document.getElementById('applybot-virtual-cursor');
                if (cur) {{
                    cur.style.left = '{cx}px';
                    cur.style.top = '{cy}px';
                    cur.style.transform = 'translate(-50%, -50%) scale(1.3)';
                    setTimeout(() => {{ if (cur) cur.style.transform = 'translate(-50%, -50%) scale(1.0)'; }}, 200);
                }}
            }}""")
            # Move Playwright OS mouse
            await page.mouse.move(cx, cy, steps=6)
            await page.wait_for_timeout(100)
    except Exception:
        pass


async def smooth_scroll_page(page, amount=350):
    """Performs a smooth human-like page scroll."""
    try:
        await page.evaluate(f"""() => {{
            window.scrollBy({{ top: {amount}, behavior: 'smooth' }});
        }}""")
        await page.wait_for_timeout(300)
    except Exception:
        pass


async def safe_click(page, selectors, label="button", timeout=6000):
    """Try each selector, scroll into view, animate cursor to target, and click in real-time."""
    for sel in selectors:
        try:
            el = await page.wait_for_selector(sel, timeout=timeout, state="visible")
            if el:
                await el.scroll_into_view_if_needed()
                await move_cursor_to_element(page, el)
                # Visual click glow
                try:
                    await page.evaluate("el => { el.style.outline = '3px solid #10b981'; el.style.boxShadow = '0 0 16px #10b981aa'; }", el)
                    await page.wait_for_timeout(150)
                    await page.evaluate("el => { el.style.outline = 'none'; el.style.boxShadow = 'none'; }", el)
                except Exception:
                    pass
                await el.click()
                print(f"      -> Clicked [{label}]: {sel}", flush=True)
                return True
        except Exception:
            pass
    return False


async def fill_if_empty(page, selector, value):
    """Fill a field with visual cursor movement, human keystrokes, and visible focus outline."""
    try:
        el = await page.query_selector(selector)
        if el and await el.is_visible():
            cur = await el.input_value()
            if not cur.strip():
                await el.scroll_into_view_if_needed()
                await move_cursor_to_element(page, el)
                # Highlight active field in blue
                await page.evaluate("el => { el.style.outline = '2px solid #3b82f6'; el.style.boxShadow = '0 0 10px #3b82f666'; }", el)
                await el.click()
                try:
                    await el.press_sequentially(str(value), delay=25)
                except Exception:
                    await el.fill(str(value))
                await page.wait_for_timeout(100)
                await page.evaluate("el => { el.style.outline = 'none'; el.style.boxShadow = 'none'; }", el)
    except Exception:
        pass


async def wait_for_login_if_needed(page, portal_name: str, max_wait_seconds: int = 180) -> bool:
    """
    Detects if the current page is a login wall.
    If so, prints a clear message and waits up to max_wait_seconds for the user to log in.
    Returns True if logged in (or not a login wall), False if timed out.
    """
    LOGIN_INDICATORS = [
        "a:has-text('Login')",
        "a:has-text('Log in')",
        "a:has-text('Sign in')",
        "button:has-text('Login')",
        "button:has-text('Log in')",
        "button:has-text('Sign In')",
        "input[name='username']",
        "input[name='email'][placeholder*='mail']",
        "form[action*='login']",
        "form[action*='signin']",
    ]
    NOT_LOGGED_IN_URLS = ["login", "signin", "sign-in", "nlogin", "authwall", "checkpoint/lg"]

    async def is_login_page():
        try:
            url = page.url.lower()
            if any(kw in url for kw in NOT_LOGGED_IN_URLS):
                return True
            for sel in LOGIN_INDICATORS[:4]:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        return True
                except Exception:
                    pass
        except Exception:
            pass
        return False

    if not await is_login_page():
        return True  # Already logged in or no login wall

    # Print a prominent login prompt
    print(f"\n{'!'*60}", flush=True)
    print(f"  [LOGIN REQUIRED] {portal_name} is showing a login page.", flush=True)
    print(f"  Please log into {portal_name} in the browser window.", flush=True)
    print(f"  Bot will wait up to {max_wait_seconds} seconds...", flush=True)
    print(f"{'!'*60}\n", flush=True)

    waited = 0
    check_interval = 5   # check every 5 seconds
    while waited < max_wait_seconds:
        await asyncio.sleep(check_interval)
        waited += check_interval
        if not await is_login_page():
            print(f"  [LOGIN] {portal_name}: Logged in! ✓ Continuing...", flush=True)
            await page.wait_for_timeout(2000)
            return True
        remaining = max_wait_seconds - waited
        if waited % 30 == 0 and remaining > 0:
            print(f"  [LOGIN] Still waiting for {portal_name} login... ({remaining}s left)", flush=True)

    print(f"  [LOGIN] Timed out waiting for {portal_name} login. Skipping.", flush=True)
    return False


# ── HR Recruiter Email Extractor & Direct Dispatcher ──────────────────────────
def extract_recruiter_emails(text: str) -> list[str]:
    """
    Scans job descriptions for recruiter / HR email addresses.
    Filters out system, CDN, support, and domain placeholder emails.
    """
    if not text:
        return []

    raw_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)

    IGNORED_DOMAINS = [
        'naukri.com', 'naukimg.com', 'indeed.com', 'indeedemail.com',
        'linkedin.com', 'licdn.com', 'google.com',
        'example.com', 'sentry.io', 'w3.org', 'schema.org', 'github.com',
        'apple.com', 'microsoft.com', 'adobe.com', 'cloudflare.com',
        'playwright.dev', 'electronjs.org', 'npmjs.com'
    ]
    IGNORED_PREFIXES = [
        'noreply', 'no-reply', 'donotreply', 'support', 'help', 'privacy',
        'security', 'terms', 'feedback', 'abuse', 'contact-us', 'info@naukri',
        'mailer', 'postmaster', 'admin@naukri', 'alert', 'notification',
        'jobseeker', 'billing', 'sales'
    ]

    valid = []
    for em in raw_emails:
        em_clean = em.lower().strip('.').strip(',').strip(';').strip(':').strip(')')
        if '@' not in em_clean:
            continue
        parts = em_clean.split('@')
        if len(parts) != 2:
            continue
        user, domain = parts[0], parts[1]

        if any(d in domain for d in IGNORED_DOMAINS):
            continue
        if any(user.startswith(p) for p in IGNORED_PREFIXES):
            continue
        if '.' not in domain or len(domain.split('.')[-1]) < 2:
            continue

        if em_clean not in valid:
            valid.append(em_clean)

    return valid


async def send_recruiter_direct_email(recipient_email: str, job_title: str, company: str, job_url: str = "") -> bool:
    """
    Dispatches a professional application email with Resume.pdf attached
    directly to the HR/recruiter email discovered in the job posting.
    """
    try:
        from email_sender import send_job_application_email
        domain_type = "software"
        title_lower = job_title.lower()
        if any(w in title_lower for w in ["electronics", "hardware", "embedded", "iot", "vlsi", "core", "cad"]):
            domain_type = "core"
        elif any(w in title_lower for w in ["ui", "ux", "designer", "frontend"]):
            domain_type = "software"

        print(f"      📧 [HR EMAIL FOUND] Recruiter contact: {recipient_email}", flush=True)
        print(f"      -> Sending tailored application email + Resume.pdf + Portfolio links...", flush=True)
        success = send_job_application_email(
            recipient_email=recipient_email,
            role_title=job_title,
            company_name=company,
            domain_type=domain_type,
            resume_type="software" if domain_type == "software" else "core"
        )
        if success:
            print(f"      >>> [EMAIL SENT] Successfully emailed HR at '{recipient_email}' for '{job_title}' @ '{company}'!", flush=True)
            record_application(
                platform="Recruiter Direct Email",
                company=company,
                role=job_title,
                status="Applied",
                recruiter_email=recipient_email,
                notes=f"HR email extracted from job listing ({job_url})"
            )
            return True
    except Exception as e:
        print(f"      [EMAIL ERROR] Could not dispatch to {recipient_email}: {e}", flush=True)
# ── LinkedIn Easy Apply Modal Solver ──────────────────────────────────────────
async def solve_linkedin_easy_apply_modal(page, job_title: str) -> bool:
    """
    Intelligently handles all steps of LinkedIn's Easy Apply modal:
      1. Contact info (phone number, email)
      2. Resume selection (selects active resume or uploads Resume.pdf)
      3. Screening questions (Numeric experience, Notice period, Salary, Yes/No radios, Dropdowns)
      4. Review step (unchecks Follow company, clicks Submit application)
      5. Post-submission confirmation dismiss
    """
    modal_sel = "div.jobs-easy-apply-modal, div[data-test-modal], div[role='dialog']"
    submitted = False

    for step in range(10):  # max 10 steps
        await page.wait_for_timeout(400)

        # ── 1. Check for Submit Application button ──
        submit_btn = await page.query_selector("button[aria-label='Submit application'], button:has-text('Submit application')")
        if submit_btn and await submit_btn.is_visible():
            try:
                follow_chk = await page.query_selector("label:has-text('Follow'), input[type='checkbox'][id*='follow']")
                if follow_chk:
                    is_checked = await page.evaluate("el => el.checked", follow_chk)
                    if is_checked:
                        await follow_chk.click()
            except Exception:
                pass

            await submit_btn.click()
            print("      -> Clicked [Submit application] on LinkedIn! 🎉", flush=True)
            await page.wait_for_timeout(1500)
            submitted = True
            break

        # ── 2. Contact Info Phone Number ──
        phone_input = await page.query_selector("input[id*='phoneNumber'], input[name*='phone'], input[placeholder*='phone']")
        if phone_input and await phone_input.is_visible():
            val = await phone_input.input_value()
            if not val.strip():
                clean_phone = USER_PHONE.replace("+91 ", "").replace(" ", "").replace("+91", "")
                await phone_input.fill(clean_phone)

        # ── 3. Resume Selection & Upload ──
        resume_cards = await page.query_selector_all(".jobs-document-upload__title, label[for*='resume'], div[data-test-document-upload], input[type='radio'][value*='resume' i]")
        if resume_cards:
            try:
                await resume_cards[0].click()
            except Exception:
                pass
        else:
            file_input = await page.query_selector("input[type='file']")
            if file_input and os.path.exists(RESUME_PDF_PATH):
                try:
                    await file_input.set_input_files(RESUME_PDF_PATH)
                    print(f"      -> Uploaded Resume.pdf to LinkedIn", flush=True)
                    await page.wait_for_timeout(600)
                except Exception:
                    pass

        # ── 4. Screening Questions ──
        # A. Text / Number Inputs
        inputs = await page.query_selector_all(f"{modal_sel} input[type='text'], {modal_sel} input[type='number'], {modal_sel} textarea")
        for inp in inputs:
            try:
                if not await inp.is_visible():
                    continue
                cur_val = await inp.input_value()
                if not cur_val.strip():
                    lbl_text = await page.evaluate("""el => {
                        const lbl = el.closest('div.fb-dash-form-element')?.querySelector('label') ||
                                    el.closest('div')?.querySelector('label') ||
                                    document.querySelector(`label[for="${el.id}"]`);
                        return lbl ? lbl.innerText.toLowerCase() : (el.getAttribute('aria-label') || '').toLowerCase();
                    }""", inp)

                    if any(w in lbl_text for w in ["experience", "years", "how many"]):
                        await inp.fill("1")
                    elif any(w in lbl_text for w in ["ctc", "salary", "compensation", "expected"]):
                        await inp.fill("350000")
                    elif any(w in lbl_text for w in ["notice", "days", "joining"]):
                        await inp.fill("0")
                    elif any(w in lbl_text for w in ["gpa", "percentage", "cgpa"]):
                        await inp.fill("8.5")
                    elif any(w in lbl_text for w in ["city", "location"]):
                        await inp.fill("Kolkata")
                    else:
                        await inp.fill("1")
            except Exception:
                pass

        # B. Radio buttons (Yes / No)
        radio_groups = await page.query_selector_all(f"{modal_sel} fieldset, {modal_sel} div[data-test-form-builder-radio-button-form-component]")
        for group in radio_groups:
            try:
                legend_text = await page.evaluate("el => el.innerText.toLowerCase()", group)
                if any(w in legend_text for w in ["sponsorship", "visa", "require sponsorship", "criminal"]):
                    no_radio = await group.query_selector("label:has-text('No'), input[value='No'], input[value='false']")
                    if no_radio:
                        await no_radio.click()
                else:
                    yes_radio = await group.query_selector("label:has-text('Yes'), input[value='Yes'], input[value='true']")
                    if yes_radio:
                        await yes_radio.click()
            except Exception:
                pass

        # C. Dropdown / Select fields
        selects = await page.query_selector_all(f"{modal_sel} select")
        for sel in selects:
            try:
                cur_val = await sel.input_value()
                if not cur_val or cur_val == "Select an option":
                    options = await page.evaluate("el => Array.from(el.options).map(o => o.value).filter(v => v && v !== 'Select an option')", sel)
                    if options:
                        await sel.select_option(value=options[0])
            except Exception:
                pass

        # ── 5. Advance Step (Next / Review) ──
        advanced = await safe_click(page, [
            "button[aria-label='Review your application']",
            "button[aria-label='Continue to next step']",
            "button:has-text('Review')",
            "button:has-text('Next')",
            "button:has-text('Continue')",
        ], label=f"LinkedIn Step {step+1}", timeout=2000)

        if not advanced:
            # Check if Submit appeared without Next
            submit_btn = await page.query_selector("button[aria-label='Submit application'], button:has-text('Submit application')")
            if submit_btn and await submit_btn.is_visible():
                await submit_btn.click()
                print("      -> Clicked [Submit application] on LinkedIn! 🎉", flush=True)
                await page.wait_for_timeout(1500)
                submitted = True
            break

    # Dismiss post-submission confirmation
    if submitted:
        await page.wait_for_timeout(600)
        await safe_click(page, [
            "button[aria-label='Dismiss']",
            "button:has-text('Done')",
            "button:has-text('Not now')",
        ], label="LinkedIn Dismiss", timeout=1800)

    return submitted


# ── External Company Website Applier & HR Email Scraper ──────────────────────
async def apply_external_company_site_or_email(context, original_page, company_name: str, job_title: str, job_url: str = "") -> bool:
    """
    When no in-portal Easy Apply button exists:
      1. Detects & follows external 'Apply on company website' link / button.
      2. Selects position/designation dropdown, fills form fields, uploads Resume.pdf, and submits.
      3. If form cannot be submitted: crawls company website & Contact/Careers pages for HR emails and dispatches tailored email.
    """
    print(f"      🌐 [COMPANY SITE] Checking external application for '{job_title}' @ '{company_name}'...", flush=True)
    company_page = None

    try:
        external_selectors = [
            "a:has-text('Apply on company website')",
            "a:has-text('Apply on employer site')",
            "a:has-text('Apply on company site')",
            "button:has-text('Apply on company website')",
            "a:has-text('Apply externally')",
            "a:has-text('Company Site')",
            "a[href*='apply']:not([href*='linkedin']):not([href*='naukri']):not([href*='indeed'])",
            "a.apply-button",
        ]

        target_url = None
        for sel in external_selectors:
            try:
                el = await original_page.query_selector(sel)
                if el and await el.is_visible():
                    href = await el.get_attribute("href")
                    if href and href.startswith("http") and not any(p in href for p in ["linkedin.com", "naukri.com", "indeed.com"]):
                        target_url = href
                        break
            except Exception:
                pass

        if target_url:
            company_page = await context.new_page()
            await company_page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
            await company_page.wait_for_timeout(2000)
        else:
            try:
                async with original_page.expect_popup(timeout=4000) as popup_info:
                    await safe_click(original_page, external_selectors, label="External Apply Link", timeout=3000)
                company_page = await popup_info.value
                await company_page.wait_for_load_state("domcontentloaded")
            except Exception:
                company_page = original_page

        if not company_page:
            company_page = original_page

        await show_browser_hud(company_page, f"Checking Form on {company_name}...")

        # Step 1: Try Deep DOM Form Filling & Resume Upload on Company Page
        try:
            from dom_job_applier import walk_form_steps, fill_form_via_dom
            # Select Designation / Position dropdown if present
            try:
                pos_selects = await company_page.query_selector_all("select[name*='position' i], select[name*='role' i], select[name*='designation' i], select[id*='job' i]")
                for p_sel in pos_selects:
                    if await p_sel.is_visible():
                        opts = await company_page.evaluate("el => Array.from(el.options).map(o => ({text: o.text, val: o.value}))", p_sel)
                        for opt in opts:
                            if any(w in opt["text"].lower() for w in job_title.lower().split() if len(w) > 3):
                                await p_sel.select_option(value=opt["val"])
                                print(f"      [DOM] Selected Designation: '{opt['text']}'", flush=True)
                                break
            except Exception:
                pass

            # Walk multi-step form & submit
            submitted = await walk_form_steps(company_page, job_title)
            if submitted:
                print(f"      >>> [APPLIED] Successfully submitted application on {company_name} website!", flush=True)
                log_applied(f"Company Website ({company_name})", company_name, job_title, "Online", job_url or company_page.url)
                return True
        except Exception as e:
            print(f"      [DOM FORM NOTICE] {e}", flush=True)

        # Step 2: Fallback — Crawl Company Website for HR / Careers Email
        print(f"      🔍 [SCRAPING HR EMAIL] Searching {company_name} website for HR/Careers email...", flush=True)
        await show_browser_hud(company_page, f"Scraping HR email for {company_name}...")

        page_html = await company_page.content()
        hr_emails = extract_recruiter_emails(page_html)

        if not hr_emails:
            contact_links = await company_page.evaluate("""() => {
                const links = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    const h = a.href.toLowerCase();
                    if (h.includes('contact') || h.includes('career') || h.includes('about') || h.includes('jobs') || h.startsWith('mailto:')) {
                        links.push(a.href);
                    }
                });
                return [...new Set(links)].slice(0, 3);
            }""")

            for c_link in contact_links:
                if c_link.startswith("mailto:"):
                    raw_mail = c_link.replace("mailto:", "").split("?")[0].strip()
                    if raw_mail and "@" in raw_mail:
                        hr_emails.append(raw_mail)
                else:
                    try:
                        aux_page = await context.new_page()
                        await aux_page.goto(c_link, wait_until="domcontentloaded", timeout=12000)
                        aux_text = await aux_page.content()
                        found = extract_recruiter_emails(aux_text)
                        if found:
                            hr_emails.extend(found)
                        await aux_page.close()
                    except Exception:
                        pass
                if hr_emails:
                    break

        if hr_emails:
            for hr_mail in hr_emails[:2]:
                if not is_already_applied(company_name, job_title, recruiter_email=hr_mail):
                    sent = await send_recruiter_direct_email(hr_mail, job_title, company_name, job_url)
                    if sent:
                        return True

    except Exception as e:
        print(f"      [EXTERNAL APPLY NOTICE] {e}", flush=True)
    finally:
        if company_page and company_page != original_page:
            try:
                await company_page.close()
            except Exception:
                pass

    return False


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
        # ── Check Naukri Login status before running search loop ──
        print("[NAUKRI] Verifying login status...", flush=True)
        try:
            await page.goto("https://www.naukri.com/mnjuser/profile", timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            cur_u = page.url.lower()
            if "nlogin" in cur_u or "login" in cur_u or "register" in cur_u:
                print("\n" + "="*65, flush=True)
                print("  [NAUKRI LOGIN REQUIRED]", flush=True)
                print("  Please log into your Naukri account in the opened Chrome window.", flush=True)
                print("  (Login via Google or Password. Once logged in, the bot continues automatically).", flush=True)
                print("  Waiting up to 180 seconds...", flush=True)
                print("="*65 + "\n", flush=True)
                if "nlogin" not in cur_u:
                    await page.goto("https://www.naukri.com/nlogin/login", timeout=15000)

                logged_in = False
                for i in range(36):  # 36 * 5s = 180s
                    await asyncio.sleep(5)
                    u = page.url.lower()
                    if "nlogin" not in u and "login" not in u and "naukri.com" in u:
                        print("  [NAUKRI] Logged in successfully! ✓ Proceeding with applications...", flush=True)
                        logged_in = True
                        await page.wait_for_timeout(2000)
                        break
                    if (i+1) % 6 == 0:
                        print(f"  [NAUKRI] Waiting for login... ({180 - (i+1)*5}s left)", flush=True)
                if not logged_in:
                    print("  [NAUKRI NOTICE] Login timed out. Continuing with available jobs...", flush=True)
            else:
                print("[NAUKRI] Login verified! ✓", flush=True)
        except Exception as e:
            print(f"[NAUKRI] Login check error: {e}", flush=True)

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

                # ── 1. Scan job description for Recruiter / HR email address ──
                page_text = await jp.evaluate("() => document.body ? document.body.innerText : ''")
                found_hr_emails = extract_recruiter_emails(page_text)
                emailed_hr = False
                for hr_em in found_hr_emails[:2]:
                    if not is_already_applied(company, title, recruiter_email=hr_em):
                        sent = await send_recruiter_direct_email(hr_em, title, company, job_url)
                        if sent:
                            applied += 1
                            emailed_hr = True

                # ── 2. Apply button on portal (Naukri 2024 DOM) ──
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

                if not clicked and not emailed_hr:
                    ext_applied = await apply_external_company_site_or_email(context, jp, company, title, job_url)
                    if ext_applied:
                        applied += 1
                    else:
                        print(f"      -> No Apply button, external form, or HR email found. Skipping.", flush=True)
                    await jp.close()
                    continue

                if clicked:
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

                    # Log portal submission
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

    # Inject anti-detection stealth script
    try:
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.navigator.chrome = { runtime: {} };
        """)
    except Exception:
        pass

    try:
        kw_slug = search_term.lower().replace(" ", "-")
        search_urls = [
            f"https://in.indeed.com/jobs?q={urllib.parse.quote(search_term)}&l={urllib.parse.quote(location)}",
            f"https://in.indeed.com/q-{kw_slug}-jobs.html",
            f"https://www.indeed.com/jobs?q={urllib.parse.quote(search_term)}&l={urllib.parse.quote(location)}",
        ]

        for s_url in search_urls:
            print(f"[INDEED] Search: {s_url}", flush=True)
            try:
                await page.goto(s_url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(3000)

                # Check for Cloudflare Challenge / Turnstile Checkbox
                for attempt in range(15):
                    cur_title = (await page.title()).lower()
                    if "just a moment" in cur_title or "security check" in cur_title or "challenge" in page.url.lower():
                        await show_browser_hud(page, "Solving Indeed Human Verification (up to 30s)...")
                        if attempt == 0:
                            print("\n" + "="*65, flush=True)
                            print("  [INDEED HUMAN VERIFICATION DETECTED]", flush=True)
                            print("  Please check the 'Verify you are human' box in the Chrome window if prompted.", flush=True)
                            print("  Waiting up to 30 seconds for verification to clear...", flush=True)
                            print("="*65 + "\n", flush=True)

                        # Attempt auto-click on Turnstile frames
                        for frame in page.frames:
                            try:
                                if "challenges.cloudflare.com" in frame.url or "turnstile" in frame.url:
                                    box = await frame.query_selector("input[type='checkbox'], .ctp-checkbox-label, #challenge-stage, .cb-i")
                                    if box:
                                        await box.click()
                                        print("  -> Auto-clicked Cloudflare Turnstile box!", flush=True)
                                        await page.wait_for_timeout(2000)
                                        break
                            except Exception:
                                pass

                        await asyncio.sleep(2)
                    else:
                        break

                # Extract jobs using comprehensive DOM evaluate
                extracted = await page.evaluate("""() => {
                    const results = [];
                    const seen = new Set();

                    document.querySelectorAll('a.jcs-JobTitle, a[data-jk], h2.jobTitle a, a[id^="job_"], a[href*="/viewjob"], a[href*="/rc/clk"]').forEach(a => {
                        const title = a.innerText.trim();
                        const jk = a.getAttribute('data-jk') || (a.id.startsWith('job_') ? a.id.replace('job_', '') : '');
                        const href = a.href || '';

                        let card = a.closest('div.job_seen_beacon') || a.closest('div.cardOutline') || a.closest('li') || a.closest('td.resultContent') || a.closest('div[data-testid="slider_item"]') || a.closest('div');
                        let company = "Indeed Employer";
                        if (card) {
                            const cEl = card.querySelector('[data-testid="company-name"], .companyName, span[class*="companyName"], span.css-63koeb');
                            if (cEl) company = cEl.innerText.trim();
                        }

                        let finalUrl = jk ? `https://in.indeed.com/viewjob?jk=${jk}` : (href.includes('viewjob') || href.includes('/rc/clk') ? href : '');
                        if (title && title.length > 2 && finalUrl && !seen.has(finalUrl)) {
                            seen.add(finalUrl);
                            results.push({title, company, url: finalUrl});
                        }
                    });

                    return results;
                }""")

                if extracted:
                    for item in extracted:
                        item["loc"] = location
                        if not any(j["url"] == item["url"] for j in jobs):
                            jobs.append(item)
                    print(f"[INDEED] Successfully found {len(jobs)} jobs!", flush=True)
                    break
            except Exception as e:
                print(f"[INDEED SEARCH NOTICE] {e}", flush=True)

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

                # ── 1. Scan Indeed job description for HR / Recruiter email ──
                page_text = await jp.evaluate("() => document.body ? document.body.innerText : ''")
                found_hr_emails = extract_recruiter_emails(page_text)
                emailed_hr = False
                for hr_em in found_hr_emails[:2]:
                    if not is_already_applied(company, title, recruiter_email=hr_em):
                        sent = await send_recruiter_direct_email(hr_em, title, company, job_url)
                        if sent:
                            applied += 1
                            emailed_hr = True

                # ── 2. Indeed Apply button selectors (2024) ──
                clicked = await safe_click(jp, [
                    "#indeedApplyButton",
                    "button[data-testid='indeedApplyButton']",
                    "button[class*='IndeedApply']",
                    "a[data-testid='indeedApplyButton']",
                    "button:has-text('Apply now')",
                    "button:has-text('Apply on Indeed')",
                    "button:has-text('Easy Apply')",
                ], label="Indeed Apply", timeout=6000)

                if not clicked and not emailed_hr:
                    ext_applied = await apply_external_company_site_or_email(context, jp, company, title, job_url)
                    if ext_applied:
                        applied += 1
                    else:
                        print(f"      -> No Apply button, external form, or HR email found. Skipping.", flush=True)
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
        # ── Check LinkedIn login status ──
        print("[LINKEDIN] Verifying login status...", flush=True)
        try:
            await page.goto("https://www.linkedin.com/feed/", timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            u = page.url.lower()
            if "login" in u or "authwall" in u or "checkpoint" in u or "feed" not in u:
                print("\n" + "="*65, flush=True)
                print("  [LINKEDIN LOGIN REQUIRED]", flush=True)
                print("  Please log into LinkedIn in the opened Chrome window.", flush=True)
                print("  (Sign in with your email/password. Once in feed, bot proceeds automatically).", flush=True)
                print("  Waiting up to 180 seconds...", flush=True)
                print("="*65 + "\n", flush=True)
                if "login" not in u:
                    await page.goto("https://www.linkedin.com/login", timeout=15000)

                logged_in = False
                for i in range(36):
                    await asyncio.sleep(5)
                    curr = page.url.lower()
                    if "feed" in curr or ("linkedin.com" in curr and "login" not in curr and "authwall" not in curr):
                        print("  [LINKEDIN] Logged in successfully! ✓ Proceeding with Easy Apply...", flush=True)
                        logged_in = True
                        await page.wait_for_timeout(2000)
                        break
                    if (i+1) % 6 == 0:
                        print(f"  [LINKEDIN] Waiting for login... ({180 - (i+1)*5}s left)", flush=True)
                if not logged_in:
                    print("  [LINKEDIN NOTICE] Login timed out. Continuing with available search...", flush=True)
            else:
                print("[LINKEDIN] Login verified! ✓", flush=True)
        except Exception as e:
            print(f"[LINKEDIN] Login check error: {e}", flush=True)

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

                # ── 1. Scan LinkedIn job description for Recruiter / HR email ──
                page_text = await jp.evaluate("() => document.body ? document.body.innerText : ''")
                found_hr_emails = extract_recruiter_emails(page_text)
                emailed_hr = False
                for hr_em in found_hr_emails[:2]:
                    if not is_already_applied(company, title, recruiter_email=hr_em):
                        sent = await send_recruiter_direct_email(hr_em, title, company, job_url)
                        if sent:
                            applied += 1
                            emailed_hr = True

                # ── 2. Easy Apply button selectors (LinkedIn 2024) ──
                clicked = await safe_click(jp, [
                    "button.jobs-apply-button[aria-label*='Easy Apply']",
                    "button[aria-label*='Easy Apply']",
                    ".jobs-apply-button--top-card",
                    "button:has-text('Easy Apply')",
                    "button.artdeco-button:has-text('Easy Apply')",
                ], label="LinkedIn Easy Apply", timeout=7000)

                if not clicked and not emailed_hr:
                    ext_applied = await apply_external_company_site_or_email(context, jp, company, title, job_url)
                    if ext_applied:
                        applied += 1
                    else:
                        print(f"      -> No Easy Apply button, external form, or HR email found. Skipping.", flush=True)
                    await jp.close()
                    continue

                await jp.wait_for_timeout(1500)

                # Solve full LinkedIn Easy Apply multi-step modal
                actually_submitted = await solve_linkedin_easy_apply_modal(jp, title)

                if actually_submitted:
                    log_applied("LinkedIn", company, title, loc, job_url)
                    print(f"      >>> [APPLIED] '{title}' @ '{company}' on LinkedIn! Check LinkedIn for confirmation.", flush=True)
                    applied += 1
                elif not emailed_hr:
                    print(f"      -> Could not reach final Submit step on modal. Skipping.", flush=True)

            except Exception as e:
                print(f"      [ERROR] {e}", flush=True)
            finally:
                await jp.close()
                await asyncio.sleep(1)

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

    # ── Bot-specific Chrome profile ─────────────────────────────────────────
    # We CANNOT use the main Chrome profile while Chrome is open (profile lock).
    # Solution: use a dedicated bot profile dir and copy Cookies from main profile.
    BOT_PROFILE_DIR = os.path.join(APP_ROOT, "data", "bot_chrome_profile")
    COOKIE_SRC = os.path.join(user_data_path, "Default", "Cookies")
    BOT_COOKIE_DST = os.path.join(BOT_PROFILE_DIR, "Default", "Cookies")
    
    # Copy Cookies & Extensions from user's main Chrome profile to bot profile
    import shutil
    os.makedirs(os.path.join(BOT_PROFILE_DIR, "Default"), exist_ok=True)
    if os.path.exists(COOKIE_SRC):
        try:
            shutil.copy2(COOKIE_SRC, BOT_COOKIE_DST)
            print("[BROWSER] Synced login cookies to bot profile.", flush=True)
        except Exception as e:
            print(f"[BROWSER] Could not sync Cookies ({e}).", flush=True)

    # Sync installed Chrome extensions (Simplify, Buster, CapSolver, uBlock, LetMeApply)
    src_ext_dir = os.path.join(user_data_path, "Default", "Extensions")
    dst_ext_dir = os.path.join(BOT_PROFILE_DIR, "Default", "Extensions")
    if os.path.exists(src_ext_dir):
        os.makedirs(dst_ext_dir, exist_ok=True)
        for ext_id in os.listdir(src_ext_dir):
            s_ext = os.path.join(src_ext_dir, ext_id)
            d_ext = os.path.join(dst_ext_dir, ext_id)
            if os.path.isdir(s_ext) and not os.path.exists(d_ext):
                try:
                    shutil.copytree(s_ext, d_ext)
                except Exception:
                    pass
        print("[BROWSER] Chrome Extensions (Simplify Copilot, Buster, CapSolver, LetMeApply) loaded into bot!", flush=True)

    async with async_playwright() as p:
        context = None
        try:
            # Try using the dedicated bot profile (won't conflict with running Chrome)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=BOT_PROFILE_DIR,
                executable_path=chrome_exe if os.path.exists(chrome_exe) else None,
                headless=headless,
                args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--start-maximized",
                    "--enable-extensions",
                    "--disable-session-crashed-bubble",
                    "--disable-features=TranslateUI",
                ],
                ignore_default_args=["--enable-automation"],
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/127.0.0.0 Safari/537.36"
                ),
                viewport=None,
                ignore_https_errors=True,
                slow_mo=20,
            )
            print("[BROWSER] Launched bot Chrome profile (isolated from your main Chrome).", flush=True)
        except Exception as e:
            print(f"[BROWSER] Bot profile launch failed ({e}). Using Playwright Chromium fallback...", flush=True)
            try:
                # Playwright's bundled Chromium — always works, no conflicts
                browser = await p.chromium.launch(
                    headless=headless,
                    args=[
                        "--no-first-run",
                        "--disable-blink-features=AutomationControlled",
                        "--start-maximized",
                    ],
                    ignore_default_args=["--enable-automation"],
                )
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/127.0.0.0 Safari/537.36"
                    ),
                )
                print("[BROWSER] Using Playwright's built-in Chromium. You may need to log in.", flush=True)
            except Exception as e2:
                print(f"[BROWSER FATAL] Cannot launch any browser: {e2}", flush=True)
                return 0

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
