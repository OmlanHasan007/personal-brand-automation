"""
jobs/scraper.py  v2
-------------------
Upgraded job hunt radar.
- User-defined search config stored in data/search_config.json
  (edited from dashboard — no code change needed)
- Custom job titles: search for exactly what you want
- Custom sources: add any RSS feed, JSON endpoint, or Arbeitnow tag
- Built-in sources: Arbeitnow Germany, RemoteOK, We Work Remotely, Jobicy
- Per-source enable/disable toggle
- Gap analysis: Gemini extracts criteria, Groq scores match + gap projects
"""

import json, re
from datetime import datetime
from pathlib import Path
import httpx, feedparser
from src.models.router import call

DATA_DIR    = Path("data")
CACHE_FILE  = DATA_DIR / "job_cache.json"
CONFIG_FILE = DATA_DIR / "search_config.json"
DATA_DIR.mkdir(exist_ok=True)

# ── Profile used for gap analysis ─────────────────────────────────────────────
YOUR_PROFILE = {
    "skills": [
        "Python","PyTorch","LangChain","LangGraph","RAG","YOLO",
        "FastAPI","SQLite","Docker","GitHub Actions","SQL","REST APIs","Git","Linux"
    ],
    "experience_years": 4,
    "education": "M.Sc. AI/ML, TU Dresden (ongoing)",
    "publication": "ECG Heart Block Detection, HIS 2022",
    "seeking": "Werkstudent or AI Intern",
}

# ── Default search config (saved to data/search_config.json on first run) ─────
DEFAULT_CONFIG = {
    "job_titles": [
        "Werkstudent Machine Learning",
        "Werkstudent Artificial Intelligence",
        "Working Student AI",
        "AI Engineer Intern",
        "NLP Engineer",
        "Computer Vision Intern"
    ],
    "keywords": [
        "machine learning","deep learning","llm","nlp",
        "computer vision","pytorch","langchain","python ai"
    ],
    "sources": {
        "arbeitnow_de": {
            "label": "Arbeitnow Germany (Werkstudent)",
            "type": "arbeitnow_api",
            "enabled": True,
            "params": {"tags": "machine-learning,artificial-intelligence,python", "remote": "false"}
        },
        "arbeitnow_remote": {
            "label": "Arbeitnow Remote",
            "type": "arbeitnow_api",
            "enabled": True,
            "params": {"tags": "machine-learning,artificial-intelligence", "remote": "true"}
        },
        "remoteok": {
            "label": "RemoteOK (Global)",
            "type": "remoteok_json",
            "enabled": True,
            "url": "https://remoteok.com/remote-machine-learning-jobs.json"
        },
        "wwr": {
            "label": "We Work Remotely",
            "type": "rss",
            "enabled": True,
            "url": "https://weworkremotely.com/categories/remote-programming-jobs.rss"
        },
        "jobicy": {
            "label": "Jobicy (Global Remote AI/ML)",
            "type": "rss",
            "enabled": True,
            "url": "https://jobicy.com/?feed=job_feed&job_categories=dev-engineering&job_types=full-time"
        }
    },
    "limit_per_source": 8,
    "cache_hours": 6
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            stored = json.load(f)
        # Merge so new default keys always present
        for k, v in DEFAULT_CONFIG.items():
            if k not in stored:
                stored[k] = v
        return stored
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ── Main search ───────────────────────────────────────────────────────────────

def search_jobs(source_ids: list[str] = None, title_filter: str = "", refresh: bool = False) -> list[dict]:
    """
    Fetch jobs from enabled sources.
    title_filter: if provided, only return jobs whose title contains this string (case-insensitive).
    """
    cfg     = load_config()
    sources = cfg["sources"]
    kws     = cfg["keywords"]
    limit   = cfg["limit_per_source"]
    titles  = cfg["job_titles"]

    # Which sources to hit
    active_ids = source_ids or [sid for sid, s in sources.items() if s.get("enabled", True)]

    all_jobs = []
    for sid in active_ids:
        src = sources.get(sid)
        if not src or not src.get("enabled", True):
            continue
        try:
            stype = src["type"]
            if stype == "arbeitnow_api":
                jobs = _fetch_arbeitnow(src.get("params", {}), limit)
            elif stype == "remoteok_json":
                jobs = _fetch_remoteok(src["url"], kws, limit)
            elif stype == "rss":
                jobs = _fetch_rss(src["url"], kws + titles, limit)
            else:
                jobs = []
            for j in jobs:
                j["source_id"]   = sid
                j["source_name"] = src["label"]
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"[scraper] {sid} failed: {e}")

    # Filter by job title if specified
    if title_filter:
        tf = title_filter.lower()
        all_jobs = [j for j in all_jobs if tf in j.get("title","").lower()
                    or tf in " ".join(j.get("tags",[])).lower()]

    # Also filter by configured job titles (any match)
    if titles and not title_filter:
        def matches_titles(j):
            text = (j.get("title","") + " " + " ".join(j.get("tags",[]))).lower()
            return any(t.lower() in text for t in titles) or any(k.lower() in text for k in kws)
        all_jobs = [j for j in all_jobs if matches_titles(j)]

    # Deduplicate
    seen, unique = set(), []
    for j in all_jobs:
        key = (j.get("title","").lower()[:40], j.get("company","").lower()[:30])
        if key not in seen:
            seen.add(key)
            unique.append(j)

    _save_cache(unique)
    return unique


# ── Gap analysis ──────────────────────────────────────────────────────────────

def analyse_job(job: dict) -> dict:
    job["criteria"]     = _extract_criteria(job)
    job["gap_analysis"] = _gap_analysis(job, job["criteria"])
    return job


def _extract_criteria(job: dict) -> dict:
    desc  = job.get("description","")[:3000]
    title = job.get("title","")
    prompt = f"""Extract job requirements. Return ONLY valid JSON, no explanation.

Job title: {title}
Description: {desc}

JSON structure:
{{
  "required_skills": ["skill1"],
  "nice_to_have": ["skill1"],
  "experience_level": "junior|mid|senior",
  "experience_years": "0-1|1-2|2-3|3+",
  "education": "Bachelor|Master|PhD|Any",
  "keywords": ["top 5 keywords"],
  "role_type": "engineering|research|data|mlops|fullstack",
  "summary": "2 sentences: what this role actually does day-to-day"
}}"""
    try:
        raw = call("quick_classify", prompt, max_tokens=500)
        m   = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return {"required_skills":[],"nice_to_have":[],"experience_level":"unknown",
            "keywords":[],"summary": desc[:200] or "No description."}


def _gap_analysis(job: dict, criteria: dict) -> dict:
    required    = criteria.get("required_skills",[])
    nice     = criteria.get("nice_to_have",[])
    your     = YOUR_PROFILE["skills"]
    have     = [s for s in required if any(s.lower() in y.lower() or y.lower() in s.lower() for y in your)]
    missing  = [s for s in required if s not in have]
    match_pct = round(len(have) / max(len(required),1) * 100)

    prompt = f"""Career mentor reviewing job fit for Omlan Hasan.

PROFILE: {json.dumps(YOUR_PROFILE)}
JOB: {job.get('title')} at {job.get('company')}
Required: {', '.join(required)}
Nice-to-have: {', '.join(nice)}
He has: {', '.join(have)}
Missing: {', '.join(missing)}
Match: {match_pct}%

Return ONLY valid JSON:
{{
  "match_score": {match_pct},
  "verdict": "strong|good|stretch|skip",
  "verdict_reason": "one sentence",
  "strengths": ["strength1","strength2"],
  "gaps": ["gap1","gap2"],
  "gap_projects": [
    {{"gap":"skill","project":"project to build","time_weeks":2,"difficulty":"easy|medium|hard"}}
  ],
  "cover_letter_angle": "one sentence on strongest angle",
  "skills_have": {json.dumps(have)},
  "skills_missing": {json.dumps(missing)}
}}"""
    try:
        raw = call("post_generation", prompt, max_tokens=800)
        m   = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            result = json.loads(m.group())
            result["match_score"]     = match_pct
            result["skills_have"]     = have
            result["skills_missing"]  = missing
            return result
    except Exception:
        pass
    return {"match_score":match_pct,"verdict":"unknown","skills_have":have,"skills_missing":missing,"gap_projects":[]}


# ── Source fetchers ───────────────────────────────────────────────────────────

def _fetch_arbeitnow(params: dict, limit: int) -> list[dict]:
    resp = httpx.get("https://www.arbeitnow.com/api/job-board-api", params=params, timeout=15)
    resp.raise_for_status()
    jobs = resp.json().get("data",[])[:limit]
    return [{
        "id":          j.get("slug",""),
        "title":       j.get("title",""),
        "company":     j.get("company_name",""),
        "location":    j.get("location","Germany"),
        "url":         j.get("url",""),
        "description": j.get("description",""),
        "tags":        j.get("tags",[]),
        "remote":      j.get("remote",False),
        "posted":      j.get("created_at",""),
    } for j in jobs]


def _fetch_remoteok(url: str, keywords: list, limit: int) -> list[dict]:
    resp = httpx.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data,list) and data and "legal" in str(data[0]):
        data = data[1:]
    results = []
    for j in data:
        text = (j.get("position","")+" "+" ".join(j.get("tags",[]))+" "+j.get("description","")).lower()
        if any(k.lower() in text for k in keywords):
            results.append({
                "id":          str(j.get("id","")),
                "title":       j.get("position",""),
                "company":     j.get("company",""),
                "location":    "Remote",
                "url":         j.get("url",""),
                "description": j.get("description","")[:2000],
                "tags":        j.get("tags",[]),
                "remote":      True,
                "posted":      j.get("date",""),
            })
            if len(results) >= limit:
                break
    return results


def _fetch_rss(url: str, keywords: list, limit: int) -> list[dict]:
    feed    = feedparser.parse(url)
    results = []
    for entry in feed.entries:
        text = (entry.get("title","")+" "+entry.get("summary","")).lower()
        if any(k.lower() in text for k in keywords):
            results.append({
                "id":          entry.get("id",""),
                "title":       entry.get("title",""),
                "company":     entry.get("author",""),
                "location":    "Remote",
                "url":         entry.get("link",""),
                "description": re.sub(r'<[^>]+>','',entry.get("summary","")),
                "tags":        [],
                "remote":      True,
                "posted":      "",
            })
            if len(results) >= limit:
                break
    return results


# ── Cache ─────────────────────────────────────────────────────────────────────

def _save_cache(jobs: list):
    with open(CACHE_FILE,"w",encoding="utf-8") as f:
        json.dump({"fetched_at":datetime.utcnow().isoformat(),"jobs":jobs},f,indent=2)

def load_cache() -> list:
    if not CACHE_FILE.exists(): return []
    with open(CACHE_FILE,encoding="utf-8") as f: return json.load(f).get("jobs",[])

def cache_age_hours() -> float:
    if not CACHE_FILE.exists(): return 999
    with open(CACHE_FILE,encoding="utf-8") as f:
        data = json.load(f)
    fetched = datetime.fromisoformat(data.get("fetched_at","2000-01-01"))
    return (datetime.utcnow()-fetched).total_seconds()/3600
