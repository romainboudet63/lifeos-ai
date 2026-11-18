from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.integrations import google_calendar as gcal
from app.calendar_utils import TimeRange, find_conflicts

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/google/status", response_model=schemas.ConnectionStatus)
def google_status(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    conn = (
        db.query(models.OAuthConnection)
        .filter(models.OAuthConnection.user_id == user.id, models.OAuthConnection.provider == "google_calendar")
        .first()
    )
    return schemas.ConnectionStatus(connected=conn is not None, provider="google_calendar" if conn else None)


@router.get("/google/auth-url")
def google_auth_url(user: models.User = Depends(auth.get_current_user)):
    """Renvoie l'URL à ouvrir dans un navigateur pour connecter Google
    Calendar. On met l'id utilisateur dans `state` pour le retrouver au
    retour sur /callback (Google nous le renvoie tel quel)."""
    if not settings_configured():
        raise HTTPException(
            status_code=503,
            detail="Google Calendar non configuré : renseigne GOOGLE_CLIENT_ID et GOOGLE_CLIENT_SECRET dans backend/.env",
        )
    return {"auth_url": gcal.build_auth_url(state=user.id)}


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Google redirige ici après consentement de l'utilisateur. `state`
    contient l'id utilisateur qu'on avait passé dans /auth-url."""
    user = db.query(models.User).filter(models.User.id == state).first()
    if not user:
        raise HTTPException(status_code=400, detail="Utilisateur introuvable pour ce state")

    tokens = await gcal.exchange_code_for_tokens(code)
    expires_at = datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))

    existing = (
        db.query(models.OAuthConnection)
        .filter(models.OAuthConnection.user_id == user.id, models.OAuthConnection.provider == "google_calendar")
        .first()
    )
    if existing:
        existing.access_token = tokens["access_token"]
        if tokens.get("refresh_token"):
            existing.refresh_token = tokens["refresh_token"]
        existing.expires_at = expires_at
    else:
        db.add(models.OAuthConnection(
            user_id=user.id,
            provider="google_calendar",
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_at=expires_at,
        ))
    db.commit()

    # En dev, on renvoie un message simple plutôt qu'une vraie redirection
    # vers l'app mobile (deep link à configurer en Phase suivante).
    return RedirectResponse(url="/calendar/google/connected")


@router.get("/google/connected")
def google_connected_page():
    return {"message": "Google Calendar connecté avec succès. Tu peux retourner dans l'app."}


async def _get_valid_access_token(db: Session, user: models.User) -> str:
    conn = (
        db.query(models.OAuthConnection)
        .filter(models.OAuthConnection.user_id == user.id, models.OAuthConnection.provider == "google_calendar")
        .first()
    )
    if not conn:
        raise HTTPException(status_code=400, detail="Google Calendar non connecté")

    if gcal.is_token_expired(conn.expires_at):
        if not conn.refresh_token:
            raise HTTPException(status_code=401, detail="Session Google expirée, reconnecte ton compte")
        tokens = await gcal.refresh_access_token(conn.refresh_token)
        conn.access_token = tokens["access_token"]
        conn.expires_at = datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))
        db.commit()

    return conn.access_token


@router.post("/sync", response_model=List[schemas.CalendarEventOut])
async def sync_google_calendar(
    days_ahead: int = 14,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Récupère les événements Google Calendar des `days_ahead` prochains
    jours et les copie dans la base locale (upsert par external_id)."""
    access_token = await _get_valid_access_token(db, user)

    time_min = datetime.utcnow()
    time_max = time_min + timedelta(days=days_ahead)
    google_events = await gcal.list_events(access_token, time_min, time_max)

    synced = []
    for ev in google_events:
        start, end = gcal.parse_google_event_times(ev)
        if start is None:
            continue  # événement "jour entier" sans horaire, ignoré dans ce prototype

        existing = (
            db.query(models.CalendarEvent)
            .filter(models.CalendarEvent.external_id == ev["id"], models.CalendarEvent.user_id == user.id)
            .first()
        )
        if existing:
            existing.title = ev.get("summary", "(sans titre)")
            existing.start_at = start.replace(tzinfo=None)
            existing.end_at = end.replace(tzinfo=None)
            existing.location = ev.get("location")
        else:
            existing = models.CalendarEvent(
                user_id=user.id,
                external_provider="google",
                external_id=ev["id"],
                title=ev.get("summary", "(sans titre)"),
                start_at=start.replace(tzinfo=None),
                end_at=end.replace(tzinfo=None),
                location=ev.get("location"),
            )
            db.add(existing)
        synced.append(existing)

    db.commit()
    for e in synced:
        db.refresh(e)
    return synced


@router.get("/events", response_model=List[schemas.CalendarEventOut])
def list_events(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return (
        db.query(models.CalendarEvent)
        .filter(models.CalendarEvent.user_id == user.id)
        .order_by(models.CalendarEvent.start_at)
        .all()
    )


@router.post("/events", response_model=schemas.CalendarEventOut, status_code=201)
async def create_event(
    payload: schemas.CalendarEventCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Crée un événement local, détecte les conflits avec l'existant, et
    le pousse aussi sur Google Calendar si demandé et connecté."""
    existing_events = (
        db.query(models.CalendarEvent).filter(models.CalendarEvent.user_id == user.id).all()
    )
    candidate = TimeRange(start=payload.start_at, end=payload.end_at, label=payload.title)
    existing_ranges = [TimeRange(start=e.start_at, end=e.end_at, label=e.title) for e in existing_events]
    conflicts = find_conflicts(candidate, existing_ranges)
    if conflicts:
        conflict_titles = ", ".join(c.label for c in conflicts)
        raise HTTPException(status_code=409, detail=f"Conflit d'agenda avec : {conflict_titles}")

    external_id = None
    if payload.push_to_google:
        conn = (
            db.query(models.OAuthConnection)
            .filter(models.OAuthConnection.user_id == user.id, models.OAuthConnection.provider == "google_calendar")
            .first()
        )
        if conn:
            access_token = await _get_valid_access_token(db, user)
            google_event = await gcal.create_event(
                access_token, payload.title, payload.start_at, payload.end_at, payload.location
            )
            external_id = google_event.get("id")

    event = models.CalendarEvent(
        user_id=user.id,
        external_provider="google" if external_id else None,
        external_id=external_id,
        title=payload.title,
        start_at=payload.start_at,
        end_at=payload.end_at,
        location=payload.location,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def settings_configured() -> bool:
    from app.config import settings
    return bool(settings.google_client_id and settings.google_client_secret)
