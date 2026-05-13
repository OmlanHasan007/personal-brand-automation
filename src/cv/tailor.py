"""
cv/tailor.py
------------
Generates tailored CV bullets and cover letters for a specific job.
Uses Groq (free) for generation.
Reads master CV from data/master_cv.json (you fill this once).
"""

import json
from pathlib import Path
from src.models.router import call

DATA_DIR    = Path("data")
MASTER_CV   = DATA_DIR / "master_cv.json"

# Default master CV — copy to data/master_cv.json and edit with your real results
DEFAULT_CV = {
    "experience": [
        {
            "role": "Python Developer",
            "company": "Authentic Four Technology",
            "years": "4+",
            "bullets": [
                "Built data-driven Python applications for business automation",
                "Designed and maintained REST APIs and backend systems",
                "Worked with SQL databases and ETL data pipelines",
            ]
        }
    ],
    "projects": [
        {
            "name": "Conversational RAG Pipeline",
            "bullets": [
                "Built LangChain RAG pipeline with chat history injection for follow-up question handling",
                "Implemented semantic chunking on medical documents — 73% improvement in retrieval relevance",
                "Deployed with FastAPI backend and SQLite storage",
            ]
        },
        {
            "name": "ECG Heart Block Detection (HIS 2022)",
            "bullets": [
                "Co-authored peer-reviewed paper on automated cardiac anomaly detection",
                "Trained YOLOv4 on ECG datasets — achieved [F1 score] on [dataset]",
                "Presented at HIS 2022 international conference",
            ]
        },
        {
            "name": "Personal Brand Automation",
            "bullets": [
                "Built multi-model pipeline (Groq + Gemini) for automated LinkedIn posting",
                "Implemented LinkedIn OAuth 2.0, GitHub Actions CI/CD, SQLite job tracker",
                "Zero API cost architecture — routes tasks to best free model per task type",
            ]
        },
    ],
    "skills": {
        "ml_ai": ["PyTorch", "LangChain", "LangGraph", "RAG", "YOLO", "Hugging Face", "vector databases"],
        "backend": ["FastAPI", "SQLite", "REST APIs", "Python"],
        "devops": ["Docker", "GitHub Actions", "Git", "Linux"],
        "languages": ["Python (expert)", "SQL (solid)", "Bash"],
    },
    "education": "M.Sc. Computational Engineering, TU Dresden (ongoing)",
    "publication": "ECG Heart Block Detection Using YOLOv4 — HIS 2022",
}


def load_master_cv() -> dict:
    if MASTER_CV.exists():
        with open(MASTER_CV, encoding="utf-8") as f:
            return json.load(f)
    # First run — save default
    DATA_DIR.mkdir(exist_ok=True)
    with open(MASTER_CV, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CV, f, indent=2)
    return DEFAULT_CV


def tailor_cv(job: dict, criteria: dict) -> dict:
    """
    Generate tailored CV bullets and cover letter for a specific job.
    Returns dict with: bullets, cover_letter, keywords_used, ats_score
    """
    cv = load_master_cv()
    required = criteria.get("required_skills", [])
    keywords = criteria.get("keywords", [])
    summary  = criteria.get("summary", "")
    gap      = job.get("gap_analysis", {})

    # --- Tailor CV bullets ---
    bullets_prompt = f"""Rewrite these CV bullets to best match this job.

JOB: {job.get('title')} at {job.get('company')}
Required skills: {', '.join(required)}
Key keywords: {', '.join(keywords)}
Role summary: {summary}

MASTER CV BULLETS:
{json.dumps(cv, indent=2)}

Rules:
1. Reorder bullets so the most relevant appear first
2. Reword using exact keywords from the job posting where they honestly apply
3. Never invent experience he does not have
4. Each bullet: strong action verb + specific detail + metric where possible
5. Flag gaps: if a requirement cannot be matched, add [GAP: suggest how to address]
6. Return as JSON: {{"experience": [...], "projects": [...], "skills_to_highlight": [...]}}
Output ONLY valid JSON."""

    cover_prompt = f"""Write a 3-paragraph cover letter for Omlan Hasan for this role.

JOB: {job.get('title')} at {job.get('company')}
Location: {job.get('location')}
Role summary: {summary}
His strongest angle for this role: {gap.get('cover_letter_angle', 'his RAG and LLM experience')}
His key matching skills: {', '.join(gap.get('skills_have', [])[:5])}

Rules:
- P1: Specific hook about this company/role (research something real about them)
- P2: His most relevant project with one concrete metric
- P3: Short confident close — invite conversation, mention availability
- 180–220 words total
- No "I am passionate about", no "I believe I would be a great fit"
- First person, German professional standard
Output ONLY the letter body (no salutation, no date)."""

    try:
        raw_bullets  = call("cover_letter", bullets_prompt, max_tokens=1000)
        match = __import__('re').search(r'\{.*\}', raw_bullets, __import__('re').DOTALL)
        bullets = json.loads(match.group()) if match else {"raw": raw_bullets}
    except Exception:
        bullets = {}

    try:
        cover_letter = call("cover_letter", cover_prompt, max_tokens=600)
    except Exception as e:
        cover_letter = f"Error generating cover letter: {e}"

    # ATS score — how many keywords appear in the tailored output
    output_text = json.dumps(bullets).lower() + cover_letter.lower()
    matched_kw  = [k for k in keywords if k.lower() in output_text]
    ats_score   = round(len(matched_kw) / max(len(keywords), 1) * 100)

    return {
        "bullets":       bullets,
        "cover_letter":  cover_letter,
        "keywords_used": matched_kw,
        "ats_score":     ats_score,
        "job_title":     job.get("title"),
        "company":       job.get("company"),
    }
