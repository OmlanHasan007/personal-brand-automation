"""
main.py — Personal Brand Automation CLI
----------------------------------------
Commands:
  draft          Generate a post draft → saves to drafts/ for ChatGPT Go review
  publish        Publish the latest draft (or a specific file) to LinkedIn
  papers         Fetch + summarise AI papers (Gemini, free)
  readme         Update GitHub profile README (Gemini, free)
  tracker        Start job application tracker API
  weekly         Full pipeline: papers → draft → reminder to review → README
  auth-linkedin  One-time LinkedIn OAuth setup
  status         Check all API keys and connections
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()
app     = typer.Typer(help="Personal Brand Automation — zero cost AI career pipeline")
console = Console()


# ──────────────────────────────────────────────────────────
# DRAFT — Option B step 1: generate and save for review
# ──────────────────────────────────────────────────────────

@app.command()
def draft(
    topic:   str = typer.Option("project",      "--topic",   "-t", help="project|paper|learning|seeking|insight|progress"),
    tone:    str = typer.Option("professional",  "--tone",    "-n", help="professional|casual|technical"),
    context: str = typer.Option("",              "--context", "-c", help="What happened this week — be specific"),
):
    """
    Step 1 of Option B: Generate a post draft with Groq (free).
    Draft saved to drafts/ folder. Open it, refine in ChatGPT Go, then run: publish
    """
    from src.content.generator import generate_draft

    if not context:
        console.print("[yellow]Tip: Use --context to describe what you built or learned this week.[/]")
        console.print('[dim]Example: --context "Built a RAG pipeline, improved retrieval by 40%"[/]\n')

    with console.status(f"[cyan]Drafting '{topic}' post via Groq (Llama 3.3 70B, free)..."):
        result = generate_draft(topic=topic, tone=tone, context=context)

    console.print(Panel(
        result["text"],
        title=f"[bold cyan]Draft — {topic} / {tone} ({result['word_count']} words)[/]",
        border_style="cyan",
    ))

    console.print(f"\n[green]✓ Draft saved:[/] [bold]{result['draft_path']}[/]")
    console.print("\n[bold]Next steps (Option B):[/]")
    console.print("  1. Open the draft file above")
    console.print("  2. Copy the post text → refine in [bold]ChatGPT Go[/] browser")
    console.print("     (Refinement commands are inside the draft file)")
    console.print("  3. Paste the refined version back into the draft file")
    console.print("  4. Run: [bold cyan]python main.py publish[/]")


# ──────────────────────────────────────────────────────────
# PUBLISH — Option B step 2: post the reviewed draft
# ──────────────────────────────────────────────────────────

@app.command()
def publish(
    file:    str  = typer.Option("", "--file", "-f", help="Specific draft file to publish (default: latest)"),
    dry_run: bool = typer.Option(False, "--dry-run",   help="Preview without posting"),
):
    """
    Step 2 of Option B: Publish the reviewed draft to LinkedIn.
    Uses the latest draft in drafts/ by default.
    """
    from src.content.generator import list_drafts, load_latest_draft

    if file:
        draft_path = Path(file)
        if not draft_path.exists():
            console.print(f"[red]File not found: {file}[/]")
            raise typer.Exit(1)
        post_text = _extract_post_text(draft_path)
    else:
        drafts = list_drafts()
        if not drafts:
            console.print("[red]No drafts found. Run: python main.py draft[/]")
            raise typer.Exit(1)
        draft_path = drafts[0]
        post_text  = load_latest_draft()

    if not post_text:
        console.print(f"[red]Could not read post text from {draft_path}[/]")
        raise typer.Exit(1)

    console.print(Panel(
        post_text,
        title=f"[bold]Ready to publish[/] — [dim]{draft_path.name}[/]",
        border_style="green",
    ))
    console.print(f"\n[dim]Words: {len(post_text.split())} | Characters: {len(post_text)}[/]")

    if dry_run:
        console.print("\n[yellow]Dry run — not posted.[/]")
        return

    confirm = typer.confirm("\nPost this to LinkedIn?")
    if not confirm:
        console.print("[yellow]Cancelled.[/]")
        return

    from src.linkedin.poster import post_to_linkedin
    result = post_to_linkedin(post_text)
    console.print(f"\n[green]✓ Posted:[/] {result.get('url', 'check LinkedIn')}")


def _extract_post_text(path: Path) -> str | None:
    """Extract post text between markers in a draft file."""
    import re
    content = path.read_text(encoding="utf-8")
    match = re.search(r"## POST TEXT.*?\n\n(.*?)\n\n## CONTEXT", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: return everything after the last # header
    lines = content.split("\n")
    for i, line in enumerate(reversed(lines)):
        if line.startswith("## POST TEXT"):
            return "\n".join(lines[len(lines) - i:]).strip()
    return None


# ──────────────────────────────────────────────────────────
# PAPERS — Gemini paper digest (free)
# ──────────────────────────────────────────────────────────

@app.command()
def papers(
    feed:  str  = typer.Option("arxiv_cs_lg", "--feed",  "-f", help="arxiv_cs_lg|arxiv_cs_ai|arxiv_cs_cv|huggingface|paperswithcode"),
    limit: int  = typer.Option(5,             "--limit", "-l", help="Max papers to fetch"),
    save:  bool = typer.Option(False,          "--save",  "-s", help="Save digest to logs/"),
):
    """Fetch and summarise the latest AI/ML papers (Gemini 2.0 Flash, free)."""
    from src.content.rss_reader import fetch_papers, format_digest

    with console.status(f"[cyan]Fetching papers from {feed} via Gemini (free)..."):
        items = fetch_papers(feed_name=feed, limit=limit)

    if not items:
        console.print("[yellow]No relevant papers found.[/]")
        return

    digest = format_digest(items)
    console.print(Panel(digest, title="[bold green]AI Paper Digest[/]", border_style="green"))
    console.print("\n[dim]Tip: Copy any abstract into ChatGPT Go with prompts/paper_summary.md for deep reading.[/]")

    if save:
        out = Path("logs") / f"digest_{datetime.utcnow().strftime('%Y%m%d')}.md"
        out.parent.mkdir(exist_ok=True)
        out.write_text(digest, encoding="utf-8")
        console.print(f"\n[green]Saved:[/] {out}")


# ──────────────────────────────────────────────────────────
# README — GitHub profile updater (Gemini, free)
# ──────────────────────────────────────────────────────────

@app.command()
def readme(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without pushing"),
):
    """Update GitHub profile README with latest stats (Gemini, free)."""
    from src.github.readme_updater import update_readme

    with console.status("[cyan]Fetching GitHub stats and generating README..."):
        content = update_readme(dry_run=dry_run)

    if dry_run:
        console.print(Panel(content[:800] + "\n...", title="[bold]README Preview[/]", border_style="blue"))
    else:
        console.print("[green]✓ GitHub README updated.[/]")


# ──────────────────────────────────────────────────────────
# TRACKER — FastAPI job application tracker
# ──────────────────────────────────────────────────────────

@app.command()
def tracker():
    """Start the job application tracker (FastAPI + SQLite, localhost:8000)."""
    console.print(Panel(
        "Starting at [bold cyan]http://localhost:8000[/]\n"
        "API docs:   [bold cyan]http://localhost:8000/docs[/]\n\n"
        "Press [bold]Ctrl+C[/] to stop.",
        title="[bold]Job Tracker[/]",
        border_style="blue",
    ))
    from src.tracker.api import start
    start()


# ──────────────────────────────────────────────────────────
# WEEKLY — Full Option B pipeline
# ──────────────────────────────────────────────────────────

@app.command()
def weekly(
    dry_run: bool = typer.Option(False, "--dry-run", help="Run without posting or pushing"),
):
    """
    Full weekly Option B pipeline:
    1. Fetch AI papers (Gemini, auto)
    2. Generate post draft (Groq, auto) → saved to drafts/
    3. Remind you to review in ChatGPT Go
    4. Update GitHub README (Gemini, auto)
    """
    console.rule("[bold cyan]Weekly pipeline — Option B[/]")

    # Step 1: Papers
    console.print("\n[1/3] Fetching AI papers (Gemini)...")
    from src.content.rss_reader import summarise_all_feeds, format_digest

    papers_list = summarise_all_feeds(limit_per_feed=3)
    digest = format_digest(papers_list[:5])
    digest_path = Path("logs") / f"digest_{datetime.utcnow().strftime('%Y%m%d')}.md"
    digest_path.parent.mkdir(exist_ok=True)
    digest_path.write_text(digest, encoding="utf-8")
    console.print(f"  ✓ {len(papers_list)} papers summarised → {digest_path}")

    # Step 2: Draft post
    console.print("\n[2/3] Generating post draft (Groq, free)...")
    from src.content.generator import generate_draft

    week_num = datetime.utcnow().isocalendar()[1]
    topics   = ["project", "learning", "paper", "insight", "progress"]
    topic    = topics[week_num % len(topics)]
    result   = generate_draft(topic=topic, tone="professional")

    console.print(Panel(result["text"], title=f"[cyan]Draft ({topic})[/]", border_style="cyan"))
    console.print(f"\n  ✓ Draft saved: [bold]{result['draft_path']}[/]")

    # Step 3: Human review reminder
    console.print("\n[bold yellow]⏸  PAUSE HERE — Option B review step:[/]")
    console.print("  → Open the draft file above")
    console.print("  → Copy post text → refine in ChatGPT Go")
    console.print("  → Paste refined version back into the draft file")
    console.print("  → Run: [bold cyan]python main.py publish[/]")

    # Step 4: README
    if not dry_run:
        proceed = typer.confirm("\nUpdate GitHub README now?")
    else:
        proceed = False

    if proceed or dry_run:
        console.print("\n[3/3] Updating GitHub README (Gemini)...")
        from src.github.readme_updater import update_readme
        update_readme(dry_run=dry_run)
        console.print("  ✓ README updated" if not dry_run else "  ✓ README preview done (dry run)")

    console.rule("[bold green]Pipeline done — review your draft, then publish[/]")


# ──────────────────────────────────────────────────────────
# AUTH-LINKEDIN — One-time OAuth setup
# ──────────────────────────────────────────────────────────

@app.command()
def dashboard(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run on"),
):
    """Start the web dashboard — control everything from your browser."""
    import webbrowser, threading, time
    url = f"http://localhost:{port}"
    console.print(Panel(
        f"Dashboard starting at [bold cyan]{url}[/]\n\n"
        "Sections:\n"
        "  🏠 Dashboard  — status + metrics\n"
        "  ✍️  Generate   — draft + edit + publish\n"
        "  📄 Papers     — AI paper digest\n"
        "  💼 Job tracker — full CRUD\n"
        "  📋 Prompts    — copy any prompt\n\n"
        "Press [bold]Ctrl+C[/] to stop.",
        title="[bold]Personal Brand Automation — Web Dashboard[/]",
        border_style="cyan",
    ))
    def open_browser():
        time.sleep(1.2)
        webbrowser.open(url)
    threading.Thread(target=open_browser, daemon=True).start()
    from src.dashboard.app import start
    start(port=port)


@app.command(name="auth-linkedin")
def auth_linkedin():
    """One-time LinkedIn OAuth 2.0 setup (opens browser)."""
    console.print(Panel(
        "Opens your browser for LinkedIn authorization.\n"
        "Requires in .env: [bold]LINKEDIN_CLIENT_ID[/] and [bold]LINKEDIN_CLIENT_SECRET[/]\n\n"
        "App permissions needed: [bold]w_member_social, openid, profile, email[/]\n"
        "Create app at: https://www.linkedin.com/developers/apps",
        title="[bold]LinkedIn OAuth Setup[/]",
        border_style="yellow",
    ))
    from src.linkedin.oauth import run_oauth_flow
    run_oauth_flow()


# ──────────────────────────────────────────────────────────
# STATUS — Check everything
# ──────────────────────────────────────────────────────────

@app.command()
def status():
    """Check all API keys, connections, and draft queue."""
    from src.models.router import available_models
    from src.content.generator import list_drafts

    models = available_models()

    table = Table(title="System status — Personal Brand Automation")
    table.add_column("Component",  style="cyan", min_width=18)
    table.add_column("Status",     min_width=28)
    table.add_column("Notes")

    # Groq
    table.add_row(
        "Groq API (free)",
        "[green]✓ Configured[/]" if models["groq"] else "[red]✗ Missing GROQ_API_KEY[/]",
        f"Model: {models['groq_model']} | get key: console.groq.com",
    )
    # Gemini
    table.add_row(
        "Gemini API (free)",
        "[green]✓ Configured[/]" if models["gemini"] else "[yellow]⚠ Missing GEMINI_API_KEY[/]",
        f"Model: {models['gemini_model']} | get key: aistudio.google.com",
    )
    # GitHub
    table.add_row(
        "GitHub token",
        "[green]✓ Configured[/]" if os.environ.get("GITHUB_TOKEN") else "[red]✗ Missing GITHUB_TOKEN[/]",
        f"Username: {os.environ.get('GITHUB_USERNAME', 'not set in .env')}",
    )
    # LinkedIn
    token_ok = os.path.exists("data/linkedin_token.json") or bool(os.environ.get("LINKEDIN_ACCESS_TOKEN"))
    table.add_row(
        "LinkedIn OAuth",
        "[green]✓ Token saved[/]" if token_ok else "[yellow]⚠ Not set up[/]",
        "Run: python main.py auth-linkedin" if not token_ok else "Ready to publish",
    )
    # Job tracker
    table.add_row(
        "Job tracker DB",
        "[green]✓ Ready[/]" if os.path.exists("data/jobs.db") else "[dim]Not created yet[/]",
        "Run: python main.py tracker",
    )
    # Draft queue
    drafts = list_drafts()
    table.add_row(
        "Draft queue",
        f"[cyan]{len(drafts)} draft(s)[/]" if drafts else "[dim]Empty[/]",
        drafts[0].name if drafts else "Run: python main.py draft",
    )

    console.print(table)

    if drafts:
        console.print(f"\n[bold]Latest draft:[/] {drafts[0]}")
        console.print("Review it → refine in ChatGPT Go → run: [bold cyan]python main.py publish[/]")


if __name__ == "__main__":
    app()
