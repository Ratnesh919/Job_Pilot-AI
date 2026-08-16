"""
ApplyBot Pro — AI-Powered Company Website Auto-Applier
=======================================================
Uses browser-use (AI browser agent) to intelligently:
  - Navigate to any company careers/jobs page
  - Read and understand any form layout
  - Fill ALL fields (name, email, phone, address, experience, skills)
  - Upload Resume.pdf automatically
  - Handle multi-step forms & wizards
  - Attempt to solve simple image CAPTCHAs via vision
  - Submit and confirm application

Requires Python 3.11+ (browser-use needs datetime.UTC)
Run via: py -3.11 backend/ai_company_applier.py "Software Engineer"
"""

import os
import sys
import asyncio
import csv
import json
from datetime import datetime, timezone

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
except Exception:
    def record_application(*a, **kw): pass
    def is_already_applied(*a, **kw): return False

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH     = os.path.join(APP_ROOT, "config.json")
DATA_DIR        = os.path.join(APP_ROOT, "data")
LOG_FILE        = os.path.join(DATA_DIR, "ai_company_applications.csv")
RESUME_PDF      = os.path.join(APP_ROOT, "Resume.pdf")

# Fallback to cv root
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

# Candidate info
C = cfg.get("candidate", {})
NAME            = C.get("name", "Ratnesh Kumar Singh")
EMAIL           = C.get("email", "kumarsinghratnesh3@gmail.com")
PHONE           = C.get("phone", "+91 70049 37129")
LOCATION        = C.get("location", "Kolkata, West Bengal, India")
LINKEDIN        = C.get("linkedin", "https://tinyurl.com/2st86aht")
PORTFOLIO       = C.get("portfolio", "https://gmail.com")
NOTICE_PERIOD   = C.get("notice_period", "Immediate / 0 Days")
EXP_YEARS       = C.get("experience_years", "0-1")
DEGREE          = C.get("degree", "B.Tech in Electronics & Communication Engineering (2026)")
SKILLS          = ", ".join(C.get("skills", ["Python", "AI", "REST API"]))
OPENROUTER_KEY  = cfg.get("api_keys", {}).get("openrouter", "")
CHROME_EXE      = cfg.get("browser", {}).get("chrome_path", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
CHROME_DATA     = cfg.get("browser", {}).get("user_data_path", r"C:\Users\akssi\AppData\Local\Google\Chrome\User Data")

# ── Target companies with careers pages ───────────────────────────────────────
# These are real company careers portals — the AI agent will navigate each one
COMPANY_CAREER_PAGES = [
    # Indian tech companies
    {"company": "Tata Consultancy Services", "url": "https://www.tcs.com/careers/apply-now"},
    {"company": "Infosys",                   "url": "https://career.infosys.com/joblist"},
    {"company": "Wipro",                     "url": "https://careers.wipro.com/careers-home/jobs"},
    {"company": "HCL Technologies",          "url": "https://www.hcltech.com/careers/search-jobs"},
    {"company": "Tech Mahindra",             "url": "https://careers.techmahindra.com/search/?q=&q2=&alertId=&locationsearch="},
    {"company": "Cognizant",                 "url": "https://careers.cognizant.com/global/en/search-results"},
    {"company": "Mphasis",                   "url": "https://jobs.mphasis.com/search-jobs"},
    {"company": "Hexaware",                  "url": "https://hexaware.com/careers/"},
    # Global ATS portals
    {"company": "Accenture",                 "url": "https://www.accenture.com/in-en/careers/explore-your-fit"},
    {"company": "IBM India",                 "url": "https://www.ibm.com/in-en/employment/"},
    # Startup-friendly ATS
    {"company": "AngelList Network",         "url": "https://wellfound.com/jobs"},
    {"company": "Internshala",               "url": "https://internshala.com/jobs/"},
]

# ── Logging helper ────────────────────────────────────────────────────────────
def log_company_application(company: str, job_title: str, url: str, status: str = "Applied"):
    os.makedirs(DATA_DIR, exist_ok=True)
    exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["Timestamp", "Company", "Job Title", "URL", "Status", "Method"])
        w.writerow([
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            company, job_title, url, status, "AI-Agent (browser-use)"
        ])
    try:
        record_application("Company Website", company, job_title, status=status,
                           notes="AI browser-use agent applied via company careers portal")
    except Exception:
        pass


# ── Core AI Application Agent ─────────────────────────────────────────────────
async def ai_apply_to_company(company: str, careers_url: str, job_keyword: str) -> bool:
    """
    Uses browser-use AI agent to navigate to a company careers page,
    search for matching jobs, open the application form, fill ALL fields,
    upload resume, and submit.
    Returns True if application was submitted successfully.
    """
    try:
        # browser-use must be imported inside the function because it needs
        # Python 3.11+ and may not be in the main python path
        from browser_use import Agent, BrowserSession, BrowserProfile
        from browser_use.llm.openai.chat import ChatOpenAI
    except ImportError as e:
        print(f"  [AI-AGENT] browser-use not available: {e}", flush=True)
        print(f"  [AI-AGENT] Install with: py -3.11 -m pip install browser-use", flush=True)
        return False

    if not OPENROUTER_KEY:
        print("  [AI-AGENT] No OpenRouter API key in config.json", flush=True)
        return False

    if not os.path.exists(RESUME_PDF):
        print(f"  [AI-AGENT] Resume not found at: {RESUME_PDF}", flush=True)
        return False

    print(f"\n  [AI-AGENT] Starting AI browser agent for: {company}", flush=True)
    print(f"  [AI-AGENT] Careers URL: {careers_url}", flush=True)

    # Use OpenRouter with a capable model via OpenAI-compatible API
    llm = ChatOpenAI(
        model="openai/gpt-4o-mini",   # fast + cheap via OpenRouter
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
    )

    # Build detailed task prompt with all candidate data
    task = f"""
You are a job application AI assistant. Your job is to apply for a position at {company}.

CANDIDATE INFORMATION (use exactly as written):
- Full Name: {NAME}
- Email: {EMAIL}
- Phone: {PHONE}
- Location / City: {LOCATION}
- LinkedIn: {LINKEDIN}
- Portfolio: {PORTFOLIO}
- Notice Period: {NOTICE_PERIOD}
- Experience: {EXP_YEARS} years (Fresher)
- Education: {DEGREE}
- Key Skills: {SKILLS}
- Current CTC: 0 (Fresher)
- Expected CTC: As per company norms
- Gender: Male
- Nationality: Indian
- Work Authorization: Indian citizen, no visa sponsorship needed

TASK STEPS:
1. Navigate to: {careers_url}
2. Search for jobs matching "{job_keyword}" or similar role
3. Click on the most relevant fresher/entry-level job listing
4. Click the Apply / Apply Now / Easy Apply button
5. Fill out ALL form fields using the candidate information above
6. For resume upload fields: upload the file at path: {RESUME_PDF}
7. For cover letter / motivation fields, write 2-3 sentences about passion for {job_keyword} and desire to contribute
8. For questions you don't know the answer to, answer honestly based on the candidate profile
9. For CAPTCHA: try to solve image-based CAPTCHAs by reading the text/images carefully
10. Click Submit / Send Application
11. Confirm the application was submitted (look for "Thank you", "Application received", "Successfully submitted")

IMPORTANT RULES:
- If a field is required and you can't fill it, make a reasonable guess
- Do NOT skip the resume upload step
- Do NOT close any popups — fill them if they are part of the form
- If there is no matching job, go back to step 2 and try a broader search term
- When done, confirm submission status

Submit the application and report: "SUBMITTED" or "FAILED" with reason.
"""

    try:
        # Use user's existing Chrome profile so they're already logged in
        profile = BrowserProfile(
            executable_path=CHROME_EXE if os.path.exists(CHROME_EXE) else None,
            user_data_dir=CHROME_DATA,
            headless=False,    # Must be visible — portals block headless
            args=[
                "--no-first-run",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        session = BrowserSession(browser_profile=profile)

        agent = Agent(
            task=task,
            llm=llm,
            browser=session,
            available_file_paths=[RESUME_PDF],
            max_actions_per_step=10,
            max_failures=3,
        )

        history = await agent.run(max_steps=40)
        result  = history.final_result() or ""

        print(f"  [AI-AGENT] Result: {result[:200]}", flush=True)

        # Check if actually submitted
        submitted = any(kw in result.upper() for kw in [
            "SUBMITTED", "THANK YOU", "APPLICATION RECEIVED",
            "SUCCESSFULLY", "COMPLETE", "CONFIRMATION"
        ])

        if submitted:
            log_company_application(company, job_keyword, careers_url, "Applied")
            print(f"  [AI-AGENT] >>> APPLIED to {company}!", flush=True)
            return True
        else:
            print(f"  [AI-AGENT] Application not confirmed for {company}.", flush=True)
            return False

    except Exception as e:
        print(f"  [AI-AGENT] Error: {e}", flush=True)
        return False


# ── Batch runner ──────────────────────────────────────────────────────────────
async def run_ai_company_applier(keyword: str = "Software Engineer", max_companies: int = 3):
    """
    Runs the AI browser agent on multiple company career portals.
    Applies to max_companies per run to avoid being too aggressive.
    """
    print("\n" + "="*65, flush=True)
    print("  AI COMPANY WEBSITE APPLIER (browser-use AI Agent)", flush=True)
    print("="*65, flush=True)
    print(f"  Role: {keyword}", flush=True)
    print(f"  Resume: {RESUME_PDF}", flush=True)
    print(f"  Candidate: {NAME} | {EMAIL}", flush=True)
    print("="*65 + "\n", flush=True)

    if not os.path.exists(RESUME_PDF):
        print(f"[ERROR] Resume PDF not found at: {RESUME_PDF}", flush=True)
        print("Please make sure Resume.pdf exists in your cv folder.", flush=True)
        return 0

    applied_count = 0

    for i, entry in enumerate(COMPANY_CAREER_PAGES[:max_companies]):
        company = entry["company"]
        url     = entry["url"]

        if is_already_applied(company, keyword):
            print(f"[{i+1}] SKIP — already applied to {company} for '{keyword}'", flush=True)
            continue

        print(f"[{i+1}/{max_companies}] Targeting: {company}", flush=True)
        try:
            success = await ai_apply_to_company(company, url, keyword)
            if success:
                applied_count += 1
        except Exception as e:
            print(f"  [ERROR] {company}: {e}", flush=True)

        # Pause between companies to appear human
        await asyncio.sleep(5)

    print(f"\n[DONE] AI Company Applier finished. Applied: {applied_count}/{max_companies}", flush=True)
    return applied_count


if __name__ == "__main__":
    kw  = sys.argv[1] if len(sys.argv) > 1 else "Python Developer"
    max_c = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    asyncio.run(run_ai_company_applier(keyword=kw, max_companies=max_c))
