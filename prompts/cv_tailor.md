# CV tailoring prompt
# -------------------
# Used by: python main.py cv --job-url <url>  (automatic via Groq)
# Used by: you manually (paste into ChatGPT Go)
#
# PURPOSE: Takes a job posting + your master CV bullets → rewrites bullets
# to match the job's keywords and priorities. Never invents experience.

---

## MASTER CV BULLETS (update this as you do more projects)

EXPERIENCE:

Python Developer — Authentic Four Technology (4+ years)
- Built data-driven Python applications for business automation
- Designed and maintained REST APIs and backend systems
- Worked with SQL databases and data pipelines

AI/ML Projects (TU Dresden M.Sc.):
- Built conversational RAG pipeline with LangChain — 73% improvement in retrieval relevance on follow-up questions
- Developed multi-agent system with LangGraph for automated research workflows
- Trained YOLO models for object detection tasks
- Built FastAPI + SQLite job tracker with automated follow-up scheduling
- Created GitHub Actions CI/CD pipelines for automated README updates and weekly posting

Publication:
- Co-authored "ECG Heart Block Detection Using YOLOv4" — HIS 2022 conference
- Achieved [F1 score] on [dataset] for automated cardiac anomaly detection

SKILLS:
- Languages: Python (expert), SQL (solid), Bash
- ML/AI: PyTorch, LangChain, LangGraph, RAG, YOLO, Hugging Face, vector databases
- Backend: FastAPI, SQLite, REST APIs
- DevOps: Docker, GitHub Actions, Git

---

## CV TAILORING REQUEST

Rewrite Omlan's CV bullet points to best match the following job posting.

JOB TITLE: [e.g. Werkstudent NLP Engineer]

COMPANY: [e.g. Deutsche Telekom]

TOP 5 KEYWORDS/REQUIREMENTS FROM THE JOB POSTING:
[Paste the 5 most important skills or requirements]

STRICT RULES:
1. Only reorder and reword existing bullets. Never add experience he does not have.
2. Lead with the 3 most relevant bullets for this specific role.
3. Use exact keywords from the job posting where they honestly apply.
4. Each bullet: start with a strong action verb, include one metric or technical detail where possible.
5. Flag any requirement in the job posting that he cannot honestly claim — mark it [GAP: suggest how to address].
6. Output format: rewritten bullet list only, grouped by section. No explanation.

---

## REFINEMENT COMMANDS

**ATS check:**
> Review these rewritten bullets. List every keyword from the job posting that is missing. Suggest where to naturally add each one without lying.

**Quantify more:**
> For each bullet that lacks a number or metric, suggest a realistic placeholder (e.g. "[X% improvement]") that Omlan should fill in from his actual results.

**German CV version:**
> Translate these bullets into German. Keep technical terms (PyTorch, LangChain, RAG, etc.) in English.
