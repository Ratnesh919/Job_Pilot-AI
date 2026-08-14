import os
import sys
import re
import csv
import urllib.request
import urllib.parse
import json
from datetime import datetime

# Force UTF-8 encoding on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from email_sender import SENDER_EMAIL, APP_PASSWORD
    from db_helper import record_application, is_already_applied
except ImportError:
    from .email_sender import SENDER_EMAIL, APP_PASSWORD
    from .db_helper import record_application, is_already_applied

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(BACKEND_DIR)
CONFIG_PATH = os.path.join(APP_ROOT, "config.json")
DATA_DIR = os.path.join(APP_ROOT, "data")
LLM_LOG_FILE = os.path.join(DATA_DIR, "llm_applications_log.csv")
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
EXP_LEVEL = config.get("experience_level", "fresher")

def extract_api_keys():
    cfg = load_config()
    keys = {
        "openrouter": cfg.get("api_keys", {}).get("openrouter") or os.getenv("OPENROUTER_API_KEY", ""),
        "nvidia": cfg.get("api_keys", {}).get("nvidia") or os.getenv("NVIDIA_API_KEY", ""),
        "gemini": cfg.get("api_keys", {}).get("gemini") or os.getenv("GEMINI_API_KEY", "")
    }
    return keys

# Verified direct hiring inboxes for tech companies
VERIFIED_TECH_HIRING_TARGETS = [
    {"company": "Razorpay", "role": "Software Development Engineer", "email": "careers@razorpay.com"},
    {"company": "Postman", "role": "Frontend Developer", "email": "careers@postman.com"},
    {"company": "BrowserStack", "role": "Software Engineer", "email": "careers@browserstack.com"},
    {"company": "Hasura", "role": "Full Stack Developer", "email": "jobs@hasura.io"},
    {"company": "InMobi", "role": "AI Engineer", "email": "talent@inmobi.com"}
]

# Blacklist known closed group emails or non-existent inboxes
BOUNCE_BLACKLIST = ["hiring@juspay.in", "careers@swiggy.in", "careers@swiggy.com", "example.com", "test.com"]

def search_unlisted_jobs_ddg(query_keyword="Software Engineer hiring email"):
    results = []
    try:
        encoded = urllib.parse.quote(query_keyword)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            html = response.read().decode('utf-8', errors='ignore')
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
            blacklist = ['duckduckgo', 'github', 'sentry', 'w3.org', 'png', 'jpg', 'bootstrap', 'schema.org', 'microsoft', 'google.com'] + BOUNCE_BLACKLIST
            valid_emails = list(set([e for e in emails if not any(x in e.lower() for x in blacklist)]))
            for email in valid_emails[:5]:
                domain = email.split('@')[-1].split('.')[0].capitalize()
                results.append({
                    "company": domain,
                    "email": email,
                    "role": query_keyword.split(' ')[0] + " Developer",
                    "snippet": f"Off-campus hiring contact at {domain}"
                })
    except Exception:
        pass
        
    return results

def call_low_latency_llm_cover_letter(company_name, role_title):
    keys = extract_api_keys()
    cfg = load_config()
    cand = cfg.get("candidate", {})

    cand_name = cand.get("name", "Job Candidate")
    cand_degree = cand.get("degree", "Computer Science / Engineering Graduate")
    cand_skills = ", ".join(cand.get("skills", ["Python", "JavaScript", "REST APIs", "SQL", "Git"]))
    cand_portfolio = cand.get("portfolio", "")
    cand_linkedin = cand.get("linkedin", "")
    cand_github = cand.get("github", "")

    exp_desc = f"{cand_degree} - Entry Level" if EXP_LEVEL == "fresher" else "Software Engineer with 1-3 years experience"

    prompt = f"""Write a professional, compelling 3-paragraph cold job application email for candidate {cand_name} applying for the role of {role_title} at {company_name}.

Candidate Highlights:
- Name: {cand_name}
- Background: {exp_desc}
- Key Skills: {cand_skills}
- Portfolio: {cand_portfolio}
- LinkedIn: {cand_linkedin}
- GitHub: {cand_github}

Make it engaging, professional, tailored to the company, and highlight readiness to add immediate value. Return ONLY the plain text email body.
"""
    if keys["openrouter"]:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {keys['openrouter']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "meta-llama/llama-3.3-70b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.2
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data['choices'][0]['message']['content'].strip()
        except Exception:
            pass

    # High quality fallback template
    links_section = ""
    if cand_portfolio: links_section += f"Portfolio: {cand_portfolio}\n"
    if cand_linkedin: links_section += f"LinkedIn: {cand_linkedin}\n"
    if cand_github: links_section += f"GitHub: {cand_github}\n"

    return f"""Dear Hiring Team at {company_name},

I hope this email finds you well.

I am writing to express my enthusiastic interest in the {role_title} position at {company_name}. As an eager {exp_desc} with hands-on experience in modern software development and problem solving, I am excited to bring my technical skills and energy to your engineering team.

Key Highlights & Technical Capabilities:
• Core Technologies: Strong proficiency in {cand_skills}.
• Hands-on Projects: Practical experience architecting scalable applications and collaborating via modern development workflows.
• Rapid Problem Solving: Quick learner capable of adapting to complex codebases and delivering reliable results.

I have attached my resume for your review and would welcome the opportunity to discuss how my background aligns with your upcoming projects.

{links_section}
Warm regards,

{cand_name}
Email: {cand.get('email', '')}
Phone: {cand.get('phone', '')}
Location: {cand.get('location', '')}
"""

def run_llm_email_job_search_and_apply(api_key=None, provider="openrouter"):
    print(f"\n--- LLM UNLISTED JOB FINDER & DIRECT EMAIL APPLICATION ENGINE [{EXP_LEVEL.upper()}] ---", flush=True)
    cfg = load_config()
    resume_path = cfg.get("resume_path", DEFAULT_RESUME)
    if not os.path.isabs(resume_path):
        resume_path = os.path.join(APP_ROOT, resume_path)

    print(f"Attaching Resume PDF: {resume_path}", flush=True)
    if not os.path.exists(resume_path):
        print(f"WARNING: Resume PDF not found at {resume_path}. Please place Resume.pdf in project folder.", flush=True)

    found_jobs = []
    target_loc = cfg.get("primary_location", "Remote")
    print(f"Searching web for verified tech hiring contacts in {target_loc} & Remote...", flush=True)
    for role in ["Software Engineer", "AI Developer"]:
        query = f"careers {role} {EXP_LEVEL} hr email {target_loc} OR Remote"
        jobs = search_unlisted_jobs_ddg(query)
        found_jobs.extend(jobs)
        
    if len(found_jobs) < 3:
        found_jobs.extend(VERIFIED_TECH_HIRING_TARGETS[:3])

    print(f"[FOUND] {len(found_jobs)} candidate recruiter & company contacts.", flush=True)
    
    sender_email = cfg.get("email", {}).get("sender", "")
    app_pass = cfg.get("email", {}).get("app_password", "").replace(" ", "")

    if not sender_email or not app_pass:
        print("[NOTICE] Gmail SMTP not fully configured in Settings. Skipping actual mail dispatch.", flush=True)
        return 0

    dispatched_count = 0
    for idx, j in enumerate(found_jobs[:3]):
        comp = j['company']
        rec_email = j['email']
        role = j['role']
        
        if is_already_applied(comp, role, rec_email):
            print(f"[{idx+1}] [SKIPPED] Already applied to {comp} ({rec_email}) in the last 30 days.", flush=True)
            continue

        if rec_email.lower() == sender_email.lower() or rec_email.lower() in BOUNCE_BLACKLIST:
            continue
        
        print(f"\n[{idx+1}] Generating tailored AI application for {role} at {comp} ({rec_email})...", flush=True)
        custom_body = call_low_latency_llm_cover_letter(comp, role)
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.application import MIMEApplication
        
        msg = MIMEMultipart()
        msg["From"] = f"{cfg.get('candidate', {}).get('name', 'Job Candidate')} <{sender_email}>"
        msg["To"] = rec_email
        msg["Subject"] = f"Application for {role} - {cfg.get('candidate', {}).get('name', 'Job Candidate')}"
        msg.attach(MIMEText(custom_body, "plain"))
        
        try:
            if os.path.exists(resume_path):
                with open(resume_path, "rb") as f:
                    pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                    pdf_attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(resume_path))
                    msg.attach(pdf_attachment)
                
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12)
            server.login(sender_email, app_pass)
            server.send_message(msg)
            server.quit()
            
            print(f"[SUCCESS] Dispatched application email with Resume.pdf to {rec_email}!", flush=True)
            dispatched_count += 1
            
            os.makedirs(DATA_DIR, exist_ok=True)
            file_exists = os.path.exists(LLM_LOG_FILE)
            with open(LLM_LOG_FILE, mode="a", newline="", encoding="utf-8") as lf:
                writer = csv.writer(lf)
                if not file_exists:
                    writer.writerow(["Timestamp", "Company", "Role", "Email", "Status"])
                writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), comp, role, rec_email, "SENT_RESUME_PDF"])
                
            record_application("Recruiter Email", comp, role, status="Applied", recruiter_email=rec_email, notes=f"Dispatched cold email with Resume.pdf to {rec_email} ({EXP_LEVEL.upper()})")
                
        except Exception as e:
            print(f"[ERROR] Failed to send email to {rec_email}: {e}", flush=True)
            
    print(f"\n[DONE] Successfully dispatched {dispatched_count} applications using Resume.pdf.", flush=True)
    return dispatched_count

if __name__ == "__main__":
    run_llm_email_job_search_and_apply()
