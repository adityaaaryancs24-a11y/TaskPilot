import os
from dotenv import load_dotenv

# Load .env BEFORE any connector reads environment variables.
# Connectors are instantiated at module level below, so this
# must run first.
load_dotenv()

# Map XAI_API_KEY -> LLM_API_KEY if only XAI_API_KEY is set
if not os.environ.get("LLM_API_KEY") and os.environ.get("XAI_API_KEY"):
    os.environ["LLM_API_KEY"] = os.environ["XAI_API_KEY"]

# NOTE (MCP migration): jira_connector, outlook_connector, and
# servicenow_connector are DISABLED, not deleted — they did direct REST/PAT
# calls with a single shared credential and no per-user auth. GitHub is now
# served via the MCP-based connector (per-user OAuth + MCP tool calls,
# see core/github_oauth.py + core/mcp_client.py). Re-enable the others the
# same way (OAuth login route + MCP server) when it's their turn.
from core.connectors.github_mcp_connector import GitHubMCPConnector
from core.connectors.slack_connector import SlackConnector
from core.connectors.transcript_connector import TranscriptConnector

_GITHUB_CONNECTOR = None
_SLACK_CONNECTOR = None
_TRANSCRIPT_CONNECTOR = None


def _get_github():
    global _GITHUB_CONNECTOR
    if _GITHUB_CONNECTOR is None:
        _GITHUB_CONNECTOR = GitHubMCPConnector()
    return _GITHUB_CONNECTOR


def _get_slack():
    global _SLACK_CONNECTOR
    if _SLACK_CONNECTOR is None:
        _SLACK_CONNECTOR = SlackConnector()
    return _SLACK_CONNECTOR


def _get_transcript():
    global _TRANSCRIPT_CONNECTOR
    if _TRANSCRIPT_CONNECTOR is None:
        _TRANSCRIPT_CONNECTOR = TranscriptConnector()
    return _TRANSCRIPT_CONNECTOR


connector_registry: dict[str, object] = {
    "transcript": _get_transcript(),
    "github": _get_github(),
    "slack": _get_slack(),
    # "jira": _get_jira(),          # disabled — pending MCP migration
    # "defects": _get_servicenow(), # disabled — pending MCP migration
    # "emails": _get_outlook(),     # disabled — pending MCP migration
}
