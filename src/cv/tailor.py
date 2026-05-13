"""
cv/tailor.py  v2
----------------
- Generates tailored CV bullets + cover letter per job
- Auto-saves every output to data/cv_outputs/ (named by job + date)
- Stores history in data/cv_history.json
- Viewable and downloadable from dashboard
- Master CV editable from dashboard (data/master_cv.json)
"""

import json, re
from datetime import datetime
from pathlib import Path
from src.models.router import call

DATA_DIR   = Path("data")
CV_DIR     = DATA_DIR / "cv_outputs"
MASTER_CV  = DATA_DIR / "master_cv.json"
CV_HISTORY = DATA_DIR / "cv_history.json"
DATA_DIR.mkdir(exist_ok=True)
CV_DIR.mkdir(exist_ok=True)

DEFAULT_CV = {
    "name": "Omlan Hasan",
    "contact": "omlanhasan@gmail.com | Dresden, Germany | github.com/OmlanHasan007",
    "experience": [
        {
            "role": "Python Developer",
            "company": "Authentic Four Technology",
            "duration": "4+ years",
            "bullets": [
                "Built data-driven Python applications for business automation and reporting",
                "Designed and maintained REST APIs handling production traffic",
                "Worked with SQL databases and ETL data pipelines",
            ]
        }
    ],
    "projects": [
        {
            "name": "Career OS — Personal Brand Automation",
            "url": "github.com/OmlanHasan007/personal-brand-automation",
            "bullets": [
                "Built multi-model AI pipeline (Groq + Gemini) with zero API cost for LinkedIn automation",
                "Implemented LinkedIn OAuth 2.0, job scraper (4 sources), FastAPI + SQLite tracker",
                "Web dashboard with 8 modules: job hunt, CV tailor, interview coach, learning radar",
            ]
        },
        {
            "name": "Conversational RAG Pipeline",
            "bullets": [
                "Built LangChain RAG with chat history injection — 73% improvement in follow-up retrieval",
                "Semantic chunking on medical documents with FastAPI backend and SQLite storage",
            ]
        },
        {
            "name": "ECG Heart Block Detection (HIS 2022 — Published)",
            "bullets": [
                "Co-authored peer-reviewed paper on automated cardiac anomaly detection using YOLOv4",
                "Trained on ECG datasets — presented at HIS 2022 international conference",
            ]
        },
    ],
    "skills": {
        "ml_ai":   ["PyTorch","LangChain","LangGraph","RAG","YOLO","Hugging Face","vector databases"],
        "backend": ["FastAPI","SQLite","REST APIs","Python"],
        "devops":  ["Docker","GitHub Actions","Git","Linux"],
        "languages": ["Python (expert)","SQL (solid)","Bash"]
    },
    "education": "M.Sc. Computational Engineering — TU Dresden (ongoing)",
    "publication": "ECG Heart Block Detection Using YOLOv4 — HIS 2022 International Conference"
}


def load_master_cv() -> dict:
    if MASTER_CV.exists():
        with open(MASTER_CV, encoding="utf-8") as f:
            return json.load(f)
    DATA_DIR.mkdir(exist_ok=True)
    with open(MASTER_CV, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CV, f, indent=2)
    return DEFAULT_CV


def save_master_cv(cv: dict):
    with open(MASTER_CV, "w", encoding="utf-8") as f:
        json.dump(cv, f, indent=2)


def tailor_cv(job: dict, criteria: dict) -> dict:
    """
    Generate tailored CV bullets + cover letter.
    Auto-saves to data/cv_outputs/ and logs to cv_history.json.
    Returns full result dict.
    """
    cv       = load_master_cv()
    required = criteria.get("required_skills", [])
    keywords = criteria.get("keywords", [])
    summary  = criteria.get("summary", "")
    gap      = job.get("gap", {}) or {}

    # ── Tailor CV bullets ─────────────────────────────────────────────────────
    bullets_prompt = f"""Rewrite these CV bullets to best match this specific job.

JOB: {job.get('job_title','') or job.get('title','')} at {job.get('company','')}
Required skills: {', '.join(required)}
Keywords to include: {', '.join(keywords)}
Role summary: {summary}
Strongest angle: {gap.get('cover_letter_angle','his RAG and applied AI experience')}

MASTER CV:
{json.dumps(cv, indent=2)}

Rules:
1. Reorder so most relevant bullets appear first in each section
2. Reword bullets using exact job keywords where they honestly apply
3. Never invent experience — only reframe what exists
4. Each bullet: action verb + specific detail + metric where possible
5. If a required skill is missing entirely, flag it: [GAP: recommend building X]
6. skills_to_highlight: list the 6-8 skills most relevant for this job

Return ONLY valid JSON (no markdown):
{{
  "experience": [
    {{"role":"...", "company":"...", "duration":"...", "bullets":["..."]}}
  ],
  "projects": [
    {{"name":"...", "bullets":["..."]}}
  ],
  "skills_to_highlight": ["skill1","skill2"],
  "gaps_flagged": ["gap1","gap2"]
}}"""

    # ── Cover letter ──────────────────────────────────────────────────────────
    cover_prompt = f"""Write a professional 3-paragraph cover letter for Omlan Hasan.

JOB: {job.get('job_title','') or job.get('title','')} at {job.get('company','')}
Location: {job.get('location','')}
Role: {summary}
His strongest angle: {gap.get('cover_letter_angle','his published research and applied LLM experience')}
His matching skills: {', '.join((gap.get('skills_have') or [])[:6])}
Contact: omlanhasan@gmail.com | Dresden, Germany

Paragraph 1 (HOOK — 2-3 sentences):
Research something specific about {job.get('company','')} — a product, research area, or initiative.
Reference it directly. Never write "I am excited to apply."

Paragraph 2 (PROOF — 3-4 sentences):
His single most relevant project for this role with one concrete metric.
Connect it explicitly to what this role needs.

Paragraph 3 (CLOSE — 2 sentences):
Short, confident. Mention Dresden availability + remote flexibility. Invite a call.

Hard rules:
- 190-220 words total
- No "passionate about", no "journey", no "I believe I would be a great fit"
- First person, professional German business standard
- Output ONLY the 3 paragraphs. No greeting, no sign-off, no subject line."""

    # ── Generate ──────────────────────────────────────────────────────────────
    bullets, cover_letter = {}, ""
    try:
        raw = call("cover_letter", bullets_prompt, max_tokens=1000)
        m   = re.search(r'\{.*\}', raw, re.DOTALL)
        bullets = json.loads(m.group()) if m else {"raw": raw}
    except Exception as e:
        bullets = {"error": str(e)}

    try:
        cover_letter = call("cover_letter", cover_prompt, max_tokens=600)
    except Exception as e:
        cover_letter = f"Error: {e}"

    # ── ATS score ─────────────────────────────────────────────────────────────
    output_text  = json.dumps(bullets).lower() + cover_letter.lower()
    matched_kw   = [k for k in keywords if k.lower() in output_text]
    ats_score    = round(len(matched_kw) / max(len(keywords), 1) * 100)

    result = {
        "job_title":     job.get("job_title","") or job.get("title",""),
        "company":       job.get("company",""),
        "generated_at":  datetime.utcnow().isoformat(),
        "bullets":       bullets,
        "cover_letter":  cover_letter,
        "keywords_used": matched_kw,
        "ats_score":     ats_score,
    }

    # ── Auto-save ─────────────────────────────────────────────────────────────
    _save_output(result)
    return result


def _save_output(result: dict):
    """Save CV output as markdown file + log to history."""
    now      = datetime.utcnow()
    slug     = re.sub(r'[^a-z0-9]+', '_', (result["company"]+"_"+result["job_title"]).lower())[:40]
    filename = f"{now.strftime('%Y-%m-%d')}_{slug}.md"
    filepath = CV_DIR / filename

    # Build readable markdown
    bullets  = result.get("bullets", {})
    md = f"""# CV & Cover Letter — {result['job_title']} @ {result['company']}
Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}
ATS score: {result['ats_score']}% | Keywords matched: {', '.join(result['keywords_used'])}

---

## Cover letter

{result['cover_letter']}

---

## Tailored CV bullets

### Experience
"""
    for exp in (bullets.get("experience") or []):
        md += f"\n**{exp.get('role','')} — {exp.get('company','')}** ({exp.get('duration','')})\n"
        for b in exp.get("bullets", []):
            md += f"- {b}\n"

    md += "\n### Projects\n"
    for proj in (bullets.get("projects") or []):
        md += f"\n**{proj.get('name','')}**\n"
        for b in proj.get("bullets", []):
            md += f"- {b}\n"

    if bullets.get("skills_to_highlight"):
        md += f"\n### Skills to highlight\n{', '.join(bullets['skills_to_highlight'])}\n"

    if bullets.get("gaps_flagged"):
        md += f"\n### Gaps to address\n"
        for g in bullets["gaps_flagged"]:
            md += f"- {g}\n"

    filepath.write_text(md, encoding="utf-8")

    # Log to history
    history = []
    if CV_HISTORY.exists():
        with open(CV_HISTORY, encoding="utf-8") as f:
            history = json.load(f)
    history.append({
        "filename":     filename,
        "job_title":    result["job_title"],
        "company":      result["company"],
        "ats_score":    result["ats_score"],
        "generated_at": result["generated_at"],
    })
    with open(CV_HISTORY, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_history() -> list[dict]:
    if not CV_HISTORY.exists(): return []
    with open(CV_HISTORY, encoding="utf-8") as f:
        return json.load(f)


def get_output(filename: str) -> str:
    path = CV_DIR / filename
    if not path.exists(): return ""
    return path.read_text(encoding="utf-8")
