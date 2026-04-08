from app.scheduler.jobs import get_scheduler_jobs


def test_get_scheduler_jobs_returns_all_jobs():
    jobs = get_scheduler_jobs()
    job_names = [j["id"] for j in jobs]
    # 6 flight scrapes
    assert "scrape_flights_02" in job_names
    assert "scrape_flights_06" in job_names
    assert "scrape_flights_10" in job_names
    assert "scrape_flights_14" in job_names
    assert "scrape_flights_18" in job_names
    assert "scrape_flights_22" in job_names
    # 1 hotel scrape
    assert "scrape_accommodations_daily" in job_names
    # Maintenance
    assert "recalculate_baselines" in job_names
    assert "expire_stale_data" in job_names
    assert "daily_digest" in job_names
    assert "daily_admin_report" in job_names


def test_get_scheduler_jobs_flight_coverage():
    jobs = get_scheduler_jobs()
    flight_jobs = [j for j in jobs if j["id"].startswith("scrape_flights")]
    assert len(flight_jobs) == 6
    hours = sorted([j["hour"] for j in flight_jobs])
    assert hours == [2, 6, 10, 14, 18, 22]  # Every 4h


def test_get_scheduler_jobs_hotel_daily():
    jobs = get_scheduler_jobs()
    hotel_jobs = [j for j in jobs if j["id"].startswith("scrape_accommodations")]
    assert len(hotel_jobs) == 1
    assert hotel_jobs[0]["hour"] == 3
