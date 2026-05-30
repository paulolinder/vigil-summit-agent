from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter
from app.config import settings
from app.api.leads import router as leads_router
from app.api.webhooks import router as webhooks_router
from app.api.events import router as events_router
from app.api.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.scheduler.runner import start_scheduler, scheduler
    from app.scheduler.cleanup import run_all_cleanups

    await start_scheduler()

    scheduler.add_job(
        run_all_cleanups,
        "cron",
        hour=3,
        minute=0,
        id="daily_cleanup",
        replace_existing=True,
    )

    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Vigil Summit Agent API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

app.include_router(leads_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
