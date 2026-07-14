import os
from dotenv import load_dotenv

# Load .env BEFORE any connector reads environment variables.
# Connectors are instantiated at module level below, so this
# must run first.
load_dotenv()

# Map XAI_API_KEY -> LLM_API_KEY if only XAI_API_KEY is set
if not os.environ.get("LLM_API_KEY") and os.environ.get("XAI_API_KEY"):
    os.environ["LLM_API_KEY"] = os.environ["XAI_API_KEY"]

from core.connectors.jira_connector import JiraConnector
from core.connectors.github_connector import GitHubConnector
from core.connectors.outlook_connector import OutlookConnector
from core.connectors.slack_connector import SlackConnector
from core.connectors.servicenow_connector import ServiceNowConnector
from core.connectors.transcript_connector import TranscriptConnector

# Lazy connector initialization — env vars are loaded before creation
_JIRA_CONNECTOR = None
_GITHUB_CONNECTOR = None
_OUTLOOK_CONNECTOR = None
_SLACK_CONNECTOR = None
_SERVICENOW_CONNECTOR = None
_TRANSCRIPT_CONNECTOR = None


def _get_jira():
    global _JIRA_CONNECTOR
    if _JIRA_CONNECTOR is None:
        _JIRA_CONNECTOR = JiraConnector()
    return _JIRA_CONNECTOR


def _get_github():
    global _GITHUB_CONNECTOR
    if _GITHUB_CONNECTOR is None:
        _GITHUB_CONNECTOR = GitHubConnector()
    return _GITHUB_CONNECTOR


def _get_outlook():
    global _OUTLOOK_CONNECTOR
    if _OUTLOOK_CONNECTOR is None:
        _OUTLOOK_CONNECTOR = OutlookConnector()
    return _OUTLOOK_CONNECTOR


def _get_slack():
    global _SLACK_CONNECTOR
    if _SLACK_CONNECTOR is None:
        _SLACK_CONNECTOR = SlackConnector()
    return _SLACK_CONNECTOR


def _get_servicenow():
    global _SERVICENOW_CONNECTOR
    if _SERVICENOW_CONNECTOR is None:
        _SERVICENOW_CONNECTOR = ServiceNowConnector()
    return _SERVICENOW_CONNECTOR


def _get_transcript():
    global _TRANSCRIPT_CONNECTOR
    if _TRANSCRIPT_CONNECTOR is None:
        _TRANSCRIPT_CONNECTOR = TranscriptConnector()
    return _TRANSCRIPT_CONNECTOR


connector_registry: dict[str, object] = {
    "jira": _get_jira(),
    "defects": _get_servicenow(),
    "emails": _get_outlook(),
    "transcript": _get_transcript(),
    "github": _get_github(),
    "slack": _get_slack(),
}
