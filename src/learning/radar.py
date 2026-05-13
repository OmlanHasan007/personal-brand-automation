"""
learning/radar.py
-----------------
Finds papers, courses, and projects aligned with your job criteria and gaps.
Uses Gemini (free) for relevance scoring and recommendations.
"""

import json
from datetime import datetime
from pathlib import Path
import feedparser
from src.models.router import call

DATA_DIR       = Path("data")
READING_FILE   = DATA_DIR / "reading_list.json"

ARXIV_FEEDS = {
    "cs.LG":  "https://rss.arxiv.org/rss/cs.LG",
    "cs.AI":  "https://rss.arxiv.org/rss/cs.AI",
    "cs.CV":  "https://rss.arxiv.org/rss/cs.CV",
    "cs.CL":  "https://rss.arxiv.org/rss/cs.CL",
}

YOUR_FOCUS = [
    "RAG", "LLM agents", "medical imaging", "ECG", "object detection",
    "LangChain", "LangGraph", "fine-tuning", "LoRA", "MLOps",
    "vector databases", "transformers", "computer vision"
]


def find_papers_for_gaps(gap_skills: list[str], limit: int = 5) -> list[dict]:
    """Find ArXiv papers that would help fill specific skill gaps."""
    all_papers = []
    for feed_id, url in ARXIV_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:30]:
                text = entry.get("title","") + " " + entry.get("summary","")
                relevance = sum(
                    1 for skill in gap_skills + YOUR_FOCUS
                    if skill.lower() in text.lower()
                )
                if relevance > 0:
                    all_papers.append({
                        "title":     entry.get("title",""),
                        "url":       entry.get("link",""),
                        "abstract":  entry.get("summary","")[:1500],
                        "feed":      feed_id,
                        "relevance": relevance,
                    })
        except Exception:
            pass

    papers = sorted(all_papers, key=lambda x: x["relevance"], reverse=True)[:limit]

    for p in papers:
        p["summary"] = _summarise_for_learning(p["title"], p["abstract"])

    return papers


def generate_learning_plan(job: dict, gap_analysis: dict) -> dict:
    """
    Generate a structured learning plan to close gaps for a specific job.
    Returns: weekly plan, projects to build, papers to read.
    """
    gaps      = gap_analysis.get("gaps", [])
    projects  = gap_analysis.get("gap_projects", [])
    job_title = job.get("title", "AI/ML role")

    if not gaps:
        return {"message": "No significant gaps identified — strong match!", "plan": []}

    prompt = f"""Create a realistic learning plan for Omlan Hasan to close these skill gaps for: {job_title}

HIS CURRENT SKILLS: PyTorch, LangChain, LangGraph, RAG, YOLO, FastAPI, SQLite, Docker, GitHub Actions
GAPS TO CLOSE: {', '.join(gaps)}
GAP PROJECTS SUGGESTED: {json.dumps(projects, indent=2)}

Create a 4-week sprint plan. Return ONLY valid JSON:
{{
  "total_weeks": 4,
  "weekly_hours": 10,
  "weeks": [
    {{
      "week": 1,
      "focus": "skill focus area",
      "goal": "specific measurable goal by end of week",
      "tasks": [
        {{"task": "specific task", "hours": 2, "resource": "free resource URL or name", "output": "what to produce"}}
      ],
      "project_milestone": "what part of the project to complete"
    }}
  ],
  "capstone_project": {{
    "name": "project name",
    "description": "what it does",
    "skills_proven": ["skill1", "skill2"],
    "github_readme_pitch": "one line for README"
  }},
  "free_resources": [
    {{"name": "resource name", "url": "url", "type": "video|course|docs|paper"}}
  ]
}}"""

    try:
        raw = call("post_generation", prompt, max_tokens=1200)
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        return {"error": str(e), "gaps": gaps, "projects": projects}


def save_to_reading_list(papers: list[dict], tag: str = ""):
    DATA_DIR.mkdir(exist_ok=True)
    reading_list = []
    if READING_FILE.exists():
        with open(READING_FILE, encoding="utf-8") as f:
            reading_list = json.load(f)
    for p in papers:
        p["added_at"] = datetime.utcnow().isoformat()
        p["tag"] = tag
        p["read"] = False
        reading_list.append(p)
    with open(READING_FILE, "w", encoding="utf-8") as f:
        json.dump(reading_list, f, indent=2)


def get_reading_list() -> list[dict]:
    if not READING_FILE.exists():
        return []
    with open(READING_FILE, encoding="utf-8") as f:
        return json.load(f)


def mark_read(index: int):
    rl = get_reading_list()
    if 0 <= index < len(rl):
        rl[index]["read"] = True
        with open(READING_FILE, "w", encoding="utf-8") as f:
            json.dump(rl, f, indent=2)


def _summarise_for_learning(title: str, abstract: str) -> str:
    prompt = f"""Summarise this paper in 2 sentences for an ML practitioner who wants to implement it.
Focus: what it does + one concrete result.
Title: {title}
Abstract: {abstract[:800]}
Output only the 2 sentences:"""
    try:
        return call("paper_summary", prompt, max_tokens=150)
    except Exception:
        return abstract[:200]
