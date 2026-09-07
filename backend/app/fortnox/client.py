"""Thin async client for the Fortnox REST API (v3).

Handles token refresh transparently; raises NotConnectedError when the app
has not completed the OAuth flow yet.
"""

import asyncio
import time

import httpx

from .. import token_store
from ..config import settings
from . import auth


class NotConnectedError(Exception):
    """No Fortnox tokens stored — user must visit /auth/login first."""


class FortnoxClient:
    # Fortnox allows 25 req / 5 s per token; ~4 req/s stays politely under it
    _MIN_INTERVAL = 0.26

    def __init__(self) -> None:
        self._refresh_lock = asyncio.Lock()
        self._rate_lock = asyncio.Lock()
        self._last_request = 0.0

    async def _throttle(self) -> None:
        async with self._rate_lock:
            wait = self._last_request + self._MIN_INTERVAL - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()

    async def _get_access_token(self) -> str:
        tokens = token_store.load()
        if tokens is None:
            raise NotConnectedError
        if not tokens.is_expired:
            return tokens.access_token
        async with self._refresh_lock:
            # Re-read: another request may have refreshed while we waited
            tokens = token_store.load()
            if tokens is None:
                raise NotConnectedError
            if tokens.is_expired:
                tokens = await auth.refresh(tokens.refresh_token)
            return tokens.access_token

    async def _raw_get(self, path: str, params: dict | None, accept: str) -> httpx.Response:
        token = await self._get_access_token()
        await self._throttle()
        async with httpx.AsyncClient(base_url=settings.fortnox_api_base) as client:
            resp = await client.get(
                path,
                params={k: v for k, v in (params or {}).items() if v is not None},
                headers={"Authorization": f"Bearer {token}", "Accept": accept},
                timeout=60,
            )
        resp.raise_for_status()
        return resp

    async def get(self, path: str, params: dict | None = None) -> dict:
        resp = await self._raw_get(path, params, "application/json")
        return resp.json()

    async def get_bytes(self, path: str, params: dict | None = None) -> bytes:
        # Fortnox's file endpoints (e.g. /sie) reject other Accept values with
        # 400 "Invalid response type" — application/json returns the raw file.
        resp = await self._raw_get(path, params, "application/json")
        return resp.content

    # ── Convenience wrappers ──────────────────────────────────

    async def company_information(self) -> dict:
        data = await self.get("/companyinformation")
        return data["CompanyInformation"]

    async def invoices(
        self,
        filter: str | None = None,
        fromdate: str | None = None,
        todate: str | None = None,
        page: int = 1,
        limit: int = 100,
        sortby: str = "documentnumber",
        sortorder: str = "descending",
    ) -> dict:
        return await self.get(
            "/invoices",
            {
                "filter": filter,
                "fromdate": fromdate,
                "todate": todate,
                "page": page,
                "limit": limit,
                "sortby": sortby,
                "sortorder": sortorder,
            },
        )

    async def invoices_all(self, **params) -> list[dict]:
        """Fetch every page for the given filters (capped to stay polite)."""
        results: list[dict] = []
        page = 1
        while page <= 20:  # 20 × 500 rows — raise if you ever need more
            data = await self.invoices(page=page, limit=500, **params)
            results.extend(data.get("Invoices", []))
            meta = data.get("MetaInformation", {})
            if page >= meta.get("@TotalPages", 1):
                break
            page += 1
        return results

    async def invoice(self, document_number: str) -> dict:
        data = await self.get(f"/invoices/{document_number}")
        return data["Invoice"]

    async def supplier_invoices(self, **params) -> dict:
        return await self.get("/supplierinvoices", params)

    async def accounts(self, financialyear: int | None = None) -> dict:
        return await self.get("/accounts", {"financialyear": financialyear})

    async def vouchers(self, **params) -> dict:
        return await self.get("/vouchers", params)

    async def financial_years(self) -> dict:
        return await self.get("/financialyears")

    # ── Fixed-asset register (Anläggningsregister; `assets` scope) ──
    # Requires the company to hold the Anläggningsregister license — a
    # missing scope returns 400 ("Har inte behörighet för scope"), a missing
    # license 403. Sync treats both as "module unavailable" and skips.

    async def asset_types(self) -> dict:
        return await self.get("/assets/types/")

    async def assets(self, **params) -> dict:
        return await self.get("/assets/", params)

    async def asset(self, number: str) -> dict:
        # Note: the single-asset response nests the object under the *plural*
        # key "Assets" (Fortnox quirk), unlike the list which is also "Assets".
        data = await self.get(f"/assets/{number}")
        return data["Assets"]


fortnox = FortnoxClient()
