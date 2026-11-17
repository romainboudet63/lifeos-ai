"""
Intégration Strava.

Même avertissement que pour google_calendar.py : je n'ai pas d'accès
réseau vers www.strava.com dans mon environnement de développement, donc
le vrai flux OAuth n'a pas pu être testé de bout en bout ici. Le code
suit la documentation officielle de l'API Strava (OAuth2 + endpoint
/athlete/activities), mais seul un test réel sur ta machine peut le
confirmer. Ce qui EST testé : `map_strava_activity`, la fonction pure
qui convertit une activité Strava en enregistrement Workout — voir
test_strava_mapping.py.
"""
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API = "https://www.strava.com/api/v3"

SCOPES = "activity:read_all"

# Strava utilise ses propres libellés de sport ; on les ramène aux
# catégories utilisées ailleurs dans l'app (habits, notifications...).
SPORT_TYPE_MAP = {
    "Run": "course",
    "TrailRun": "course",
    "Ride": "cyclisme",
    "VirtualRide": "cyclisme",
    "Swim": "natation",
    "WeightTraining": "musculation",
    "Yoga": "yoga",
    "Hike": "randonnee",
    "Walk": "marche",
}


def build_auth_url(state: str) -> str:
    params = {
        "client_id": settings.strava_client_id,
        "redirect_uri": settings.strava_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "approval_prompt": "auto",
        "state": state,
    }
    return f"{STRAVA_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        return response.json()


async def list_activities(access_token: str, per_page: int = 30) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{STRAVA_API}/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"per_page": per_page},
        )
        response.raise_for_status()
        return response.json()


def map_strava_activity(activity: dict) -> dict:
    """Convertit une activité Strava (format API v3) en champs prêts à
    stocker dans le modèle Workout. Fonction pure — pas d'accès réseau —
    donc testable indépendamment (voir test_strava_mapping.py)."""
    sport_type = activity.get("sport_type") or activity.get("type", "")
    moving_time_seconds = activity.get("moving_time", 0)
    performed_at = None
    if activity.get("start_date"):
        performed_at = datetime.fromisoformat(activity["start_date"].replace("Z", "+00:00")).replace(tzinfo=None)

    return {
        "external_id": str(activity.get("id")),
        "type": SPORT_TYPE_MAP.get(sport_type, sport_type.lower() if sport_type else "autre"),
        "duration_min": round(moving_time_seconds / 60) if moving_time_seconds else None,
        "calories": activity.get("calories"),
        "performed_at": performed_at,
        "source": "strava",
        "raw_data": {"name": activity.get("name"), "distance_m": activity.get("distance")},
    }


def is_token_expired(expires_at: Optional[datetime]) -> bool:
    if expires_at is None:
        return True
    from datetime import timedelta
    return datetime.utcnow() >= expires_at - timedelta(minutes=2)
