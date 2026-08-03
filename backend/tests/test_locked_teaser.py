"""Unit tests for the FREE-tier locked teaser formatter.

The teaser is a BLURRED preview of an exceptional premium deal: it reveals
the deal TYPE + discount % + a COARSE price bucket + the origin CITY, and
must NEVER leak the destination, dates, or a booking link.
"""
import pytest

from app.notifications.telegram import format_locked_teaser, _coarse_price_bucket


def test_long_haul_variant():
    out = format_locked_teaser("long_haul", 38, 420, "Paris")
    assert out.startswith("🔒 Vol long-courrier −38 %")
    assert "Depuis Paris" in out
    assert "A/R" in out
    # Coarse bucket, never the exact 420.
    assert "~400 €" in out
    assert "420" not in out


def test_one_way_variant():
    out = format_locked_teaser("one_way", 62, 19, "Lyon")
    # One-way headline carries the (bucketed) price, not the discount.
    assert out.startswith("🔒 Aller simple à ~20 €")
    assert "Depuis Lyon" in out
    # 19€ must read as a sensible order of magnitude, not "~0 €".
    assert "~0 €" not in out
    assert "19" not in out


def test_split_ticket_variant():
    out = format_locked_teaser("split_ticket", 45, 272, "Paris")
    assert out.startswith("🔒 Combo malin −45 %")
    assert "Depuis Paris" in out
    assert "~250 €" in out
    assert "272" not in out


def test_cta_points_to_profile_upgrade_page():
    from app.config import settings
    out = format_locked_teaser("long_haul", 38, 420, "Paris")
    assert f"{settings.FRONTEND_URL}/profile" in out
    assert "Premium" in out


@pytest.mark.parametrize(
    "price,expected",
    [
        (12, 10),
        (19, 20),
        (45, 40),
        (49, 50),
        (250, 250),
        (272, 250),
        (299, 300),
        (300, 300),
        (318, 300),
        (351, 400),
        (420, 400),
    ],
)
def test_price_rounding_is_coarse(price, expected):
    assert _coarse_price_bucket(price) == expected


def test_exact_price_never_shown():
    # A representative exact qualified price that is NOT a bucket boundary.
    out = format_locked_teaser("long_haul", 33, 437, "Marseille")
    assert "437" not in out
    # Rounds to nearest 100 above 300.
    assert "~400 €" in out


@pytest.mark.parametrize("deal_type", ["long_haul", "one_way", "split_ticket"])
def test_destination_never_appears(deal_type):
    # The destination is passed nowhere into the formatter — but assert the
    # invariant explicitly: a recognisable destination token must be absent
    # from the rendered teaser regardless of deal type.
    destination_iata = "JFK"
    destination_city = "New York"
    out = format_locked_teaser(deal_type, 40, 280, "Paris")
    assert destination_iata not in out
    assert destination_city not in out
    # No booking link / redirect token either — only the upgrade CTA.
    assert "aviasales" not in out.lower()
    assert "/r/" not in out


def test_unknown_deal_type_falls_back_to_round_trip_framing():
    out = format_locked_teaser("mystery", 30, 500, "Toulouse")
    assert out.startswith("🔒 Vol long-courrier −30 %")
    assert "~500 €" in out


def test_origin_city_defaults_when_blank():
    out = format_locked_teaser("long_haul", 30, 400, "")
    assert "Depuis Paris" in out


# ── Plafond quotidien (2026-08-03) ──────────────────────────────────────────
# Sans plafond, 11 teasers/user/jour mesurés en prod. La règle : un user
# déjà servi aujourd'hui est exclu AVANT tout envoi.

@pytest.mark.asyncio
async def test_teaser_daily_cap_skips_already_teased_user():
    from unittest.mock import MagicMock, AsyncMock, patch
    from app.scheduler import jobs

    db_mock = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "gte", "limit"):
        getattr(chain, m).return_value = chain
    db_mock.table.return_value = chain
    # 1er execute = requête du plafond (u_capped déjà servi aujourd'hui),
    # suivants = dedup par deal (vides).
    chain.execute.side_effect = [
        MagicMock(data=[{"user_id": "u_capped"}]),
        MagicMock(data=[]),
    ]

    send_mock = AsyncMock(return_value=True)
    persist_mock = AsyncMock()
    with patch.object(jobs, "db", db_mock), \
         patch("app.notifications.telegram.send_locked_teaser", new=send_mock), \
         patch.object(jobs, "_persist_sent_alerts_with_retry", new=persist_mock):
        sent = await jobs._dispatch_free_teasers(
            deal_type="long_haul",
            destination="NRT",
            departure_date="2026-10-01",
            return_date="2026-10-15",
            price=450.0,
            discount_pct=44.0,
            origin="CDG",
            free_subs=[
                {"user_id": "u_capped", "chat_id": 1, "blocked_destinations": set()},
                {"user_id": "u_fresh", "chat_id": 2, "blocked_destinations": set()},
            ],
        )

    assert sent == 1
    assert send_mock.call_count == 1
    assert send_mock.call_args.kwargs["chat_id"] == 2  # u_fresh seulement


@pytest.mark.asyncio
async def test_teaser_cap_lookup_failure_fails_closed():
    from unittest.mock import MagicMock, patch
    from app.scheduler import jobs

    db_mock = MagicMock()
    db_mock.table.side_effect = Exception("db down")
    with patch.object(jobs, "db", db_mock):
        sent = await jobs._dispatch_free_teasers(
            deal_type="long_haul", destination="NRT",
            departure_date="2026-10-01", return_date="2026-10-15",
            price=450.0, discount_pct=44.0, origin="CDG",
            free_subs=[{"user_id": "u1", "chat_id": 1, "blocked_destinations": set()}],
        )
    assert sent == 0  # rater un teaser est sans gravité, spammer non
