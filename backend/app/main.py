from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import check_production_settings, settings
from app.database import Base, engine
from app.routers import auth as auth_router
from app.routers import tasks, habits, goals, ai_chat, calendar, strava, nutrition, finance, workout_programs, nudges
from app.webapp import mount_web_app

check_production_settings()  # refuse un secret JWT faible dès que la base n'est pas SQLite

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LifeOS AI API",
    description="Backend de l'assistant personnel de vie LifeOS AI",
    version="0.1.0",
)

# CORS_ORIGINS="*" par défaut (dev). Quand l'app web est servie par ce même backend
# (cas de l'hébergement), le navigateur reste sur la même origine : rien à ouvrir.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(tasks.router)
app.include_router(habits.router)
app.include_router(goals.router)
app.include_router(ai_chat.router)
app.include_router(calendar.router)
app.include_router(strava.router)
app.include_router(nutrition.router)
app.include_router(finance.router)
app.include_router(workout_programs.router)
app.include_router(nudges.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


# En dernier : le montage à "/" capte tout ce qui n'a pas de route d'API.
mount_web_app(app, settings.web_dir)
