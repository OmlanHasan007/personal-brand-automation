"""
dashboard/app.py  v3
--------------------
All API endpoints for Career OS dashboard.
"""
import json, os, re
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
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

class CVReq(BaseModel):
    job_id: int

class PlanReq(BaseModel):
    job_id: int

class SearchReq(BaseModel):
    source_ids: List[str] = []
    title_filter: str = ""
    refresh: bool = False

class SourceToggle(BaseModel):
    source_id: str
    enabled: bool

class AddSource(BaseModel):
    id: str
    label: str
    type: str   # "arbeitnow_api" | "remoteok_json" | "rss"
    url: str = ""
    params: dict = {}

class JobTitlesUpdate(BaseModel):
    titles: List[str]

class InterviewLearnReq(BaseModel):
    topic_id: str
    q_type: str = "technical_llm"

class InterviewCheckReq(BaseModel):
    topic_id: str
    question: str
    answer: str

class InterviewQuestionReq(BaseModel):
    q_type: str = "technical_llm"
    company_type: str = "german_engineering"
    topic_id: str = ""
    job_id: int = 0

class InterviewEvalReq(BaseModel):
    question: str; answer: str; q_type: str = "technical_llm"

class JobQuestionsReq(BaseModel):
    job_id: int
    company_type: str = "german_engineering"
    count: int = 5

class MasterCVUpdate(BaseModel):
    cv: dict

# ── Helpers ───────────────────────────────────────────────────────────────────
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

def list_drafts() -> list:
    if not DRAFTS_DIR.exists(): return []
    result = []
    for f in sorted(DRAFTS_DIR.glob("*.md"), reverse=True):
        content = f.read_text(encoding="utf-8")
        m = re.search(r"## POST TEXT.*?\n\n(.*?)\n\n## CONTEXT", content, re.DOTALL)
        text = m.group(1).strip() if m else ""
        result.append({"filename": f.name, "text": text, "words": len(text.split()), "date": f.name[:10]})
    return result

def post_history() -> list:
    if not HISTORY_FILE.exists(): return []
    with open(HISTORY_FILE, encoding="utf-8") as f: return json.load(f)

# ── STATUS ────────────────────────────────────────────────────────────────────
@app.get("/api/status")
def api_status():
    db = Session()
    try:
        jobs = db.query(Job).all()
    except Exception:
        jobs = []
    finally:
        db.close()
    hist = post_history()
    from src.interview.coach import get_progress
    prog = get_progress()
    return {
        "env":          env_status(),
        "jobs_total":   len(jobs),
        "jobs_active":  sum(1 for j in jobs if j.stage in ("Phone screen","Interview")),
        "drafts":       len(list_drafts()),
        "published":    sum(1 for p in hist if p.get("posted")),
        "last_post":    hist[-1]["generated_at"][:10] if hist else None,
        "interview_sessions": prog.get("sessions", 0),
        "interview_avg": prog.get("avg_score", 0),
    }

# ── JOB HUNT ─────────────────────────────────────────────────────────────────
@app.post("/api/hunt/search")
def api_search(req: SearchReq):
    from src.jobs.scraper import search_jobs, load_cache, cache_age_hours
    if not req.refresh and not req.title_filter and cache_age_hours() < 6:
        return {"jobs": load_cache(), "from_cache": True}
    jobs = search_jobs(
        source_ids=req.source_ids or None,
        title_filter=req.title_filter,
        refresh=req.refresh
    )
    return {"jobs": jobs, "from_cache": False}

@app.get("/api/hunt/config")
def api_get_config():
    from src.jobs.scraper import load_config
    return load_config()

@app.post("/api/hunt/config/titles")
def api_update_titles(req: JobTitlesUpdate):
    from src.jobs.scraper import load_config, save_config
    cfg = load_config()
    cfg["job_titles"] = req.titles
    save_config(cfg)
    return {"ok": True, "titles": req.titles}

@app.post("/api/hunt/config/toggle-source")
def api_toggle_source(req: SourceToggle):
    from src.jobs.scraper import load_config, save_config
    cfg = load_config()
    if req.source_id in cfg["sources"]:
        cfg["sources"][req.source_id]["enabled"] = req.enabled
        save_config(cfg)
        return {"ok": True}
    raise HTTPException(404, "Source not found")

@app.post("/api/hunt/config/add-source")
def api_add_source(req: AddSource):
    from src.jobs.scraper import load_config, save_config
    cfg = load_config()
    cfg["sources"][req.id] = {
        "label": req.label, "type": req.type,
        "enabled": True, "url": req.url, "params": req.params
    }
    save_config(cfg)
    return {"ok": True}

@app.delete("/api/hunt/config/source/{source_id}")
def api_del_source(source_id: str):
    from src.jobs.scraper import load_config, save_config
    cfg = load_config()
    if source_id in cfg["sources"]:
        del cfg["sources"][source_id]
        save_config(cfg)
        return {"ok": True}
    raise HTTPException(404)

@app.post("/api/hunt/analyse")
def api_analyse(req: AnalyseReq):
    db  = Session()
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job: raise HTTPException(404)
    from src.jobs.scraper import analyse_job
    result = analyse_job(jd(job))
    job.criteria_json = json.dumps(result.get("criteria", {}))
    job.gap_json      = json.dumps(result.get("gap_analysis", {}))
    job.updated_at    = datetime.utcnow()
    db.commit(); db.close()
    return result

@app.post("/api/hunt/add-found")
def api_add_found(body: dict):
    db = Session()
    j  = Job(
        job_title = body.get("title",""),
        company   = body.get("company",""),
        location  = body.get("location",""),
        job_url   = body.get("url",""),
        source    = body.get("source_name","Job search"),
        is_remote = body.get("remote", False),
        notes     = "Tags: " + ", ".join(body.get("tags",[])),
        followup_date = date.today() + timedelta(days=7)
    )
    db.add(j); db.commit(); db.refresh(j); db.close()
    return jd(j)

# ── TRACKER ───────────────────────────────────────────────────────────────────
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
    return {"total":len(jobs),"by_stage":by_stage,
            "response_rate":round(responded/len(jobs)*100,1),
            "active":sum(1 for j in jobs if j.stage in ("Phone screen","Interview")),
            "offers":by_stage.get("Offer",0)}

# ── CV & COVER LETTER ────────────────────────────────────────────────────────
@app.post("/api/cv/tailor")
def api_tailor(req: CVReq):
    db  = Session()
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job: raise HTTPException(404)
    if not job.criteria_json:
        raise HTTPException(400, "Analyse this job first in Job Hunt Radar")
    from src.cv.tailor import tailor_cv
    result = tailor_cv(jd(job), json.loads(job.criteria_json))
    db.close()
    return result

@app.get("/api/cv/history")
def api_cv_history():
    from src.cv.tailor import get_history
    return get_history()

@app.get("/api/cv/output/{filename}")
def api_cv_output(filename: str):
    from src.cv.tailor import get_output
    content = get_output(filename)
    if not content: raise HTTPException(404)
    return PlainTextResponse(content)

@app.get("/api/cv/master")
def api_get_master_cv():
    from src.cv.tailor import load_master_cv
    return load_master_cv()

@app.post("/api/cv/master")
def api_save_master_cv(req: MasterCVUpdate):
    from src.cv.tailor import save_master_cv
    save_master_cv(req.cv)
    return {"ok": True}

# ── INTERVIEW ─────────────────────────────────────────────────────────────────
@app.get("/api/interview/curriculum")
def api_curriculum():
    from src.interview.coach import get_curriculum_with_progress
    return get_curriculum_with_progress()

@app.post("/api/interview/teach")
def api_teach(req: InterviewLearnReq):
    from src.interview.coach import teach_topic
    return teach_topic(req.topic_id, req.q_type)

@app.post("/api/interview/check")
def api_check(req: InterviewCheckReq):
    from src.interview.coach import check_understanding
    return check_understanding(req.topic_id, req.question, req.answer)

@app.post("/api/interview/question")
def api_question(req: InterviewQuestionReq):
    from src.interview.coach import generate_question
    job_skills = []
    if req.job_id:
        db  = Session()
        job = db.query(Job).filter(Job.id == req.job_id).first()
        if job and job.criteria_json:
            crit = json.loads(job.criteria_json)
            job_skills = crit.get("required_skills", [])
        db.close()
    return generate_question(req.q_type, req.company_type, req.topic_id, job_skills or None)

@app.post("/api/interview/evaluate")
def api_evaluate(req: InterviewEvalReq):
    from src.interview.coach import evaluate_answer
    return evaluate_answer(req.question, req.answer, req.q_type)

@app.post("/api/interview/job-questions")
def api_job_questions(req: JobQuestionsReq):
    from src.interview.coach import questions_from_job
    db  = Session()
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job: raise HTTPException(404)
    criteria = json.loads(job.criteria_json) if job.criteria_json else {}
    db.close()
    return questions_from_job(criteria, req.company_type, req.count)

@app.get("/api/interview/progress")
def api_progress():
    from src.interview.coach import get_progress, get_weak_areas, get_session_history
    return {
        "progress": get_progress(),
        "weak_areas": get_weak_areas(),
        "recent_sessions": get_session_history(5)
    }

@app.get("/api/interview/contexts")
def api_contexts():
    from src.interview.coach import INTERVIEWER_CONTEXTS
    return [{"id": k, "label": v[:60]+"..."} for k,v in INTERVIEWER_CONTEXTS.items()]

# ── LEARNING ──────────────────────────────────────────────────────────────────
@app.post("/api/learning/plan")
def api_plan(req: PlanReq):
    db  = Session()
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job: raise HTTPException(404)
    if not job.gap_json: raise HTTPException(400, "Analyse this job first")
    from src.learning.radar import generate_learning_plan
    result = generate_learning_plan(jd(job), json.loads(job.gap_json))
    db.close()
    return result

@app.get("/api/learning/papers")
def api_papers_for_gaps(gaps: str = ""):
    from src.learning.radar import find_papers_for_gaps
    gap_list = [g.strip() for g in gaps.split(",")] if gaps else []
    return find_papers_for_gaps(gap_list or ["RAG","LLM","fine-tuning"], limit=6)

@app.get("/api/learning/reading-list")
def api_reading_list():
    from src.learning.radar import get_reading_list
    return get_reading_list()

# ── CONTENT ───────────────────────────────────────────────────────────────────
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
    return {"ok":True,"url":result.get("url","")}

@app.get("/api/papers")
def api_papers(feed: str = "arxiv_cs_lg", limit: int = 5):
    from src.content.rss_reader import fetch_papers
    return fetch_papers(feed_name=feed, limit=limit)

# ── PROMPTS ───────────────────────────────────────────────────────────────────
@app.get("/api/prompts")
def api_prompts():
    if not PROMPTS_DIR.exists(): return []
    return [{"filename":f.name,"title":f.stem.replace("_"," ").title()}
            for f in sorted(PROMPTS_DIR.glob("*.md")) if f.name!="README.md"]

@app.get("/api/prompts/{filename}")
def api_prompt(filename: str):
    p = PROMPTS_DIR / filename
    if not p.exists(): raise HTTPException(404)
    return {"content": p.read_text(encoding="utf-8")}

# ── STATIC FILES & PWA ────────────────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/sw.js")
def service_worker():
    """Serve service worker from root scope (required for PWA)."""
    sw = STATIC_DIR / "sw.js"
    if sw.exists():
        return FileResponse(str(sw), media_type="application/javascript")
    return HTMLResponse("// No service worker", media_type="application/javascript")

@app.get("/manifest.json")
def manifest():
    m = STATIC_DIR / "manifest.json"
    if m.exists():
        return FileResponse(str(m), media_type="application/manifest+json")
    raise HTTPException(404)

@app.get("/", response_class=HTMLResponse)
def serve():
    html = open(Path(__file__).parent / "index.html", encoding="utf-8").read()
    # Inject PWA meta tags into <head> if not already present
    pwa_tags = """
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#7c6fff">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Career OS">
    <link rel="apple-touch-icon" href="/static/icon-192.svg">"""
    if 'rel="manifest"' not in html:
        html = html.replace("</head>", pwa_tags + "\n</head>", 1)
    # Inject SW registration before </body>
    sw_script = """
    <script>
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').then(reg => {
          console.log('[PWA] Service worker registered:', reg.scope);
        }).catch(err => console.log('[PWA] SW registration failed:', err));
      });
    }
    // Install prompt for Android
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', e => {
      e.preventDefault();
      deferredPrompt = e;
      // Show install banner after 10 seconds
      setTimeout(() => {
        const banner = document.createElement('div');
        banner.id = 'install-banner';
        banner.innerHTML = \`
          <div style="position:fixed;bottom:80px;left:50%;transform:translateX(-50%);
            background:#1c1f33;border:1px solid #7c6fff;border-radius:12px;
            padding:12px 18px;display:flex;align-items:center;gap:12px;z-index:9999;
            box-shadow:0 4px 24px rgba(0,0,0,.5);font-family:system-ui;color:#e4e7f5;font-size:13px">
            <span style="font-size:22px">⚡</span>
            <div>
              <div style="font-weight:600">Install Career OS</div>
              <div style="color:#6b7099;font-size:11px">Add to home screen for quick access</div>
            </div>
            <button onclick="installApp()" style="background:#7c6fff;color:#fff;border:none;
              padding:7px 14px;border-radius:7px;font-size:12px;cursor:pointer;font-weight:500">Install</button>
            <button onclick="document.getElementById('install-banner').remove()"
              style="background:none;border:none;color:#6b7099;cursor:pointer;font-size:18px;padding:0">×</button>
          </div>\`;
        document.body.appendChild(banner);
      }, 10000);
    });
    function installApp() {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(() => {
          deferredPrompt = null;
          const b = document.getElementById('install-banner');
          if (b) b.remove();
        });
      }
    }
    </script>"""
    if "serviceWorker" not in html:
        html = html.replace("</body>", sw_script + "\n</body>", 1)
    return html

def start(port: int = 8000):
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
