from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from app.routes.establishments import router as establishments_router
from app.routes.admin import router as admin_router
from app.routes.follow import router as follow_router
from app.routes.auth import router as auth_router
from app.routes.subscriptions import router as subscriptions_router
from app.routes.payments import router as payments_router
from app.routes.languages import router as languages_router
from app.services.follow_expiration import lock_expired_follows
from app.services.subscription_expiration import expire_subscriptions


app = FastAPI(
    title="Multi Resto Hôtel",
    version="1.0.0"
)


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app.include_router(establishments_router)
app.include_router(admin_router)
app.include_router(follow_router)
app.include_router(auth_router)
app.include_router(subscriptions_router)
app.include_router(payments_router)
app.include_router(languages_router)


scheduler = BackgroundScheduler()


@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(
        lock_expired_follows,
        "interval",
        minutes=1,
        id="lock_expired_follows",
        replace_existing=True
    )
    scheduler.add_job(
        expire_subscriptions,
        "interval",
        minutes=1,
        id="expire_subscriptions",
        replace_existing=True
    )
    scheduler.start()


@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown(wait=False)


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "public.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "Multi Resto Hôtel backend"
    }


# Frontend web MRH
app.mount(
    "/",
    StaticFiles(directory=str(FRONTEND_DIR), html=True),
    name="frontend"
)
