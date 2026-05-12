# Personal Brand Automation

> AI-powered career visibility system — auto-generates LinkedIn posts, updates GitHub README stats, tracks job applications, and summarises research papers. Built with Claude API, Gemini API, and GitHub Actions.

**Portfolio skills demonstrated:** Claude API · Gemini API · LinkedIn OAuth · GitHub Actions · FastAPI · SQLite · Python scheduling · Multi-model LLM routing

---

## Architecture

```
personal-brand-automation/
├── src/
│   ├── models/          # LLM router — picks Claude vs Gemini per task
│   ├── content/         # Post generation + RSS paper summariser
│   ├── linkedin/        # OAuth flow + post publisher
│   ├── github/          # README auto-updater via GitHub API
│   └── tracker/         # FastAPI + SQLite job application tracker
├── .github/workflows/   # Scheduled GitHub Actions
├── data/                # SQLite DB, post history
├── logs/                # Run logs
├── main.py              # CLI entrypoint
└── .env.example         # All required keys (never commit .env)
```

## Modules

| Module | What it does | Model used |
|---|---|---|
| `content/generator.py` | Generates LinkedIn posts from topic + context | Claude (best writing) |
| `content/rss_reader.py` | Fetches AI papers/news, summarises | Gemini 1.5 Flash (free, fast) |
| `linkedin/oauth.py` | LinkedIn OAuth 2.0 flow | — |
| `linkedin/poster.py` | Posts content to LinkedIn | — |
| `github/readme_updater.py` | Pulls repo stats, rewrites README | Gemini Flash |
| `tracker/api.py` | FastAPI job tracker with SQLite | — |
| `models/router.py` | Routes tasks to best free/cheap model | — |

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/personal-brand-automation
cd personal-brand-automation
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # Fill in your keys
```

## Run locally

```bash
# Generate a LinkedIn post
python main.py post --topic "project" --context "Built a RAG pipeline this week"

# Summarise latest AI papers
python main.py papers --feed arxiv --limit 5

# Update GitHub README
python main.py readme

# Start job tracker API
python main.py tracker

# Run full weekly pipeline
python main.py weekly
```

## GitHub Actions schedules

| Workflow | Schedule | What it does |
|---|---|---|
| `weekly_post.yml` | Every Monday 07:00 UTC | Generate + post to LinkedIn |
| `readme_update.yml` | Every Sunday 22:00 UTC | Update profile README |
| `paper_digest.yml` | Every Friday 08:00 UTC | Summarise week's papers → email/log |

## Environment variables

See `.env.example` for all required variables. Never commit `.env`.

## Results

- LinkedIn post generation: ~3 seconds
- Paper summarisation: ~8 seconds per paper (Gemini Flash)
- README update: ~5 seconds
- Job tracker API: responds in <50ms

---

*Built by Omlan Hasan — TU Dresden M.Sc. AI/ML*
