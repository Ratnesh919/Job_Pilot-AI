# 🚀 JobPilot-AI: Autonomous AI Job Application Agent

<div align="center">

![JobPilot-AI Banner](https://img.shields.io/badge/JobPilot--AI-Autonomous_Job_Agent-3b82f6?style=for-the-badge&logo=robot&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-yellow.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Electron 28+](https://img.shields.io/badge/Electron-28+-47848F.svg?style=for-the-badge&logo=electron&logoColor=white)](https://www.electronjs.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated_Browser-2EAD33.svg?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/)

**An open-source, full-stack autonomous desktop bot that searches job boards, fills company careers forms, personalizes cover letters with LLMs (Llama-3.3-70B), dispatches PDF resumes, and tracks recruiter interview responses via Gmail scanning.**

[Features](#-key-features) • [Quick Start](#-quick-start-windows) • [Free API Keys Guide](#-how-to-get-free-api-keys) • [Gmail SMTP Setup](#-how-to-get-gmail-app-password) • [Architecture](#-architecture) • [License](#-license)

</div>

---

## ✨ Key Features

- 🎯 **Multi-Portal Job Scraper & Auto-Applier**: Automates job applications across **LinkedIn**, **Naukri**, **Indeed**, and **Foundit (Monster)**.
- 🏢 **Company Careers Form Auto-Filler**: Automatically fills official application web forms (Name, Email, Phone, LinkedIn, Portfolio, and uploads your `Resume.pdf`).
- 🧠 **AI Command Bar & Dynamic Preference Engine**: Change your locations, target roles, experience level, or execute custom Python code anytime using natural language prompts.
- 🎓 **Fresher vs. Experienced Mode**: Built-in 0-1 Yr & 2026 Batch filters to target entry-level positions without senior mismatch.
- 📍 **Smart Location-Aware Targeting**: Switch between local cities (e.g., Bengaluru, Kolkata, New York, London) or Remote-only opportunities in 1-click.
- 🛡️ **30-Day Duplicate Blocker**: Tracks every submitted application in local SQLite/JSON storage to prevent applying to the same job twice.
- 📩 **Automated Gmail Interview Tracker**: Connects via SSL SMTP / IMAP to scan your inbox for interview scheduling links, online tests, and offer letters.
- 📝 **Low-Latency Cover Letter Generator**: Generates customized 3-paragraph pitch emails matching your resume highlights using Meta Llama-3.3-70B.
- 🖥️ **Modern Desktop UI**: Dark-mode glassmorphic Electron dashboard with real-time status counters, live terminal stream, and interactive Kanban tracker.

---

## ⚡ Quick Start (Windows)

### Prerequisites
1. **Python 3.10 or higher**: [Download from python.org](https://www.python.org/downloads/) *(Ensure "Add Python to PATH" is checked during setup)*.
2. **Node.js (LTS)**: [Download from nodejs.org](https://nodejs.org/).
3. **Google Chrome**: Standard desktop Google Chrome browser.

### 1-Click Installation
1. Clone or download this repository:
   ```bash
   git clone https://github.com/Ratnesh919/Job_Pilot-AI.git
   cd Job_Pilot-AI
   ```
2. Double-click **`install.bat`** (or run `npm run install:all` in terminal).
   * This automatically installs Python dependencies, Playwright Chromium binaries, and Node packages.
3. Double-click **`run.bat`** to launch the desktop application!

---

> [!IMPORTANT]  
> ### ⚠️ PREREQUISITE: Log into your Chrome accounts ONCE
> For automated applications on **LinkedIn**, **Naukri**, and **Indeed** to work seamlessly without triggering CAPTCHAs or security checkpoints:
> 1. In the desktop app, go to **Settings** -> Click **"🌐 Login to Portals"** (or click the button in the login prompt modal).
> 2. Log in to your LinkedIn, Naukri, and Indeed accounts **once** in the opened Chrome window.
> 3. JobPilot-AI will securely reuse this authenticated browser session for all subsequent autonomous background runs!

---

## 🔑 How to Get 100% FREE API Keys

JobPilot-AI works with free LLM providers out of the box:

### 1. OpenRouter (Recommended — Free Llama 3.3 70B & DeepSeek)
1. Go to [https://openrouter.ai/keys](https://openrouter.ai/keys).
2. Sign in with your Google or GitHub account.
3. Click **"Create Key"** and give it a name (e.g. `JobPilot`).
4. Copy your key (`sk-or-v1-...`) and paste it into the **Settings** tab in JobPilot-AI.
> *Note: OpenRouter includes free tier models (`meta-llama/llama-3.3-70b-instruct:free`, `deepseek/deepseek-r1:free`) with zero cost.*

### 2. NVIDIA NIM (Free 1,000 Credits)
1. Visit [https://build.nvidia.com](https://build.nvidia.com).
2. Create a free developer account.
3. Generate your API key (`nvapi-...`) and save it in the **Settings** tab.

### 3. Google AI Studio (Free Gemini Flash)
1. Go to [https://aistudio.google.com/](https://aistudio.google.com/).
2. Click **"Get API key"** -> **"Create API key in new project"**.
3. Paste the key into the app settings.

---

## ✉️ How to Get a Gmail App Password (SMTP)

To allow JobPilot-AI to send resumes and scan your inbox for interview updates:

1. Go to your [Google Account Security Settings](https://myaccount.google.com/security).
2. Under **"How you sign in to Google"**, ensure **2-Step Verification** is turned **ON**.
3. Go directly to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
4. Enter an app name (e.g. `JobPilot`) and click **Create**.
5. Copy the **16-letter password** (e.g., `abcd efgh ijkl mnop`).
6. Paste your Gmail address and this 16-letter password into the **Settings** tab in JobPilot-AI and click **Test SMTP Connection**.

---

## 🏗️ Architecture & Project Structure

```text
JobPilot-AI/
├── backend/
│   ├── ai_command_agent.py     # Natural Language Prompt Parser & Dynamic Settings Engine
│   ├── auto_job_agent.py       # Master Orchestrator (Portals + Forms + Direct Emails)
│   ├── company_site_applier.py # Careers Form Auto-Filler & Resume Uploader
│   ├── portal_auto_applier.py  # LinkedIn, Indeed & Naukri Playwright automation
│   ├── llm_job_finder.py       # Off-campus hiring search & tailored cold applier
│   ├── email_status_tracker.py # Gmail IMAP scanner for interview & test links
│   ├── email_sender.py         # SSL SMTP engine with PDF attachment handling
│   └── db_helper.py            # Local deduplication storage & application logger
├── scripts/
│   ├── app.js                  # Frontend Controller, Navigation & Real-time IPC Sync
│   └── pages/
│       ├── dashboard.js        # Analytics Overview, Start/Stop Bot & Recent Feed
│       ├── ai-agent.js         # Interactive Chat Agent with Dynamic Config Sync
│       ├── tracker.js          # Kanban & Table View for Applied Jobs
│       ├── guide.js            # In-App Free API Keys & Setup Tutorial
│       └── settings.js         # Profile, Target Roles, Location & Credentials Editor
├── styles/
│   └── main.css                # Premium Dark Glassmorphic Theme & Micro-Interactions
├── config.example.json         # Sanitized configuration template
├── package.json                # Electron app manifest
├── requirements.txt            # Python dependencies
├── install.bat                 # 1-Click Windows Setup Script
├── run.bat                     # 1-Click Windows Run Script
└── README.md                   # Project Documentation
```

---

## ⚙️ Configuration Options (`config.json`)

```json
{
  "candidate": {
    "name": "Your Full Name",
    "email": "your_email@gmail.com",
    "phone": "+1 (555) 000-0000",
    "location": "New York, NY / Remote",
    "portfolio": "https://yourportfolio.dev",
    "linkedin": "https://linkedin.com/in/yourprofile",
    "notice_period": "Immediate / 0 Days",
    "experience_years": "0-1"
  },
  "api_keys": {
    "openrouter": "sk-or-v1-...",
    "nvidia": ""
  },
  "experience_level": "fresher",
  "preferred_locations": ["Remote", "New York", "Bengaluru"],
  "primary_location": "Remote",
  "target_roles": [
    "Software Engineer",
    "Python Developer",
    "Frontend Developer",
    "AI / ML Engineer"
  ],
  "bot_settings": {
    "max_per_run": 10,
    "delay_ms": 2000,
    "retry_count": 3
  }
}
```

---

## 🛡️ Privacy & Security First

- **100% Local Execution**: All credentials, job data, and resumes remain exclusively on your local machine (`data/applications_db.json`).
- **Zero Telemetry**: No third-party data tracking or personal analytics collected.
- **Never Commits Secrets**: Pre-configured `.gitignore` prevents accidentally pushing your `.env`, `config.json`, or `Resume.pdf` to GitHub.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
