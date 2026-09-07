"""Fortnox OAuth2 authorization-code flow."""

import base64
import time
from urllib.parse import urlencode

import httpx

from .. import token_store
from ..config import settings


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.fortnox_client_id,
        "redirect_uri": settings.fortnox_redirect_uri,
        "scope": settings.fortnox_scopes,
        "state": state,
        "access_type": "offline",
        "response_type": "code",
    }
    return f"{settings.fortnox_auth_base}/auth?{urlencode(params)}"


def _basic_auth_header() -> str:
    creds = f"{settings.fortnox_client_id}:{settings.fortnox_client_secret}"
    return "Basic " + base64.b64encode(creds.encode()).decode()


async def _token_request(form: dict) -> token_store.Tokens:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.fortnox_auth_base}/token",
            data=form,
            headers={
                "Authorization": _basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    resp.raise_for_status()
    payload = resp.json()
    tokens = token_store.Tokens(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token", ""),
        expires_at=time.time() + payload.get("expires_in", 3600),
        scope=payload.get("scope", ""),
    )
    token_store.save(tokens)
    return tokens


async def exchange_code(code: str) -> token_store.Tokens:
    return await _token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.fortnox_redirect_uri,
        }
    )


async def refresh(refresh_token: str) -> token_store.Tokens:
    return await _token_request(
        {"grant_type": "refresh_token", "refresh_token": refresh_token}
    )
