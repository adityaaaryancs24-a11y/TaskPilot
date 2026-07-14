from __future__ import annotations


from core.extractor import extract_actions
from core.llm_client import HeuristicBackend


class TestExtractor:
    def test_extract_clear_action_items(self):
        text = """
        Hi team, please fix the login bug by Friday.
        Also, could you review the PR for the new feature?
        Don't forget to update the documentation.
        """
        tasks = extract_actions(text)
        assert len(tasks) >= 2

    def test_extract_from_meeting_transcript(self):
        text = """
        John: The auth service is down.
        Sarah: We need to fix this ASAP.
        Manager: Make sure to deploy the hotfix by EOD.
        """
        tasks = extract_actions(text)
        assert len(tasks) >= 1

    def test_no_action_items(self):
        text = "This is just a regular message without any requests."
        tasks = extract_actions(text)
        assert len(tasks) == 0

    def test_heuristic_backend_extraction(self):
        backend = HeuristicBackend()
        text = "Please fix the critical outage and could you review the PR?"
        result = backend._heuristic_extract(text)
        assert len(result) >= 1
        assert any("fix" in t["title"].lower() for t in result)

    def test_confidence_values(self):
        text = "Please fix the login bug by Friday."
        tasks = extract_actions(text)
        for t in tasks:
            assert 0 <= t.get("confidence", 0) <= 1

    def test_deduplicates_similar_extractions(self):
        text = """
        Please fix the login bug.
        Could you fix the login bug?
        """
        tasks = extract_actions(text)
        titles = [t["title"].lower() for t in tasks]
        assert len(set(titles)) == len(titles)
