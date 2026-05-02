"""Tests for destination_writer.generate_destination_guide.

The function calls Claude Sonnet (or Haiku as fallback) with a prompt
that follows the travel-journalist-writer skill's "guide destination"
format. Returns a dict with the structured article ready to be inserted
into the `articles` table.

Tests mock Anthropic so we never burn tokens in CI. The integration
with the real API is verified in Task 3.3 manual smoke.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


def _fake_anthropic_response(text: str, stop_reason: str = "end_turn"):
    """Build a fake Anthropic Message response carrying `text` as
    the assistant's content. We mimic the SDK's content[0].text shape."""
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    msg.stop_reason = stop_reason
    return msg


def _valid_guide_json() -> dict:
    """A minimal but valid guide JSON shape the prompt asks for."""
    return {
        "title": "Barcelone : guide complet pour un week-end réussi",
        "h1": "Barcelone en 3 jours : itinéraire d'un voyageur exigeant",
        "slug": "barcelone-3-jours-guide",
        "meta_description": "Itinéraire de 3 jours à Barcelone par quartier, adresses testées, budget réel et conseils pour éviter les pièges à touristes.",
        "lead": "Barcelone à 7h du matin, place de Catalunya...",
        "nut_graf": "Ce guide propose un itinéraire de 3 jours organisé par quartier...",
        "top_picks": [
            {"name": "MACBA", "angle": "le seul musée d'art contemporain de la ville",
             "description": "Fondé en 1995, le MACBA expose...",
             "practical": "Plaça dels Àngels 1 · 11h-19h, fermé mardi · 12 €"},
            {"name": "Cervecería Catalana", "angle": "tapas haut de gamme sans réservation",
             "description": "Comptoir et terrasse...",
             "practical": "Mallorca 236 · 9h-1h · plats 4-18 €"},
        ] * 4,  # 8 entries
        "itinerary": [
            {"day": 1, "title": "Gothic Quarter à pied",
             "morning": "9h-12h: Cathédrale et Plaça del Rei",
             "lunch": "Bar del Pla, plats 8-14 €",
             "afternoon": "14h-18h: Born et Picasso",
             "evening": "Tapas dans El Xampanyet",
             "lodging": "Hôtel mid-range à Born, 130 €",
             "rain_plan": "Musée Picasso", "budget_option": "Auberge Equity Point",
             "premium_option": "Hotel Neri 5*"},
            {"day": 2, "title": "Eixample moderniste", "morning": "Casa Batlló",
             "lunch": "Cervecería Catalana", "afternoon": "Sagrada Família",
             "evening": "Cava bar Cinc Sentits", "lodging": "Same",
             "rain_plan": "Casa Vicens", "budget_option": "Sandwich Conesa",
             "premium_option": "Restaurant Cinc Sentits"},
            {"day": 3, "title": "Park Güell + plage", "morning": "Park Güell",
             "lunch": "Pla dels Àngels", "afternoon": "Plage Barceloneta",
             "evening": "Vermouth à Sant Antoni", "lodging": "Same",
             "rain_plan": "Aquarium", "budget_option": "Pic-nic au parc",
             "premium_option": "Beach club W Hotel"},
        ],
        "infos_pratiques": {
            "best_season": "Mai-juin et septembre-octobre, 18-25°C",
            "how_to_get_there": "Vols Paris-BCN dès 35 € sur Vueling",
            "visa": "Aucun pour les ressortissants UE",
            "daily_budget_eco": "60 €", "daily_budget_comfort": "130 €", "daily_budget_premium": "300 €",
            "where_to_sleep": "Born (charme), Eixample (calme), Gràcia (local)",
            "to_avoid": "Las Ramblas en haute saison, restos sur la plage",
            "local_tips": "Tapas servies au comptoir = moins cher qu'en salle",
        },
        "faq": [
            {"q": "Combien de jours pour visiter Barcelone ?", "a": "3 à 4 jours suffisent pour les principaux quartiers."},
            {"q": "Quelle est la meilleure période ?", "a": "Mai-juin et septembre-octobre."},
            {"q": "Faut-il réserver la Sagrada Família à l'avance ?", "a": "Oui, billets coupe-file en ligne 1-2 semaines avant."},
        ],
        "sources": [
            "https://www.barcelonaturisme.com",
            "https://www.barcelona.cat",
        ],
        "tags": ["barcelone", "espagne", "weekend", "city-trip", "catalogne"],
        "photo_query": "Barcelona Spain travel",
    }


def test_generate_returns_structured_dict_on_happy_path():
    """When Claude returns valid JSON, we parse it and add the IATA + dates."""
    from app.agents import destination_writer

    raw_json = json.dumps(_valid_guide_json())
    fake_resp = _fake_anthropic_response(raw_json)
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_resp

    with patch.object(destination_writer, "get_client", return_value=fake_client):
        result = destination_writer.generate_destination_guide("BCN")

    assert result is not None
    assert result["iata"] == "BCN"
    assert result["slug"] == "barcelone-3-jours-guide"
    assert result["title"] == "Barcelone : guide complet pour un week-end réussi"
    assert "lead" in result
    assert "itinerary" in result
    assert "faq" in result
    assert "generated_at" in result
    assert result["word_count"] > 0


def test_generate_strips_markdown_code_fences_around_json():
    """Claude often wraps JSON in ```json ... ```; we must unwrap."""
    from app.agents import destination_writer

    payload = json.dumps(_valid_guide_json())
    raw_text = f"```json\n{payload}\n```"
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_anthropic_response(raw_text)

    with patch.object(destination_writer, "get_client", return_value=fake_client):
        result = destination_writer.generate_destination_guide("BCN")

    assert result is not None
    assert result["slug"] == "barcelone-3-jours-guide"


def test_generate_returns_none_when_anthropic_client_missing():
    """No API key → get_client() returns None → generator must not crash."""
    from app.agents import destination_writer

    with patch.object(destination_writer, "get_client", return_value=None):
        result = destination_writer.generate_destination_guide("BCN")

    assert result is None


def test_generate_returns_none_when_json_invalid():
    """Claude returns garbage → JSON parse fails → return None, log error."""
    from app.agents import destination_writer

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_anthropic_response("not json at all")

    with patch.object(destination_writer, "get_client", return_value=fake_client):
        result = destination_writer.generate_destination_guide("BCN")

    assert result is None


def test_generate_returns_none_when_anthropic_raises():
    """A network / API error must be caught."""
    from app.agents import destination_writer

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("API down")

    with patch.object(destination_writer, "get_client", return_value=fake_client):
        result = destination_writer.generate_destination_guide("BCN")

    assert result is None


def test_word_count_tracks_actual_text_length():
    """word_count is derived from the lead+nut_graf+top_picks+itinerary+faq
    so we can audit whether articles are reaching the 2000-word goal."""
    from app.agents import destination_writer

    raw_json = json.dumps(_valid_guide_json())
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_anthropic_response(raw_json)

    with patch.object(destination_writer, "get_client", return_value=fake_client):
        result = destination_writer.generate_destination_guide("BCN")

    # The fixture contains short text, so word_count is small. We just
    # assert it's > 0 and is an int — the smoke test in Task 3.3 checks
    # the real count against a real Claude generation.
    assert isinstance(result["word_count"], int)
    assert result["word_count"] > 0
