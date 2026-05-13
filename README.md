# Career OS — Personal Brand Automation

> A fully automated AI career pipeline built by **Omlan Hasan** (M.Sc. AI/ML, TU Dresden).
> Searches real jobs, analyses skill gaps, generates tailored CVs and cover letters, coaches interview prep, summarises research papers, and auto-posts to LinkedIn — all from a single web dashboard running locally. **Zero API cost.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-orange?style=flat)](https://console.groq.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=flat&logo=google&logoColor=white)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

---

## What this is

Most job-search tools are passive lists. This is an active system — it finds jobs, scores how well you match them, tells you exactly what to build to close the gap, then helps you apply, prepare, and stay visible. Every week it runs automatically.

**Built as a real portfolio project** to demonstrate: multi-model LLM routing, OAuth 2.0, REST APIs, web scraping, FastAPI, SQLite, GitHub Actions, and a production-quality Python codebase — all things Werkstudent AI/ML recruiters look for.

---

## Architecture

```
career-os/
├── src/
│   ├── models/         # Multi-model router — Groq for writing, Gemini for bulk tasks
│   ├── jobs/           # Job scraper — Arbeitnow, RemoteOK, RSS feeds
│   ├── cv/             # CV tailor + cover letter generator
│   ├── interview/      # Mock interview coach with scoring
│   ├── learning/       # ArXiv paper finder + 4-week learning plan generator
│   ├── content/        # LinkedIn post generator + RSS paper digest
│   ├── linkedin/       # OAuth 2.0 flow + post publisher
│   ├── github/         # Profile README auto-updater
│   ├── tracker/        # FastAPI + SQLite application tracker
│   └── dashboard/      # Full web UI (FastAPI + vanilla JS)
├── prompts/            # Prompt library — every task has a reusable prompt file
├── .github/workflows/  # 3 scheduled GitHub Actions
├── main.py             # CLI entrypoint for all commands
└── .env.example        # API keys template (never commit .env)
```

---

## 8 modules — one dashboard

Open `http://localhost:8000` after running `python main.py dashboard`.

| Module | What it does | How |
|---|---|---|
| **Job Hunt Radar** | Searches Arbeitnow + RemoteOK, extracts criteria, scores your match %, generates gap projects | Groq + Gemini |
| **Application Tracker** | Full pipeline: Applied → Screen → Interview → Offer. Auto follow-up dates. | FastAPI + SQLite |
| **CV & Cover Letter** | Tailors CV bullets + writes 3-paragraph cover letter per job. ATS keyword score. | Groq (Llama 3.3 70B) |
| **Interview Coach** | Generates questions (4 types), evaluates written answers, identifies weak areas | Groq (Llama 3.3 70B) |
| **English Practice** | Daily practice plan, key phrases, shadowing schedule | Static + prompts |
| **Project Pipeline** | Roadmap of projects to build, GitHub publishing checklist | Static + prompts |
| **Content & Brand** | Draft → refine in ChatGPT → publish to LinkedIn. Option B workflow. | Groq → LinkedIn API |
| **Learning Radar** | Finds ArXiv papers for your skill gaps, generates 4-week sprint plans | Gemini + Groq |

---

## Zero-cost model strategy

No paid API required. Every task routes to the best available free model:

```
Post generation    →  Groq  / Llama 3.3 70B   (500k tokens/day free)
Cover letters      →  Groq  / Llama 3.3 70B
Interview coach    →  Groq  / Llama 3.3 70B
Paper summaries    →  Gemini 2.0 Flash         (1,500 req/day free)
Job criteria       →  Gemini 2.0 Flash
README updates     →  Gemini 2.0 Flash
Human review       →  ChatGPT Go (browser, your subscription)
```

The router in `src/models/router.py` handles all routing. Swap any model by editing one line.

---

## Setup

```bash
git clone https://github.com/OmlanHasan007/personal-brand-automation
cd personal-brand-automation

python -m venv venv
venv\Scripts\activate        # Windows PowerShell
# source venv/bin/activate   # Mac / Linux

pip install -r requirements.txt
cp .env.example .env         # Add your free API keys
```

**Free API keys needed** (no credit card for either):
- Groq: [console.groq.com](https://console.groq.com) → API Keys → `GROQ_API_KEY`
- Gemini: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → `GEMINI_API_KEY`

```bash
python main.py status        # Check everything is connected
python main.py dashboard     # Open the full Career OS at localhost:8000
```

---

## CLI commands

```bash
python main.py dashboard              # Start full web dashboard (recommended)
python main.py draft --topic project  # Generate LinkedIn post draft (Groq)
python main.py publish                # Publish latest draft to LinkedIn
python main.py papers --save          # Fetch + summarise AI papers (Gemini)
python main.py readme                 # Update GitHub profile README
python main.py weekly                 # Full weekly pipeline: papers → draft → README
python main.py auth-linkedin          # One-time LinkedIn OAuth setup
python main.py status                 # Check all API keys + connections
```

---

## The Option B weekly workflow

Fully automated drafting with a human review step — keeps posts authentic:

```
Monday morning (~10 min):

1. python main.py draft --topic project --context "what you built this week"
   → Groq generates draft → saved to drafts/

2. Open draft → copy text → paste into ChatGPT Go browser
   → Refine with commands from prompts/linkedin_post.md

3. Paste refined version back → python main.py publish
   → Posts to LinkedIn
```

---

## Job search → gap analysis flow

```
Job Hunt Radar tab:
  1. Search (Arbeitnow Germany + RemoteOK global)
  2. Gemini extracts: required skills, keywords, role type
  3. Groq scores: match %, gaps, gap projects to build, cover letter angle
  4. Add to tracker with one click
  5. Go to CV & Cover Letter → generate tailored documents
  6. Go to Learning Radar → generate 4-week plan to close gaps
```

---

## GitHub Actions (automated, no intervention needed)

| Workflow | Schedule | Action |
|---|---|---|
| `weekly_post.yml` | Every Monday 07:00 UTC | Generates + posts to LinkedIn |
| `readme_update.yml` | Every Sunday 22:00 UTC | Updates GitHub profile README |
| `paper_digest.yml` | Every Friday 08:00 UTC | Fetches papers → saves digest to logs/ |

Set secrets in GitHub repo Settings → Secrets → Actions. See `SETUP.md` for full list.

---

## Prompts library

Every AI task has a dedicated prompt file in `prompts/`. Each file works two ways:
- **Automatically** — called by the pipeline via Groq/Gemini API
- **Manually** — paste into ChatGPT Go for human-in-the-loop refinement

```
prompts/
├── linkedin_post.md     # Weekly post — topics, tones, refinement commands
├── cover_letter.md      # 3-paragraph formula — hook → proof → close
├── cv_tailor.md         # Per-job CV bullet tailoring + ATS check
├── interview_coach.md   # 3 modes: full session, single drill, answer feedback
└── paper_summary.md     # Quick summary + deep reading guide + NotebookLM usage
```

---

## Skills demonstrated

This project was built to prove real engineering skills to Werkstudent AI/ML recruiters:

| Skill area | Implementation |
|---|---|
| **LLM APIs** | Groq (Llama 3.3 70B) + Gemini 2.0 Flash — multi-model routing |
| **OAuth 2.0** | LinkedIn OAuth flow with token storage and refresh |
| **REST APIs** | FastAPI with full CRUD, Pydantic models, SQLAlchemy ORM |
| **Web scraping** | Arbeitnow API, RemoteOK JSON, RSS feed parsing (feedparser) |
| **Database** | SQLite with SQLAlchemy — job tracker with relationships |
| **CI/CD** | 3 GitHub Actions workflows with scheduled triggers |
| **CLI** | Typer CLI with Rich terminal output |
| **Frontend** | Vanilla JS + FastAPI serving a single-page dashboard |
| **Prompt engineering** | Structured prompts with JSON extraction, multi-task routing |
| **Architecture** | Modular Python package — 9 independent `src/` modules |

---

## About the author

**Omlan Hasan** — AI/ML developer, M.Sc. student at TU Dresden, Germany

- 4+ years Python development experience
- Published paper: *ECG Heart Block Detection Using YOLOv4* — HIS 2022
- Niche: Applied AI — medical imaging + LLM-powered agents
- Stack: PyTorch · LangChain · LangGraph · RAG · YOLO · FastAPI · Docker
- Open to **Werkstudent / AI Intern** roles in Germany (on-site or remote)

📧 omlanhasan@gmail.com · 📍 Dresden, Germany
