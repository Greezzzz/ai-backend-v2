from app.features.job.model import Job


def _make_job() -> Job:
    return Job(type="echo", payload={"text": "halo"})


def test_mark_running_sets_status_and_started_at():
    job = _make_job()
    job.mark_running()
    assert job.status == "running"
    assert job.started_at is not None
    assert job.finished_at is None


def test_mark_succeeded_sets_status_result_and_finished():
    job = _make_job()
    job.mark_running()
    job.mark_succeeded("echo: halo")

    assert job.status == "succeeded"
    assert job.result == "echo: halo"
    assert job.error is None
    assert job.finished_at is not None


def test_mark_failed_sets_status_error_and_finished():
    job = _make_job()
    job.mark_running()
    job.mark_failed("boom")

    assert job.status == "failed"
    assert job.error == "boom"
    assert job.result is None
    assert job.finished_at is not None