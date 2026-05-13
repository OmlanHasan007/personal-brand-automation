"""
dashboard/app.py  —  Career OS Full Dashboard
----------------------------------------------
8 modules matching the Career OS:
  / home          Overview + metrics + quick actions
  / hunt          Job hunt radar — search + criteria + gap analysis
  / tracker       Application tracker — full pipeline management
  / documents     CV tailor + cover letter generator
  / interview     Mock interview coach — questions + feedback
  / english       English practice system + speaking tips
  / projects      Project pipeline — what to build + GitHub checklist
  / content       Content & brand — draft + edit + publish
  / learning      Learning radar — papers + reading list + study plan
"""

import json, os, re
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

app = FastAPI(title="Career OS", docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_DIR     = Path("data")
DRAFTS_DIR   = Path("drafts")
PROMPTS_DIR  = Path("prompts")
LOGS_DIR     = Path("logs")
HISTORY_FILE = DATA_DIR / "post_history.json"
DATA_DIR.mkdir(exist_ok=True)
DRAFTS_DIR.mkdir(exist_ok=True)

# ── DB ────────────────────────────────────────────────────────────────────────
engine  = create_engine(f"sqlite:///{DATA_DIR/'jobs.db'}", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base    = declarative_base()

class Job(Base):
    __tablename__ = "applications"
    id            = Column(Integer, primary_key=True)
    job_title     = Column(String, nullable=False)
    company       = Column(String, nullable=False)
    location      = Column(String, default="")
    job_url       = Column(String, default="")
    source        = Column(String, default="")
    stage         = Column(String, default="Applied")
    applied_date  = Column(Date,   default=date.today)
    deadline      = Column(Date,   nullable=True)
    followup_date = Column(Date,   nullable=True)
    notes         = Column(Text,   default="")
    is_remote     = Column(Boolean, default=False)
    contact_name  = Column(String, default="")
    criteria_json = Column(Text,   default="")
    gap_json      = Column(Text,   default="")
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

STAGES = ["Applied", "Phone screen", "Interview", "Offer", "Rejected", "Withdrawn"]

# ── Pydantic ──────────────────────────────────────────────────────────────────
class JobCreate(BaseModel):
    job_title: str; company: str; location: str = ""; job_url: str = ""
    source: str = ""; stage: str = "Applied"; notes: str = ""; is_remote: bool = False

class JobUpdate(BaseModel):
    stage: Optional[str] = None; notes: Optional[str] = None
    followup_date: Optional[date] = None; contact_name: Optional[str] = None

class DraftReq(BaseModel):
    topic: str = "project"; tone: str = "professional"; context: str = ""

class PublishReq(BaseModel):
    text: str

class AnalyseReq(BaseModel):
    job_id: int

class InterviewReq(BaseModel):
    q_type: str = "technical_llm"; company_type: str = "german_engineering"

class EvalReq(BaseModel):
    question: str; answer: str; q_type: str = "technical_llm"

class CVReq(BaseModel):
    job_id: int

class PlanReq(BaseModel):
    job_id: int

# ── helpers ───────────────────────────────────────────────────────────────────
def jd(j: Job) -> dict:
    return {
        "id": j.id, "job_title": j.job_title, "company": j.company,
        "location": j.location, "job_url": j.job_url, "source": j.source,
        "stage": j.stage, "applied_date": str(j.applied_date) if j.applied_date else None,
        "followup_date": str(j.followup_date) if j.followup_date else None,
        "notes": j.notes, "is_remote": j.is_remote,
        "criteria": json.loads(j.criteria_json) if j.criteria_json else None,
        "gap": json.loads(j.gap_json) if j.gap_json else None,
        "updated_at": j.updated_at.isoformat() if j.updated_at else None,
    }

def env_status() -> dict:
    try:
        from src.models.router import available_models
        m = available_models()
    except Exception:
        m = {}
    return {
        "groq":     m.get("groq", False),
        "gemini":   m.get("gemini", False),
        "github":   bool(os.environ.get("GITHUB_TOKEN")),
        "linkedin": os.path.exists("data/linkedin_token.json") or bool(os.environ.get("LINKEDIN_ACCESS_TOKEN")),
    }

def list_drafts() -> list[dict]:
    if not DRAFTS_DIR.exists(): return []
    result = []
    for f in sorted(DRAFTS_DIR.glob("*.md"), reverse=True):
        content = f.read_text(encoding="utf-8")
        match = re.search(r"## POST TEXT.*?\n\n(.*?)\n\n## CONTEXT", content, re.DOTALL)
        text = match.group(1).strip() if match else ""
        result.append({"filename": f.name, "text": text, "words": len(text.split()), "date": f.name[:10]})
    return result

def post_history() -> list:
    if not HISTORY_FILE.exists(): return []
    with open(HISTORY_FILE, encoding="utf-8") as f: return json.load(f)

# ── API: status ───────────────────────────────────────────────────────────────
@app.get("/api/status")
def api_status():
    db = Session()
    jobs = db.query(Job).all(); db.close()
    hist = post_history()
    return {
        "env":         env_status(),
        "jobs_total":  len(jobs),
        "jobs_active": sum(1 for j in jobs if j.stage in ("Phone screen","Interview")),
        "jobs_applied": sum(1 for j in jobs if j.stage == "Applied"),
        "drafts":      len(list_drafts()),
        "published":   sum(1 for p in hist if p.get("posted")),
        "last_post":   hist[-1]["generated_at"][:10] if hist else None,
    }

# ── API: job hunt ─────────────────────────────────────────────────────────────
@app.get("/api/hunt/search")
def api_search_jobs(sources: str = "arbeitnow,remoteok", limit: int = 8, refresh: bool = False):
    from src.jobs.scraper import search_jobs, load_cache, cache_age_hours
    if not refresh and cache_age_hours() < 6:
        return {"jobs": load_cache(), "from_cache": True}
    jobs = search_jobs(sources=sources.split(","), limit_per_source=limit)
    return {"jobs": jobs, "from_cache": False}

@app.post("/api/hunt/analyse")
def api_analyse_job(req: AnalyseReq):
    db  = Session()
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job: raise HTTPException(404)
    job_dict = jd(job)
    from src.jobs.scraper import analyse_job
    result = analyse_job(job_dict)
    job.criteria_json = json.dumps(result.get("criteria", {}))
    job.gap_json      = json.dumps(result.get("gap_analysis", {}))
    job.updated_at    = datetime.utcnow()
    db.commit(); db.close()
    return result

@app.post("/api/hunt/add-found")
def api_add_found_job(body: dict):
    """Add a job found in the search to the tracker."""
    db = Session()
    j  = Job(
        job_title = body.get("title",""),
        company   = body.get("company",""),
        location  = body.get("location",""),
        job_url   = body.get("url",""),
        source    = body.get("source_name","Job search"),
        is_remote = body.get("remote", False),
        notes     = f"Tags: {', '.join(body.get('tags',[]))}"
    )
    j.followup_date = date.today() + timedelta(days=7)
    db.add(j); db.commit(); db.refresh(j); db.close()
    return jd(j)

# ── API: tracker ──────────────────────────────────────────────────────────────
@app.get("/api/jobs")
def api_jobs():
    db = Session()
    jobs = db.query(Job).order_by(Job.applied_date.desc()).all()
    db.close()
    return [jd(j) for j in jobs]

@app.post("/api/jobs", status_code=201)
def api_add_job(job: JobCreate):
    db = Session()
    j  = Job(**job.model_dump(), applied_date=date.today(), followup_date=date.today()+timedelta(days=7))
    db.add(j); db.commit(); db.refresh(j); db.close()
    return jd(j)

@app.patch("/api/jobs/{jid}")
def api_update_job(jid: int, u: JobUpdate):
    db = Session()
    j  = db.query(Job).filter(Job.id == jid).first()
    if not j: raise HTTPException(404)
    for k,v in u.model_dump(exclude_none=True).items(): setattr(j,k,v)
    j.updated_at = datetime.utcnow()
    db.commit(); db.refresh(j); db.close()
    return jd(j)

@app.delete("/api/jobs/{jid}")
def api_del_job(jid: int):
    db = Session()
    j  = db.query(Job).filter(Job.id == jid).first()
    if not j: raise HTTPException(404)
    db.delete(j); db.commit(); db.close()
    return {"deleted": jid}

@app.get("/api/jobs/stats")
def api_job_stats():
    db = Session(); jobs = db.query(Job).all(); db.close()
    if not jobs: return {"total":0}
    by_stage = {}
    for j in jobs: by_stage[j.stage] = by_stage.get(j.stage,0)+1
    responded = sum(1 for j in jobs if j.stage != "Applied")
    return {"total":len(jobs), "by_stage":by_stage,
            "response_rate": round(responded/len(jobs)*100,1),
            "active": sum(1 for j in jobs if j.stage in ("Phone screen","Interview")),
            "offers": by_stage.get("Offer",0)}

# ── API: CV & cover letter ────────────────────────────────────────────────────
@app.post("/api/cv/tailor")
def api_tailor_cv(req: CVReq):
    db  = Session()
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job: raise HTTPException(404)
    if not job.criteria_json: raise HTTPException(400, "Analyse this job first (Job Radar → Analyse)")
    from src.cv.tailor import tailor_cv
    result = tailor_cv(jd(job), json.loads(job.criteria_json))
    db.close()
    return result

# ── API: interview ────────────────────────────────────────────────────────────
@app.post("/api/interview/question")
def api_question(req: InterviewReq):
    from src.interview.coach import generate_question
    return generate_question(req.q_type, req.company_type)

@app.post("/api/interview/evaluate")
def api_evaluate(req: EvalReq):
    from src.interview.coach import evaluate_answer
    return evaluate_answer(req.question, req.answer, req.q_type)

@app.get("/api/interview/history")
def api_interview_history():
    from src.interview.coach import get_history, get_weak_areas
    return {"sessions": get_history()[-5:], "weak_areas": get_weak_areas()}

# ── API: learning ─────────────────────────────────────────────────────────────
@app.post("/api/learning/plan")
def api_learning_plan(req: PlanReq):
    db  = Session()
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job: raise HTTPException(404)
    if not job.gap_json: raise HTTPException(400, "Analyse this job first")
    from src.learning.radar import generate_learning_plan
    result = generate_learning_plan(jd(job), json.loads(job.gap_json))
    db.close()
    return result

@app.get("/api/learning/papers")
def api_learning_papers(gaps: str = ""):
    from src.learning.radar import find_papers_for_gaps
    gap_list = [g.strip() for g in gaps.split(",")] if gaps else []
    return find_papers_for_gaps(gap_list or ["RAG","LLM","fine-tuning"], limit=6)

@app.get("/api/learning/reading-list")
def api_reading_list():
    from src.learning.radar import get_reading_list
    return get_reading_list()

# ── API: content / post ───────────────────────────────────────────────────────
@app.post("/api/draft")
def api_draft(req: DraftReq):
    from src.content.generator import generate_draft
    return generate_draft(topic=req.topic, tone=req.tone, context=req.context)

@app.get("/api/drafts")
def api_drafts():
    return list_drafts()

@app.post("/api/publish")
def api_publish(req: PublishReq):
    from src.linkedin.poster import post_to_linkedin
    result = post_to_linkedin(req.text)
    hist = post_history()
    if hist:
        hist[-1]["posted"] = True
        with open(HISTORY_FILE,"w",encoding="utf-8") as f: json.dump(hist,f,indent=2)
    return {"ok": True, "url": result.get("url","")}

# ── API: papers ───────────────────────────────────────────────────────────────
@app.get("/api/papers")
def api_papers(feed: str = "arxiv_cs_lg", limit: int = 5):
    from src.content.rss_reader import fetch_papers
    return fetch_papers(feed_name=feed, limit=limit)

# ── API: prompts ──────────────────────────────────────────────────────────────
@app.get("/api/prompts")
def api_prompts():
    if not PROMPTS_DIR.exists(): return []
    return [{"filename": f.name, "title": f.stem.replace("_"," ").title()}
            for f in sorted(PROMPTS_DIR.glob("*.md")) if f.name != "README.md"]

@app.get("/api/prompts/{filename}")
def api_prompt(filename: str):
    p = PROMPTS_DIR / filename
    if not p.exists(): raise HTTPException(404)
    return {"content": p.read_text(encoding="utf-8")}

# ── HTML ──────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def serve():
    return open(Path(__file__).parent / "index.html", encoding="utf-8").read()

def start(port: int = 8000):
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
