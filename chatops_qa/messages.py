"""Slack presentation layer: turn run records into readable message cards."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any


STATUS_LABELS = {
    "queued": "Queued",
    "running": "Running",
    "passed": "PASSED",
    "failed": "FAILED",
    "error": "ERROR",
}


def run_started_message(run_id: str, suite: str) -> dict[str, Any]:
    return {
        "response_type": "ephemeral",
        "text": f"Started the {suite.upper()} test suite. Run ID: `{run_id[:8]}`.",
    }


def run_result_message(run: dict[str, Any]) -> dict[str, Any]:
    """Format final metrics and a short failure excerpt for Slack Block Kit."""

    status = STATUS_LABELS.get(run["status"], run["status"].upper())
    duration = (run.get("duration_ms") or 0) / 1000
    fields = [
        {"type": "mrkdwn", "text": f"*Status*\n{status}"},
        {"type": "mrkdwn", "text": f"*Suite*\n{escape(run['suite'].upper())}"},
        {
            "type": "mrkdwn",
            "text": f"*Results*\n{run['passed_count']} passed · {run['failed_count']} failed · {run['skipped_count']} skipped",
        },
        {"type": "mrkdwn", "text": f"*Duration*\n{duration:.1f}s"},
    ]
    blocks: list[dict[str, Any]] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*SauceDemo UI test run {run['run_id'][:8]}*",
            },
        },
        {"type": "section", "fields": fields},
    ]
    error_excerpt = (run.get("error_log") or "").strip()
    if error_excerpt:
        safe_excerpt = escape(error_excerpt[:1800]).replace("`", "ˋ")
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Failure details*\n```{safe_excerpt}```"},
            }
        )
    if run.get("finished_at"):
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "text": f"Finished at {run['finished_at']} (UTC)",
                        "emoji": False,
                    }
                ],
            }
        )
    return {
        "response_type": "in_channel",
        "text": (
            f"SauceDemo UI run {status}: {run['passed_count']} passed, "
            f"{run['failed_count']} failed, {run['skipped_count']} skipped."
        ),
        "blocks": blocks,
    }


def history_message(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Render recent executions as a compact, private Slack response."""

    if not runs:
        return {"response_type": "ephemeral", "text": "No test runs have been recorded yet."}

    blocks: list[dict[str, Any]] = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Recent SauceDemo test runs*"},
        }
    ]
    for run in runs:
        requested_at = _format_timestamp(run.get("requested_at", ""))
        status = STATUS_LABELS.get(run["status"], run["status"].upper())
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"`{run['run_id'][:8]}`  *{status}* · {escape(run['suite'].upper())}\n"
                        f"{run['passed_count']} passed, {run['failed_count']} failed, "
                        f"{run['skipped_count']} skipped · requested {requested_at} by "
                        f"{escape(run.get('display_name') or run['slack_user_id'])}"
                    ),
                },
            }
        )
    return {
        "response_type": "ephemeral",
        "text": f"Found {len(runs)} recent SauceDemo test run(s).",
        "blocks": blocks,
    }


def command_error_message(message: str) -> dict[str, Any]:
    return {"response_type": "ephemeral", "text": message}


def _format_timestamp(value: str) -> str:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp.strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        return value or "unknown time"
