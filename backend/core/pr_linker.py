"""Auto-detects task links from GitHub PR text.

GitHub itself recognizes a set of closing keywords ("Fixes #12", "Closes #7",
"Resolves org/repo#9") and auto-closes the issue on merge. We mirror that
same keyword set here so a PR gets linked to a TaskPilot task the moment
it's opened/edited — not just at merge time.
"""

from __future__ import annotations

import re

# Same keyword set GitHub recognizes for auto-closing issues via PR text.
# Cross-repo refs (org/repo#9) are intentionally not matched — TaskPilot
# only tracks issues in the configured GITHUB_REPO_OWNER/GITHUB_REPO_NAME,
# so a cross-repo number would produce a false-positive link to the wrong task.
_ISSUE_REF_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s*#(\d+)\b",
    re.IGNORECASE,
)


def extract_linked_issue_numbers(pr_body: str) -> list[int]:
    """Return the sorted, de-duplicated set of issue numbers a PR body
    references via a GitHub closing keyword (Fixes/Closes/Resolves #N).

    Returns an empty list for None/empty input rather than raising, since
    PR bodies are frequently empty and this is called straight from the
    webhook handler on every "opened"/"edited"/"synchronize" event.
    """
    if not pr_body:
        return []
    return sorted({int(n) for n in _ISSUE_REF_RE.findall(pr_body)})
