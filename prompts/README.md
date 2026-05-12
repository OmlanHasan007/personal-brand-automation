# Prompts folder
# ==============
# Every prompt in this folder has two uses:
# 1. AUTOMATIC — called by the Python pipeline via Groq or Gemini API (zero cost)
# 2. MANUAL    — paste into ChatGPT Go browser for human review and refinement

# This is the heart of Option B:
# Pipeline drafts automatically → you review in ChatGPT Go → publish.

---

## Files and what they do

| File | Auto via | Manual use | When to use it |
|---|---|---|---|
| `linkedin_post.md` | Groq (Llama 3.3 70B) | ChatGPT Go | Every week — generate + refine post |
| `cover_letter.md` | Groq (Llama 3.3 70B) | ChatGPT Go | Every job application |
| `cv_tailor.md` | Groq (Llama 3.3 70B) | ChatGPT Go | Every job application |
| `interview_coach.md` | Groq (Llama 3.3 70B) | ChatGPT Go | 48h before every interview |
| `paper_summary.md` | Gemini 2.0 Flash | ChatGPT Go / NotebookLM | Weekly paper reading |

---

## The Option B weekly workflow

```
Monday morning (10 min total):

1. Terminal: python main.py draft --topic project --context "what you built this week"
   → Groq generates post draft
   → Saved to: drafts/YYYY-MM-DD_post.md

2. Open drafts/YYYY-MM-DD_post.md
   → Copy the draft text

3. Open ChatGPT Go browser
   → Paste the draft + any refinement command from linkedin_post.md
   → Refine until it sounds like you

4. Copy the final version
   → Terminal: python main.py publish
   → Pastes from clipboard and posts to LinkedIn

Total active time: ~10 minutes. Rest is automated.
```

---

## How to update prompts

The prompts are plain text files — edit them like any document.

When to update:
- `linkedin_post.md` — when you finish a new project (add it to the PROFILE section)
- `cv_tailor.md` — after every new project or result (update MASTER CV BULLETS)
- `interview_coach.md` — after an interview (add questions you were asked to KEY TOPICS)

Each improvement makes every future output better. The prompts compound.

---

## Model routing (zero cost)

```
Your pipeline spends £0/month:

Post generation   → Groq free tier  (Llama 3.3 70B, 500k tokens/day)
Paper summaries   → Gemini free tier (2.0 Flash, 1500 req/day)
Cover letters     → Groq free tier
Interview coach   → Groq free tier
README updates    → Gemini free tier

ChatGPT Go        → Manual browser review only (your subscription)
NotebookLM        → Deep paper reading (Google, free)
```
