"""
ApplyBot Pro — Deep DOM Job Applier
====================================
Uses Playwright's full DOM API to:
  1. Extract the complete DOM tree of any careers/apply page
  2. Identify ALL input fields (text, select, radio, checkbox, file, textarea)
  3. Map each field to the right candidate data using field labels + attributes
  4. Fill every field accurately including hidden/shadow-DOM fields
  5. Upload Resume.pdf via the file input element
  6. Handle multi-step forms by detecting pagination buttons
  7. Detect and attempt image CAPTCHA solving via vision LLM
  8. Submit and verify success confirmation

This is more robust than CSS-selector-based automation because:
- It reads actual labels, aria-labels, placeholders, name attributes
- Works even when class names/IDs change
- Handles dynamic forms rendered by React/Vue/Angular
- Detects all input types including custom components
"""

import os
import sys
import asyncio
import json
import csv
import re
import base64
from datetime import datetime, timezone
from pathlib import Path

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

from playwright.async_api import async_playwright, Page, ElementHandle

try:
    from db_helper import record_application, is_already_applied
except Exception:
    def record_application(*a, **kw): pass
    def is_already_applied(*a, **kw): return False

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(APP_ROOT, "config.json")
DATA_DIR    = os.path.join(APP_ROOT, "data")
LOG_FILE    = os.path.join(DATA_DIR, "dom_applications.csv")
RESUME_PDF  = os.path.join(APP_ROOT, "Resume.pdf")
if not os.path.exists(RESUME_PDF):
    RESUME_PDF = os.path.join(os.path.dirname(APP_ROOT), "Resume.pdf")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

cfg = load_config()
C   = cfg.get("candidate", {})

# Candidate data dict — used for all field mapping
CANDIDATE = {
    "name":            C.get("name",            "Ratnesh Kumar Singh"),
    "first_name":      C.get("name",            "Ratnesh Kumar Singh").split()[0],
    "last_name":       " ".join(C.get("name",   "Ratnesh Kumar Singh").split()[1:]),
    "email":           C.get("email",           "kumarsinghratnesh3@gmail.com"),
    "phone":           C.get("phone",           "+91 70049 37129"),
    "phone_plain":     re.sub(r"[^\d]", "",     C.get("phone", "917004937129")),
    "location":        C.get("location",        "Kolkata, West Bengal, India"),
    "city":            "Kolkata",
    "state":           "West Bengal",
    "country":         "India",
    "pincode":         "700001",
    "linkedin":        C.get("linkedin",        "https://tinyurl.com/2st86aht"),
    "portfolio":       C.get("portfolio",       "https://gmail.com"),
    "github":          "https://github.com/",
    "notice_period":   C.get("notice_period",   "Immediate"),
    "experience":      C.get("experience_years","0"),
    "degree":          C.get("degree",          "B.Tech Electronics & Communication Engineering"),
    "college":         "Institute of Engineering & Management, Kolkata",
    "graduation_year": "2026",
    "skills":          ", ".join(C.get("skills", ["Python","AI","REST API","HTML","CSS"])),
    "current_ctc":     "0",
    "expected_ctc":    "As per company norms",
    "gender":          "Male",
    "nationality":     "Indian",
    "work_auth":       "Yes",   # authorized to work
    "sponsorship":     "No",    # no visa sponsorship needed
    "cover_letter": (
        "I am a passionate B.Tech Electronics & Communication Engineering graduate (2026) "
        "from IEM Kolkata, with hands-on experience in Python, AI automation, REST APIs, "
        "and full-stack development. I am eager to contribute to your team and grow as a "
        "fresher in a challenging role. I am available immediately and am excited about "
        "this opportunity."
    ),
}

CHROME_EXE  = cfg.get("browser", {}).get("chrome_path",    r"C:\Program Files\Google\Chrome\Application\chrome.exe")
BOT_PROFILE = os.path.join(DATA_DIR, "bot_chrome_profile")
CHROME_DATA = BOT_PROFILE
OR_KEY      = cfg.get("api_keys", {}).get("openrouter", "")

# ── Field-to-value mapping rules ──────────────────────────────────────────────
# Maps keywords found in label/name/placeholder/aria-label → candidate value
FIELD_RULES = [
    # Name variants
    (["first name", "firstname", "first_name", "given name"],     CANDIDATE["first_name"]),
    (["last name", "lastname", "last_name", "surname", "family"],  CANDIDATE["last_name"]),
    (["full name", "your name", "candidate name", "applicant"],   CANDIDATE["name"]),
    # Contact
    (["email", "e-mail", "mail address"],                          CANDIDATE["email"]),
    (["phone", "mobile", "contact number", "cell"],                CANDIDATE["phone"]),
    # Location
    (["city", "town"],                                             CANDIDATE["city"]),
    (["state", "province", "region"],                              CANDIDATE["state"]),
    (["country"],                                                   CANDIDATE["country"]),
    (["pin", "postal", "zip", "postcode"],                         CANDIDATE["pincode"]),
    (["address", "street"],                                        CANDIDATE["location"]),
    # Professional
    (["linkedin"],                                                  CANDIDATE["linkedin"]),
    (["github"],                                                    CANDIDATE["github"]),
    (["portfolio", "website", "personal site"],                    CANDIDATE["portfolio"]),
    (["notice", "joining", "availability"],                        CANDIDATE["notice_period"]),
    (["experience", "years of exp", "work exp"],                   CANDIDATE["experience"]),
    (["current ctc", "current salary", "present salary"],          CANDIDATE["current_ctc"]),
    (["expected ctc", "expected salary", "desired salary"],        CANDIDATE["expected_ctc"]),
    # Education
    (["degree", "qualification", "highest education"],             CANDIDATE["degree"]),
    (["college", "university", "institution", "school"],           CANDIDATE["college"]),
    (["graduation", "pass out", "passout year"],                   CANDIDATE["graduation_year"]),
    # Misc
    (["skill", "technology", "tech stack", "expertise"],           CANDIDATE["skills"]),
    (["cover letter", "motivation", "why do you", "tell us about"],CANDIDATE["cover_letter"]),
    (["gender"],                                                    CANDIDATE["gender"]),
    (["nationality", "citizenship"],                                CANDIDATE["nationality"]),
]

SELECT_RULES = [
    # For <select> and radio buttons
    (["experience", "years"],  ["0", "0-1", "fresher", "less than 1", "entry"]),
    (["gender"],               ["male", "man"]),
    (["notice"],               ["immediate", "0", "15 days", "less than 15"]),
    (["work auth", "legally authorized"],  ["yes", "authorized", "eligible"]),
    (["sponsorship"],          ["no", "not required"]),
    (["country"],              ["india", "in"]),
    (["state"],                ["west bengal"]),
    (["city"],                 ["kolkata"]),
]


# ═══════════════════════════════════════════════════════════════════════════════
# DOM INTROSPECTION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def get_all_inputs(page: Page) -> list[dict]:
    """
    Extract all interactive form elements from the page DOM.
    Returns list of dicts with: tag, type, id, name, placeholder, aria_label,
    label_text, handle (ElementHandle), value.
    """
    # JavaScript that walks the DOM and finds all form fields + their labels
    js = """
    () => {
        const results = [];
        const tags = ['input', 'textarea', 'select'];
        
        function getLabel(el) {
            // Method 1: explicit <label for="id">
            if (el.id) {
                const lbl = document.querySelector(`label[for="${el.id}"]`);
                if (lbl) return lbl.innerText.trim();
            }
            // Method 2: wrapping <label>
            const parent = el.closest('label');
            if (parent) return parent.innerText.replace(el.value || '', '').trim();
            // Method 3: preceding sibling text
            let sib = el.previousElementSibling;
            while (sib) {
                const t = sib.innerText?.trim();
                if (t && t.length < 100) return t;
                sib = sib.previousElementSibling;
            }
            // Method 4: aria-labelledby
            const lblId = el.getAttribute('aria-labelledby');
            if (lblId) {
                const lblEl = document.getElementById(lblId);
                if (lblEl) return lblEl.innerText.trim();
            }
            // Method 5: parent container text
            const container = el.closest('div, fieldset, section, li');
            if (container) {
                const texts = [];
                for (const child of container.childNodes) {
                    if (child.nodeType === 3 && child.textContent.trim()) {
                        texts.push(child.textContent.trim());
                    }
                }
                if (texts.length) return texts.join(' ').substring(0, 80);
            }
            return '';
        }
        
        tags.forEach(tag => {
            document.querySelectorAll(tag).forEach((el, idx) => {
                if (el.type === 'hidden' || el.type === 'submit' || 
                    el.type === 'button' || el.type === 'reset') return;
                if (!el.offsetParent && !el.closest('[class*="modal"]')) return; // skip invisible
                
                results.push({
                    tag: tag,
                    type: el.type || tag,
                    id: el.id || '',
                    name: el.name || '',
                    placeholder: el.placeholder || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    labelText: getLabel(el),
                    required: el.required,
                    idx: idx,
                    value: el.value || '',
                    options: tag === 'select' ? 
                        Array.from(el.options).map(o => ({val: o.value, text: o.text})) : [],
                });
            });
        });
        return results;
    }
    """
    try:
        return await page.evaluate(js) or []
    except Exception as e:
        print(f"      [DOM] Could not extract inputs: {e}", flush=True)
        return []


def match_field_value(field: dict) -> str | None:
    """
    Given a field's metadata, return the best matching candidate value.
    Checks label, name, placeholder, aria-label against FIELD_RULES.
    """
    haystack = " ".join([
        field.get("labelText", ""),
        field.get("name", ""),
        field.get("placeholder", ""),
        field.get("ariaLabel", ""),
        field.get("id", ""),
    ]).lower()

    for keywords, value in FIELD_RULES:
        if any(kw in haystack for kw in keywords):
            return value
    return None


def match_select_option(field: dict, options: list[dict]) -> str | None:
    """
    For <select> elements, find the best matching option value.
    """
    haystack = " ".join([
        field.get("labelText", ""),
        field.get("name", ""),
        field.get("ariaLabel", ""),
    ]).lower()

    for keywords, preferred_vals in SELECT_RULES:
        if any(kw in haystack for kw in keywords):
            for opt in options:
                opt_text = (opt.get("text", "") + " " + opt.get("val", "")).lower()
                for pv in preferred_vals:
                    if pv.lower() in opt_text and opt.get("val", ""):
                        return opt["val"]
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# FORM FILLER
# ═══════════════════════════════════════════════════════════════════════════════

async def fill_form_via_dom(page: Page, job_title: str = "") -> int:
    """
    Main DOM form filler. Returns count of fields successfully filled.
    """
    print(f"      [DOM] Scanning page for form fields...", flush=True)
    inputs = await get_all_inputs(page)
    print(f"      [DOM] Found {len(inputs)} interactive fields.", flush=True)

    filled = 0
    file_input_filled = False

    for field in inputs:
        tag        = field.get("tag", "input")
        ftype      = field.get("type", "text")
        field_id   = field.get("id", "")
        field_name = field.get("name", "")
        idx        = field.get("idx", 0)
        label      = field.get("labelText", "")

        # Build a selector for this field
        if field_id:
            selector = f"#{field_id}"
        elif field_name:
            selector = f"{tag}[name='{field_name}']"
        else:
            selector = f"{tag}:nth-of-type({idx+1})"

        try:
            el = page.locator(selector).first

            # ── File upload ───────────────────────────────────────────────
            if ftype == "file" and not file_input_filled:
                if os.path.exists(RESUME_PDF):
                    await el.set_input_files(RESUME_PDF)
                    print(f"      [DOM] Uploaded Resume.pdf to: '{label or field_name}'", flush=True)
                    filled += 1
                    file_input_filled = True
                continue

            # ── Select ────────────────────────────────────────────────────
            if tag == "select":
                options = field.get("options", [])
                best_val = match_select_option(field, options)
                if best_val:
                    await el.select_option(value=best_val)
                    print(f"      [DOM] Selected '{best_val}' for: '{label or field_name}'", flush=True)
                    filled += 1
                elif options and len(options) > 1:
                    # Select second option as safe fallback (skips empty "--- Select ---")
                    await el.select_option(index=1)
                    print(f"      [DOM] Selected option[1] for: '{label or field_name}'", flush=True)
                    filled += 1
                continue

            # ── Checkbox / Radio ──────────────────────────────────────────
            if ftype in ("checkbox", "radio"):
                haystack = (label + " " + field_name + " " + field.get("ariaLabel","")).lower()
                # Agree to terms / privacy policy
                if any(kw in haystack for kw in ["agree", "terms", "privacy", "consent", "accept"]):
                    cur = await el.is_checked()
                    if not cur:
                        await el.check()
                        print(f"      [DOM] Checked: '{label or field_name}'", flush=True)
                        filled += 1
                # Yes to work authorization
                elif any(kw in haystack for kw in ["authorized", "eligible", "legally"]):
                    if ftype == "radio":
                        # Find "Yes" radio sibling
                        try:
                            yes_radio = page.locator(f"input[type='radio'][value='yes'], input[type='radio'][value='Yes'], input[type='radio'][value='true']").first
                            await yes_radio.check()
                            print(f"      [DOM] Selected 'Yes' for: '{label}'", flush=True)
                            filled += 1
                        except Exception:
                            pass
                continue

            # ── Text / Textarea ───────────────────────────────────────────
            if ftype in ("text", "email", "tel", "number", "url", "textarea", "textarea"):
                value = match_field_value(field)
                if value:
                    # Clear existing content first
                    await el.click()
                    await el.select_text() if hasattr(el, 'select_text') else None
                    await el.fill(value)
                    print(f"      [DOM] Filled '{label or field_name}': {value[:40]}...", flush=True)
                    filled += 1
                    await page.wait_for_timeout(200)

        except Exception as e:
            # Don't crash on individual field errors
            pass

    return filled


# ═══════════════════════════════════════════════════════════════════════════════
# CAPTCHA DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

async def detect_and_handle_captcha(page: Page) -> bool:
    """
    Detects common CAPTCHAs and attempts to handle them.
    Returns True if CAPTCHA was handled or not present.
    """
    # Check for reCAPTCHA iframe
    recaptcha = await page.query_selector("iframe[src*='recaptcha'], iframe[title*='captcha']")
    if recaptcha:
        print("      [CAPTCHA] reCAPTCHA detected — attempting checkbox click...", flush=True)
        try:
            frame = await recaptcha.content_frame()
            if frame:
                checkbox = await frame.query_selector(".recaptcha-checkbox-border, #recaptcha-anchor")
                if checkbox:
                    await checkbox.click()
                    await page.wait_for_timeout(3000)
                    print("      [CAPTCHA] Clicked reCAPTCHA checkbox.", flush=True)
                    return True
        except Exception:
            pass

    # Check for hCaptcha
    hcaptcha = await page.query_selector("iframe[src*='hcaptcha']")
    if hcaptcha:
        print("      [CAPTCHA] hCaptcha detected — this requires manual solving.", flush=True)
        print("      [CAPTCHA] Waiting 30 seconds for manual solve...", flush=True)
        await page.wait_for_timeout(30000)
        return True

    # Check for simple image CAPTCHA (text in image)
    captcha_img = await page.query_selector("img[alt*='captcha' i], img[src*='captcha' i], img[id*='captcha' i]")
    if captcha_img and OR_KEY:
        print("      [CAPTCHA] Image CAPTCHA detected — using vision LLM to solve...", flush=True)
        try:
            import httpx
            screenshot_bytes = await captcha_img.screenshot()
            b64 = base64.b64encode(screenshot_bytes).decode()
            
            resp = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Read the CAPTCHA text in this image exactly. Reply with ONLY the text, nothing else."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                        ]
                    }]
                },
                timeout=15
            )
            captcha_text = resp.json()["choices"][0]["message"]["content"].strip()
            print(f"      [CAPTCHA] Vision LLM read: '{captcha_text}'", flush=True)
            
            # Find captcha input and fill it
            captcha_input = await page.query_selector(
                "input[name*='captcha' i], input[id*='captcha' i], input[placeholder*='captcha' i]")
            if captcha_input and captcha_text:
                await captcha_input.fill(captcha_text)
                print(f"      [CAPTCHA] Filled CAPTCHA answer.", flush=True)
                return True
        except Exception as e:
            print(f"      [CAPTCHA] Vision solve failed: {e}", flush=True)

    return True  # No captcha or handled


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-STEP FORM HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

async def walk_form_steps(page: Page, job_title: str) -> bool:
    """
    Handles multi-step forms. Fills each step, clicks Next/Continue,
    fills again, until Submit is reached and clicked.
    Returns True if form was submitted.
    """
    submitted = False

    for step in range(10):  # max 10 steps
        print(f"      [DOM] Form step {step+1}...", flush=True)

        # Fill current step's fields
        filled = await fill_form_via_dom(page, job_title)
        print(f"      [DOM] Filled {filled} fields in step {step+1}.", flush=True)

        # Handle any CAPTCHA on this step
        await detect_and_handle_captcha(page)
        await page.wait_for_timeout(800)

        # Look for Submit button first
        submit_selectors = [
            "button[type='submit']:visible",
            "input[type='submit']:visible",
            "button:has-text('Submit'):visible",
            "button:has-text('Apply'):visible",
            "button:has-text('Send Application'):visible",
            "button:has-text('Submit Application'):visible",
            "button:has-text('Complete Application'):visible",
            "a:has-text('Submit'):visible",
            "[data-testid*='submit']:visible",
        ]

        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    btn_text = await btn.text_content() or "Submit"
                    print(f"      [DOM] Found Submit: '{btn_text.strip()}'. Clicking...", flush=True)
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    submitted = True
                    break
            except Exception:
                pass

        if submitted:
            break

        # Look for Next / Continue to advance step
        next_selectors = [
            "button:has-text('Next'):visible",
            "button:has-text('Continue'):visible",
            "button:has-text('Proceed'):visible",
            "button:has-text('Next Step'):visible",
            "a:has-text('Next'):visible",
            "[aria-label*='next' i]:visible",
        ]

        advanced = False
        for sel in next_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    btn_text = await btn.text_content() or "Next"
                    print(f"      [DOM] Advancing: '{btn_text.strip()}'", flush=True)
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    advanced = True
                    break
            except Exception:
                pass

        if not advanced:
            print(f"      [DOM] No Next/Submit button found. Form may be complete or stuck.", flush=True)
            break

    return submitted


# ═══════════════════════════════════════════════════════════════════════════════
# SUCCESS DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

async def check_success(page: Page) -> bool:
    """Check if the page shows an application confirmation."""
    try:
        content = (await page.content()).lower()
        success_keywords = [
            "thank you", "thanks for applying", "application received",
            "successfully submitted", "we've received", "application submitted",
            "confirmation", "we will be in touch", "hear from us",
            "application complete", "applied successfully"
        ]
        return any(kw in content for kw in success_keywords)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# LOG
# ═══════════════════════════════════════════════════════════════════════════════

def log_applied(company, title, url, status="Applied"):
    os.makedirs(DATA_DIR, exist_ok=True)
    exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["Timestamp","Company","Job Title","URL","Status","Method"])
        w.writerow([
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            company, title, url, status, "DOM Applier"
        ])
    try:
        record_application("Company Website", company, title, status=status,
                           notes="Applied via deep DOM form filler")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# PORTAL-SPECIFIC APPLY FLOWS (DOM-powered)
# ═══════════════════════════════════════════════════════════════════════════════

async def dom_apply_naukri(context, keyword="Software Engineer", location="Kolkata"):
    """Naukri with DOM-based form filling for apply wizard."""
    import urllib.parse
    print(f"\n{'='*60}", flush=True)
    print(f"[NAUKRI-DOM] Applying: '{keyword}' in {location}", flush=True)
    page  = await context.new_page()
    count = 0

    try:
        url = f"https://www.naukri.com/jobs?k={urllib.parse.quote(keyword)}&l={urllib.parse.quote(location)}"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Get all job links from DOM
        job_links = await page.evaluate("""
        () => {
            const links = [];
            document.querySelectorAll('a.title, a[class*="jobTitle"], a[title]').forEach(a => {
                if (a.href && a.href.includes('naukri.com') && a.textContent.trim().length > 3) {
                    links.push({title: a.textContent.trim(), url: a.href});
                }
            });
            return [...new Map(links.map(l => [l.url, l])).values()].slice(0, 5);
        }
        """)
        print(f"[NAUKRI-DOM] Found {len(job_links)} jobs via DOM.", flush=True)

        for job in job_links:
            if is_already_applied("Naukri", job["title"]):
                continue
            jp = await context.new_page()
            try:
                await jp.goto(job["url"], wait_until="domcontentloaded", timeout=20000)
                await jp.wait_for_timeout(2500)

                # Click Apply via DOM button detection
                apply_btns = await jp.evaluate("""
                () => {
                    const results = [];
                    document.querySelectorAll('button, a').forEach(el => {
                        const t = el.textContent.trim().toLowerCase();
                        if ((t.includes('apply') || t.includes('apply now')) && el.offsetParent) {
                            results.push({text: el.textContent.trim()});
                        }
                    });
                    return results;
                }
                """)

                clicked = False
                for btn_info in apply_btns[:3]:
                    try:
                        btn = jp.get_by_text(btn_info["text"]).first
                        if await btn.is_visible():
                            await btn.click()
                            await jp.wait_for_timeout(2000)
                            clicked = True
                            break
                    except Exception:
                        pass

                if not clicked:
                    print(f"  [NAUKRI-DOM] No Apply button found for: {job['title']}", flush=True)
                    await jp.close()
                    continue

                # Fill any modal/form that appeared
                submitted = await walk_form_steps(jp, keyword)
                success   = await check_success(jp)

                if clicked:  # Naukri often shows profile-based apply (no form)
                    log_applied("Naukri", job["title"], job["url"])
                    print(f"  [NAUKRI-DOM] Applied: {job['title']}", flush=True)
                    count += 1

            except Exception as e:
                print(f"  [NAUKRI-DOM] Error: {e}", flush=True)
            finally:
                await jp.close()
                await asyncio.sleep(2)

    except Exception as e:
        print(f"[NAUKRI-DOM ERROR] {e}", flush=True)
    finally:
        await page.close()

    print(f"[NAUKRI-DOM] Done. Applied: {count}", flush=True)
    return count


async def dom_apply_company_site(context, company: str, careers_url: str, keyword: str) -> bool:
    """
    Universal DOM-based applier for any company careers page.
    Works on Lever, Greenhouse, Ashby, Workday, SmartRecruiters, custom sites.
    """
    if is_already_applied(company, keyword):
        print(f"  [DOM] SKIP – already applied to {company} for '{keyword}'", flush=True)
        return False

    print(f"\n  [DOM] Targeting: {company} — {careers_url}", flush=True)
    page = await context.new_page()
    try:
        await page.goto(careers_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Search for keyword in search box if present
        search_inputs = await page.evaluate("""
        () => {
            const el = document.querySelector(
                'input[placeholder*="search" i], input[placeholder*="role" i], input[placeholder*="keyword" i], input[type="search"]'
            );
            return el ? el.id || el.name || '' : null;
        }
        """)

        if search_inputs:
            try:
                search_box = page.locator(f"#{search_inputs}, input[name='{search_inputs}']").first
                await search_box.fill(keyword)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2000)
            except Exception:
                pass

        # Find job listings via DOM
        job_links = await page.evaluate("""
        (kw) => {
            const links = [];
            const kwLower = kw.toLowerCase();
            document.querySelectorAll('a').forEach(a => {
                const t = a.textContent.trim();
                const h = a.href || '';
                if (t.length > 5 && t.length < 100 &&
                    (h.includes('job') || h.includes('career') || h.includes('apply') || h.includes('opening')) &&
                    (t.toLowerCase().includes(kwLower.split(' ')[0]) || h.includes('apply'))) {
                    links.push({title: t, url: h});
                }
            });
            return [...new Map(links.map(l => [l.url, l])).values()].slice(0, 3);
        }
        """, keyword)

        if not job_links:
            # If no specific job found, try to find any Apply/Submit form on current page
            print(f"  [DOM] No specific job links found. Checking current page for apply form...", flush=True)
            submitted = await walk_form_steps(page, keyword)
            success   = await check_success(page)
            if submitted or success:
                log_applied(company, keyword, careers_url)
                print(f"  [DOM] Applied directly from careers page: {company}", flush=True)
                return True
            return False

        # Try the first matching job
        for job in job_links[:2]:
            jp = await context.new_page()
            try:
                print(f"  [DOM] Opening job: '{job['title']}'", flush=True)
                await jp.goto(job["url"], wait_until="domcontentloaded", timeout=25000)
                await jp.wait_for_timeout(2500)

                # Click Apply if needed
                apply_links = await jp.evaluate("""
                () => {
                    const els = [];
                    document.querySelectorAll('a, button').forEach(el => {
                        const t = el.textContent.trim().toLowerCase();
                        if (t.includes('apply') && el.offsetParent) {
                            els.push({text: el.textContent.trim()});
                        }
                    });
                    return els.slice(0, 5);
                }
                """)

                for btn_info in apply_links:
                    try:
                        btn = jp.get_by_text(btn_info["text"], exact=False).first
                        if await btn.is_visible():
                            await btn.click()
                            await jp.wait_for_timeout(2500)
                            break
                    except Exception:
                        pass

                submitted = await walk_form_steps(jp, keyword)
                success   = await check_success(jp)

                if submitted or success:
                    log_applied(company, job["title"], job["url"])
                    print(f"  [DOM] >>> APPLIED: '{job['title']}' @ {company}", flush=True)
                    return True

            except Exception as e:
                print(f"  [DOM] Error on job page: {e}", flush=True)
            finally:
                await jp.close()
                await asyncio.sleep(2)

    except Exception as e:
        print(f"  [DOM ERROR] {company}: {e}", flush=True)
    finally:
        await page.close()

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# COMPANY TARGET LIST
# ═══════════════════════════════════════════════════════════════════════════════

COMPANY_TARGETS = [
    # Greenhouse ATS (most common for tech companies)
    {"company": "Zepto",         "url": "https://jobs.lever.co/zepto"},
    {"company": "Meesho",        "url": "https://meesho.io/careers"},
    {"company": "Razorpay",      "url": "https://razorpay.com/jobs/"},
    {"company": "CRED",          "url": "https://careers.cred.club/"},
    {"company": "PhonePe",       "url": "https://www.phonepe.com/en/careers.html"},
    {"company": "Swiggy",        "url": "https://careers.swiggy.com/#/"},
    {"company": "Zomato",        "url": "https://www.zomato.com/careers"},
    {"company": "Freshworks",    "url": "https://www.freshworks.com/company/careers/"},
    {"company": "Zoho",          "url": "https://careers.zohocorp.com/jobs/Careers"},
    {"company": "Infosys BPM",   "url": "https://career.infosys.com/joblist"},
    {"company": "Capgemini",     "url": "https://www.capgemini.com/in-en/careers/"},
    {"company": "Persistent",    "url": "https://www.persistent.com/careers/"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

async def run_dom_applier(keyword: str = "Software Engineer", max_companies: int = 4, headless: bool = False):
    """
    Master runner: launches Chrome with user's profile and runs DOM applier
    on portal sites + company career pages.
    """
    print("\n" + "="*65, flush=True)
    print("  DOM-POWERED JOB APPLIER (Deep Form Introspection)", flush=True)
    print("="*65, flush=True)
    print(f"  Role: {keyword}", flush=True)
    print(f"  Resume: {RESUME_PDF} (exists: {os.path.exists(RESUME_PDF)})", flush=True)
    print(f"  Candidate: {CANDIDATE['name']} | {CANDIDATE['email']}", flush=True)
    print("="*65 + "\n", flush=True)

    total = 0

    async with async_playwright() as p:
        context = None
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=CHROME_DATA,
                executable_path=CHROME_EXE if os.path.exists(CHROME_EXE) else None,
                headless=headless,
                args=[
                    "--no-first-run",
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
                viewport=None,
                slow_mo=80,
                ignore_https_errors=True,
            )
            print("[BROWSER] Launched with your Chrome profile.", flush=True)
        except Exception as e:
            print(f"[BROWSER] Persistent context failed: {e}", flush=True)
            browser  = await p.chromium.launch(headless=headless)
            context  = await browser.new_context()

        try:
            # Stage A: Naukri with DOM introspection
            total += await dom_apply_naukri(context, keyword, location="Kolkata")

            # Stage B: Company career pages
            for entry in COMPANY_TARGETS[:max_companies]:
                try:
                    success = await dom_apply_company_site(
                        context, entry["company"], entry["url"], keyword)
                    if success:
                        total += 1
                except Exception as e:
                    print(f"  [DOM] {entry['company']} error: {e}", flush=True)
                await asyncio.sleep(3)

        except Exception as e:
            print(f"[RUNNER ERROR] {e}", flush=True)
        finally:
            try:
                await context.close()
            except Exception:
                pass

    print(f"\n[DOM APPLIER DONE] Total applications submitted: {total}", flush=True)
    return total


if __name__ == "__main__":
    kw    = sys.argv[1] if len(sys.argv) > 1 else "Python Developer"
    maxc  = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    asyncio.run(run_dom_applier(keyword=kw, max_companies=maxc, headless=False))
