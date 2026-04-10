from app.scheduler.jobs import get_scheduler_jobs


def test_get_scheduler_jobs_returns_all_jobs():
    jobs = get_scheduler_jobs()
    job_names = [j["id"] for j in jobs]
    # 12 flight scrapes (every 2h)
    assert "scrape_flights_00" in job_names
    assert "scrape_flights_12" in job_names
    assert "scrape_flights_22" in job_names
    # 2 hotel scrapes
    assert "scrape_accommodations_03" in job_names
    assert "scrape_accommodations_15" in job_names
    # Maintenance
    assert "recalculate_baselines" in job_names
    assert "expire_stale_data" in job_names
    assert "daily_digest" in job_names
    assert "daily_admin_report" in job_names


def test_get_scheduler_jobs_flight_every_2h():
    jobs = get_scheduler_jobs()
    flight_jobs = [j for j in jobs if j["id"].startswith("scrape_flights")]
    assert len(flight_jobs) == 12
    hours = sorted([j["hour"] for j in flight_jobs])
    assert hours == list(range(0, 24, 2))


def test_get_scheduler_jobs_hotels_2x_daily():
    jobs = get_scheduler_jobs()
    hotel_jobs = [j for j in jobs if j["id"].startswith("scrape_accommodations")]
    assert len(hotel_jobs) == 2
    hours = sorted([j["hour"] for j in hotel_jobs])
    assert hours == [3, 15]
