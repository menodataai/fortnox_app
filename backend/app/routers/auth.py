"""OAuth flow endpoints: /auth/login → Fortnox consent → /auth/callback."""

import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from .. import token_store
from ..config import settings
from ..fortnox import auth as fortnox_auth

router = APIRouter(prefix="/auth", tags=["auth"])

# Single-user local app: one pending state at a time is fine
_pending_states: set[str] = set()


@router.get("/login")
async def login():
    if settings.demo_mode:
        raise HTTPException(status_code=400, detail="Demo mode — no Fortnox connection.")
    if not settings.fortnox_client_id or not settings.fortnox_client_secret:
        raise HTTPException(
            status_code=500,
            detail="FORTNOX_CLIENT_ID / FORTNOX_CLIENT_SECRET missing — fill in the .env file first.",
        )
    state = secrets.token_urlsafe(24)
    _pending_states.add(state)
    return RedirectResponse(fortnox_auth.build_authorize_url(state))


@router.get("/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        raise HTTPException(status_code=400, detail=f"Fortnox returned error: {error}")
    if state not in _pending_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")
    _pending_states.discard(state)
    await fortnox_auth.exchange_code(code)
    # Kick off the first mirror sync right away so the dashboard fills itself
    import asyncio

    from .. import sync as sync_service

    asyncio.create_task(sync_service.run())
    return RedirectResponse(settings.frontend_origin + "?connected=1")


@router.get("/status")
async def status():
    if settings.demo_mode:
        return {"connected": True, "scopes": "demo", "configured": True}
    tokens = token_store.load()
    return {
        "connected": tokens is not None,
        "scopes": tokens.scope if tokens else None,
        "configured": bool(settings.fortnox_client_id and settings.fortnox_client_secret),
    }


@router.post("/logout")
async def logout():
    token_store.clear()
    return {"connected": False}
