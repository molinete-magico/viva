import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.public import api_router
from app.config import DATA_DIR, settings
from app.database.migrate import run_migrations
from app.database.seed import run_seed
from app.domain.errors import ServiceError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("viva")


def _run_startup_catchup() -> None:
    try:
        from app.database.session import engine
        from app.services.simulation_service import run_catchup
        from sqlmodel import Session

        with Session(engine) as session:
            report = run_catchup(session, with_social=False)
        if report and "skipped" not in report:
            logger.info(
                "startup catch-up: %s min -> %s",
                report.get("elapsed_minutes"),
                report.get("summary", ""),
            )
    except Exception:  # noqa: BLE001
        logger.exception("startup catch-up failed (the world keeps going anyway)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_migrate:
        run_migrations()
        run_seed()
    logger.info("Viva API started (llm=%s)", "groq" if settings.groq_api_key else "mock")
    _run_startup_catchup()
    yield


app = FastAPI(title="Viva API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    message = first.get("msg", "Dados inválidos.")
    detail = f"{field}: {message}" if field else message
    return JSONResponse(status_code=422, content={"detail": detail})


app.include_router(api_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


photos_dir = DATA_DIR / "photos"
photos_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/photos", StaticFiles(directory=str(photos_dir)), name="photos")
