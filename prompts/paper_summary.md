# Paper summary prompt
# --------------------
# Used by: python main.py papers  (automatic via Gemini)
# Used by: you manually (paste into ChatGPT Go or NotebookLM for deep reading)
#
# TWO MODES:
# Mode A: Quick summary (3 sentences) — used in the automation pipeline
# Mode B: Deep reading guide — use in NotebookLM or ChatGPT Go when you want to
#         actually understand and potentially implement the paper

---

## MODE A — Quick summary (automation use)

Summarise this AI/ML paper in exactly 3 sentences for an ML practitioner.

Sentence 1: What problem does it solve and why does it matter?
Sentence 2: What is the key method or insight (be specific — name the technique)?
Sentence 3: What is the most interesting result (include numbers if available)?

Do not start with "This paper". Do not use passive voice. Output only the 3 sentences.

TITLE: [paper title]
ABSTRACT: [paste abstract]

---

## MODE B — Deep reading guide (use in NotebookLM or ChatGPT Go)

I am reading this paper and want to understand it deeply enough to explain it to someone and potentially implement it.

PAPER TITLE: [title]
ABSTRACT: [paste abstract]

Walk me through this paper in 5 steps:

1. **The problem** (2–3 sentences): What gap in existing work does this paper address? Why did previous approaches fail or fall short?

2. **The key idea** (3–4 sentences): What is the central contribution? Explain the method as if I'm an ML engineer who will implement it — be specific about the architecture, algorithm, or approach.

3. **Why it works** (2–3 sentences): What is the intuition behind why this approach is better? What assumption does it exploit that others missed?

4. **The results** (2–3 sentences): What did they demonstrate? Include the most important metric. What dataset or benchmark?

5. **What I should try** (3–5 bullet points): If I wanted to apply this idea to [RAG pipelines / medical imaging / LLM agents], what would I experiment with first? Be specific about what code I would write.

After step 5, ask me: "Which section do you want to go deeper on?"

---

## MODE C — Relevance filter (use when scanning many papers)

I will give you a list of paper titles and abstracts. For each one, tell me:
- Relevance score 1–5 (5 = directly relevant to my work)
- One sentence on why it is or isn't relevant
- Whether I should read the full paper or just the abstract

My focus areas: RAG pipelines, LLM agents, medical imaging (ECG, cardiac), computer vision, fine-tuning, MLOps.

Rate these papers:
[paste list of title + abstract pairs]

---

## NOTEBOOKLM USAGE GUIDE

NotebookLM is best for papers you want to deeply understand, not just summarise.

How to use it:
1. Upload the paper PDF to NotebookLM
2. Start with this prompt: "What is the central contribution of this paper in one paragraph?"
3. Then: "What would I need to implement this from scratch? List the components."
4. Then: "What are the limitations the authors acknowledge?"
5. Finally: "How could I apply this specifically to [your current project]?"

NotebookLM remembers the whole paper — ask it anything you'd ask a co-author.
Best used for: papers you found via Mode C above with score 4 or 5.
