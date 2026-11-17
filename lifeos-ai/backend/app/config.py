from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings

DEFAULT_JWT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    # En dev local -> SQLite. En prod, mettre une URL Postgres, ex:
    # postgresql://user:password@localhost:5432/lifeos
    database_url: str = "sqlite:///./lifeos.db"

    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 jours

    # Qui peut créer un compte :
    #   "open"       n'importe qui (développement local)
    #   "first_user" uniquement tant qu'aucun compte n'existe (usage personnel : se ferme tout seul)
    #   "closed"     plus aucune inscription
    registration_mode: str = "open"

    # Origines autorisées pour CORS, séparées par des virgules. "*" = toutes (développement).
    # Inutile quand l'app web est servie par le backend lui-même (même origine).
    cors_origins: str = "*"

    # Dossier de l'app web exportée (npx expo export --platform web). Ignoré s'il n'existe pas.
    web_dir: str = "web"

    anthropic_api_key: str = ""
    # Vide = modèle par défaut défini dans app/ai/engine.py (DEFAULT_MODEL).
    anthropic_model: str = ""

    # Fuseau utilisé pour les rappels quand le client n'en précise pas (?tz=...).
    default_timezone: str = "Europe/Paris"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/calendar/google/callback"

    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/strava/callback"

    class Config:
        env_file = ".env"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        # Neon/Heroku fournissent "postgres://" ou "postgresql://" : on fixe le pilote (psycopg2,
        # celui de requirements.txt) pour ne pas dépendre du défaut de la version de SQLAlchemy.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg2://" + value[len(prefix):]
        return value

    @field_validator("registration_mode")
    @classmethod
    def _check_registration_mode(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"open", "first_user", "closed"}:
            raise ValueError('REGISTRATION_MODE doit valoir "open", "first_user" ou "closed"')
        return value

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or ["*"]

    @property
    def is_production_database(self) -> bool:
        return not self.database_url.startswith("sqlite")


settings = Settings()


def check_production_settings(current: Settings = settings) -> None:
    """Refuse de démarrer en production avec un secret JWT faible : n'importe qui pourrait forger un jeton."""
    if not current.is_production_database:
        return
    if current.jwt_secret.startswith("change-me") or len(current.jwt_secret) < 32:
        raise RuntimeError(
            "JWT_SECRET doit être défini (32 caractères au moins) quand la base n'est pas SQLite. "
            "Génère-en un avec : python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
