from __future__ import annotations
"""Gmail Monitor - checks for job search and legal updates."""

import codecs
import email
import email.message
import email.policy
import imaplib
import json
import os
import sys
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

# Register handler for unknown encodings before anything else
def _unknown_codec(name):
    if name in ("unknown-8bit", "x-unknown"):
        return codecs.lookup("latin-1")
    return None

codecs.register(_unknown_codec)

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/data/gmail-monitor"))
LATEST_FILE = OUTPUT_DIR / "latest.json"
SEEN_FILE = OUTPUT_DIR / "seen_ids.json"

JOB_SENDERS = [
    "indeed.com", "linkedin.com", "dice.com", "larajobs.com",
    "glassdoor.com", "ziprecruiter.com", "lever.co", "greenhouse.io",
    "workday.com", "smartrecruiters.com", "jobvite.com",
]

JOB_KEYWORDS = [
    "interview", "offer", "application", "position", "hiring",
    "candidate", "role", "opportunity", "job alert", "new jobs",
    "application status", "phone screen", "technical interview",
    "onsite", "recruiter", "salary", "compensation",
]

LEGAL_SENDERS = [
    "law", "attorney", "legal", "esq", "court", "paralegal",
]

LEGAL_KEYWORDS = [
    "case", "hearing", "filing", "settlement", "court",
    "motion", "order", "petition", "custody", "decree",
    "mediation", "deposition", "discovery", "21DR05710",
    "respondent", "petitioner", "judgment",
]

EXCLUDED_SENDERS = [
    "amazon.com", "ebay.com", "ups.com", "fedex.com", "usps.com",
    "dhl.com", "target.com", "walmart.com", "bestbuy.com",
    "aliexpress.com", "etsy.com", "shopify.com",
    "noreply@", "parentsquare", "donotreply",
]


def decode_subject(subject: str) -> str:
    """Decode email subject header."""
    try:
        decoded = decode_header(subject)
        parts = []
        for part, charset in decoded:
            if isinstance(part, bytes):
                try:
                    parts.append(part.decode(charset or "utf-8", errors="replace"))
                except (LookupError, UnicodeDecodeError):
                    parts.append(part.decode("latin-1", errors="replace"))
            else:
                parts.append(str(part))
        return " ".join(parts)
    except Exception:
        return str(subject)


def get_body(msg: email.message.Message) -> str:
    """Extract plain text body from email."""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                    except Exception:
                        continue
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        try:
                            return payload.decode(charset, errors="replace")[:2000]
                        except (LookupError, UnicodeDecodeError):
                            return payload.decode("latin-1", errors="replace")[:2000]
        else:
            try:
                payload = msg.get_payload(decode=True)
            except Exception:
                return ""
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                try:
                    return payload.decode(charset, errors="replace")[:2000]
                except (LookupError, UnicodeDecodeError):
                    return payload.decode("latin-1", errors="replace")[:2000]
    except Exception:
        pass
    return ""


def categorize_email(from_addr: str, subject: str, body: str) -> str | None:
    """Categorize email as job-search, legal, or None."""
    from_lower = from_addr.lower()

    # Exclude known noise senders
    if any(excluded in from_lower for excluded in EXCLUDED_SENDERS):
        # Exception: allow if it explicitly mentions the case number
        if "21DR05710" not in f"{subject} {body}":
            return None

    combined = f"{from_addr} {subject} {body}".lower()

    # Check legal first (higher priority)
    # Require stronger signal -- sender must match OR multiple keywords
    if any(sender in from_lower for sender in LEGAL_SENDERS):
        return "legal"
    legal_hits = sum(1 for kw in LEGAL_KEYWORDS if kw in combined)
    if legal_hits >= 2:
        return "legal"
    if "21DR05710" in combined:
        return "legal"

    # Check job-related
    if any(sender in from_lower for sender in JOB_SENDERS):
        return "job-search"
    if any(kw in combined for kw in JOB_KEYWORDS):
        return "job-search"

    return None


def is_urgent(category: str, subject: str, body: str) -> bool:
    """Check if the email is urgent."""
    combined = f"{subject} {body}".lower()
    urgent_keywords = [
        "interview scheduled", "court date", "hearing date",
        "offer expiring", "deadline", "urgent", "immediate",
        "time sensitive", "action required", "respond by",
        "expires", "final notice", "tomorrow",
    ]
    return any(kw in combined for kw in urgent_keywords)


def load_seen_ids() -> set:
    """Load previously seen message IDs."""
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen_ids(seen: set) -> None:
    """Save seen message IDs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Keep last 5000 IDs
    ids = sorted(seen)[-5000:]
    SEEN_FILE.write_text(json.dumps(ids))


def check_gmail() -> list[dict]:
    """Connect to Gmail via IMAP and check for relevant new emails."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print(f"[{datetime.now().isoformat()}] ERROR: GMAIL_USER or GMAIL_APP_PASSWORD not set", file=sys.stderr)
        return []

    relevant_emails = []
    seen_ids = load_seen_ids()

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("INBOX", readonly=True)

        # Search for emails from the last 2 days
        since_date = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        _, message_numbers = mail.search(None, f'(SINCE {since_date})')

        if not message_numbers[0]:
            mail.logout()
            return []

        for num in message_numbers[0].split():
            try:
                _, msg_data = mail.fetch(num, "(BODY.PEEK[] FLAGS)")
            except Exception:
                continue
            if not msg_data or not msg_data[0]:
                continue

            raw = msg_data[0][1]
            try:
                msg = email.message_from_bytes(raw, policy=email.policy.compat32)
            except Exception:
                continue

            try:
                msg_id = msg.get("Message-ID", num.decode())
                if msg_id in seen_ids:
                    continue

                from_addr = msg.get("From", "")
                subject = decode_subject(msg.get("Subject", ""))
                date_str = msg.get("Date", "")
                body = get_body(msg)

                category = categorize_email(from_addr, subject, body)
                if category:
                    urgent = is_urgent(category, subject, body)
                    relevant_emails.append({
                        "id": msg_id,
                        "from": from_addr,
                        "subject": subject,
                        "date": date_str,
                        "category": category,
                        "urgent": urgent,
                        "snippet": body[:500] if body else "",
                    })
                    if urgent:
                        print(f"[{datetime.now().isoformat()}] URGENT {category}: {subject}", file=sys.stderr)

                seen_ids.add(msg_id)
            except Exception as e:
                print(f"[{datetime.now().isoformat()}] Skipping message: {e}", file=sys.stderr)
                continue

        mail.logout()

    except Exception as e:
        print(f"[{datetime.now().isoformat()}] IMAP error: {e}", file=sys.stderr)

    save_seen_ids(seen_ids)
    return relevant_emails


def save_results(emails: list[dict]) -> None:
    """Save results to JSON."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result = {
        "checked_at": datetime.now().isoformat(),
        "new_relevant_count": len(emails),
        "job_search": [e for e in emails if e["category"] == "job-search"],
        "legal": [e for e in emails if e["category"] == "legal"],
        "urgent": [e for e in emails if e.get("urgent")],
    }

    LATEST_FILE.write_text(json.dumps(result, indent=2))

    # Append to history
    history_file = OUTPUT_DIR / "history.json"
    history = []
    if history_file.exists():
        history = json.loads(history_file.read_text())
    history.append(result)
    history_file.write_text(json.dumps(history[-500:], indent=2))


def main() -> None:
    """Main entry point."""
    print(f"[{datetime.now().isoformat()}] Checking Gmail for job/legal updates...")

    emails = check_gmail()

    if emails:
        job_count = sum(1 for e in emails if e["category"] == "job-search")
        legal_count = sum(1 for e in emails if e["category"] == "legal")
        urgent_count = sum(1 for e in emails if e.get("urgent"))
        print(f"[{datetime.now().isoformat()}] Found {len(emails)} relevant emails "
              f"(job: {job_count}, legal: {legal_count}, urgent: {urgent_count})")

        # Update shared summary
        from summary import update_summary
        update_summary("gmail", emails)
    else:
        print(f"[{datetime.now().isoformat()}] No new relevant emails.")

    save_results(emails)


if __name__ == "__main__":
    main()
