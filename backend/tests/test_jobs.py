from app.scheduler.jobs import get_scheduler_jobs


def test_get_scheduler_jobs_returns_all_jobs():
    jobs = get_scheduler_jobs()
    job_names = [j["id"] for j in jobs]
    assert "scrape_flights_early" in job_names
    assert "scrape_flights_afternoon" in job_names
    assert "scrape_flights_tuesday" in job_names
    assert "scrape_accommodations_monday" in job_names
    assert "scrape_accommodations_thursday" in job_names
    assert "recalculate_baselines" in job_names
    assert "expire_stale_data" in job_names
    assert "daily_digest" in job_names
    assert "daily_admin_report" in job_names


def test_get_scheduler_jobs_strategic_timing():
    jobs = get_scheduler_jobs()
    jobs_by_id = {j["id"]: j for j in jobs}
    # Flights: 4h daily, 14h daily, 2h tuesday
    assert jobs_by_id["scrape_flights_early"]["hour"] == 4
    assert jobs_by_id["scrape_flights_afternoon"]["hour"] == 14
    assert jobs_by_id["scrape_flights_tuesday"]["hour"] == 2
    assert jobs_by_id["scrape_flights_tuesday"]["day_of_week"] == "tue"
    # Hotels: monday 3h, thursday 3h
    assert jobs_by_id["scrape_accommodations_monday"]["hour"] == 3
    assert jobs_by_id["scrape_accommodations_monday"]["day_of_week"] == "mon"
    assert jobs_by_id["scrape_accommodations_thursday"]["day_of_week"] == "thu"
