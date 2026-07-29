import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.api.routes import (
    SignupRequest,
    _check_rate_limit,
    _client_ip,
    _create_jwt,
    _hash_password,
    _send_welcome_email_safe,
    db,
)
from app.auth.email_validator import validate_email_address

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/auth/signup-public")
async def signup_public(req: SignupRequest, request: Request, bg_tasks: BackgroundTasks):
    """Create a standard free account without the historical founder cap.

    Existing founder grants remain untouched. New accounts are created on the
    free tier and may subscribe to Premium once Stripe checkout is opened.
    """
    _check_rate_limit(f"signup-public:{_client_ip(request)}")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caractères")

    email_check = await validate_email_address(req.email)
    if not email_check.is_valid:
        if email_check.reason == "typo_tld":
            raise HTTPException(
                status_code=400,
                detail=f"L'extension du domaine '{email_check.domain}' semble incorrecte. Vérifiez l'adresse.",
            )
        if email_check.reason == "no_mx":
            raise HTTPException(
                status_code=400,
                detail=f"Le domaine '{email_check.domain}' ne peut pas recevoir d'email. Vérifiez l'adresse.",
            )
        raise HTTPException(status_code=400, detail="Adresse email invalide.")

    loop = asyncio.get_running_loop()
    existing = await loop.run_in_executor(
        None,
        lambda: db.table("users").select("id").eq("email", req.email).execute(),
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé")

    password_hash = await loop.run_in_executor(None, _hash_password, req.password)
    user = await loop.run_in_executor(
        None,
        lambda: db.table("users").insert({
            "email": req.email,
            "password_hash": password_hash,
            "tier": "free",
        }).execute(),
    )
    if not user.data:
        raise HTTPException(status_code=500, detail="Erreur lors de la création du compte")

    user_id = user.data[0]["id"]
    try:
        await loop.run_in_executor(
            None,
            lambda: db.table("user_preferences").insert({
                "user_id": user_id,
                "airport_codes": ["CDG"],
                "offer_types": ["flight"],
                "flight_trip_types": ["round_trip", "one_way"],
                "deal_tier": "regular",
                "include_split_tickets": False,
                "accept_longhaul_stopover": True,
            }).execute(),
        )
    except Exception as exc:
        logger.exception("Preference creation failed for new user %s", user_id)
        try:
            await loop.run_in_executor(
                None,
                lambda: db.table("users").delete().eq("id", user_id).execute(),
            )
        except Exception:
            logger.exception("Rollback failed for incomplete signup %s", user_id)
        raise HTTPException(status_code=500, detail="Erreur lors de l'initialisation du compte") from exc

    bg_tasks.add_task(_send_welcome_email_safe, req.email)
    token = _create_jwt(user_id, req.email)
    return {"user_id": user_id, "email": req.email, "token": token}
