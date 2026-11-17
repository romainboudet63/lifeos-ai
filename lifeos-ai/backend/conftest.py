import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base

# Script de bout en bout : exige un serveur lancé sur localhost:8000 (python test_nutrition_finance.py).
collect_ignore = ["test_nutrition_finance.py"]


@pytest.fixture
def session_factory():
    """Base SQLite en mémoire, neuve pour chaque test."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


@pytest.fixture
def db(session_factory):
    session = session_factory()
    yield session
    session.close()


def make_user(db, email="romain@example.com"):
    user = models.User(email=email, hashed_password="x", full_name=email.split("@")[0])
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def user(db):
    return make_user(db)


@pytest.fixture
def other_user(db):
    return make_user(db, "autre@example.com")
