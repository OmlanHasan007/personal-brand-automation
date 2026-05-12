"""
linkedin/poster.py
------------------
Posts text content to LinkedIn using the UGC Posts API.
Requires: w_member_social permission + valid access token.
"""

import json
import os
from datetime import datetime
from pathlib import Path
import httpx
from src.linkedin.oauth import load_token

LINKEDIN_POST_URL = "https://api.linkedin.com/v2/ugcPosts"
POST_LOG_FILE = Path("data/post_history.json")


def post_to_linkedin(text: str, dry_run: bool = False) -> dict:
    """
    Post text to LinkedIn.

    Args:
        text:    The post text (with hashtags)
        dry_run: If True, prints the post but does not actually publish

    Returns:
        dict with: post_id, url, posted_at, text, dry_run
    """
    if len(text) > 3000:
        raise ValueError(f"Post too long: {len(text)} chars (LinkedIn max: 3000)")

    if dry_run:
        print("\n[DRY RUN] Would post to LinkedIn:")
        print("─" * 60)
        print(text)
        print("─" * 60)
        return {"dry_run": True, "text": text, "posted_at": datetime.utcnow().isoformat()}

    token = load_token()
    access_token = token["access_token"]
    person_urn   = token["person_urn"]

    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text
                },
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    response = httpx.post(
        LINKEDIN_POST_URL,
        json=payload,
        headers={
            "Authorization":  f"Bearer {access_token}",
            "Content-Type":   "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )

    if response.status_code == 201:
        post_id = response.headers.get("x-restli-id", "unknown")
        post_url = f"https://www.linkedin.com/feed/update/{post_id}/"
        result = {
            "post_id":   post_id,
            "url":       post_url,
            "posted_at": datetime.utcnow().isoformat(),
            "text":      text,
            "dry_run":   False,
        }
        _log_post(result)
        print(f"\n✅ Posted to LinkedIn: {post_url}")
        return result
    else:
        raise RuntimeError(
            f"LinkedIn API error {response.status_code}: {response.text}"
        )


def _log_post(post: dict):
    """Append post record to history file."""
    POST_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if POST_LOG_FILE.exists():
        with open(POST_LOG_FILE) as f:
            history = json.load(f)
    history.append(post)
    with open(POST_LOG_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_post_history(n: int = 10) -> list[dict]:
    """Return the last N posts."""
    if not POST_LOG_FILE.exists():
        return []
    with open(POST_LOG_FILE) as f:
        history = json.load(f)
    return history[-n:]
