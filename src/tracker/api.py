"""
tracker/api.py
--------------
FastAPI + SQLite job application tracker.
Tracks: applications, stages, deadlines, follow-ups, notes.

Run locally:
    python main.py tracker
    # Then open: http://localhost:8000/docs

Endpoints:
    GET    /jobs            - List all applications
    POST   /jobs            - Add a new application
    PATCH  /jobs/{id}       - Update stage or add note
    DELETE /jobs/{id}       - Remove application
    GET    /stats           - Summary metrics
    GET    /due-followups   - Applications needing follow-up today
"""

import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, DateTime, Text, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- Database setup ---
DB_PATH = Path("data/jobs.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class JobApplication(Base):
    __tablename__ = "applications"

    id             = Column(Integer, primary_key=True, index=True)
    job_title      = Column(String, nullable=False)
    company        = Column(String, nullable=False)
    location       = Column(String, default="")           # e.g. "Dresden, Germany" or "Remote"
    job_url        = Column(String, default="")
    source         = Column(String, default="")           # e.g. "LinkedIn", "StepStone", "cold-email"
    stage          = Column(String, default="Applied")    # Applied / Screen / Interview / Offer / Rejected
    applied_date   = Column(Date, default=date.today)
    deadline       = Column(Date, nullable=True)
    followup_date  = Column(Date, nullable=True)
    notes          = Column(Text, default="")
    is_remote      = Column(Boolean, default=False)
    salary_range   = Column(String, default="")
    contact_name   = Column(String, default="")
    contact_url    = Column(String, default="")
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# --- Pydantic models ---
class JobCreate(BaseModel):
    job_title:    str
    company:      str
    location:     str = ""
    job_url:      str = ""
    source:       str = ""
    stage:        str = "Applied"
    applied_date: Optional[date] = None
    deadline:     Optional[date] = None
    notes:        str = ""
    is_remote:    bool = False
    salary_range: str = ""
    contact_name: str = ""
    contact_url:  str = ""


class JobUpdate(BaseModel):
    stage:         Optional[str] = None
    notes:         Optional[str] = None
    followup_date: Optional[date] = None
    deadline:      Optional[date] = None
    contact_name:  Optional[str] = None
    contact_url:   Optional[str] = None


# --- API ---
app = FastAPI(
    title="Job Application Tracker",
    description="Track every application from radar to offer.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_STAGES = {"Applied", "Phone screen", "Interview", "Offer", "Rejected", "Withdrawn"}


@app.get("/jobs")
def list_jobs(stage: Optional[str] = None, remote_only: bool = False):
    db = SessionLocal()
    q  = db.query(JobApplication)
    if stage:
        q = q.filter(JobApplication.stage == stage)
    if remote_only:
        q = q.filter(JobApplication.is_remote == True)
    jobs = q.order_by(JobApplication.applied_date.desc()).all()
    db.close()
    return [_job_dict(j) for j in jobs]


@app.post("/jobs", status_code=201)
def add_job(job: JobCreate):
    db = SessionLocal()
    if job.stage not in VALID_STAGES:
        raise HTTPException(400, f"Invalid stage. Choose from: {VALID_STAGES}")
    applied = job.applied_date or date.today()
    followup = applied + timedelta(days=7)  # Auto-set follow-up 7 days after applying
    db_job = JobApplication(
        **job.model_dump(exclude={"applied_date"}),
        applied_date  = applied,
        followup_date = followup,
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    db.close()
    return _job_dict(db_job)


@app.patch("/jobs/{job_id}")
def update_job(job_id: int, update: JobUpdate):
    db  = SessionLocal()
    job = db.query(JobApplication).filter(JobApplication.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(job, field, value)
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    db.close()
    return _job_dict(job)


@app.delete("/jobs/{job_id}")
def delete_job(job_id: int):
    db  = SessionLocal()
    job = db.query(JobApplication).filter(JobApplication.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    db.delete(job)
    db.commit()
    db.close()
    return {"deleted": job_id}


@app.get("/stats")
def get_stats():
    db   = SessionLocal()
    jobs = db.query(JobApplication).all()
    db.close()
    if not jobs:
        return {"total": 0}

    total     = len(jobs)
    by_stage  = {}
    for j in jobs:
        by_stage[j.stage] = by_stage.get(j.stage, 0) + 1

    responded  = sum(1 for j in jobs if j.stage not in {"Applied"})
    in_pipeline= sum(1 for j in jobs if j.stage in {"Phone screen", "Interview"})
    offers     = by_stage.get("Offer", 0)
    rejections = by_stage.get("Rejected", 0)

    return {
        "total":           total,
        "by_stage":        by_stage,
        "response_rate":   round(responded / total * 100, 1),
        "active_pipeline": in_pipeline,
        "offers":          offers,
        "rejections":      rejections,
        "remote_count":    sum(1 for j in jobs if j.is_remote),
    }


@app.get("/due-followups")
def due_followups():
    """Return applications where follow-up date is today or overdue."""
    db   = SessionLocal()
    today = date.today()
    jobs = db.query(JobApplication).filter(
        JobApplication.followup_date <= today,
        JobApplication.stage.in_(["Applied", "Phone screen"]),
    ).all()
    db.close()
    return [_job_dict(j) for j in jobs]


def _job_dict(job: JobApplication) -> dict:
    return {
        "id":           job.id,
        "job_title":    job.job_title,
        "company":      job.company,
        "location":     job.location,
        "job_url":      job.job_url,
        "source":       job.source,
        "stage":        job.stage,
        "applied_date": str(job.applied_date) if job.applied_date else None,
        "deadline":     str(job.deadline) if job.deadline else None,
        "followup_date":str(job.followup_date) if job.followup_date else None,
        "notes":        job.notes,
        "is_remote":    job.is_remote,
        "salary_range": job.salary_range,
        "contact_name": job.contact_name,
        "contact_url":  job.contact_url,
        "updated_at":   job.updated_at.isoformat() if job.updated_at else None,
    }


def start():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
