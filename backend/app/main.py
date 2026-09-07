import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .analytics import NeedsSyncError
from .config import PROJECT_ROOT, settings
from .fortnox.client import NotConnectedError
from .ai import router as ai_router
from .routers import auth, dashboard, reports, sync

app = FastAPI(title="Fortnox Insights API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sync.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(ai_router.router)


@app.exception_handler(NotConnectedError)
async def not_connected_handler(request: Request, exc: NotConnectedError):
    return JSONResponse(
        status_code=401,
        content={"detail": "Not connected to Fortnox. Visit /auth/login to authorize."},
    )


@app.exception_handler(NeedsSyncError)
async def needs_sync_handler(request: Request, exc: NeedsSyncError):
    return JSONResponse(
        status_code=409,
        content={"detail": "No data in the local mirror yet — run a sync.", "needs_sync": True},
    )


@app.exception_handler(httpx.HTTPStatusError)
async def fortnox_error_handler(request: Request, exc: httpx.HTTPStatusError):
    return JSONResponse(
        status_code=502,
        content={
            "detail": "Fortnox API error",
            "status": exc.response.status_code,
            "body": exc.response.text[:2000],
        },
    )


@app.get("/health")
async def health():
    return {"ok": True}


# Single-app production mode: serve the built frontend when frontend/dist
# exists. Dev keeps using the Vite server + proxy; this route is registered
# last so /api, /auth and /health always win.
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

if FRONTEND_DIST.is_dir():

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = (FRONTEND_DIST / full_path).resolve()
        if (
            full_path
            and candidate.is_relative_to(FRONTEND_DIST.resolve())
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
