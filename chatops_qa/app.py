"""FastAPI webhook listener: Slack presentation entry point and orchestration."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from chatops_qa.commands import CommandError, parse_command
from chatops_qa.config import settings
from chatops_qa.database import Database
from chatops_qa.messages import (
    command_error_message,
    history_message,
    run_started_message,
)
from chatops_qa.runner import execute_and_notify
from chatops_qa.slack_security import is_valid_response_url, verify_slack_signature


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
database = Database(settings.database_path)


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize()
    yield


app = FastAPI(
    title="ChatOps QA Automation Bot",
    description="Trigger SauceDemo Playwright checks and inspect run history from Slack.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/healthz")
async def health_check() -> dict[str, object]:
    """Simple health endpoint for local checks and tunnel diagnostics."""

    return {"status": "ok", "slack_configured": bool(settings.slack_signing_secret)}


@app.post("/slack/commands")
async def slack_commands(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    """Verify Slack's signed form payload and route the two supported commands."""

    raw_body = await request.body()
    if not verify_slack_signature(
        settings.slack_signing_secret,
        request.headers.get("x-slack-request-timestamp"),
        request.headers.get("x-slack-signature"),
        raw_body,
    ):
        raise HTTPException(status_code=401, detail="Invalid or expired Slack signature")

    try:
        decoded_body = raw_body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Expected a UTF-8 form payload") from exc
    form = parse_qs(decoded_body, keep_blank_values=True)
    payload = {key: values[-1] for key, values in form.items() if values}

    try:
        parsed = parse_command(payload.get("command", ""), payload.get("text", ""))
    except CommandError as exc:
        return JSONResponse(command_error_message(str(exc)))

    if parsed.name == "test-history":
        runs = database.history(parsed.history_limit or 5)
        return JSONResponse(history_message(runs))

    response_url = payload.get("response_url", "")
    if not is_valid_response_url(response_url):
        return JSONResponse(
            command_error_message("Slack did not provide a valid response URL for this run.")
        )

    slack_user_id = payload.get("user_id", "unknown-user")
    display_name = payload.get("user_name") or slack_user_id
    channel_id = payload.get("channel_id", "")
    run_id = database.create_run(
        suite=parsed.suite or "ui",
        slack_user_id=slack_user_id,
        display_name=display_name,
        channel_id=channel_id,
    )
    # FastAPI sends the acknowledgment first; this task runs the long browser suite
    # in its worker pool and uses Slack's temporary response URL for the final card.
    background_tasks.add_task(
        execute_and_notify,
        run_id,
        response_url,
        database,
        settings,
    )
    return JSONResponse(run_started_message(run_id, parsed.suite or "ui"))
