# Career OS — Personal Brand Automation

> AI-powered career pipeline built by **Omlan Hasan** (M.Sc. AI/ML, TU Dresden).
> Searches real jobs, analyses skill gaps, generates tailored CVs and cover letters,
> coaches interview prep with a teach-first approach, and auto-posts to LinkedIn —
> all from a web dashboard that works on desktop and **mobile (PWA)**.
> **Zero API cost.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-orange?style=flat)](https://console.groq.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=flat&logo=google)](https://aistudio.google.com)
[![PWA](https://img.shields.io/badge/PWA-installable-5A0FC8?style=flat)](https://web.dev/pwa)
[![Auto README](https://img.shields.io/badge/README-auto--generated-brightgreen?style=flat)](scripts/generate_readme.py)

> **Last updated:** 2026-05-16 00:19 UTC · **Python files:** 12 across 10 modules

---

## What this is

A full career automation system — not a job board wrapper. It actively:
- Searches 4 job sources and scores your match % against each posting
- Teaches you a concept first, then drills you with tailored interview questions
- Generates tailored CV + cover letter per application and saves them automatically
- Posts to LinkedIn on a weekly schedule via GitHub Actions
- Runs as a **mobile PWA** — install on Android, use from anywhere

Built as a portfolio project to prove: multi-model LLM routing, OAuth 2.0, REST APIs,
job scraping, FastAPI, SQLite, GitHub Actions, PWA, and production Python architecture —
all in one repo that actually does something useful.

---

## Architecture

```
personal-brand-automation/
├── src/
│   ├── content/  # generator, rss_reader
│   ├── cv/  # tailor
│   ├── dashboard/  # app
│   ├── github/  # readme_updater
│   ├── interview/  # coach
│   ├── jobs/  # scraper
│   ├── learning/  # radar
│   ├── linkedin/  # oauth, poster
│   ├── models/  # router
│   ├── tracker/  # api
├── scripts/
│   └── generate_readme.py  # This file — auto-generates README on push
├── prompts/                 # Prompt library: Cover Letter, Cv Tailor, Interview Coach, Linkedin Post, Paper Summary
├── .github/workflows/       # 4 automated workflows
├── data/                    # SQLite DB, CV outputs, job cache, interview progress
└── main.py                  # CLI entrypoint
```

---

## 8 modules — one dashboard

Open `http://localhost:8000` — works on desktop and as a PWA on Android.

| Module | What it does | Model |
|---|---|---|
| **Job Hunt Radar** | Multi-source search · editable job titles · per-source toggle · custom sources | Groq + Gemini |
| **Application Tracker** | Full pipeline: Applied → Screen → Interview → Offer · match score · follow-ups | SQLite |
| **CV & Cover Letter** | Tailored bullets + 3-para cover letter · auto-saved to `data/cv_outputs/` · ATS score | Groq |
| **Interview Coach** | Teach first → check understanding → drill questions · progress tracking · job-based Q bank | Groq |
| **English Practice** | Beginner → advanced track · daily plan · shadowing → conversation → interview-ready | Static |
| **Project Pipeline** | Roadmap · GitHub publishing checklist · gap-closing project suggestions | Static |
| **Content & Brand** | Draft → refine in ChatGPT Go → publish to LinkedIn · post history | Groq |
| **Learning Radar** | ArXiv paper finder · 4-week sprint plan · skill gap tracking | Gemini |

---

## Zero-cost model strategy

```
Post generation    →  Groq  / Llama 3.3 70B   (500k tokens/day, free, no card)
Cover letters      →  Groq  / Llama 3.3 70B
Interview coach    →  Groq  / Llama 3.3 70B
Paper summaries    →  Gemini 2.0 Flash         (1,500 req/day, free, no card)
Job criteria       →  Gemini 2.0 Flash
Human review       →  ChatGPT Go (browser)
```

Router in `src/models/router.py` — swap any model by editing one dict.

---

## Mobile PWA — install on Android

This dashboard is a Progressive Web App. To install on your phone:

1. Run `python main.py dashboard` on your computer
2. Find your computer's local IP: `ipconfig` (Windows) → look for IPv4
3. On your Android phone, open Chrome → go to `http://YOUR_IP:8000`
4. Chrome shows "Add to Home Screen" banner after 10 seconds — tap Install
5. Career OS appears on your home screen like a native app

For use **outside your home network**, deploy to Railway or Render (free tier):
```bash
# One-command deploy to Railway (free)
railway login
railway init
railway up
```

---

## Setup

```bash
git clone https://github.com/OmlanHasan007/personal-brand-automation
cd personal-brand-automation
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env         # Add your free API keys
python main.py status        # Check everything
python main.py dashboard     # Open at localhost:8000
```

**Free API keys needed (no credit card):**
- Groq: [console.groq.com](https://console.groq.com) → `GROQ_API_KEY`
- Gemini: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → `GEMINI_API_KEY`

---

## CLI commands

```bash
python main.py dashboard              # Start web + mobile dashboard
python main.py draft --topic project  # Generate LinkedIn post
python main.py publish                # Publish latest draft to LinkedIn
python main.py papers --save          # Fetch AI papers (Gemini)
python main.py readme                 # Update GitHub profile README
python main.py weekly                 # Full weekly pipeline
python main.py auth-linkedin          # One-time LinkedIn OAuth
python main.py status                 # Check all keys
```

---

## GitHub Actions

| `auto_readme.yml` | Auto Readme | on push / manual |
| `paper_digest.yml` | Paper Digest | 0 8 * * 5'   # Every Friday at 08:00 UTC |
| `readme_update.yml` | Readme Update | 0 22 * * 0'   # Every Sunday 22:00 UTC |
| `weekly_post.yml` | Weekly Post | 0 7 * * 1'   # Every Monday 07:00 UTC (09:00 Dresden) |

All workflows run on GitHub's free tier. Set secrets in repo Settings → Secrets → Actions.

---

## Dependencies

`groq`, `google-genai`, `python-dotenv`, `httpx`, `requests`, `fastapi`, `uvicorn`, `sqlalchemy`, `aiofiles`, `flask`, `feedparser`, `schedule`, `rich`, `typer`, `PyGithub`, `pydantic`, `python-dateutil`

---

## Prompts library

Every AI task has a dedicated prompt file in `prompts/`. Each works two ways:
- **Automatic** — called by the pipeline via API
- **Manual** — paste into ChatGPT Go for human refinement

Files: `cover_letter.md`, `cv_tailor.md`, `interview_coach.md`, `linkedin_post.md`, `paper_summary.md`

---

## Skills demonstrated

| Skill | Implementation |
|---|---|
| **LLM APIs** | Groq (Llama 3.3 70B) + Gemini 2.0 Flash — task-based routing |
| **OAuth 2.0** | LinkedIn OAuth with token storage |
| **REST APIs** | FastAPI + Pydantic + SQLAlchemy ORM |
| **Web scraping** | Arbeitnow API, RemoteOK JSON, RSS feeds (feedparser) |
| **PWA** | Service worker, Web App Manifest, install prompt, offline cache |
| **Database** | SQLite — job tracker, CV history, interview progress |
| **CI/CD** | 4 GitHub Actions with scheduled triggers |
| **Mobile** | Responsive CSS, bottom nav, safe-area support, Android install |
| **Prompt engineering** | Structured JSON extraction, multi-task routing, teach-first pedagogy |
| **Architecture** | 10 independent `src/` modules, clean separation of concerns |

---

## About the author

**Omlan Hasan** — AI/ML developer, M.Sc. student at TU Dresden, Germany

- 4+ years Python development
- Published: *ECG Heart Block Detection Using YOLOv4* — HIS 2022
- Stack: PyTorch · LangChain · LangGraph · RAG · YOLO · FastAPI · Docker
- Open to **Werkstudent / AI Intern** roles in Germany (on-site or remote)

📧 omlanhasan@gmail.com · 📍 Dresden, Germany · [GitHub](https://github.com/OmlanHasan007) · [LinkedIn](https://linkedin.com/in/omlan-hasan)

---

*This README is auto-generated by [`scripts/generate_readme.py`](scripts/generate_readme.py) on every push.*
