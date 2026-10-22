from __future__ import annotations

import pytest

from chatops_qa.commands import CommandError, parse_command


def test_run_tests_accepts_only_the_ui_suite() -> None:
    assert parse_command("/run-tests", "ui").suite == "ui"


@pytest.mark.parametrize("text", ["", "all", "ui; whoami", "ui extra"])
def test_run_tests_rejects_unrecognized_input(text: str) -> None:
    with pytest.raises(CommandError):
        parse_command("/run-tests", text)


def test_history_defaults_to_five_and_accepts_a_bounded_limit() -> None:
    assert parse_command("/test-history", "").history_limit == 5
    assert parse_command("/test-history", "12").history_limit == 12


@pytest.mark.parametrize("text", ["0", "21", "latest", "2 extra"])
def test_history_rejects_invalid_limits(text: str) -> None:
    with pytest.raises(CommandError):
        parse_command("/test-history", text)
