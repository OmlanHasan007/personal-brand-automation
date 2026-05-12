"""
github/readme_updater.py
------------------------
Fetches your GitHub stats and rewrites your profile README.md.
Runs weekly via GitHub Actions (see .github/workflows/readme_update.yml).

What it updates:
- Pinned repos with descriptions and star counts
- Recent commit activity
- Languages used
- A short AI-generated "what I'm building now" section via Gemini
"""

import os
from github import Github
from datetime import datetime, timedelta
from src.models.router import call


README_TEMPLATE = """<!-- AUTO-GENERATED — do not edit this section manually -->
<!-- Updated: {updated_at} -->

# Hi, I'm Omlan 👋

AI/ML developer · M.Sc. student at TU Dresden · Published researcher

I build applied AI systems: RAG pipelines, LLM agents, and computer vision models.
My published paper: [ECG Heart Block Detection with YOLOv4 (HIS 2022)](https://link-to-paper)

---

## 🔨 What I'm building now

{building_now}

---

## 📌 Featured projects

{pinned_repos}

---

## 📊 GitHub stats

| Metric | Value |
|---|---|
| Public repos | {repo_count} |
| Stars earned | {total_stars} |
| Commits this week | {weekly_commits} |
| Primary languages | {top_languages} |

---

## 🛠 Tech stack

`Python` `PyTorch` `LangChain` `LangGraph` `RAG` `YOLO` `FastAPI` `Docker` `SQLite` `GitHub Actions`

---

## 📫 Contact

- LinkedIn: [linkedin.com/in/omlan-hasan](https://linkedin.com/in/omlan-hasan)
- Email: omlanhasan@gmail.com
- Location: Dresden, Germany · Open to Werkstudent / remote AI roles

<!-- END AUTO-GENERATED -->
"""


def update_readme(dry_run: bool = False) -> str:
    """
    Fetch GitHub stats and rewrite profile README.

    Args:
        dry_run: If True, returns the new README content without pushing

    Returns:
        The generated README content
    """
    token    = os.environ["GITHUB_TOKEN"]
    username = os.environ["GITHUB_USERNAME"]

    g    = Github(token)
    user = g.get_user(username)

    # --- Collect stats ---
    repos      = list(user.get_repos(type="owner", sort="updated"))
    repo_count = len(repos)
    total_stars = sum(r.stargazers_count for r in repos)
    top_languages = _top_languages(repos)
    weekly_commits = _commits_this_week(repos)
    pinned_repos_text = _format_pinned_repos(repos[:6])

    # --- Generate "building now" section with Gemini ---
    recent_repo_names = [r.name for r in repos[:5]]
    building_now = _generate_building_now(recent_repo_names)

    # --- Render README ---
    readme_content = README_TEMPLATE.format(
        updated_at    = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        building_now  = building_now,
        pinned_repos  = pinned_repos_text,
        repo_count    = repo_count,
        total_stars   = total_stars,
        weekly_commits= weekly_commits,
        top_languages = ", ".join(f"`{lang}`" for lang in top_languages[:4]),
    )

    if dry_run:
        print("[DRY RUN] Generated README:")
        print(readme_content[:500] + "...")
        return readme_content

    # --- Push to GitHub ---
    profile_repo_name = f"{username}/{username}"
    try:
        profile_repo = g.get_repo(profile_repo_name)
    except Exception:
        raise RuntimeError(
            f"Profile repo '{profile_repo_name}' not found. "
            "Create a repo with the same name as your GitHub username."
        )

    try:
        existing = profile_repo.get_contents("README.md")
        profile_repo.update_file(
            "README.md",
            f"chore: auto-update README stats [{datetime.utcnow().strftime('%Y-%m-%d')}]",
            readme_content,
            existing.sha,
        )
    except Exception:
        profile_repo.create_file(
            "README.md",
            "feat: create auto-updating profile README",
            readme_content,
        )

    print(f"✅ README updated on GitHub: {profile_repo_name}")
    return readme_content


def _top_languages(repos: list, n: int = 4) -> list[str]:
    lang_counts: dict[str, int] = {}
    for repo in repos:
        if repo.language:
            lang_counts[repo.language] = lang_counts.get(repo.language, 0) + 1
    return sorted(lang_counts, key=lang_counts.get, reverse=True)[:n]


def _commits_this_week(repos: list) -> int:
    since = datetime.utcnow() - timedelta(days=7)
    count = 0
    for repo in repos[:10]:  # Only check 10 most recent to avoid rate limits
        try:
            commits = repo.get_commits(since=since)
            count += commits.totalCount
        except Exception:
            pass
    return count


def _format_pinned_repos(repos: list) -> str:
    lines = []
    for repo in repos:
        desc = repo.description or "No description yet"
        stars = f"⭐ {repo.stargazers_count}" if repo.stargazers_count > 0 else ""
        lang  = f"`{repo.language}`" if repo.language else ""
        lines.append(f"- **[{repo.name}]({repo.html_url})** {lang} {stars}")
        lines.append(f"  {desc}")
    return "\n".join(lines)


def _generate_building_now(recent_repo_names: list[str]) -> str:
    prompt = f"""Based on these recent GitHub repository names, write 2 sentences describing
what this AI/ML developer is currently building. Be specific and technical.
Don't start with "I". Start with a present participle (Building / Developing / Exploring / Training).

Repository names: {', '.join(recent_repo_names)}

Output only the 2 sentences:"""
    return call("readme_update", prompt, max_tokens=100)
