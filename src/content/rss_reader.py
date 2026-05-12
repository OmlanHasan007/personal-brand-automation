"""
content/rss_reader.py
---------------------
Fetches AI/ML papers and news from RSS feeds.
Summarises each item using Gemini 1.5 Flash (free tier).
Filters for relevance to your profile: medical AI, LLMs, agents, RAG.
"""

import feedparser
from datetime import datetime, timedelta
from src.models.router import call

# --- Feed sources ---
FEEDS = {
    "arxiv_cs_ai":   "https://rss.arxiv.org/rss/cs.AI",
    "arxiv_cs_lg":   "https://rss.arxiv.org/rss/cs.LG",
    "arxiv_cs_cv":   "https://rss.arxiv.org/rss/cs.CV",
    "huggingface":   "https://huggingface.co/blog/feed.xml",
    "paperswithcode":"https://paperswithcode.com/latest.xml",
}

# --- Relevance keywords (your niche) ---
RELEVANT_KEYWORDS = [
    "llm", "language model", "agent", "rag", "retrieval", "medical imaging",
    "ecg", "cardiology", "yolo", "object detection", "langchain", "langgraph",
    "fine-tuning", "lora", "transformer", "attention", "multimodal",
    "clinical", "healthcare", "nlp", "embedding", "vector",
]


def fetch_papers(feed_name: str = "arxiv_cs_lg", limit: int = 5, days_back: int = 7) -> list[dict]:
    """
    Fetch recent papers from a feed, filter for relevance, summarise each.

    Args:
        feed_name: Key from FEEDS dict
        limit:     Max papers to return
        days_back: Only include papers from last N days

    Returns:
        List of dicts: title, url, summary, relevance_score, published
    """
    if feed_name not in FEEDS:
        raise ValueError(f"Unknown feed '{feed_name}'. Choose from: {list(FEEDS.keys())}")

    url = FEEDS[feed_name]
    feed = feedparser.parse(url)
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    results = []
    for entry in feed.entries:
        # Parse publish date
        published = _parse_date(entry)
        if published and published < cutoff:
            continue

        # Score relevance
        text_to_check = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
        score = sum(1 for kw in RELEVANT_KEYWORDS if kw in text_to_check)

        results.append({
            "title":     entry.get("title", "No title"),
            "url":       entry.get("link", ""),
            "abstract":  entry.get("summary", "")[:2000],
            "published": published.isoformat() if published else "",
            "relevance_score": score,
        })

    # Sort by relevance, take top N
    results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)[:limit]

    # Summarise each
    for item in results:
        item["summary"] = _summarise(item["title"], item["abstract"])

    return results


def summarise_all_feeds(limit_per_feed: int = 3) -> list[dict]:
    """Fetch and summarise from all configured feeds."""
    all_items = []
    for feed_name in FEEDS:
        try:
            items = fetch_papers(feed_name, limit=limit_per_feed)
            for item in items:
                item["feed"] = feed_name
            all_items.extend(items)
        except Exception as e:
            print(f"[rss_reader] Failed to fetch {feed_name}: {e}")

    # Deduplicate by title similarity and sort by relevance
    seen_titles = set()
    unique = []
    for item in sorted(all_items, key=lambda x: x["relevance_score"], reverse=True):
        title_key = item["title"][:40].lower()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique.append(item)

    return unique


def _summarise(title: str, abstract: str) -> str:
    """Use Gemini to summarise a paper abstract into 2–3 useful sentences."""
    prompt = f"""Summarise this AI/ML paper in exactly 2–3 sentences for an ML practitioner.
Focus on: what problem it solves, the key method, and the most interesting result.
Be specific — include numbers if the abstract mentions them.
Do not start with "This paper".

Title: {title}
Abstract: {abstract}

Output only the 2–3 sentence summary:"""

    return call("paper_summary", prompt, max_tokens=200)


def _parse_date(entry) -> datetime | None:
    for field in ["published_parsed", "updated_parsed"]:
        val = entry.get(field)
        if val:
            try:
                return datetime(*val[:6])
            except Exception:
                pass
    return None


def format_digest(papers: list[dict]) -> str:
    """Format a list of summarised papers into a readable digest."""
    lines = [f"# AI/ML Paper Digest — {datetime.utcnow().strftime('%Y-%m-%d')}\n"]
    for i, p in enumerate(papers, 1):
        lines.append(f"## {i}. {p['title']}")
        lines.append(f"**Relevance score:** {p['relevance_score']} | **Feed:** {p.get('feed', 'unknown')}")
        lines.append(f"\n{p['summary']}")
        lines.append(f"\n🔗 {p['url']}\n")
    return "\n".join(lines)
