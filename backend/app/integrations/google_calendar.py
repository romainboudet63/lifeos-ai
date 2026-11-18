"""
Intégration Google Calendar.

IMPORTANT — ce que ce module ne peut PAS garantir depuis ce
développement : je n'ai aucun accès réseau vers accounts.google.com ou
googleapis.com dans mon environnement de développement (sandbox
restreint), donc je n'ai pas pu tester un vrai échange OAuth de bout
en bout. Le code suit fidèlement la documentation officielle du
protocole OAuth2 "authorization code" de Google et de l'API Calendar
v3, mais SEUL UN TEST RÉEL sur ta machine (avec de vrais identifiants
Google Cloud) peut confirmer que ça fonctionne. Voir README.md pour la
procédure de création des identifiants et le premier test.

Choix : appels HTTP directs via httpx plutôt que la librairie officielle
google-api-python-client, pour rester léger et lisible. Si tu préfères
la librairie officielle (plus robuste sur la gestion des cas limites),
c'est un remplacement direct de ce fichier.
"""
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"

SCOPES = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/calendar.readonly"


def build_auth_url(state: str) -> str:
    """Construit l'URL de consentement Google que l'utilisateur doit ouvrir
    dans son navigateur pour autoriser l'accès à son calendrier."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",   # nécessaire pour obtenir un refresh_token
        "prompt": "consent",        # force le renvoi d'un refresh_token à chaque fois (utile en dev)
        "state": state,             # on y met l'id utilisateur pour retrouver qui autorise
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """Échange le code d'autorisation reçu sur /callback contre un
    access_token + refresh_token."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Utilise le refresh_token pour obtenir un nouvel access_token une
    fois que l'ancien a expiré (durée de vie ~1h côté Google)."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        return response.json()


async def list_events(access_token: str, time_min: datetime, time_max: datetime) -> list[dict]:
    """Récupère les événements du calendrier principal de l'utilisateur
    entre deux dates."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "timeMin": time_min.isoformat() + "Z",
                "timeMax": time_max.isoformat() + "Z",
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": 250,
            },
        )
        response.raise_for_status()
        return response.json().get("items", [])


async def create_event(
    access_token: str, title: str, start_at: datetime, end_at: datetime, location: Optional[str] = None
) -> dict:
    """Crée un événement sur le calendrier Google principal de l'utilisateur."""
    body = {
        "summary": title,
        "start": {"dateTime": start_at.isoformat()},
        "end": {"dateTime": end_at.isoformat()},
    }
    if location:
        body["location"] = location

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )
        response.raise_for_status()
        return response.json()


def parse_google_event_times(event: dict) -> tuple[Optional[datetime], Optional[datetime]]:
    """Google renvoie soit dateTime (événement horodaté), soit date (jour
    entier, ex: anniversaires) — on ne gère que le premier cas ici."""
    start = event.get("start", {}).get("dateTime")
    end = event.get("end", {}).get("dateTime")
    if not start or not end:
        return None, None
    return datetime.fromisoformat(start), datetime.fromisoformat(end)


def is_token_expired(expires_at: Optional[datetime]) -> bool:
    if expires_at is None:
        return True
    # marge de 2 minutes pour éviter d'utiliser un token expirant pendant l'appel
    return datetime.utcnow() >= expires_at - timedelta(minutes=2)
