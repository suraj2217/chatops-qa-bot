"""Parse the small, explicit command language exposed through Slack."""

from __future__ import annotations

from dataclasses import dataclass


class CommandError(ValueError):
    """Raised when a Slack command or its arguments are not supported."""


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    suite: str | None = None
    history_limit: int | None = None


def parse_command(command: str, text: str) -> ParsedCommand:
    """Validate a Slack slash command without interpreting arbitrary shell input."""

    name = command.strip().lstrip("/").lower()
    arguments = text.strip().split()

    if name == "run-tests":
        if len(arguments) != 1 or arguments[0].lower() != "ui":
            raise CommandError("Usage: /run-tests ui")
        return ParsedCommand(name=name, suite="ui")

    if name == "test-history":
        if len(arguments) > 1:
            raise CommandError("Usage: /test-history [number of runs, 1-20]")
        if not arguments:
            return ParsedCommand(name=name, history_limit=5)
        try:
            limit = int(arguments[0])
        except ValueError as exc:
            raise CommandError("History count must be a whole number from 1 to 20.") from exc
        if not 1 <= limit <= 20:
            raise CommandError("History count must be between 1 and 20.")
        return ParsedCommand(name=name, history_limit=limit)

    raise CommandError("Unknown command. Use /run-tests ui or /test-history.")
