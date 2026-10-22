"""Execute the fixed SauceDemo Pytest suite and post its result to Slack."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import httpx

from chatops_qa.config import Settings
from chatops_qa.database import Database
from chatops_qa.messages import run_result_message


logger = logging.getLogger(__name__)
MAX_LOG_CHARS = 20_000


def execute_and_notify(run_id: str, response_url: str, database: Database, config: Settings) -> None:
    """Background task: run Pytest, persist metrics, and notify the Slack channel."""

    try:
        database.mark_started(run_id)
        result = execute_ui_suite(config)
    except Exception as exc:  # Keep an unexpected worker exception visible in history.
        logger.exception("Unexpected error while executing run %s", run_id)
        result = _error_result(f"The test worker stopped unexpectedly: {exc}")
    database.finish_run(run_id, result)
    run = database.get_run(run_id)
    if run is None:
        logger.error("Run %s disappeared before its Slack notification was built", run_id)
        return
    try:
        response = httpx.post(
            response_url,
            json=run_result_message(run),
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        # The run remains persisted even if Slack's temporary response URL expired.
        logger.exception("Could not post completed run %s to Slack", run_id)


def execute_ui_suite(config: Settings) -> dict[str, Any]:
    """Run only the maintained UI suite; Slack text never becomes a shell argument."""

    test_file = config.project_root / "tests" / "saucedemo" / "test_saucedemo.py"
    if not test_file.is_file():
        return _error_result("The SauceDemo UI test suite was not found in this installation.")

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="chatops-qa-") as temp_dir:
        junit_path = Path(temp_dir) / "junit.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "--junitxml",
            str(junit_path),
            "-q",
            "--disable-warnings",
        ]
        environment = os.environ.copy()
        environment.update(
            {
                "SAUCEDEMO_BASE_URL": config.sauce_demo_base_url,
                "SAUCEDEMO_USERNAME": config.sauce_demo_username,
                "SAUCEDEMO_PASSWORD": config.sauce_demo_password,
            }
        )
        try:
            completed = subprocess.run(
                command,
                cwd=config.project_root,
                env=environment,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=config.run_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            output = _as_text(exc.stdout) + _as_text(exc.stderr)
            return {
                **_error_result("The UI test run exceeded its configured time limit.", output),
                "duration_ms": elapsed_ms,
            }
        except OSError as exc:
            return _error_result(f"Could not start Pytest: {exc}")

        elapsed_ms = int((time.monotonic() - started) * 1000)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        output_log = (stdout + ("\n" + stderr if stderr else ""))[-MAX_LOG_CHARS:]
        metrics = _read_junit_metrics(junit_path)
        if metrics is None:
            explanation = "Pytest did not produce a test report. Check the saved execution log."
            return {
                **_error_result(explanation, output_log),
                "duration_ms": elapsed_ms,
            }

        failures = _failure_details(junit_path)
        has_tests = metrics["total_count"] > 0
        status = "passed" if completed.returncode == 0 and has_tests else ("failed" if has_tests else "error")
        error_log = failures or (stderr[-MAX_LOG_CHARS:] if status != "passed" else "")
        if not has_tests and not error_log:
            error_log = "Pytest collected no tests."
        return {
            "status": status,
            **metrics,
            "duration_ms": elapsed_ms,
            "error_log": error_log[-MAX_LOG_CHARS:],
            "output_log": output_log,
        }


def _read_junit_metrics(path: Path) -> dict[str, int] | None:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return None
    cases = list(root.iter("testcase"))
    if cases:
        skipped = sum(case.find("skipped") is not None for case in cases)
        failed = sum(
            case.find("failure") is not None or case.find("error") is not None
            for case in cases
        )
        return {
            "total_count": len(cases),
            "passed_count": len(cases) - failed - skipped,
            "failed_count": failed,
            "skipped_count": skipped,
        }

    # Empty reports can still carry collection errors on a testsuite element.
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        return None
    return {
        "total_count": sum(int(suite.attrib.get("tests", 0)) for suite in suites),
        "passed_count": 0,
        "failed_count": sum(
            int(suite.attrib.get("failures", 0)) + int(suite.attrib.get("errors", 0))
            for suite in suites
        ),
        "skipped_count": sum(int(suite.attrib.get("skipped", 0)) for suite in suites),
    }


def _failure_details(path: Path) -> str:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return ""
    messages: list[str] = []
    for case in root.iter("testcase"):
        for failure in list(case.findall("failure")) + list(case.findall("error")):
            label = f"{case.attrib.get('classname', '')}.{case.attrib.get('name', 'test')}"
            detail = failure.attrib.get("message", "") or (failure.text or "").strip()
            messages.append(f"{label}: {detail}".strip())
    return "\n\n".join(messages)


def _error_result(message: str, output: str = "") -> dict[str, Any]:
    return {
        "status": "error",
        "total_count": 0,
        "passed_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "duration_ms": 0,
        "error_log": message,
        "output_log": output[-MAX_LOG_CHARS:],
    }


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
