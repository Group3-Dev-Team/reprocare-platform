"""ReproCare API: application factory, shared middleware and router registration.

Run locally from backend/:  uvicorn app.main:app --reload
Feature routers live in app/routes/<feature>_routes.py, expose `router`, and are added to ROUTERS below.
Every router is mounted under /api.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import import_routes

ROUTERS: list = [import_routes]  # each module must define `router`

app = FastAPI(
    title="ReproCare API",
    description="Reproductive healthcare discovery for Kenya.",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Import-Key"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith(("/api/auth", "/api/me")):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok"}


for module in ROUTERS:
    app.include_router(module.router, prefix="/api")
