# Cover letter prompt
# -------------------
# Used by: python main.py cover-letter --job-url <url>  (automatic via Groq)
# Used by: you manually (paste into ChatGPT Go for any job posting)
#
# MANUAL USE: Copy PROFILE + RULES below into ChatGPT Go, fill the brackets.

---

## PROFILE

You are writing a cover letter for Omlan Hasan:

- M.Sc. AI/ML student, TU Dresden, Germany
- 4+ years Python developer (data-driven applications)
- Published paper: ECG Heart Block Detection with YOLOv4 (HIS 2022 conference)
- Tech stack: PyTorch, LangChain, LangGraph, RAG, YOLO, FastAPI, Docker, SQLite, GitHub Actions
- Niche: Applied AI — medical imaging + LLM agents
- Target roles: Werkstudent or AI Intern in Germany (on-site or remote)
- Email: omlanhasan@gmail.com | Location: Dresden, Germany

---

## COVER LETTER REQUEST

Write a cover letter for Omlan for the following job posting.

JOB TITLE: [e.g. Werkstudent Machine Learning — Bosch Dresden]

COMPANY: [e.g. Bosch]

JOB POSTING KEY REQUIREMENTS:
[Paste the 4–6 most important requirements from the job posting]

HIS MOST RELEVANT EXPERIENCE FOR THIS ROLE:
[Write 2–3 sentences about which of his projects or skills are the strongest match]

STRICT RULES:
1. Exactly 3 paragraphs. No more, no less.
2. Paragraph 1 — The hook: One specific sentence about why THIS company or THIS role. Reference something real about their product, research, or mission. Not: "I am excited to apply to your company."
3. Paragraph 2 — The proof: His most relevant project or result, connected directly to their requirement. Include one specific metric or technical detail. 4–5 sentences maximum.
4. Paragraph 3 — The close: Short and confident. Express availability and invite a conversation. One sentence. No summary of what was already said.
5. Total length: 180–220 words. Tight and respectful of the reader's time.
6. No "I am passionate about", no "I believe I would be a great fit", no "please find attached".
7. Write in first person as Omlan.
8. Output only the letter body (no subject line, no "Dear X", no date). Just the three paragraphs.

---

## REFINEMENT COMMANDS

**More specific hook:**
> Rewrite paragraph 1 only. Research [company name] and reference one specific product, paper, or initiative they are known for.

**Stronger proof paragraph:**
> Rewrite paragraph 2 only. Add one more concrete technical detail from his project. Make the connection to their requirement more explicit.

**German version:**
> Translate the entire letter into formal German (Sie-form). Keep all technical terms in English.

---

## EXAMPLE FILLED REQUEST

JOB TITLE: Werkstudent Machine Learning — Medical Imaging

COMPANY: Siemens Healthineers

JOB POSTING KEY REQUIREMENTS:
- Experience with deep learning for medical image analysis
- Python, PyTorch
- Understanding of CNNs and object detection
- Ability to work independently on research tasks

HIS MOST RELEVANT EXPERIENCE FOR THIS ROLE:
His published paper (HIS 2022) used YOLOv4 to detect heart blocks in ECG signals — directly in the medical imaging + object detection intersection. He has hands-on PyTorch experience from that project and his Master's coursework.
