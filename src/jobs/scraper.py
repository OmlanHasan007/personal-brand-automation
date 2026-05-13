"""
jobs/scraper.py
---------------
Searches real job postings from multiple free sources.
No API keys needed — uses public RSS feeds + HTTP scraping.

Sources:
  - Arbeitnow (Germany Werkstudent, has free API)
  - RemoteOK (global remote, free RSS)
  - LinkedIn Jobs RSS (public, no auth)
  - Wellfound / AngelList (AI startups)
  - We Work Remotely (remote-first)

For each job found:
  - Title, company, location, URL, tags
  - Gemini extracts: required skills, nice-to-haves, experience level
  - Groq generates: gap analysis vs your profile + project plan to fill gaps
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import httpx
import feedparser
from src.models.router import call

DATA_DIR  = Path("data")
CACHE_FILE = DATA_DIR / "job_cache.json"
DATA_DIR.mkdir(exist_ok=True)

# --- Your profile for gap analysis ---
YOUR_PROFILE = {
    "skills": [
        "Python", "PyTorch", "LangChain", "LangGraph", "RAG",
        "YOLO", "FastAPI", "SQLite", "Docker", "GitHub Actions",
        "SQL", "REST APIs", "Git", "Linux"
    ],
    "experience_years": 4,
    "education": "M.Sc. AI/ML, TU Dresden (ongoing)",
    "publication": "ECG Heart Block Detection, HIS 2022",
    "languages": ["Python", "SQL", "Bash"],
    "location": "Dresden, Germany",
    "seeking": "Werkstudent or AI Intern",
}

# --- Job sources ---
SOURCES = {
    "arbeitnow": {
        "name": "Arbeitnow (Germany)",
        "url": "https://www.arbeitnow.com/api/job-board-api",
        "type": "api",
        "params": {"tags": "machine-learning,artificial-intelligence,python", "remote": "false"},
    },
    "arbeitnow_remote": {
        "name": "Arbeitnow Remote",
        "url": "https://www.arbeitnow.com/api/job-board-api",
        "type": "api",
        "params": {"tags": "machine-learning,artificial-intelligence", "remote": "true"},
    },
    "remoteok": {
        "name": "RemoteOK (Global)",
        "url": "https://remoteok.com/remote-machine-learning-jobs.json",
        "type": "json",
    },
    "wwr": {
        "name": "We Work Remotely",
        "url": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "type": "rss",
        "keywords": ["machine learning", "ai", "python", "nlp", "deep learning"],
    },
}

SEARCH_KEYWORDS = [
    "machine learning", "künstliche intelligenz", "werkstudent KI",
    "deep learning", "nlp", "computer vision", "llm", "ai engineer",
    "data scientist", "pytorch", "langchain", "python developer ai"
]


def search_jobs(
    sources: list[str] = None,
    keywords: list[str] = None,
    limit_per_source: int = 10,
    remote_only: bool = False,
) -> list[dict]:
    """
    Fetch jobs from all configured sources.
    Returns list of normalised job dicts.
    """
    sources   = sources or list(SOURCES.keys())
    keywords  = keywords or SEARCH_KEYWORDS[:5]
    all_jobs  = []

    for src_key in sources:
        if src_key not in SOURCES:
            continue
        src = SOURCES[src_key]
        try:
            if src["type"] == "api":
                jobs = _fetch_arbeitnow(src["url"], src.get("params", {}), limit_per_source)
            elif src["type"] == "json":
                jobs = _fetch_remoteok(src["url"], keywords, limit_per_source)
            elif src["type"] == "rss":
                jobs = _fetch_rss(src["url"], src.get("keywords", keywords), limit_per_source)
            else:
                jobs = []

            for j in jobs:
                j["source_name"] = src["name"]
                j["source_key"]  = src_key
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"[scraper] {src_key} failed: {e}")

    # Deduplicate by title+company
    seen = set()
    unique = []
    for j in all_jobs:
        key = (j.get("title","").lower()[:40], j.get("company","").lower()[:30])
        if key not in seen:
            seen.add(key)
            unique.append(j)

    # Cache results
    _save_cache(unique)
    return unique


def analyse_job(job: dict) -> dict:
    """
    Use Gemini to extract criteria from a job posting,
    then Groq to generate a gap analysis + project plan.
    """
    # Step 1: Extract criteria with Gemini
    criteria = _extract_criteria(job)
    job["criteria"] = criteria

    # Step 2: Gap analysis with Groq
    gap = _gap_analysis(job, criteria)
    job["gap_analysis"] = gap

    return job


def _extract_criteria(job: dict) -> dict:
    """Gemini extracts structured requirements from job description."""
    desc = job.get("description", "")[:3000]
    title = job.get("title", "")

    prompt = f"""Extract the job requirements from this posting. Return ONLY valid JSON, no explanation.

Job title: {title}
Description: {desc}

Return this exact JSON structure:
{{
  "required_skills": ["skill1", "skill2"],
  "nice_to_have": ["skill1", "skill2"],
  "experience_level": "junior|mid|senior",
  "experience_years": "0-1|1-2|2-3|3+",
  "education": "Bachelor|Master|PhD|Any",
  "languages": ["Python", "etc"],
  "keywords": ["top 5 keywords from posting"],
  "role_type": "engineering|research|data|mlops|fullstack",
  "summary": "2 sentence summary of what this role actually does"
}}"""

    try:
        raw = call("quick_classify", prompt, max_tokens=500)
        # Extract JSON from response
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass

    return {
        "required_skills": [],
        "nice_to_have": [],
        "experience_level": "unknown",
        "keywords": [],
        "summary": desc[:200] if desc else "No description available",
    }


def _gap_analysis(job: dict, criteria: dict) -> dict:
    """Groq analyses the gap between your skills and job requirements."""
    required = criteria.get("required_skills", [])
    nice     = criteria.get("nice_to_have", [])
    your     = YOUR_PROFILE["skills"]

    have     = [s for s in required if any(s.lower() in y.lower() or y.lower() in s.lower() for y in your)]
    missing  = [s for s in required if s not in have]
    match_pct = round(len(have) / max(len(required), 1) * 100)

    prompt = f"""You are a career mentor reviewing a job fit for Omlan Hasan.

HIS PROFILE:
- Skills: {', '.join(YOUR_PROFILE['skills'])}
- Experience: {YOUR_PROFILE['experience_years']} years Python dev
- Education: {YOUR_PROFILE['education']}
- Publication: {YOUR_PROFILE['publication']}
- Seeking: {YOUR_PROFILE['seeking']}

JOB: {job.get('title')} at {job.get('company')}
Required skills: {', '.join(required)}
Nice to have: {', '.join(nice)}
He has: {', '.join(have)}
He's missing: {', '.join(missing)}
Match: {match_pct}%

Return ONLY valid JSON:
{{
  "match_score": {match_pct},
  "verdict": "strong|good|stretch|skip",
  "verdict_reason": "one sentence why",
  "strengths": ["what he has that directly matches"],
  "gaps": ["what he's missing"],
  "gap_projects": [
    {{
      "gap": "missing skill name",
      "project": "specific project to build that proves this skill",
      "time_weeks": 2,
      "difficulty": "easy|medium|hard"
    }}
  ],
  "apply_priority": 1,
  "cover_letter_angle": "one sentence on the strongest angle for his cover letter"
}}"""

    try:
        raw = call("post_generation", prompt, max_tokens=800)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            result["match_score"]  = match_pct
            result["skills_have"]  = have
            result["skills_missing"] = missing
            return result
    except Exception:
        pass

    return {
        "match_score":    match_pct,
        "verdict":        "unknown",
        "skills_have":    have,
        "skills_missing": missing,
        "gap_projects":   [],
    }


def _fetch_arbeitnow(url: str, params: dict, limit: int) -> list[dict]:
    resp = httpx.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    jobs = data.get("data", [])[:limit]
    return [_normalise_arbeitnow(j) for j in jobs]


def _normalise_arbeitnow(j: dict) -> dict:
    return {
        "id":          j.get("slug", ""),
        "title":       j.get("title", ""),
        "company":     j.get("company_name", ""),
        "location":    j.get("location", "Remote" if j.get("remote") else "Germany"),
        "url":         j.get("url", ""),
        "description": j.get("description", ""),
        "tags":        j.get("tags", []),
        "remote":      j.get("remote", False),
        "posted":      j.get("created_at", ""),
    }


def _fetch_remoteok(url: str, keywords: list[str], limit: int) -> list[dict]:
    resp = httpx.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list) and data and "legal" in str(data[0]):
        data = data[1:]  # RemoteOK prepends legal notice

    results = []
    for j in data:
        text = (j.get("position","") + " " + " ".join(j.get("tags",[])) + " " + j.get("description","")).lower()
        if any(kw.lower() in text for kw in keywords):
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


def _fetch_rss(url: str, keywords: list[str], limit: int) -> list[dict]:
    feed    = feedparser.parse(url)
    results = []
    for entry in feed.entries:
        text = (entry.get("title","") + " " + entry.get("summary","")).lower()
        if any(kw.lower() in text for kw in keywords):
            results.append({
                "id":          entry.get("id",""),
                "title":       entry.get("title",""),
                "company":     entry.get("author",""),
                "location":    "Remote",
                "url":         entry.get("link",""),
                "description": re.sub(r'<[^>]+>', '', entry.get("summary","")),
                "tags":        [],
                "remote":      True,
                "posted":      "",
            })
        if len(results) >= limit:
            break
    return results


def _save_cache(jobs: list[dict]):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": datetime.utcnow().isoformat(), "jobs": jobs}, f, indent=2)


def load_cache() -> list[dict]:
    if not CACHE_FILE.exists():
        return []
    with open(CACHE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("jobs", [])


def cache_age_hours() -> float:
    if not CACHE_FILE.exists():
        return 999
    with open(CACHE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    fetched = datetime.fromisoformat(data.get("fetched_at", "2000-01-01"))
    return (datetime.utcnow() - fetched).total_seconds() / 3600
