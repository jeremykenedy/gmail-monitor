"""Tests for Gmail Monitor."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from monitor import (
    categorize_email,
    decode_subject,
    get_body,
    is_urgent,
    load_seen_ids,
    save_results,
    save_seen_ids,
)


class TestCategorizeEmail:
    def test_linkedin_is_job_search(self):
        result = categorize_email("jobs@linkedin.com", "New role", "")
        assert result == "job-search"

    def test_indeed_is_job_search(self):
        result = categorize_email("alert@indeed.com", "New jobs", "")
        assert result == "job-search"

    def test_dice_is_job_search(self):
        result = categorize_email("alerts@dice.com", "Matching jobs", "")
        assert result == "job-search"

    def test_interview_keyword_is_job_search(self):
        result = categorize_email("someone@company.com", "Interview scheduled", "")
        assert result == "job-search"

    def test_offer_keyword_is_job_search(self):
        result = categorize_email("hr@company.com", "Your offer letter", "")
        assert result == "job-search"

    def test_attorney_is_legal(self):
        result = categorize_email("john@lawfirm.com", "Case update", "hearing scheduled")
        assert result == "legal"

    def test_court_filing_is_legal(self):
        result = categorize_email("court@state.gov", "Filing accepted", "case motion")
        assert result == "legal"

    def test_case_number_is_legal(self):
        result = categorize_email("anyone@email.com", "Filing for 21DR05710", "case update")
        assert result == "legal"

    def test_amazon_excluded(self):
        result = categorize_email("order@amazon.com", "Your order delivered", "")
        assert result is None

    def test_ebay_excluded(self):
        result = categorize_email("noreply@ebay.com", "ORDER DELIVERED", "")
        assert result is None

    def test_ups_excluded(self):
        result = categorize_email("tracking@ups.com", "Package delivered", "")
        assert result is None

    def test_amazon_with_case_number_not_excluded(self):
        result = categorize_email("order@amazon.com", "21DR05710", "case filing")
        assert result == "legal"

    def test_irrelevant_email_returns_none(self):
        result = categorize_email("friend@gmail.com", "Hey whats up", "nothing relevant")
        assert result is None

    def test_legal_requires_two_keywords(self):
        result = categorize_email("random@email.com", "order confirmation", "")
        assert result is None

    def test_legal_two_keywords_passes(self):
        result = categorize_email("random@email.com", "court hearing scheduled", "")
        assert result == "legal"


class TestIsUrgent:
    def test_interview_scheduled_is_urgent(self):
        assert is_urgent("job-search", "Interview scheduled for Monday", "")

    def test_court_date_is_urgent(self):
        assert is_urgent("legal", "Court date reminder", "hearing date tomorrow")

    def test_deadline_is_urgent(self):
        assert is_urgent("legal", "Response deadline approaching", "")

    def test_regular_job_alert_not_urgent(self):
        assert not is_urgent("job-search", "New PHP developer roles", "")

    def test_regular_legal_not_urgent(self):
        assert not is_urgent("legal", "Case status update", "no changes")


class TestDecodeSubject:
    def test_plain_subject(self):
        assert decode_subject("Hello World") == "Hello World"

    def test_empty_subject(self):
        assert decode_subject("") == ""


class TestSeenIds:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import monitor
            monitor.OUTPUT_DIR = Path(tmpdir)
            monitor.SEEN_FILE = Path(tmpdir) / "seen_ids.json"

            ids = {"msg1", "msg2", "msg3"}
            save_seen_ids(ids)

            loaded = load_seen_ids()
            assert loaded == ids


class TestSaveResults:
    def test_creates_output_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import monitor
            monitor.OUTPUT_DIR = Path(tmpdir)
            monitor.LATEST_FILE = Path(tmpdir) / "latest.json"

            emails = [
                {"category": "job-search", "subject": "Test job", "urgent": False},
                {"category": "legal", "subject": "Test filing", "urgent": True},
            ]
            save_results(emails)

            latest = json.loads((Path(tmpdir) / "latest.json").read_text())
            assert latest["new_relevant_count"] == 2
            assert len(latest["job_search"]) == 1
            assert len(latest["legal"]) == 1
            assert len(latest["urgent"]) == 1


class TestExcludedSenders:
    """Verify all excluded senders are properly filtered."""

    @pytest.mark.parametrize("sender", [
        "order@amazon.com",
        "noreply@ebay.com",
        "tracking@ups.com",
        "info@fedex.com",
        "updates@usps.com",
        "noreply@dhl.com",
        "orders@target.com",
        "alerts@walmart.com",
        "order@bestbuy.com",
    ])
    def test_excluded_sender_returns_none(self, sender):
        result = categorize_email(sender, "Your order shipped", "delivery update")
        assert result is None
