"""Write monitor results to shared summary file."""

import json
import os
from datetime import datetime
from pathlib import Path

SUMMARY_FILE = Path(os.environ.get("SUMMARY_FILE", "/data/gmail-monitor/../monitor-summary.md"))


def update_summary(section: str, items: list[dict]) -> None:
    """Update the shared monitor summary file with new items."""
    summary_path = Path(os.environ.get("CLAUDE_DATA_PATH", "/data")).parent / ".claude" / "monitor-summary.md"
    if os.environ.get("SUMMARY_FILE"):
        summary_path = Path(os.environ["SUMMARY_FILE"])

    summary_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing content
    existing = ""
    if summary_path.exists():
        existing = summary_path.read_text()

    now = datetime.now().strftime("%Y-%m-%d %I:%M %p PT")

    if section == "gmail":
        job_items = [i for i in items if i.get("category") == "job-search"]
        legal_items = [i for i in items if i.get("category") == "legal"]
        urgent_items = [i for i in items if i.get("urgent")]

        gmail_block = f"### Gmail - {len(items)} new items ({now})\n"
        if not items:
            gmail_block += "- No new relevant emails\n"
        else:
            for item in items[:20]:
                prefix = "URGENT: " if item.get("urgent") else ""
                gmail_block += f"- [{item['category']}] {prefix}{item['subject']} (from: {item['from'][:50]})\n"

        urgent_block = ""
        if urgent_items:
            urgent_block = "### URGENT\n"
            for item in urgent_items:
                urgent_block += f"- {item['subject']} (from: {item['from'][:50]})\n"

        # Replace gmail section or append
        new_content = f"## Monitor Summary - {now}\n\n{gmail_block}\n"
        if urgent_block:
            new_content += f"{urgent_block}\n"

        # Preserve court section if it exists
        if "### Court" in existing:
            court_start = existing.index("### Court")
            court_section = existing[court_start:]
            # Find end of court section
            next_section = court_section.find("\n### ", 1)
            if next_section > 0:
                court_section = court_section[:next_section]
            new_content += f"\n{court_section}\n"

        summary_path.write_text(new_content)

    elif section == "court":
        court_block = f"### Court Case 21DR05710 - {len(items)} filings ({now})\n"
        if not items:
            court_block += "- No new filings detected\n"
        else:
            for item in items[:20]:
                date = item.get("date", "N/A")
                desc = item.get("description", item.get("raw_text", ""))[:100]
                court_block += f"- {date}: {desc}\n"

        # Read existing and replace court section or append
        if "### Court" in existing:
            before_court = existing[:existing.index("### Court")]
            after_idx = existing.find("\n### ", existing.index("### Court") + 1)
            after_court = existing[after_idx:] if after_idx > 0 else ""
            new_content = f"{before_court}{court_block}\n{after_court}"
        elif existing:
            new_content = f"{existing}\n{court_block}\n"
        else:
            new_content = f"## Monitor Summary - {now}\n\n{court_block}\n"

        summary_path.write_text(new_content)
