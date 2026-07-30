"""Stripe Checkout route for the 39 EUR annual Premium plan.

Stripe prices are immutable: changing 49 EUR to 39 EUR requires creating a new
Price object. This route reuses an existing compatible 39 EUR/year price when
one already exists, or creates it under the same Stripe Product as the
configured legacy price. Existing subscriptions keep their historical price;
new Checkout sessions use 39 EUR/year.
"""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException

from app.api.routes import get_current_user
from app.config import settings
from app.db import db

logger = logging.getLogger(__name__)
router = APIRouter()

PREMIUM_ANNUAL_PRICE_CENTS = 3900
PREMIUM_CURRENCY = "eur"
PREMIUM_INTERVAL = "year"
PRICE_NICKNAME = "GlobeGenius Premium 39 EUR/an"

_cached_price_id: str | None = None


def _matches_target_price(price: object) -> bool:
    recurring = getattr(price, "recurring", None)
    interval = None
    if recurring:
        interval = (
            recurring.get("interval")
            if isinstance(recurring, dict)
            else getattr(recurring, "interval", None)
        )
    return (
        getattr(price, "active", False)
        and getattr(price, "currency", "") == PREMIUM_CURRENCY
        and getattr(price, "unit_amount", None) == PREMIUM_ANNUAL_PRICE_CENTS
        and interval == PREMIUM_INTERVAL
    )


def _resolve_39_eur_price_id() -> str:
    """Return an active 39 EUR/year Price ID, creating it once when needed."""
    global _cached_price_id
    if _cached_price_id:
        return _cached_price_id

    configured_price_id = settings.STRIPE_PRICE_ID
    if not configured_price_id:
        raise HTTPException(status_code=503, detail="Stripe price not configured")

    try:
        configured_price = stripe.Price.retrieve(configured_price_id)
        if _matches_target_price(configured_price):
            _cached_price_id = configured_price.id
            return _cached_price_id

        product_id = getattr(configured_price, "product", None)
        if not product_id:
            raise HTTPException(status_code=503, detail="Stripe product not found")

        prices = stripe.Price.list(
            product=product_id,
            active=True,
            type="recurring",
            limit=100,
        )
        for price in prices.auto_paging_iter():
            if _matches_target_price(price):
                _cached_price_id = price.id
                break

        if not _cached_price_id:
            created = stripe.Price.create(
                product=product_id,
                currency=PREMIUM_CURRENCY,
                unit_amount=PREMIUM_ANNUAL_PRICE_CENTS,
                recurring={"interval": PREMIUM_INTERVAL},
                nickname=PRICE_NICKNAME,
                metadata={
                    "plan": "premium_annual",
                    "public_price_eur": "39",
                    "created_by": "globegenius_backend",
                },
            )
            _cached_price_id = created.id
            logger.info("Created Stripe annual Premium price: %s", created.id)

        # Prevent the historical 49 EUR price from being used for new sales.
        # Existing subscriptions keep renewing normally even when a Price is
        # archived, which is Stripe's recommended migration model.
        if getattr(configured_price, "active", False):
            stripe.Price.modify(configured_price.id, active=False)
            logger.info("Archived legacy Stripe price: %s", configured_price.id)

        return _cached_price_id
    except HTTPException:
        raise
    except stripe.StripeError as exc:
        logger.exception("Unable to resolve the 39 EUR Stripe price")
        raise HTTPException(status_code=503, detail="Stripe price unavailable") from exc


@router.post("/api/stripe/create-checkout")
async def create_checkout_39(user: dict = Depends(get_current_user)):
    """Create a subscription Checkout session at exactly 39 EUR per year."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    user_id = user["sub"]
    user_email = user.get("email", "")

    customer_id = None
    if db:
        prefs = (
            db.table("user_preferences")
            .select("stripe_customer_id")
            .eq("user_id", user_id)
            .execute()
        )
        customer_id = (
            prefs.data[0].get("stripe_customer_id") if prefs.data else None
        )

    try:
        if not customer_id:
            customer = stripe.Customer.create(
                email=user_email,
                metadata={"user_id": user_id},
            )
            customer_id = customer.id
            if db:
                (
                    db.table("user_preferences")
                    .update({"stripe_customer_id": customer_id})
                    .eq("user_id", user_id)
                    .execute()
                )

        price_id = _resolve_39_eur_price_id()
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/home?payment=success",
            cancel_url=f"{settings.FRONTEND_URL}/home?payment=cancel",
            subscription_data={
                "metadata": {
                    "plan": "premium_annual",
                    "public_price_eur": "39",
                    "user_id": user_id,
                }
            },
        )
        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "annual_price_eur": 39,
        }
    except HTTPException:
        raise
    except stripe.StripeError as exc:
        logger.error("Stripe checkout error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
