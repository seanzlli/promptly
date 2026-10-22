"""Promptly backend entrypoint.

Run with ``cd backend && uvicorn main:app --reload`` (or from the repo
root with ``uvicorn backend.main:app --reload`` — the paths below make
the flat module imports work from either location).

Each feature lives in its own module that exports an ``APIRouter``. When the
frontend has been built (``npm run build``), this server also serves it, so
one process runs the whole app (see the Dockerfile).
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"
for _p in (BACKEND_DIR, BACKEND_DIR.parent):  # flat imports + root `pdf` module
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

import demo
import helper
import limits
from challenges import router as challenges_router
from config import DEMO, VISITOR_IP_HEADER
from expertise import router as expertise_router
from lecture import router as lecture_router
from peer_review import router as peer_review_router
from progress import router as progress_router

app = FastAPI(
    title="Promptly",
    description=(
        "Upload your lecture slides, test yourself on what the lecture builds on, "
        "practise prompting with reverse-prompt challenges, build your prompt "
        "expertise, and help other students as a Peer Reviewer."
    ),
    version="0.1.0",
)

app.include_router(lecture_router)
app.include_router(progress_router)
app.include_router(challenges_router)
app.include_router(expertise_router)
app.include_router(peer_review_router)

if DEMO:
    demo.seed()

# Browser protections on every response. The policy allows the frontend's own files and the
# Inter font from Google Fonts. The API docs pages load their viewer from a CDN, so they go
# without it.
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; img-src 'self' data:; object-src 'none'; "
    "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)
API_DOCS_PAGES = {app.docs_url, app.redoc_url, app.swagger_ui_oauth2_redirect_url}


@app.middleware("http")
async def remember_visitor(request: Request, call_next):
    """Charge the AI calls this request makes to the visitor's IP address (see limits.py)."""
    ip = request.headers.get(VISITOR_IP_HEADER) if VISITOR_IP_HEADER else None
    token = limits.visitor.set(ip or (request.client.host if request.client else "unknown"))
    try:
        return await call_next(request)
    finally:
        limits.visitor.reset(token)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    if request.url.path not in API_DOCS_PAGES:
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    return response


@app.exception_handler(limits.TooManyCalls)
def too_many_calls(request: Request, exc: limits.TooManyCalls) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": str(exc)})


@app.exception_handler(helper.LLMBusy)
def llm_busy(request: Request, exc: helper.LLMBusy) -> JSONResponse:
    """The AI provider's rate limit or capacity, not a bug: tell the student to wait."""
    return JSONResponse(
        status_code=503,
        content={"detail": "The AI is busy right now. Wait a minute and try again."},
    )


@app.exception_handler(helper.LLMError)
def llm_error(request: Request, exc: helper.LLMError) -> JSONResponse:
    """The LLM API failed or answered with unusable output: a bad gateway, not our bug."""
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


if FRONTEND_DIST.is_dir():

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        """The built frontend. Every page is index.html: the app picks the page from the URL."""
        if path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        file = (FRONTEND_DIST / path).resolve()
        if path and file.is_file() and file.is_relative_to(FRONTEND_DIST):
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")