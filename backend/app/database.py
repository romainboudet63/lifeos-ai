from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

if settings.database_url.startswith("sqlite"):
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
else:
    # Les Postgres "serverless" (Neon...) ferment les connexions inactives : on vérifie
    # chaque connexion avant de s'en servir et on les renouvelle régulièrement.
    engine_kwargs = {"pool_pre_ping": True, "pool_recycle": 300}

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
