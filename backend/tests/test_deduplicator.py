from __future__ import annotations


from core.deduplicator import deduplicate
from models.task import Task


def make_task(
    id: str, title: str, source: str = "jira", source_type: str = "jira", **kwargs
) -> Task:
    return Task(id=id, title=title, source=source, source_type=source_type, **kwargs)


class TestDeduplicator:
    def test_exact_duplicate_titles(self):
        tasks = [
            make_task("1", "Fix login bug"),
            make_task("2", "Fix login bug"),
        ]
        result = deduplicate(tasks)
        assert len(result) < 2

    def test_no_duplicates(self):
        tasks = [
            make_task("1", "Fix login bug"),
            make_task("2", "Implement dark mode"),
            make_task("3", "Write documentation"),
        ]
        result = deduplicate(tasks)
        assert len(result) == 3

    def test_similar_titles_deduplicated(self):
        tasks = [
            make_task("1", "Fix the login page bug"),
            make_task("2", "Fix the login bug on page"),
        ]
        result = deduplicate(tasks)
        assert len(result) < 2

    def test_different_sources_same_issue(self):
        tasks = [
            make_task("JIRA-123", "Fix upload bug", source="Jira", source_type="jira"),
            make_task(
                "email-1",
                "Fix upload bug",
                source="email@outlook.com",
                source_type="email",
            ),
        ]
        result = deduplicate(tasks)
        assert len(result) < 2

    def test_merged_sources_preserved(self):
        tasks = [
            make_task(
                "jira-1", "Critical security patch", source="Jira", source_type="jira"
            ),
            make_task(
                "email-2",
                "Critical security patch",
                source="VP@company.com",
                source_type="email",
            ),
        ]
        result = deduplicate(tasks)
        task = result[0]
        assert task.dedup_group is not None
        assert len(task.merged_sources) > 0

    def test_case_insensitive_dedup(self):
        tasks = [
            make_task("1", "DEPLOY HOTFIX"),
            make_task("2", "deploy hotfix"),
        ]
        result = deduplicate(tasks)
        assert len(result) < 2

    def test_many_unique_tasks(self):
        titles = [
            "Fix login page CSS",
            "Implement dark mode toggle",
            "Write API docs",
            "Upgrade database pool",
            "Add unit tests for billing",
            "Refactor auth middleware",
            "Set up staging environment",
            "Update dependency graph",
            "Migrate legacy endpoints",
            "Add rate limiting headers",
            "Fix WebSocket reconnection",
            "Create onboarding flow",
            "Optimize image loading",
            "Add telemetry dashboard",
            "Patch security vulnerability",
            "Update README examples",
            "Add pagination to search",
            "Fix date parsing bug",
            "Implement CSV export",
            "Add keyboard shortcuts",
            "Fix memory leak in scheduler",
            "Update SSL certificates",
            "Add loading skeletons",
            "Implement undo feature",
            "Fix timezone handling",
            "Add dark mode support",
            "Improve error messages",
            "Add request logging",
            "Implement search debounce",
            "Fix cross-browser issues",
            "Add aria labels",
            "Optimize bundle size",
            "Update API versioning",
            "Add data migration tool",
            "Fix race condition",
            "Implement retry logic",
            "Add feature flags",
            "Update license file",
            "Fix broken links",
            "Add input validation",
            "Implement caching layer",
            "Fix dropdown positioning",
            "Add toast notifications",
            "Update color palette",
            "Fix overflow issues",
            "Add drag and drop",
            "Implement lazy loading",
            "Fix tab navigation",
            "Add hover previews",
            "Update footer links",
        ]
        tasks = [make_task(str(i), titles[i]) for i in range(50)]
        result = deduplicate(tasks)
        assert len(result) == 50
