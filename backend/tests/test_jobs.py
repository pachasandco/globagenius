from app.scheduler.jobs import get_scheduler_jobs


def test_get_scheduler_jobs_returns_all_jobs():
    jobs = get_scheduler_jobs()
    job_names = [j["id"] for j in jobs]
    assert "scrape_flights_02" in job_names
    assert "scrape_flights_22" in job_names
    assert "scrape_accommodations_03" in job_names
    assert "travelpayouts_enrichment" in job_names
    assert "recalculate_baselines" in job_names
    assert "expire_stale_data" in job_names
    assert "daily_digest" in job_names
    assert "daily_admin_report" in job_names


def test_get_scheduler_jobs_flight_every_4h():
    jobs = get_scheduler_jobs()
    flight_jobs = [j for j in jobs if j["id"].startswith("scrape_flights")]
    assert len(flight_jobs) == 6
    hours = sorted([j["hour"] for j in flight_jobs])
    assert hours == [2, 6, 10, 14, 18, 22]


def test_get_scheduler_jobs_hotels_1x_daily():
    jobs = get_scheduler_jobs()
    hotel_jobs = [j for j in jobs if j["id"].startswith("scrape_accommodations")]
    assert len(hotel_jobs) == 1
    assert hotel_jobs[0]["hour"] == 3
