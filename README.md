# ChatOps QA Automation & Testing Bot

A local Python service that connects Slack slash commands to a Playwright/Pytest UI suite for SauceDemo. SQLite stores the person who triggered each run, status, timing, test counts, logs, and audit events.

## Architecture and stack

- **Slack presentation layer:** `/run-tests ui` and `/test-history [count]`, with Block Kit summaries.
- **Backend:** Python 3.10+, FastAPI, Uvicorn, HTTPX, Pytest, and Playwright.
- **Data:** SQLite through Python's standard library `sqlite3` module.
- **Test target:** SauceDemo at `https://www.saucedemo.com/`.

The architecture and data flow diagrams are in [docs/architecture.md](docs/architecture.md).

For complete Windows local setup and a live Render deployment walkthrough, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Requirements

- Python 3.10 or newer
- Internet access to install packages, download the Chromium browser, reach SauceDemo, and receive Slack webhooks
- A Slack workspace where you can install a custom app (optional for running the test suite directly)
- A public HTTPS tunnel such as ngrok or Cloudflare Tunnel for Slack to reach a local development server

## Run locally on Windows PowerShell

From the project directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
Copy-Item .env.example .env
```

Open `.env` and set `SLACK_SIGNING_SECRET` from your Slack app. The SauceDemo credentials in the example are the public practice account defaults. Change the database path or run timeout there if needed.

Start the service:

```powershell
python -m uvicorn chatops_qa.app:app --reload --host 0.0.0.0 --port 8000
```

Check `http://127.0.0.1:8000/healthz`; it should return JSON with `"status":"ok"`. The local database is created automatically at `data/chatops.sqlite3` when the service starts.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
python -m uvicorn chatops_qa.app:app --reload --host 0.0.0.0 --port 8000
```

## Configure Slack

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps), install it in your workspace, and copy its **Signing Secret** into `.env` as `SLACK_SIGNING_SECRET`.
2. Create two slash commands in the app configuration: `/run-tests` and `/test-history`.
3. Start an HTTPS tunnel to port `8000` (for example, `ngrok http 8000`). Slack cannot call `localhost` directly.
4. Set the Request URL for both slash commands to `https://YOUR-TUNNEL-DOMAIN/slack/commands` and save the commands.
5. Restart the FastAPI service after changing `.env`.

The slash-command endpoint is authenticated using Slack's request-signing headers. Do not commit `.env` or share your Signing Secret.
This implementation replies through each command's temporary `response_url` and does not call Slack's Web API, so a bot OAuth token is not needed for the stated workflow.

## Use the commands

In a Slack channel where the app is available:

```text
/run-tests ui
/test-history
/test-history 10
```

`/run-tests ui` immediately acknowledges the command, then posts the final pass/fail summary to the channel. `/test-history` returns up to five recent runs privately to the requesting user; the optional count can be from 1 through 20. The service only permits the fixed `ui` suite, so command text is never interpreted as a shell command.

You can run the same SauceDemo suite without Slack after setup:

```powershell
python -m pytest tests/saucedemo -q
```

Run the database, command-parser, and Slack-signature unit checks with:

```powershell
python -m pytest tests/unit -q
```

## Project layout

```text
chatops_qa/          FastAPI webhook, command parser, Slack cards, runner, SQLite repository
tests/saucedemo/     Browser checks for login and cart flows
tests/unit/          Command parsing and Slack request-signature checks
docs/architecture.md System/data-flow and ER diagrams
```

## Hosting note

The included deployment walkthrough hosts this training/demo app as one Render web service with a persistent disk for SQLite history. The app runs browser tests in the web service process, so an in-progress run can be interrupted during a restart or deployment; use a durable queue and separate worker before relying on it for production workloads.
