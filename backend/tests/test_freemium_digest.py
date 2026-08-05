"""Tests du programme d'emails freemium — calcul des stats hebdo.

La fonction summarize_matching_deals est PURE : elle prend les deals de
la fenêtre, les alertes complètes reçues par le user et ses préférences,
et rend les compteurs du digest. Les règles reflètent le produit RÉEL
(free tier : bande quotidienne 20-40% + gros deal >=40% hebdo), pas un
quota théorique.
"""
from app.notifications.freemium_digest import (
    summarize_matching_deals,
    week_key,
    month_key,
)
from datetime import datetime, timezone


def _deal(origin="CDG", destination="BCN", discount=35.0, price=80.0,
          baseline=130.0, departure="2026-08-10", trip_type="round_trip"):
    return {
        "origin": origin, "destination": destination,
        "discount_pct": discount, "price": price,
        "baseline_price": baseline, "departure_date": departure,
        "trip_type": trip_type,
    }


PREFS = {
    "airport_codes": ["CDG", "ORY"],
    "blocked_destinations": [],
    "flight_trip_types": ["round_trip", "one_way"],
}


def test_summarize_counts_matching_and_missed():
    deals = [
        _deal(destination="BCN", discount=35),          # matche, pas reçue
        _deal(destination="LIS", discount=52),          # matche, reçue
        _deal(origin="LYS", destination="FCO"),          # mauvais aéroport
        _deal(destination="RAK", discount=12),           # sous le plancher free (20%)
    ]
    sent = [{"destination": "LIS", "departure_date": "2026-08-10"}]
    s = summarize_matching_deals(deals, sent, PREFS)
    assert s["matching"] == 2
    assert s["received_full"] == 1
    assert s["missed"] == 1
    assert s["best_missed"]["destination"] == "BCN"


def test_summarize_best_missed_is_highest_discount_not_sent():
    deals = [
        _deal(destination="BCN", discount=35, price=80, baseline=130),
        _deal(destination="NRT", discount=55, price=450, baseline=1000),
        _deal(destination="LIS", discount=60, price=40, baseline=100),
    ]
    sent = [{"destination": "LIS", "departure_date": "2026-08-10"}]
    s = summarize_matching_deals(deals, sent, PREFS)
    best = s["best_missed"]
    assert best["destination"] == "NRT"
    assert best["discount_pct"] == 55
    # Économie = baseline observée - prix (données réelles, jamais inventées)
    assert best["savings"] == 550


def test_summarize_respects_blocked_destinations_and_trip_types():
    prefs = {
        "airport_codes": ["CDG"],
        "blocked_destinations": ["BCN"],
        "flight_trip_types": ["round_trip"],
    }
    deals = [
        _deal(destination="BCN", discount=50),                      # bloquée
        _deal(destination="LIS", discount=45, trip_type="one_way"),  # trip type exclu
        _deal(destination="FCO", discount=30),                       # OK
    ]
    s = summarize_matching_deals(deals, [], prefs)
    assert s["matching"] == 1
    assert s["best_missed"]["destination"] == "FCO"


def test_summarize_empty_window():
    s = summarize_matching_deals([], [], PREFS)
    assert s == {"matching": 0, "received_full": 0, "missed": 0, "best_missed": None}


def test_summarize_no_savings_when_baseline_missing():
    # baseline absente/incohérente -> pas d'économie affichée (jamais inventer)
    deals = [_deal(destination="BCN", discount=40, price=80, baseline=None)]
    s = summarize_matching_deals(deals, [], PREFS)
    assert s["best_missed"]["savings"] is None


def test_week_and_month_keys():
    dt = datetime(2026, 7, 30, tzinfo=timezone.utc)  # semaine ISO 31
    assert week_key(dt) == "2026_31"
    assert month_key(dt) == "2026_07"
