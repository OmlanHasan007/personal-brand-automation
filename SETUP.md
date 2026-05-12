# Setup guide — Personal Brand Automation

Follow these steps exactly. Each section is a milestone. Complete them in order.

---

## Milestone 1: Local setup (30 min)

```bash
# 1. Clone / create your GitHub repo
git init personal-brand-automation
cd personal-brand-automation

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Now open .env in your editor and fill in what you have
```

Check your status:
```bash
python main.py status
```

---

## Milestone 2: Claude API key (15 min)

1. Go to https://console.anthropic.com/
2. Create account → API Keys → Create key
3. Add to .env: `ANTHROPIC_API_KEY=sk-ant-...`
4. Test it: `python main.py post --topic project --context "Built a RAG pipeline"`

You should see a generated LinkedIn post. This is the core working.

---

## Milestone 3: Gemini API key — FREE (10 min)

1. Go to https://aistudio.google.com/app/apikey
2. Create API key (free, no credit card needed for Flash model)
3. Add to .env: `GEMINI_API_KEY=AIza...`
4. Test it: `python main.py papers --feed arxiv_cs_lg --limit 3`

You should see 3 summarised papers. Gemini handles all the bulk summarisation — saves Claude API credits.

---

## Milestone 4: GitHub token (10 min)

1. Go to https://github.com/settings/tokens → Generate new token (classic)
2. Scopes to check: `repo`, `read:user`
3. Add to .env: `GITHUB_TOKEN=ghp_...` and `GITHUB_USERNAME=your_username`
4. Create a repo named exactly `your_username/your_username` on GitHub (this is your profile README repo)
5. Test it: `python main.py readme --dry-run`

---

## Milestone 5: LinkedIn OAuth — the tricky one (45 min)

### 5a. Create LinkedIn Developer App
1. Go to https://www.linkedin.com/developers/apps/new
2. App name: "Personal Brand Automation"
3. LinkedIn Page: your personal profile
4. Submit and wait for approval (usually instant for basic permissions)

### 5b. Configure the app
1. Products tab → Request access to "Share on LinkedIn"
2. Auth tab → Add redirect URL: `http://localhost:8080/callback`
3. Copy: Client ID and Client Secret → add to .env

### 5c. Run OAuth flow
```bash
python main.py auth-linkedin
```
This opens your browser, you authorize, token is saved to `data/linkedin_token.json`.

### 5d. Test posting (dry run first!)
```bash
# Dry run — see what would be posted
python main.py post --topic seeking --tone professional

# Actually post
python main.py post --topic seeking --tone professional --publish
```

---

## Milestone 6: GitHub Actions (20 min)

Add these secrets to your GitHub repo:
Settings → Secrets and variables → Actions → New repository secret

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | From .env |
| `GEMINI_API_KEY` | From .env |
| `LINKEDIN_CLIENT_ID` | From .env |
| `LINKEDIN_CLIENT_SECRET` | From .env |
| `LINKEDIN_ACCESS_TOKEN` | From data/linkedin_token.json |
| `LINKEDIN_PERSON_URN` | From data/linkedin_token.json |
| `GITHUB_USERNAME` | Your GitHub username |

Push your code:
```bash
git add .
git commit -m "feat: initial personal brand automation pipeline"
git push origin main
```

Go to Actions tab on GitHub — you should see 3 workflows. Click "Run workflow" on `weekly_post.yml` to test it manually.

---

## Milestone 7: Job tracker (10 min)

```bash
python main.py tracker
```

Open http://localhost:8000/docs — you'll see the full API with interactive docs.

Add your first application:
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_title": "ML Werkstudent", "company": "Bosch Dresden", "source": "LinkedIn", "location": "Dresden, Germany"}'
```

---

## Full weekly run

Once everything is set up, the full pipeline is:
```bash
python main.py weekly
```

Or just let GitHub Actions run it automatically every Monday at 09:00 Dresden time.

---

## What to build next (from here)

1. **CV tailor bot** — `python main.py cv --job-url <url>` → tailored cover letter
2. **Interview coach** — `python main.py mock-interview --role "ML Werkstudent"` → LangGraph agent
3. **Job aggregator** — scrape 5 boards, score match to profile, weekly email digest

Each one is a new module in `src/` and a new command in `main.py`. The architecture already supports it.
