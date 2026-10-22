"""Slack request signature verification and response URL validation."""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlparse


def verify_slack_signature(
    signing_secret: str,
    timestamp: str | None,
    signature: str | None,
    raw_body: bytes,
    *,
    now: float | None = None,
    tolerance_seconds: int = 300,
) -> bool:
    """Verify Slack's v0 HMAC over the exact raw request body and fresh timestamp."""

    if not signing_secret or not timestamp or not signature:
        return False
    try:
        request_time = int(timestamp)
    except (TypeError, ValueError):
        return False
    current_time = time.time() if now is None else now
    if abs(current_time - request_time) > tolerance_seconds:
        return False

    basestring = b"v0:" + timestamp.encode("utf-8") + b":" + raw_body
    digest = hmac.new(
        signing_secret.encode("utf-8"), basestring, hashlib.sha256
    ).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature)


def is_valid_response_url(value: str) -> bool:
    """Accept only Slack's HTTPS response webhooks to avoid arbitrary callbacks."""

    try:
        parsed = urlparse(value)
        hostname = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and parsed.username is None
            and parsed.password is None
            and hostname in {"hooks.slack.com", "hooks.slack-gov.com"}
            and bool(parsed.path)
        )
    except (TypeError, ValueError):
        return False
