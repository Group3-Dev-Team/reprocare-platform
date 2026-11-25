"""ReproCare API: application factory, shared middleware and router registration.

Run locally from backend/:  uvicorn app.main:app --reload
Feature routers live in app/routes/<feature>_routes.py, expose `router`, and are added to ROUTERS below.
Every router is mounted under /api.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.session import require_shared_database
from app.routes import (
    facility_routes,
    practitioner_routes,
    program_routes,
    content_routes,
    reference_routes,
    import_routes,
    places_routes,
    external_feedback_routes,
    facebook_moderation_routes,
    facebook_demo_routes,
    facebook_collection_routes,
    appointment_routes,
    review_routes,
    facility_staff_routes,
    media_routes,
    auth_routes,
    password_recovery_routes,
    account_routes,
    admin_routes,
)

ROUTERS: list = [
    facility_routes,
    practitioner_routes,
    program_routes,
    content_routes,
    reference_routes,
    import_routes,
    places_routes,
    external_feedback_routes,
    facebook_moderation_routes,
    facebook_demo_routes,
    facebook_collection_routes,
    appointment_routes,
    review_routes,
    facility_staff_routes,
    media_routes,
    auth_routes,
    password_recovery_routes,
    account_routes,
    admin_routes,
]

@asynccontextmanager
async def lifespan(_app):
    require_shared_database()  # no-op unless REPROCARE_REQUIRE_SHARED_DATABASE is set
    yield


app = FastAPI(
    lifespan=lifespan,
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