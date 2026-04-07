from app.scheduler.jobs import get_scheduler_jobs


def test_get_scheduler_jobs_returns_all_jobs():
    jobs = get_scheduler_jobs()
    job_names = [j["id"] for j in jobs]
    assert "scrape_flights" in job_names
    assert "scrape_accommodations" in job_names
    assert "recalculate_baselines" in job_names
    assert "expire_stale_data" in job_names
    assert "daily_digest" in job_names
    assert "daily_admin_report" in job_names


def test_get_scheduler_jobs_has_correct_intervals():
    jobs = get_scheduler_jobs()
    jobs_by_id = {j["id"]: j for j in jobs}
    assert jobs_by_id["scrape_flights"]["hours"] == 2
    assert jobs_by_id["scrape_accommodations"]["hours"] == 4
    assert jobs_by_id["expire_stale_data"]["minutes"] == 30
