"""
JobPilot-AI — Autonomous AI Resume Parser & Profile Extractor
Extracts candidate information (name, contact details, skills, target roles, experience level,
location, and links) from uploaded PDF resumes using PDF text extraction + LLM parsing with heuristic fallback.
"""

import sys
import os
import json
import re
import requests

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, 'config.json')

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(cfg):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        sys.stderr.write(f"Error saving config: {e}\n")
        return False

def extract_text_from_pdf(pdf_path):
    """Extracts raw text from a PDF file using multiple fallback engines."""
    if not os.path.exists(pdf_path):
        return ""
    
    extracted_text = ""
    
    # 1. Try PyMuPDF (fitz) - fastest & best layout preservation
    try:
        import fitz
        doc = fitz.open(pdf_path)
        for page in doc:
            extracted_text += page.get_text() + "\n"
        if extracted_text.strip():
            return extracted_text.strip()
    except Exception:
        pass
    
    # 2. Try pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                extracted_text += t + "\n"
        if extracted_text.strip():
            return extracted_text.strip()
    except Exception:
        pass

    # 3. Try pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    extracted_text += t + "\n"
        if extracted_text.strip():
            return extracted_text.strip()
    except Exception:
        pass

    return extracted_text.strip()

COMMON_SKILLS = [
    "Python", "JavaScript", "TypeScript", "React", "React.js", "Next.js", "Vue", "Vue.js", "Angular",
    "Node.js", "Express", "Express.js", "FastAPI", "Flask", "Django", "Spring Boot", "Java", "C++", "C",
    "C#", ".NET", "Rust", "Go", "Golang", "PHP", "Laravel", "Ruby", "Ruby on Rails", "SQL", "PostgreSQL",
    "MySQL", "SQLite", "MongoDB", "Redis", "Elasticsearch", "Cassandra", "DynamoDB", "GraphQL", "REST API",
    "Docker", "Kubernetes", "AWS", "Amazon Web Services", "Azure", "Google Cloud", "GCP", "CI/CD", "Git",
    "GitHub", "GitLab", "Linux", "Bash", "Playwright", "Selenium", "Puppeteer", "PyTorch", "TensorFlow",
    "Keras", "Scikit-Learn", "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "LLM", "Generative AI",
    "OpenAI", "LangChain", "LlamaIndex", "Hugging Face", "Pandas", "NumPy", "Matplotlib", "Seaborn",
    "HTML", "HTML5", "CSS", "CSS3", "Tailwind CSS", "Bootstrap", "Sass", "Redux", "Zustand", "Jest", "Pytest"
]

COMMON_ROLES = [
    "Software Engineer", "Full Stack Developer", "Frontend Developer", "Backend Developer",
    "Python Developer", "React Developer", "AI Engineer", "Machine Learning Engineer",
    "Data Scientist", "Data Engineer", "DevOps Engineer", "Cloud Engineer",
    "Mobile App Developer", "React Native Developer", "Web Developer", "QA Engineer"
]

def heuristic_extract(raw_text):
    """Rule-based extractor for emails, phone numbers, links, skills, and roles."""
    data = {
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin": "",
        "github": "",
        "portfolio": "",
        "skills": [],
        "target_roles": [],
        "experience_level": "fresher",
        "education": "",
        "summary": ""
    }

    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    # 1. Name heuristic (usually first 1-3 lines)
    for line in lines[:4]:
        # Filter out common header words
        clean_line = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = clean_line.split()
        if 2 <= len(words) <= 4 and not any(w.lower() in ['resume', 'curriculum', 'vitae', 'cv', 'profile', 'page', 'contact', 'email', 'phone'] for w in words):
            data["name"] = clean_line
            break

    # 2. Email extraction
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw_text)
    if email_match:
        data["email"] = email_match.group(0).lower()

    # 3. Phone extraction
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{4,5}', raw_text)
    if phone_match:
        data["phone"] = phone_match.group(0).strip()

    # 4. URLs (LinkedIn, GitHub, Portfolio)
    linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9-_%]+)', raw_text, re.IGNORECASE)
    if linkedin_match:
        data["linkedin"] = f"https://linkedin.com/in/{linkedin_match.group(1)}"

    github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9-_%]+)', raw_text, re.IGNORECASE)
    if github_match:
        data["github"] = f"https://github.com/{github_match.group(1)}"

    portfolio_match = re.search(r'(?:https?://)?([a-zA-Z0-9-]+\.(?:dev|me|io|tech|app|com|in|org))', raw_text, re.IGNORECASE)
    if portfolio_match and "linkedin" not in portfolio_match.group(0) and "github" not in portfolio_match.group(0):
        url = portfolio_match.group(0)
        data["portfolio"] = url if url.startswith('http') else f"https://{url}"

    # 5. Skills extraction
    found_skills = []
    text_lower = raw_text.lower()
    for skill in COMMON_SKILLS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)
    data["skills"] = list(dict.fromkeys(found_skills))[:20]

    # 6. Target roles detection
    found_roles = []
    for role in COMMON_ROLES:
        pattern = r'\b' + re.escape(role.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_roles.append(role)
    if not found_roles:
        found_roles = ["Software Engineer", "Full Stack Developer"]
    data["target_roles"] = list(dict.fromkeys(found_roles))[:5]

    # 7. Experience level detection
    exp_matches = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience', text_lower)
    if exp_matches:
        try:
            years = int(exp_matches[0])
            if years >= 3:
                data["experience_level"] = "senior"
            elif years >= 1:
                data["experience_level"] = "experienced"
            else:
                data["experience_level"] = "fresher"
        except ValueError:
            data["experience_level"] = "fresher"
    else:
        # Check if fresher keywords exist
        if any(w in text_lower for w in ["fresher", "entry level", "student", "intern", "undergraduate", "graduate 202"]):
            data["experience_level"] = "fresher"
        else:
            data["experience_level"] = "fresher"

    # 8. Education extraction
    edu_match = re.search(r'(Bachelor|Master|B\.Tech|B\.E\.|B\.Sc|M\.Tech|M\.Sc|B\.S\.|M\.S\.)[^\n,.]+', raw_text, re.IGNORECASE)
    if edu_match:
        data["education"] = edu_match.group(0).strip()

    return data

def llm_extract(raw_text, api_keys):
    """Uses LLM (OpenRouter / NVIDIA / Gemini) to extract high-accuracy structured JSON from resume text."""
    openrouter_key = api_keys.get("openrouter") or os.environ.get("OPENROUTER_API_KEY", "")
    nvidia_key = api_keys.get("nvidia") or os.environ.get("NVIDIA_API_KEY", "")

    prompt = f"""You are an expert HR recruitment parser. Extract all candidate information from the following resume text and format it into a STRICT JSON object.

Resume Text:
\"\"\"
{raw_text[:4000]}
\"\"\"

Return ONLY a JSON object with this exact schema (no markdown, no backticks, no explanations):
{{
  "name": "Candidate Full Name",
  "email": "candidate email or empty string",
  "phone": "candidate phone or empty string",
  "location": "City, State, Country or primary location",
  "linkedin": "LinkedIn profile URL or empty string",
  "github": "GitHub profile URL or empty string",
  "portfolio": "Portfolio/personal website URL or empty string",
  "skills": ["Skill1", "Skill2", "Skill3"],
  "target_roles": ["Role 1", "Role 2", "Role 3"],
  "experience_level": "fresher" (0-1 yrs) or "experienced" (1-3 yrs) or "senior" (3+ yrs),
  "education": "Highest degree and field of study",
  "summary": "2-sentence professional executive summary"
}}"""

    # 1. Try OpenRouter
    if openrouter_key:
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/Ratnesh919/Job_Pilot-AI",
                    "X-Title": "JobPilot-AI Resume Parser"
                },
                json={
                    "model": "meta-llama/llama-3.3-70b-instruct",
                    "messages": [
                        {"role": "system", "content": "You are a professional resume parsing engine. Output strictly valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 800
                },
                timeout=18
            )
            if resp.status_code == 200:
                raw_json = resp.json()['choices'][0]['message']['content'].strip()
                raw_json = re.sub(r'^```(?:json)?\s*', '', raw_json, flags=re.MULTILINE)
                raw_json = re.sub(r'\s*```$', '', raw_json, flags=re.MULTILINE).strip()
                return json.loads(raw_json)
        except Exception as e:
            sys.stderr.write(f"OpenRouter extraction error: {e}\n")

    # 2. Try NVIDIA NIM
    if nvidia_key:
        try:
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {nvidia_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta/llama-3.3-70b-instruct",
                    "messages": [
                        {"role": "system", "content": "You are a professional resume parsing engine. Output strictly valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 800
                },
                timeout=18
            )
            if resp.status_code == 200:
                raw_json = resp.json()['choices'][0]['message']['content'].strip()
                raw_json = re.sub(r'^```(?:json)?\s*', '', raw_json, flags=re.MULTILINE)
                raw_json = re.sub(r'\s*```$', '', raw_json, flags=re.MULTILINE).strip()
                return json.loads(raw_json)
        except Exception as e:
            sys.stderr.write(f"NVIDIA extraction error: {e}\n")

    return None

def parse_and_update_resume(pdf_path):
    """Main workflow: extracts text, parses fields with LLM/heuristics, and saves to config.json."""
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join(ROOT_DIR, pdf_path)

    if not os.path.exists(pdf_path):
        return {"success": False, "error": f"File not found: {pdf_path}"}

    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text:
        return {"success": False, "error": "Could not extract text from PDF (file may be empty or corrupted)."}

    config = load_config()
    api_keys = config.get("api_keys", {})

    # Try LLM extraction first
    extracted = llm_extract(raw_text, api_keys)

    # Fallback to heuristic parser if LLM is unavailable or failed
    if not extracted:
        extracted = heuristic_extract(raw_text)

    # Merge into config.json
    candidate = config.get("candidate", {})
    if extracted.get("name"):
        candidate["name"] = extracted["name"]
    if extracted.get("email"):
        candidate["email"] = extracted["email"]
        # Also update sender email in config.email if empty
        if not config.get("email", {}).get("sender"):
            config.setdefault("email", {})["sender"] = extracted["email"]
    if extracted.get("phone"):
        candidate["phone"] = extracted["phone"]
    if extracted.get("linkedin"):
        candidate["linkedin"] = extracted["linkedin"]
    if extracted.get("github"):
        candidate["github"] = extracted["github"]
    if extracted.get("portfolio"):
        candidate["portfolio"] = extracted["portfolio"]
    if extracted.get("skills"):
        candidate["skills"] = extracted["skills"]

    config["candidate"] = candidate
    config["resume_path"] = pdf_path

    if extracted.get("experience_level"):
        config["experience_level"] = extracted["experience_level"]

    if extracted.get("target_roles"):
        config["target_roles"] = extracted["target_roles"]
        config["keywords"] = extracted["target_roles"]

    if extracted.get("location"):
        config["primary_location"] = extracted["location"]

    save_config(config)

    return {
        "success": True,
        "extracted": extracted,
        "updated_config": config,
        "message": f"Successfully extracted profile for {candidate.get('name', 'Candidate')}!"
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        pdf_file = os.path.join(ROOT_DIR, "Resume.pdf")
    else:
        pdf_file = sys.argv[1]

    result = parse_and_update_resume(pdf_file)
    print(json.dumps(result, indent=2, ensure_ascii=False))
