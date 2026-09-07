import asyncio

from fastapi import APIRouter

from .. import db, sync
from ..config import settings

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("")
async def start_sync():
    if settings.demo_mode:
        return {"started": False, "demo": True}
    asyncio.create_task(sync.run())
    return {"started": True}


@router.get("/status")
async def sync_status():
    status = dict(sync.state)
    if status["last_sync"] is None:
        with db.session() as conn:
            status["last_sync"] = db.get_meta(conn, "last_sync")
    status["has_data"] = db.has_ledger_data()
    return status
