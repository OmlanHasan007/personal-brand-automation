"""
interview/coach.py  v2
----------------------
Redesigned flow: TEACH → then TEST

Modes:
  1. Learn mode  — AI teaches a concept from scratch with examples + checks understanding
  2. Drill mode  — generates a question, evaluates written answer, gives ideal answer
  3. Job mode    — question bank built from a specific job's required skills
  4. History     — tracks scores over time, surfaces weak areas

Question types (all expandable from dashboard):
  technical_llm, technical_ml, technical_cv, behavioural, system_design, german_workplace

Interviewer contexts (configurable):
  german_engineering, ai_startup, research_institute, big_tech, consulting
"""

import json, re, random
from datetime import datetime
from pathlib import Path
from src.models.router import call

DATA_DIR         = Path("data")
SESSIONS_FILE    = DATA_DIR / "interview_sessions.json"
PROGRESS_FILE    = DATA_DIR / "interview_progress.json"
CUSTOM_QS_FILE   = DATA_DIR / "custom_questions.json"
DATA_DIR.mkdir(exist_ok=True)

PROFILE = """Omlan Hasan — M.Sc. AI/ML student, TU Dresden, Germany.
4+ years Python developer. Published: ECG Heart Block Detection, YOLOv4 (HIS 2022).
Projects: RAG pipelines (LangChain), multi-agent (LangGraph), YOLO, FastAPI, SQLite.
Seeking: Werkstudent / AI Intern in Germany (or remote)."""

# ── Built-in topic curriculum ─────────────────────────────────────────────────
CURRICULUM = {
    "technical_llm": {
        "label": "LLMs & RAG",
        "topics": [
            {"id":"rag_basics",       "title":"How RAG works",                   "level":1},
            {"id":"attention",        "title":"Attention mechanism",              "level":1},
            {"id":"transformers",     "title":"Transformer architecture",         "level":2},
            {"id":"embeddings",       "title":"Vector embeddings & similarity",   "level":2},
            {"id":"hallucination",    "title":"Reducing LLM hallucinations",      "level":2},
            {"id":"langchain_graph",  "title":"LangChain vs LangGraph",           "level":3},
            {"id":"fine_tuning_rag",  "title":"Fine-tuning vs RAG — when to use","level":3},
            {"id":"lora",             "title":"LoRA & parameter-efficient tuning","level":3},
        ]
    },
    "technical_ml": {
        "label": "ML Fundamentals",
        "topics": [
            {"id":"backprop",         "title":"Backpropagation",                  "level":1},
            {"id":"bias_variance",    "title":"Bias-variance tradeoff",           "level":1},
            {"id":"overfitting",      "title":"Overfitting & regularisation",     "level":1},
            {"id":"precision_recall", "title":"Precision, recall & F1",          "level":1},
            {"id":"batch_norm",       "title":"Batch normalisation",              "level":2},
            {"id":"optimisers",       "title":"SGD, Adam, learning rate",         "level":2},
            {"id":"cnn_basics",       "title":"CNN architecture",                 "level":2},
            {"id":"train_eval",       "title":"Train/val/test splits",            "level":1},
        ]
    },
    "technical_cv": {
        "label": "Computer Vision",
        "topics": [
            {"id":"yolo",             "title":"YOLO object detection",            "level":2},
            {"id":"iou_nms",          "title":"IoU & non-max suppression",        "level":2},
            {"id":"data_augment",     "title":"Data augmentation strategies",     "level":1},
            {"id":"medical_imaging",  "title":"Medical imaging challenges",       "level":3},
        ]
    },
    "behavioural": {
        "label": "Behavioural (STAR)",
        "topics": [
            {"id":"star_method",      "title":"STAR answer structure",            "level":1},
            {"id":"failure_story",    "title":"Describing a failure / learning",  "level":2},
            {"id":"conflict",         "title":"Handling disagreement",            "level":2},
            {"id":"deadline",         "title":"Multiple priorities / deadlines",  "level":1},
            {"id":"paper_story",      "title":"Telling your research story",      "level":2},
        ]
    },
    "system_design": {
        "label": "System Design (AI)",
        "topics": [
            {"id":"rag_system",       "title":"Design a document Q&A system",     "level":2},
            {"id":"inference_scale",  "title":"Real-time ML inference at scale",  "level":3},
            {"id":"mlops_pipeline",   "title":"End-to-end MLOps pipeline",        "level":3},
            {"id":"moderation",       "title":"Content moderation with LLMs",     "level":3},
        ]
    },
    "german_workplace": {
        "label": "German workplace German",
        "topics": [
            {"id":"intro_de",         "title":"Vorstellung auf Deutsch",           "level":1},
            {"id":"project_de",       "title":"Projekt beschreiben (Deutsch)",     "level":2},
            {"id":"formal_email_de",  "title":"Formal email auf Deutsch",          "level":1},
        ]
    }
}

INTERVIEWER_CONTEXTS = {
    "german_engineering": "a senior ML engineer at a German engineering firm (Bosch, Siemens, Zeiss) — formal, structured, values precision and thoroughness",
    "ai_startup":         "a technical lead at a fast-moving AI startup — values depth, creativity, and getting things done",
    "research_institute": "a researcher at Fraunhofer or DFKI — values academic rigour, publications, and methodological correctness",
    "big_tech":           "a senior engineer at a large tech company (Google, Microsoft, Amazon) — values scalability, systems thinking, and clear communication",
    "consulting":         "a technical consultant — values clear communication, client-facing skills, and practical problem-solving",
}


# ── TEACH mode ────────────────────────────────────────────────────────────────

def teach_topic(topic_id: str, q_type: str = "technical_llm") -> dict:
    """
    Teach a concept from scratch.
    Returns: explanation, key_points, analogy, common_mistake, check_question
    """
    # Find topic title
    topic_title = topic_id.replace("_"," ").title()
    for qt_data in CURRICULUM.values():
        for t in qt_data["topics"]:
            if t["id"] == topic_id:
                topic_title = t["title"]
                break

    prompt = f"""You are a patient, expert tutor teaching {PROFILE}

Teach this topic from scratch as if they know nothing about it yet: "{topic_title}"

Structure your response as JSON:
{{
  "topic": "{topic_title}",
  "one_line_summary": "explain it in one plain sentence a non-expert would understand",
  "explanation": "clear explanation in 3-4 paragraphs, build from simple to complex, use concrete examples",
  "analogy": "one analogy that makes this click intuitively",
  "key_points": ["point 1", "point 2", "point 3", "point 4"],
  "common_mistake": "the most common wrong assumption beginners make",
  "how_it_shows_up_in_interviews": "what interviewers actually want to hear about this",
  "check_question": "one comprehension question to test if they understood — not the same as an interview question, simpler"
}}

Make the explanation genuinely educational — not a list of facts, but a real understanding of how it works.
Output ONLY valid JSON."""

    try:
        raw = call("interview_question", prompt, max_tokens=1000)
        m   = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            result = json.loads(m.group())
            _log_progress(topic_id, "learned")
            return result
    except Exception as e:
        pass
    return {
        "topic": topic_title,
        "explanation": "Could not generate lesson. Check your Groq API key.",
        "key_points": [],
        "check_question": ""
    }


def check_understanding(topic_id: str, question: str, answer: str) -> dict:
    """Quick check after teaching — did they get it?"""
    prompt = f"""Student just learned about "{topic_id.replace('_',' ')}" and answered a check question.

Question: {question}
Their answer: {answer}

Evaluate understanding (not interview performance — just: did they grasp the concept?):
{{
  "understood": true|false,
  "score": 1-10,
  "what_they_got_right": "...",
  "what_is_missing": "...",
  "brief_correction": "fill in the gap in 2-3 sentences",
  "ready_for_interview_question": true|false
}}
Output ONLY valid JSON."""
    try:
        raw = call("interview_feedback", prompt, max_tokens=400)
        m   = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            result = json.loads(m.group())
            _log_progress(topic_id, "checked", result.get("score", 0))
            return result
    except Exception:
        pass
    return {"understood": False, "score": 0, "brief_correction": "Could not evaluate."}


# ── DRILL mode ────────────────────────────────────────────────────────────────

def generate_question(
    q_type: str = "technical_llm",
    company_type: str = "german_engineering",
    topic_id: str = "",
    job_skills: list = None
) -> dict:
    """
    Generate an interview question.
    If topic_id given: targets that topic.
    If job_skills given: targets those skills specifically.
    """
    context = INTERVIEWER_CONTEXTS.get(company_type, INTERVIEWER_CONTEXTS["german_engineering"])

    if job_skills:
        skills_focus = f"Focus on these skills from the job requirements: {', '.join(job_skills[:5])}"
    elif topic_id:
        topic_title = next(
            (t["title"] for qt in CURRICULUM.values() for t in qt["topics"] if t["id"] == topic_id),
            topic_id.replace("_"," ")
        )
        skills_focus = f"Ask specifically about: {topic_title}"
    else:
        curriculum = CURRICULUM.get(q_type, CURRICULUM["technical_llm"])
        topics = curriculum["topics"]
        weak   = _get_weak_topic_ids()
        # Prioritise weak topics
        weak_topics = [t for t in topics if t["id"] in weak]
        chosen = random.choice(weak_topics) if weak_topics else random.choice(topics)
        skills_focus = f"Ask about: {chosen['title']}"

    prompt = f"""You are {context}.
You are interviewing: {PROFILE}

{skills_focus}
Question type: {q_type}

Generate ONE interview question. Make it specific, realistic, and appropriately challenging.
Return ONLY valid JSON:
{{
  "question": "the full interview question",
  "topic_id": "which topic this tests",
  "difficulty": "basic|intermediate|advanced",
  "what_strong_answer_covers": ["point1","point2","point3"],
  "time_target_seconds": 90
}}"""

    try:
        raw = call("interview_question", prompt, max_tokens=500)
        m   = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return {"question": "Explain how you would approach building a RAG system from scratch.", "what_strong_answer_covers": []}


def evaluate_answer(question: str, answer: str, q_type: str = "technical_llm") -> dict:
    """Evaluate answer and return structured feedback with ideal answer."""
    prompt = f"""Evaluate this interview answer for a Werkstudent AI/ML role.

Candidate: {PROFILE}
Question: {question}
Their answer: {answer}

Return ONLY valid JSON:
{{
  "technical_accuracy": {{"score": 7, "comment": "one sentence"}},
  "clarity":            {{"score": 7, "comment": "one sentence"}},
  "structure":          {{"score": 7, "comment": "STAR/problem-solution-result used?"}},
  "completeness":       {{"score": 7, "comment": "what key points were missing?"}},
  "overall_score": 7,
  "length_verdict": "too_short|good|too_long",
  "strongest_part": "what they did best in 1 sentence",
  "biggest_gap": "the single most important missing element",
  "ideal_answer": "model answer in 150-180 words — specific, structured, uses their background where relevant",
  "follow_up_question": "one follow-up an interviewer would naturally ask based on their answer"
}}"""

    try:
        raw = call("interview_feedback", prompt, max_tokens=800)
        m   = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            result = json.loads(m.group())
            _log_session(question, answer, result, q_type)
            return result
    except Exception as e:
        return {"error": str(e), "overall_score": 0}


# ── Questions from job requirements ───────────────────────────────────────────

def questions_from_job(job_criteria: dict, company_type: str = "german_engineering", count: int = 5) -> list[dict]:
    """Generate a tailored question bank from a job's required skills."""
    required = job_criteria.get("required_skills", [])
    role_type = job_criteria.get("role_type", "engineering")

    prompt = f"""Generate {count} interview questions for this specific job.

Required skills: {', '.join(required)}
Role type: {role_type}
Interviewer: {INTERVIEWER_CONTEXTS.get(company_type, '')}
Candidate: {PROFILE}

Mix question types: technical (60%), behavioural (20%), system design (20%).
Make each question targeted at a specific required skill.

Return ONLY valid JSON array:
[
  {{
    "question": "...",
    "skill_tested": "which required skill",
    "q_type": "technical|behavioural|system_design",
    "difficulty": "basic|intermediate|advanced",
    "what_strong_answer_covers": ["point1","point2"]
  }}
]"""

    try:
        raw = call("interview_question", prompt, max_tokens=1200)
        m   = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return []


# ── Progress tracking ─────────────────────────────────────────────────────────

def get_progress() -> dict:
    if not PROGRESS_FILE.exists(): return {"topics":{}, "sessions":0, "avg_score":0}
    with open(PROGRESS_FILE, encoding="utf-8") as f:
        return json.load(f)

def get_weak_areas() -> list[str]:
    progress = get_progress()
    topics   = progress.get("topics", {})
    weak = []
    for tid, data in topics.items():
        scores = data.get("scores", [])
        if scores and sum(scores)/len(scores) < 6:
            weak.append(tid)
        elif not scores and data.get("status") != "learned":
            weak.append(tid)
    return weak

def get_curriculum_with_progress() -> dict:
    progress = get_progress()
    topics   = progress.get("topics", {})
    result   = {}
    for q_type, data in CURRICULUM.items():
        result[q_type] = {
            "label":  data["label"],
            "topics": []
        }
        for t in data["topics"]:
            td = topics.get(t["id"], {})
            scores = td.get("scores", [])
            result[q_type]["topics"].append({
                **t,
                "status":    td.get("status", "not_started"),
                "avg_score": round(sum(scores)/len(scores), 1) if scores else None,
                "attempts":  len(scores),
            })
    return result

def get_session_history(n: int = 10) -> list[dict]:
    if not SESSIONS_FILE.exists(): return []
    with open(SESSIONS_FILE, encoding="utf-8") as f:
        return json.load(f)[-n:]

def _get_weak_topic_ids() -> list[str]:
    progress = get_progress()
    topics   = progress.get("topics", {})
    weak = []
    for tid, data in topics.items():
        scores = data.get("scores", [])
        if scores and sum(scores)/len(scores) < 6:
            weak.append(tid)
    return weak

def _log_progress(topic_id: str, status: str, score: float = None):
    progress = get_progress()
    if "topics" not in progress: progress["topics"] = {}
    if topic_id not in progress["topics"]: progress["topics"][topic_id] = {"scores":[],"status":"not_started"}
    progress["topics"][topic_id]["status"] = status
    if score is not None:
        progress["topics"][topic_id]["scores"].append(score)
    progress["topics"][topic_id]["last_seen"] = datetime.utcnow().isoformat()
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)

def _log_session(question: str, answer: str, feedback: dict, q_type: str):
    sessions = []
    if SESSIONS_FILE.exists():
        with open(SESSIONS_FILE, encoding="utf-8") as f:
            sessions = json.load(f)
    sessions.append({
        "question":   question,
        "answer":     answer,
        "feedback":   feedback,
        "q_type":     q_type,
        "score":      feedback.get("overall_score", 0),
        "saved_at":   datetime.utcnow().isoformat()
    })
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)
    # Update global progress
    progress = get_progress()
    all_scores = [s.get("score",0) for s in sessions if s.get("score")]
    progress["sessions"] = len(sessions)
    progress["avg_score"] = round(sum(all_scores)/len(all_scores),1) if all_scores else 0
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)
