import os
import sys
import re
import json
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime

# Force UTF-8 encoding on Windows to prevent UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(APP_ROOT, "data")
CONFIG_PATH = os.path.join(APP_ROOT, "config.json")
DB_PATH = os.path.join(DATA_DIR, "applications_db.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}", file=sys.stderr)
        return False

def load_db():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def get_api_key():
    config = load_config()
    openrouter = config.get("api_keys", {}).get("openrouter") or os.getenv("OPENROUTER_API_KEY", "")
    nvidia = config.get("api_keys", {}).get("nvidia") or os.getenv("NVIDIA_API_KEY", "")
    gemini = config.get("api_keys", {}).get("gemini") or os.getenv("GEMINI_API_KEY", "")
    
    if openrouter:
        return {"provider": "openrouter", "key": openrouter}
    if nvidia:
        return {"provider": "nvidia", "key": nvidia}
    if gemini:
        return {"provider": "gemini", "key": gemini}
    return None

def call_llm(prompt, system_prompt="You are JobPilot-AI Assistant, an autonomous job application agent."):
    key_info = get_api_key()
    if not key_info:
        return None
        
    if key_info["provider"] == "openrouter":
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {key_info['key']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "meta-llama/llama-3.3-70b-instruct",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"LLM API Error: {e}", file=sys.stderr)
            return None
    return None

def interpret_and_execute_user_prompt(user_instruction):
    config = load_config()
    db = load_db()
    cand = config.get("candidate", {})
    
    system_prompt = """You are the AI Command & Settings Orchestrator for JobPilot-AI.
You can change system settings, preferences, configuration, target roles, locations, experience modes, and execute code or actions on commands.

Supported Actions:

1. "update_settings": Change user preferences, target cities, location, experience level, remote toggle, or candidate profile.
   Parameters:
     - "primary_location": (optional string) e.g. "Bengaluru", "New York", "San Francisco", "Remote"
     - "preferred_locations": (optional list of strings)
     - "include_remote": (optional boolean)
     - "experience_level": (optional string) "fresher" | "experienced" | "senior"
     - "roles_to_add": (optional list of strings)
     - "roles_to_remove": (optional list of strings)
     - "replace_all_roles": (optional list of strings)
     - "candidate_updates": (optional dict)
     - "bot_settings_updates": (optional dict)

2. "apply_portal": Search and auto-apply on job portals (LinkedIn, Naukri, Indeed, or all).
   Parameters: {"portal": "all"|"linkedin"|"naukri"|"indeed", "keyword": "string", "location": "string", "headless": true|false}

3. "send_cold_emails": Find recruiter emails and dispatch cold applications with resume.
   Parameters: {"keyword": "string", "location": "string", "count": number}

4. "check_email_status": Scan Gmail inbox for interview invites, replies, rejections, or status updates.
   Parameters: {}

5. "generate_cover_letter": Write a tailored cover letter for a specific company & role.
   Parameters: {"company": "string", "role": "string", "highlights": "string"}

6. "execute_custom_code": Run a custom Python script or automation task.
   Parameters: {"code": "string", "description": "string"}

7. "analyze_stats": Provide application metrics, conversion rate, and strategic advice.
   Parameters: {}

8. "chat_response": General queries or answers.
   Parameters: {"reply": "string"}

You must return ONLY valid JSON in this format:
{
  "thought": "Brief explanation of user request",
  "action": "update_settings" | "apply_portal" | "send_cold_emails" | "check_email_status" | "generate_cover_letter" | "execute_custom_code" | "analyze_stats" | "chat_response",
  "parameters": { ... },
  "message_to_user": "Clear confirmation describing the changes made or action taken"
}
"""

    prompt = f"""User Instruction: "{user_instruction}"

Current System Configuration:
- Candidate Name: {cand.get('name', 'Job Candidate')}
- Experience Level: {config.get('experience_level', 'fresher')}
- Primary Location: {config.get('primary_location', 'Remote')}
- Preferred Locations: {json.dumps(config.get('preferred_locations', ['Remote', 'New York']))}
- Include Remote: {config.get('include_remote', True)}
- Current Target Roles: {json.dumps(config.get('target_roles', [])[:8])}
- Total Applications in Database: {len(db)}

Analyze the user's instruction and return the exact JSON action:"""

    llm_output = call_llm(prompt, system_prompt)
    plan = None
    
    if llm_output:
        try:
            json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group(0))
        except Exception as e:
            print(f"Error parsing LLM JSON: {e}", file=sys.stderr)
            
    if not plan:
        inst_lower = user_instruction.lower()
        
        # Check for location changes
        if "location" in inst_lower or "city" in inst_lower or "cities" in inst_lower:
            locs = []
            for city in ["bengaluru", "bangalore", "kolkata", "hyderabad", "pune", "noida", "new york", "san francisco", "london", "remote"]:
                if city in inst_lower:
                    c_name = "Bengaluru" if city in ["bengaluru", "bangalore"] else city.title()
                    locs.append(c_name)
            if not locs:
                locs = ["Remote", "New York"]
            plan = {
                "thought": f"User requested changing target locations to {locs}",
                "action": "update_settings",
                "parameters": {
                    "primary_location": locs[0],
                    "preferred_locations": locs,
                    "include_remote": True
                },
                "message_to_user": f"Updated your target locations to {', '.join(locs)}."
            }
        # Check for experience level changes
        elif "fresher" in inst_lower or "entry level" in inst_lower or "0-1" in inst_lower:
            plan = {
                "thought": "User wants to set experience level to Fresher",
                "action": "update_settings",
                "parameters": {"experience_level": "fresher"},
                "message_to_user": "Set bot experience level to Fresher (0-1 Yrs)."
            }
        elif "experienced" in inst_lower or "senior" in inst_lower or "2 year" in inst_lower:
            plan = {
                "thought": "User wants to set experience level to Experienced",
                "action": "update_settings",
                "parameters": {"experience_level": "experienced"},
                "message_to_user": "Set bot experience level to Experienced (1-3 Yrs)."
            }
        elif "scan" in inst_lower or "check" in inst_lower and ("email" in inst_lower or "inbox" in inst_lower or "update" in inst_lower):
            plan = {
                "thought": "User requested scanning email inbox for status updates",
                "action": "check_email_status",
                "parameters": {},
                "message_to_user": "Scanning your Gmail inbox for recruiter replies and status updates..."
            }
        elif "cover letter" in inst_lower:
            comp = "Tech Company"
            words = user_instruction.split()
            if "for" in words:
                idx = words.index("for")
                if idx + 1 < len(words):
                    comp = words[idx+1].replace(',', '').replace('.', '')
            plan = {
                "thought": f"User wants a cover letter for {comp}",
                "action": "generate_cover_letter",
                "parameters": {"company": comp, "role": "Software Engineer"},
                "message_to_user": f"Generating a tailored cover letter for {comp}..."
            }
        else:
            kw = "Software Engineer"
            for candidate_kw in ["python", "frontend", "ui", "ux", "ai", "hardware", "embedded", "iot", "react", "golang", "java"]:
                if candidate_kw in inst_lower:
                    kw = candidate_kw.title() + " Developer"
                    break
            plan = {
                "thought": f"User wants to apply to jobs for keyword '{kw}'",
                "action": "apply_portal",
                "parameters": {"portal": "all", "keyword": kw, "headless": True},
                "message_to_user": f"Starting automated portal applier for '{kw}' across LinkedIn, Naukri, and Indeed..."
            }

    result = execute_action(plan)
    return {
        "plan": plan,
        "execution": result
    }

def execute_action(plan):
    action = plan.get("action")
    params = plan.get("parameters", {})
    
    if action == "update_settings":
        cfg = load_config()
        changes_applied = []
        
        if "primary_location" in params:
            cfg["primary_location"] = params["primary_location"]
            changes_applied.append(f"Primary Location: {params['primary_location']}")
            
        if "preferred_locations" in params:
            cfg["preferred_locations"] = params["preferred_locations"]
            changes_applied.append(f"Preferred Cities: {', '.join(params['preferred_locations'])}")
            
        if "include_remote" in params:
            cfg["include_remote"] = bool(params["include_remote"])
            changes_applied.append(f"Include Remote: {cfg['include_remote']}")
            
        if "experience_level" in params:
            cfg["experience_level"] = params["experience_level"].lower()
            changes_applied.append(f"Experience Mode: {cfg['experience_level'].capitalize()}")
            
        roles = cfg.setdefault("target_roles", [])
        if "replace_all_roles" in params and params["replace_all_roles"]:
            cfg["target_roles"] = params["replace_all_roles"]
            changes_applied.append(f"Target Roles reset to: {', '.join(cfg['target_roles'])}")
        else:
            if "roles_to_add" in params:
                for r in params["roles_to_add"]:
                    if r not in roles:
                        roles.append(r)
                changes_applied.append(f"Added Roles: {', '.join(params['roles_to_add'])}")
            if "roles_to_remove" in params:
                for r in params["roles_to_remove"]:
                    if r in roles:
                        roles.remove(r)
                changes_applied.append(f"Removed Roles: {', '.join(params['roles_to_remove'])}")
                
        if "candidate_updates" in params and isinstance(params["candidate_updates"], dict):
            cand = cfg.setdefault("candidate", {})
            for k, v in params["candidate_updates"].items():
                cand[k] = v
                changes_applied.append(f"Candidate {k}: {v}")
                
        if "bot_settings_updates" in params and isinstance(params["bot_settings_updates"], dict):
            b_set = cfg.setdefault("bot_settings", {})
            for k, v in params["bot_settings_updates"].items():
                b_set[k] = v
                changes_applied.append(f"Bot Setting {k}: {v}")
                
        saved = save_config(cfg)
        return {
            "success": saved,
            "config_updated": True,
            "config": cfg,
            "changes": changes_applied,
            "message": f"Successfully updated preferences on command! Applied: {'; '.join(changes_applied)}"
        }

    elif action == "execute_custom_code":
        code = params.get("code", "")
        desc = params.get("description", "Custom execution task")
        if not code:
            return {"success": False, "message": "No code provided to execute."}
        try:
            res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=25, cwd=BACKEND_DIR)
            return {
                "success": res.returncode == 0,
                "description": desc,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "message": f"Code executed. Output: {res.stdout[:300] or 'Completed successfully.'}"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "message": f"Error running custom code: {e}"}

    elif action == "check_email_status":
        from email_status_tracker import check_gmail_inbox_updates
        return check_gmail_inbox_updates()
        
    elif action == "generate_cover_letter":
        from llm_job_finder import call_low_latency_llm_cover_letter
        company = params.get("company", "Tech Company")
        role = params.get("role", "Software Engineer")
        letter = call_low_latency_llm_cover_letter(company, role)
        return {
            "success": True,
            "company": company,
            "role": role,
            "cover_letter": letter
        }
        
    elif action == "analyze_stats":
        db = load_db()
        total = len(db)
        interviews = len([a for a in db if a.get("status") == "Interview Scheduled"])
        under_review = len([a for a in db if a.get("status") == "Under Review"])
        tests = len([a for a in db if a.get("status") == "Assessment / Test"])
        applied = len([a for a in db if a.get("status") == "Applied"])
        rejected = len([a for a in db if a.get("status") == "Rejected"])
        
        rate = round(((total - rejected) / total * 100)) if total > 0 else 0
        return {
            "success": True,
            "total_applications": total,
            "applied": applied,
            "under_review": under_review,
            "tests": tests,
            "interviews": interviews,
            "rejected": rejected,
            "success_rate": f"{rate}%",
            "recommendation": "Maintain consistent daily application runs between 9 AM - 11 AM local time."
        }
        
    elif action == "apply_portal":
        return {
            "success": True,
            "async_task": "portal_apply",
            "portal": params.get("portal", "all"),
            "keyword": params.get("keyword", "Software Engineer"),
            "location": params.get("location", "Remote"),
            "headless": params.get("headless", True),
            "message": f"Ready to launch portal applier for '{params.get('keyword', 'Software Engineer')}' in {params.get('location', 'target location')}"
        }
        
    elif action == "send_cold_emails":
        return {
            "success": True,
            "async_task": "cold_email",
            "keyword": params.get("keyword", "Software Engineer"),
            "location": params.get("location", "Remote"),
            "count": params.get("count", 5),
            "message": f"Searching recruiter emails and sending customized cold letters..."
        }
        
    elif action == "chat_response":
        return {
            "success": True,
            "reply": params.get("reply", plan.get("message_to_user", "I'm here to help with your job search."))
        }
        
    return {"success": True, "message": "Action parsed successfully."}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        instruction = " ".join(sys.argv[1:])
        res = interpret_and_execute_user_prompt(instruction)
        print(json.dumps(res, indent=2))
    else:
        test_inst = "Change my target location to London and Remote and add AI Engineer"
        res = interpret_and_execute_user_prompt(test_inst)
        print(json.dumps(res, indent=2))
