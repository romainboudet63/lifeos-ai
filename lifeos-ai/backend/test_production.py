"""Garde-fous de mise en production : inscriptions, secret JWT, URL Postgres, service de l'app web."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import models
from app.config import DEFAULT_JWT_SECRET, Settings, check_production_settings, settings
from app.database import get_db
from app.routers import auth as auth_router
from app.webapp import mount_web_app


# ---------- inscriptions ----------

@pytest.fixture
def register_client(db):
    app = FastAPI()
    app.include_router(auth_router.router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def register(client, email="romain@example.com"):
    return client.post("/auth/register", json={"email": email, "password": "azerty123"})


def test_open_mode_lets_anyone_register(register_client, monkeypatch):
    monkeypatch.setattr(settings, "registration_mode", "open")
    assert register(register_client, "a@example.com").status_code == 201
    assert register(register_client, "b@example.com").status_code == 201


def test_first_user_mode_closes_itself_after_the_first_account(register_client, monkeypatch):
    monkeypatch.setattr(settings, "registration_mode", "first_user")
    assert register(register_client, "moi@example.com").status_code == 201
    r = register(register_client, "intrus@example.com")
    assert r.status_code == 403
    assert "fermées" in r.json()["detail"]


def test_closed_mode_refuses_everyone(register_client, monkeypatch):
    monkeypatch.setattr(settings, "registration_mode", "closed")
    assert register(register_client).status_code == 403


def test_closing_registration_does_not_block_login(register_client, monkeypatch):
    monkeypatch.setattr(settings, "registration_mode", "first_user")
    register(register_client)
    r = register_client.post("/auth/login", data={"username": "romain@example.com", "password": "azerty123"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_invalid_registration_mode_is_rejected_at_startup():
    with pytest.raises(ValueError):
        Settings(registration_mode="ouvert-a-tous")
    assert Settings(registration_mode=" First_User ").registration_mode == "first_user"


# ---------- configuration de production ----------

def test_postgres_scheme_is_normalized():
    expected = "postgresql+psycopg2://u:p@h/db"
    assert Settings(database_url="postgres://u:p@h/db").database_url == expected
    assert Settings(database_url="postgresql://u:p@h/db").database_url == expected
    assert Settings(database_url="postgresql://u:p@h/db?sslmode=require").database_url == expected + "?sslmode=require"
    assert Settings(database_url=expected).database_url == expected  # déjà explicite : inchangé
    assert Settings(database_url="sqlite:///./x.db").database_url == "sqlite:///./x.db"


def test_weak_jwt_secret_is_refused_outside_sqlite():
    prod = "postgresql://u:p@h/db"
    for secret in (DEFAULT_JWT_SECRET, "trop-court", "change-me-with-a-long-random-string"):
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            check_production_settings(Settings(database_url=prod, jwt_secret=secret))
    check_production_settings(Settings(database_url=prod, jwt_secret="x" * 32))  # ne lève pas
    check_production_settings(Settings(database_url="sqlite:///./dev.db"))  # dev local : toléré


def test_cors_origins_parsing():
    assert Settings(cors_origins="*").cors_origin_list == ["*"]
    assert Settings(cors_origins=" https://a.app , https://b.app ,").cors_origin_list == ["https://a.app", "https://b.app"]
    assert Settings(cors_origins="").cors_origin_list == ["*"]


# ---------- service de l'app web ----------

@pytest.fixture
def web_dir(tmp_path):
    (tmp_path / "_expo" / "static" / "js").mkdir(parents=True)
    (tmp_path / "index.html").write_text("<!doctype html><title>LifeOS</title>", encoding="utf8")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf8")
    (tmp_path / "_expo" / "static" / "js" / "entry-abc123.js").write_text("console.log(1)", encoding="utf8")
    return tmp_path


def test_web_app_is_served_after_the_api_and_does_not_shadow_it(web_dir):
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    assert mount_web_app(app, str(web_dir)) is True
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}  # l'API garde la priorité
    home = client.get("/")
    assert home.status_code == 200 and "LifeOS" in home.text
    assert client.get("/introuvable").status_code == 404


def test_web_app_cache_headers(web_dir):
    app = FastAPI()
    mount_web_app(app, str(web_dir))
    client = TestClient(app)
    assert client.get("/").headers["cache-control"] == "no-cache"  # une mise à jour doit être vue
    assert client.get("/manifest.json").headers["cache-control"] == "no-cache"
    hashed = client.get("/_expo/static/js/entry-abc123.js")
    assert hashed.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_missing_web_dir_leaves_the_api_alone(tmp_path):
    app = FastAPI()
    assert mount_web_app(app, str(tmp_path / "absent")) is False
    assert mount_web_app(app, str(tmp_path)) is False  # dossier sans index.html
    assert TestClient(app).get("/").status_code == 404
