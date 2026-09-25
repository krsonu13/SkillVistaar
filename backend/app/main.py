from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router, register_api_router
from app.core.config import settings
from app.db.init_db import check_database_connection
from app.services.otp_delivery_service import validate_smtp_configuration, validate_sms_configuration


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.PROJECT_NAME}...")
    print(f"Environment: {settings.ENVIRONMENT}")

    # ── Email (SMTP) Startup Validation ──────────────────────────
    smtp_info = validate_smtp_configuration()
    if smtp_info["ready"]:
        print(f"  Email: CONFIGURED — {smtp_info['message']}")
    else:
        print(f"  Email: NOT CONFIGURED — {smtp_info['message']}")
        print("    To enable REAL Gmail OTP delivery, configure backend/.env:")
        print("      SMTP_HOST=smtp.gmail.com")
        print("      SMTP_PORT=587")
        print("      SMTP_USERNAME=<your_email>@gmail.com")
        print("      SMTP_PASSWORD=<16_char_google_app_password>")
        print("      SMTP_FROM_EMAIL=<your_email>@gmail.com")

    # ── SMS Startup Validation ───────────────────────────────────
    sms_info = validate_sms_configuration()
    if sms_info["ready"]:
        print(f"  SMS:   CONFIGURED — {sms_info['message']}")
    else:
        print(f"  SMS:   NOT CONFIGURED — {sms_info['message']}")
        print("    For free-tier deployment, configure backend/.env:")
        print("      SMS_PROVIDER=sandbox")
        print("      ALLOW_DEMO_SMS=true")

    yield

    print(f"Stopping {settings.PROJECT_NAME}...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "SkillVistaar — Labour-market intelligence, "
        "verified skills, recruitment, education alignment "
        "and government analytics platform."
    ),
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

cors_origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API V1 ROUTES
# ---------------------------------------------------------------------------

register_api_router(
    app,
    api_router,
    prefix=settings.API_V1_PREFIX,
)


# ---------------------------------------------------------------------------
# ROOT & PROBES
# ---------------------------------------------------------------------------

@app.get("/", tags=["General"])
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "message": "Welcome to SkillVistaar API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/live", tags=["Health"])
async def liveness():
    """
    Fast liveness probe: returns 200 OK as long as the local server process is alive.
    """
    return {"status": "alive", "project": settings.PROJECT_NAME}


@app.get("/health/ready", tags=["Health"])
async def readiness(res: Response):
    """
    Readiness probe: validates database connectivity before routing traffic.
    Returns 503 if the database is unreachable.
    """
    database_healthy = await check_database_connection()
    if not database_healthy:
        res.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "database": "disconnected"}
    return {"status": "ready", "database": "connected"}


@app.get("/health", tags=["Health"])
async def health(res: Response):
    """
    Full diagnostic health check: checks Database, SMTP Email, and SMS status.
    """
    database_healthy = await check_database_connection()
    smtp_status = validate_smtp_configuration()
    sms_status = validate_sms_configuration()

    overall_healthy = database_healthy
    if not overall_healthy:
        res.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": (
            "connected"
            if database_healthy
            else "disconnected"
        ),
        "email_service": {
            "ready": smtp_status["ready"],
            "host": smtp_status["host"],
            "is_gmail": smtp_status["is_gmail"],
            "status": "configured" if smtp_status["ready"] else "unconfigured",
            "message": smtp_status["message"],
        },
        "sms_service": {
            "ready": sms_status["ready"],
            "provider": sms_status["provider"],
            "is_sandbox": sms_status.get("is_sandbox", False),
            "status": "configured" if sms_status["ready"] else "unconfigured",
            "message": sms_status["message"],
        },
    }
