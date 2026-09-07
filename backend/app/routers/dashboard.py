from fastapi import APIRouter

from .. import analytics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def summary(year: int | None = None):
    return analytics.dashboard_summary(year)
