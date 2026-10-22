# System architecture

## Components

1. **Presentation layer — Slack**: `/run-tests ui` starts a run and `/test-history [N]` reads recent records. Slack Block Kit cards display run summaries. The service uses Slack's signed slash-command requests and response URLs.
2. **Application layer — FastAPI and Pytest**: `chatops_qa/app.py` validates and routes commands. `commands.py` parses a fixed command grammar. `runner.py` launches the SauceDemo suite as a subprocess after the initial Slack acknowledgment, then sends a completion card.
3. **Data layer — SQLite**: `slack_users` stores trigger identities, `test_runs` stores run state and metrics/logs, and `run_events` records request/start/finish audit events.

## Data flow

```mermaid
flowchart LR
    U[Slack user] -->|/run-tests ui| S[Slack slash command]
    S -->|signed form payload| A[FastAPI webhook]
    A -->|verify signature and parse| C[Command router]
    C -->|create queued run| D[(SQLite)]
    C -->|immediate acknowledgment| S
    C -->|background job| P[Pytest + Playwright]
    P -->|SauceDemo UI checks| W[SauceDemo]
    P -->|metrics and logs| D
    P -->|completion card via response_url| S
    U -->|/test-history N| S
    S -->|signed form payload| A
    A -->|query recent rows| D
    D -->|formatted history| S
```

## Entity relationship

```mermaid
erDiagram
    SLACK_USERS ||--o{ TEST_RUNS : triggers
    TEST_RUNS ||--o{ RUN_EVENTS : records
    SLACK_USERS {
        text slack_user_id PK
        text display_name
        text first_seen_at
        text last_seen_at
    }
    TEST_RUNS {
        text run_id PK
        text slack_user_id FK
        text suite
        text status
        text channel_id
        text requested_at
        text started_at
        text finished_at
        integer duration_ms
        integer total_count
        integer passed_count
        integer failed_count
        integer skipped_count
        text error_log
        text output_log
    }
    RUN_EVENTS {
        integer event_id PK
        text run_id FK
        text event_type
        text details_json
        text occurred_at
    }
```

## Request lifecycle

Slack must be able to reach the local service over HTTPS. The endpoint verifies the HMAC against the exact raw body and rejects timestamps older than five minutes. It writes the run request to SQLite, acknowledges the slash command immediately, and lets the background task execute the browser suite. The final card is sent through Slack's short-lived `response_url`. `/test-history` returns an ephemeral response and defaults to the latest five records, with a maximum of twenty.
