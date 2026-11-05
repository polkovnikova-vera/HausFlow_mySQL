from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.reports import router as reports_router
from app.api.invoices import router as invoices_router
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.application_name,
    version=settings.version,
    description=(
        "HausFlow REST API zur Verwaltung von Gebäuden, "
        "Schadensmeldungen und Rechnungen."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=[
        "Accept",
        "Content-Type",
        "Authorization",
    ],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(invoices_router, prefix="/api/v1")