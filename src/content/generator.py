"""
content/generator.py
--------------------
Generates LinkedIn post drafts via Groq (Llama 3.3 70B, free).
Reads the prompt template from prompts/linkedin_post.md.
Saves drafts to drafts/ folder for human review before publishing.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from src.models.router import call

HISTORY_FILE  = Path("data/post_history.json")
DRAFTS_DIR    = Path("drafts")
PROMPT_FILE   = Path("prompts/linkedin_post.md")

# Profile injected into every prompt — update this as you grow
PROFILE = """
Name: Omlan Hasan
Degree: M.Sc. AI/ML student at TU Dresden, Germany
Background: 4+ years Python developer before starting the Master's
Publication: Co-authored peer-reviewed paper — ECG Heart Block Detection using YOLOv4 (HIS 2022)
Tech stack: PyTorch, LangChain, LangGraph, RAG pipelines, YOLO, FastAPI, SQLite, Docker, GitHub Actions
Niche: Applied AI — medical imaging + LLM-powered agents
Seeking: Werkstudent or AI Intern roles in Germany (on-site or remote)
Based in: Dresden, Germany
Email: omlanhasan@gmail.com
Voice: Direct, technical but human. Never corporate.
"""

TOPIC_MAP = {
    "project":  "a specific AI project he built this week — what problem it solves, the approach, one concrete result",
    "paper":    "an insight from a research paper he read — what it means in plain language for ML practitioners",
    "learning": "something surprising or counter-intuitive he learned while building an AI system",
    "seeking":  "a concise, confident post seeking a Werkstudent or AI intern role in Germany, leading with his strongest credential",
    "insight":  "a nuanced opinion about LLMs, agents, or applied AI that most posts don't say",
    "progress": "a weekly progress update — what he shipped, what he struggled with, what is next",
}

TONE_MAP = {
    "professional": "Professional and direct. Value-first. No fluff. The reader learns something in 30 seconds.",
    "casual":       "Warm and human. Like a message to a smart colleague, not a press release.",
    "technical":    "Technical depth for an ML audience. Specific terms used correctly.",
}


def generate_draft(
    topic: str = "project",
    tone: str = "professional",
    context: str = "",
    hashtag_count: int = 4,
) -> dict:
    """
    Generate a post draft via Groq and save it to drafts/ for human review.

    Returns dict with: text, topic, tone, draft_path, generated_at, word_count
    """
    if topic not in TOPIC_MAP:
        raise ValueError(f"Unknown topic '{topic}'. Choose from: {list(TOPIC_MAP.keys())}")
    if tone not in TONE_MAP:
        raise ValueError(f"Unknown tone '{tone}'. Choose from: {list(TONE_MAP.keys())}")

    # Avoid repeating recent post themes
    recent = _load_recent(n=3)
    avoid = ""
    if recent:
        avoid = "\n\nAvoid repeating these recent themes:\n" + "\n".join(
            f"- {p['topic']} ({p['generated_at'][:10]})" for p in recent
        )

    prompt = f"""You are a LinkedIn ghostwriter. Write a post for this person:

{PROFILE}

Topic: {TOPIC_MAP[topic]}
Tone: {TONE_MAP[tone]}
{f"Context to include: {context}" if context else ""}
{avoid}

Requirements:
- 150–220 words exactly
- Hook in the first line — no "I am excited", no "Thrilled to announce"
- No bullet points — flowing paragraphs only
- End with exactly {hashtag_count} relevant hashtags on the last line
- Good hashtags: #MachineLearning #AI #LLMAgents #RAG #Python #Werkstudent #DeepLearning #TUDresden #MedicalAI
- No clichés: no "passionate about", no "journey", no "leverage"
- Output ONLY the post text. No preamble. No explanation."""

    text = call("post_generation", prompt, max_tokens=600)
    word_count = len(text.split())
    now = datetime.utcnow()
    draft_path = _save_draft(text, topic, tone, context, now)

    result = {
        "text":         text,
        "topic":        topic,
        "tone":         tone,
        "context":      context,
        "draft_path":   str(draft_path),
        "generated_at": now.isoformat(),
        "word_count":   word_count,
        "posted":       False,
    }
    _save_history(result)
    return result


def _save_draft(text: str, topic: str, tone: str, context: str, now: datetime) -> Path:
    """Save draft to drafts/YYYY-MM-DD_topic.md with instructions for ChatGPT Go."""
    DRAFTS_DIR.mkdir(exist_ok=True)
    date_str = now.strftime("%Y-%m-%d")
    path = DRAFTS_DIR / f"{date_str}_{topic}.md"

    content = f"""# LinkedIn draft — {topic} / {tone}
# Generated: {now.strftime("%Y-%m-%d %H:%M UTC")} via Groq (Llama 3.3 70B)
# Words: {len(text.split())}
#
# NEXT STEP — Option B review:
# 1. Copy the POST TEXT below
# 2. Open ChatGPT Go in browser
# 3. Paste: "Refine this LinkedIn post for Omlan Hasan (AI/ML student, TU Dresden).
#            Keep his voice — direct, technical, no corporate speak.
#            [paste post]
#            Make the hook stronger. Keep length 150-220 words."
# 4. Copy refined version → run: python main.py publish
#
# REFINEMENT COMMANDS (paste any of these into ChatGPT Go after the draft):
#   → "Rewrite only the first sentence. More direct and surprising."
#   → "Make it more technical. Add one specific implementation detail."
#   → "Give me 3 alternative opening sentences. No 'I'."
#   → "Cut to 160 words. Remove anything that repeats."
# ─────────────────────────────────────────────────────────────────────────

## POST TEXT (copy everything below this line)

{text}

## CONTEXT USED
Topic: {topic}
Tone: {tone}
Context: {context or "none provided"}
"""
    path.write_text(content, encoding="utf-8")
    return path


def _load_recent(n: int = 5) -> list:
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        return json.load(f)[-n:]


def _save_history(post: dict):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, encoding="utf-8") as f:
            history = json.load(f)
    history.append(post)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def list_drafts() -> list[Path]:
    """Return all draft files, newest first."""
    if not DRAFTS_DIR.exists():
        return []
    return sorted(DRAFTS_DIR.glob("*.md"), reverse=True)


def load_latest_draft() -> str | None:
    """Load text from the most recent draft file."""
    drafts = list_drafts()
    if not drafts:
        return None
    content = drafts[0].read_text(encoding="utf-8")
    # Extract just the post text (between the marker and CONTEXT USED)
    match = re.search(r"## POST TEXT.*?\n\n(.*?)\n\n## CONTEXT", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None
