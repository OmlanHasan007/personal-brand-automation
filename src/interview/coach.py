"""
interview/coach.py
------------------
AI interview coach using Groq (Llama 3.3 70B, free).
Conducts mock interviews, evaluates answers, tracks progress.
"""

import json
from datetime import datetime
from pathlib import Path
from src.models.router import call

DATA_DIR      = Path("data")
SESSIONS_FILE = DATA_DIR / "interview_sessions.json"

PROFILE = """Omlan Hasan — M.Sc. AI/ML student, TU Dresden.
4+ years Python dev. Published paper on ECG detection (YOLOv4, HIS 2022).
Projects: RAG pipelines (LangChain), multi-agent (LangGraph), YOLO, FastAPI.
Seeking: Werkstudent / AI Intern in Germany."""

QUESTION_BANKS = {
    "technical_llm": [
        "Explain how RAG works and when you'd use it vs fine-tuning.",
        "What is attention in transformers? Explain without diagrams.",
        "How would you reduce hallucinations in a production LLM system?",
        "What is the difference between LangChain and LangGraph? When do you use each?",
        "How does vector similarity search work? What distance metrics exist?",
    ],
    "technical_ml": [
        "Explain backpropagation from first principles.",
        "What is the bias-variance tradeoff?",
        "How do you detect and handle overfitting?",
        "Explain precision vs recall. When does each matter more?",
        "What is batch normalisation and why does it help?",
    ],
    "behavioural": [
        "Tell me about a project where things didn't go as planned.",
        "Describe a time you had to learn something new very quickly.",
        "Tell me about a technical decision you disagreed with.",
        "How do you prioritise when you have multiple deadlines?",
        "Tell me about your published paper — what was hard, what would you do differently?",
    ],
    "system_design": [
        "Design a document Q&A system for a company's internal knowledge base.",
        "How would you build a real-time ML inference pipeline that handles 1000 requests/sec?",
        "Design a content moderation system using LLMs.",
        "How would you set up a medical image classification system in production?",
    ],
}


def generate_question(q_type: str = "technical_llm", company_type: str = "german_engineering") -> dict:
    """Generate a single interview question."""
    import random
    bank = QUESTION_BANKS.get(q_type, QUESTION_BANKS["technical_llm"])
    base_q = random.choice(bank)

    company_context = {
        "german_engineering": "a German engineering company like Bosch or Siemens — formal, structured",
        "ai_startup": "a fast-moving AI startup — expect depth and creativity",
        "research_institute": "a research institute like Fraunhofer or DFKI — expect academic rigour",
    }.get(company_type, "a tech company")

    prompt = f"""You are a technical interviewer at {company_context}.
Interviewing: {PROFILE}

Ask this question in a natural, conversational way.
Base question: {base_q}
Add one follow-up that makes it specific to their background.
Return JSON: {{"question": "...", "what_strong_answer_covers": ["point1","point2","point3"]}}
Output ONLY valid JSON."""

    try:
        raw = call("interview_question", prompt, max_tokens=400)
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {"question": base_q, "what_strong_answer_covers": []}


def evaluate_answer(question: str, answer: str, q_type: str = "technical_llm") -> dict:
    """Evaluate a candidate's answer and return structured feedback."""
    prompt = f"""You are evaluating an interview answer for a Werkstudent AI/ML role.

Candidate: {PROFILE}

Question: {question}
Their answer: {answer}

Evaluate on these dimensions and return ONLY valid JSON:
{{
  "technical_accuracy": {{
    "score": 7,
    "comment": "one sentence"
  }},
  "clarity": {{
    "score": 7,
    "comment": "one sentence"
  }},
  "structure": {{
    "score": 7,
    "comment": "STAR used? Problem→solution→result?"
  }},
  "estimated_length_seconds": 90,
  "length_verdict": "too_short|good|too_long",
  "strongest_part": "what they did best",
  "biggest_gap": "the single most important thing missing",
  "ideal_answer": "the ideal answer in 150 words",
  "overall_score": 7
}}"""

    try:
        raw = call("interview_feedback", prompt, max_tokens=700)
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        return {"error": str(e), "overall_score": 0}


def save_session(session: dict):
    """Save interview session to history."""
    DATA_DIR.mkdir(exist_ok=True)
    history = []
    if SESSIONS_FILE.exists():
        with open(SESSIONS_FILE, encoding="utf-8") as f:
            history = json.load(f)
    session["saved_at"] = datetime.utcnow().isoformat()
    history.append(session)
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_history() -> list[dict]:
    if not SESSIONS_FILE.exists():
        return []
    with open(SESSIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_weak_areas() -> list[str]:
    """Analyse history to find consistently low-scoring areas."""
    history = get_history()
    if not history:
        return []
    scores = {}
    counts = {}
    for s in history:
        for qa in s.get("qa_pairs", []):
            feedback = qa.get("feedback", {})
            for dim in ["technical_accuracy", "clarity", "structure"]:
                if dim in feedback:
                    sc = feedback[dim].get("score", 0)
                    scores[dim] = scores.get(dim, 0) + sc
                    counts[dim] = counts.get(dim, 0) + 1
    return [d for d, c in counts.items() if c > 0 and scores[d]/c < 6]
