from __future__ import annotations

import hashlib
import hmac

from chatops_qa.slack_security import is_valid_response_url, verify_slack_signature


def _signature(secret: str, timestamp: str, body: bytes) -> str:
    basestring = b"v0:" + timestamp.encode() + b":" + body
    digest = hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()
    return f"v0={digest}"


def test_valid_recent_slack_signature_is_accepted() -> None:
    body = b"command=%2Frun-tests&text=ui"
    timestamp = "1700000000"
    assert verify_slack_signature(
        "test-secret", timestamp, _signature("test-secret", timestamp, body), body, now=1700000000
    )


def test_signature_rejects_tampering_and_stale_requests() -> None:
    body = b"command=%2Frun-tests&text=ui"
    timestamp = "1700000000"
    valid = _signature("test-secret", timestamp, body)
    assert not verify_slack_signature("test-secret", timestamp, valid, body + b"x", now=1700000000)
    assert not verify_slack_signature("test-secret", timestamp, valid, body, now=1700000600)


def test_response_url_is_limited_to_slack_webhooks() -> None:
    assert is_valid_response_url("https://hooks.slack.com/commands/team/token")
    assert not is_valid_response_url("http://hooks.slack.com/commands/team/token")
    assert not is_valid_response_url("https://example.com/commands")
