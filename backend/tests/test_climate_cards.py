from types import SimpleNamespace

from app.notifications.climate_cards import (
    climate_summary,
    install_climate_card_formatters,
)


def test_climate_summary_is_explicitly_estimated():
    line = climate_summary("RAK", "2026-08-12", "2026-08-20")
    assert line == "☀️ Climat habituel en août : environ 23–39 °C"


def test_climate_summary_handles_two_months():
    line = climate_summary("JFK", "2026-12-20", "2027-01-04")
    assert line == "❄️ Climat habituel de décembre à janvier : environ -5–7 °C"


def test_unknown_destination_stays_silent():
    assert climate_summary("XXX", "2026-08-12") is None


def test_grouped_card_gets_one_climate_line_per_month():
    def format_grouped_flight_alerts(
        origin_city,
        dest_city,
        destination_iata,
        offers,
        tier="premium",
        **kwargs,
    ):
        return (
            "*Deal*\n\n"
            "📅 *Août 2026*\n"
            "💰 120 €\n\n"
            "📅 *Septembre 2026*\n"
            "💰 130 €"
        )

    def format_simple(flight, *args, **kwargs):
        return "📅 12 août\n💰 120 €"

    def format_package(package, flight, accommodation):
        return "📅 12 août – 20 août\n💰 500 €"

    def format_split(outbound, inbound, *args, **kwargs):
        return "✅ 2 billets vérifiés\n✈️ Aller"

    def format_stopover(leg1, leg2, leg3, *args, **kwargs):
        return "✅ 3 billets vérifiés\n✈️ Étape 1"

    module = SimpleNamespace(
        _FR_MONTHS_LONG=[
            "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
        ],
        format_grouped_flight_alerts=format_grouped_flight_alerts,
        format_flight_deal_alert=format_simple,
        format_oneway_deal_alert=format_simple,
        format_deal_alert=format_package,
        format_split_ticket_alert=format_split,
        format_stopover_alert=format_stopover,
    )

    install_climate_card_formatters(module)
    message = module.format_grouped_flight_alerts(
        "Paris",
        "Marrakech",
        "RAK",
        [
            {"departure_date": "2026-08-12"},
            {"departure_date": "2026-09-10"},
        ],
    )

    assert "📅 *Août 2026*\n☀️ Climat habituel : environ 23–39 °C" in message
    assert "📅 *Septembre 2026*\n☀️ Climat habituel : environ 20–34 °C" in message
