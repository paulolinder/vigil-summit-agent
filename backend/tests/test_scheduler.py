import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def _make_sb(job=None, lead_stage="ENRICHED", msgs=None):
    """Build a per-table supabase mock for scheduler tests."""
    tables = {}

    def get_table(name):
        if name not in tables:
            tables[name] = MagicMock()
        return tables[name]

    mock = MagicMock()
    mock.table.side_effect = get_table

    # scheduled_jobs — fetch by id+status (double .eq chain)
    tables["scheduled_jobs"] = MagicMock()
    (
        tables["scheduled_jobs"]
        .select.return_value
        .eq.return_value
        .eq.return_value
        .single.return_value
        .execute.return_value
        .data
    ) = job
    tables["scheduled_jobs"].update.return_value.eq.return_value.execute.return_value = None

    # leads — stage check
    tables["leads"] = MagicMock()
    tables["leads"].select.return_value.eq.return_value.single.return_value.execute.return_value.data = (
        {"stage": lead_stage} if lead_stage else None
    )

    # messages — engagement query (direction + channel filter)
    tables["messages"] = MagicMock()
    (
        tables["messages"]
        .select.return_value
        .eq.return_value
        .eq.return_value
        .eq.return_value
        .order.return_value
        .limit.return_value
        .execute.return_value
        .data
    ) = msgs or []

    return mock


_JOB = {
    "id": "job-001",
    "lead_id": "lead-001",
    "job_type": "FOLLOWUP_D3",
    "condition": {},
    "retry_count": 0,
    "max_retries": 3,
}


async def test_skip_when_job_not_found():
    """No-op when job is missing or already processed."""
    mock_sb = _make_sb(job=None)
    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb):
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")
    # Verify no update was called
    mock_sb.table("scheduled_jobs").update.assert_not_called()


async def test_skip_opted_out_lead():
    mock_sb = _make_sb(job=_JOB, lead_stage="OPTED_OUT")
    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb):
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "SKIPPED" in update_calls


async def test_skip_when_lead_not_found():
    mock_sb = _make_sb(job=_JOB, lead_stage=None)
    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb):
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "SKIPPED" in update_calls


async def test_skip_if_wrong_stage():
    job = {**_JOB, "condition": {"only_if_stage": "CONFIRMED"}}
    mock_sb = _make_sb(job=job, lead_stage="ENRICHED")
    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb):
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "SKIPPED" in update_calls


async def test_skip_if_email_opened_and_condition_set():
    job = {**_JOB, "condition": {"skip_if_opened": True}}
    msgs = [{"opened_at": "2026-05-29T10:00:00+00:00", "clicked_at": None}]
    mock_sb = _make_sb(job=job, lead_stage="ENRICHED", msgs=msgs)
    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb):
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "SKIPPED" in update_calls


async def test_skip_if_email_clicked_with_only_if_not_clicked():
    job = {**_JOB, "condition": {"only_if_not_clicked": True}}
    msgs = [{"opened_at": "2026-05-29T10:00:00+00:00", "clicked_at": "2026-05-29T10:05:00+00:00"}]
    mock_sb = _make_sb(job=job, lead_stage="ENRICHED", msgs=msgs)
    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb):
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "SKIPPED" in update_calls


async def test_marks_done_on_successful_run():
    mock_sb = _make_sb(job=_JOB, lead_stage="ENRICHED")
    mock_run_agent = AsyncMock(return_value="Agente concluiu.")

    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb), \
         patch("app.scheduler.jobs.run_agent", mock_run_agent):
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    mock_run_agent.assert_called_once_with("lead-001", "FOLLOWUP_D3")
    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "DONE" in update_calls


async def test_retry_on_exception_increments_count():
    """On failure with retries remaining, job is rescheduled with incremented retry_count."""
    job = {**_JOB, "retry_count": 0, "max_retries": 3}
    mock_sb = _make_sb(job=job, lead_stage="ENRICHED")
    mock_run_agent = AsyncMock(side_effect=RuntimeError("Anthropic timeout"))

    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb), \
         patch("app.scheduler.jobs.run_agent", mock_run_agent), \
         patch("app.scheduler.runner.add_job_to_scheduler") as mock_add:

        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "retry_count" in update_calls
    assert "FAILED" not in update_calls
    mock_add.assert_called_once()


async def test_marks_failed_after_max_retries():
    """After max_retries exhausted, job is permanently marked FAILED."""
    job = {**_JOB, "retry_count": 2, "max_retries": 3}
    mock_sb = _make_sb(job=job, lead_stage="ENRICHED")
    mock_run_agent = AsyncMock(side_effect=RuntimeError("Persistent error"))

    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb), \
         patch("app.scheduler.jobs.run_agent", mock_run_agent), \
         patch("app.scheduler.runner.add_job_to_scheduler") as mock_add:

        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "FAILED" in update_calls
    mock_add.assert_not_called()


async def test_does_not_skip_when_email_not_opened_but_skip_if_opened_set():
    """skip_if_opened=True should NOT skip if the email was never opened."""
    job = {**_JOB, "condition": {"skip_if_opened": True}}
    msgs = [{"opened_at": None, "clicked_at": None}]
    mock_sb = _make_sb(job=job, lead_stage="ENRICHED", msgs=msgs)
    mock_run_agent = AsyncMock(return_value="ok")

    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb), \
         patch("app.scheduler.jobs.run_agent", mock_run_agent):
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    mock_run_agent.assert_called_once()
