from __future__ import annotations

from chatops_qa.database import Database


def test_run_lifecycle_is_saved_and_returned_in_history(tmp_path) -> None:
    database = Database(tmp_path / "chatops.sqlite3")
    database.initialize()
    run_id = database.create_run(
        suite="ui",
        slack_user_id="U123",
        display_name="Suraj",
        channel_id="C123",
    )
    database.mark_started(run_id)
    database.finish_run(
        run_id,
        {
            "status": "failed",
            "duration_ms": 1250,
            "total_count": 3,
            "passed_count": 2,
            "failed_count": 1,
            "skipped_count": 0,
            "error_log": "login assertion failed",
            "output_log": "pytest output",
        },
    )

    saved_run = database.get_run(run_id)
    history = database.history()

    assert saved_run is not None
    assert saved_run["status"] == "failed"
    assert saved_run["error_log"] == "login assertion failed"
    assert history[0]["run_id"] == run_id
    assert history[0]["display_name"] == "Suraj"
    assert history[0]["failed_count"] == 1
