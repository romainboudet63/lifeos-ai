from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.integrations import strava as strava_client

router = APIRouter(prefix="/strava", tags=["strava"])


@router.get("/status", response_model=schemas.ConnectionStatus)
def strava_status(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    conn = (
        db.query(models.OAuthConnection)
        .filter(models.OAuthConnection.user_id == user.id, models.OAuthConnection.provider == "strava")
        .first()
    )
    return schemas.ConnectionStatus(connected=conn is not None, provider="strava" if conn else None)


@router.get("/auth-url")
def strava_auth_url(user: models.User = Depends(auth.get_current_user)):
    if not settings_configured():
        raise HTTPException(
            status_code=503,
            detail="Strava non configuré : renseigne STRAVA_CLIENT_ID et STRAVA_CLIENT_SECRET dans backend/.env",
        )
    return {"auth_url": strava_client.build_auth_url(state=user.id)}


@router.get("/callback")
async def strava_callback(code: str, state: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == state).first()
    if not user:
        raise HTTPException(status_code=400, detail="Utilisateur introuvable pour ce state")

    tokens = await strava_client.exchange_code_for_tokens(code)
    expires_at = datetime.utcfromtimestamp(tokens["expires_at"]) if "expires_at" in tokens else (
        datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 21600))
    )

    existing = (
        db.query(models.OAuthConnection)
        .filter(models.OAuthConnection.user_id == user.id, models.OAuthConnection.provider == "strava")
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
            provider="strava",
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_at=expires_at,
        ))
    db.commit()

    return RedirectResponse(url="/strava/connected")


@router.get("/connected")
def strava_connected_page():
    return {"message": "Strava connecté avec succès. Tu peux retourner dans l'app."}


async def _get_valid_access_token(db: Session, user: models.User) -> str:
    conn = (
        db.query(models.OAuthConnection)
        .filter(models.OAuthConnection.user_id == user.id, models.OAuthConnection.provider == "strava")
        .first()
    )
    if not conn:
        raise HTTPException(status_code=400, detail="Strava non connecté")

    if strava_client.is_token_expired(conn.expires_at):
        if not conn.refresh_token:
            raise HTTPException(status_code=401, detail="Session Strava expirée, reconnecte ton compte")
        tokens = await strava_client.refresh_access_token(conn.refresh_token)
        conn.access_token = tokens["access_token"]
        conn.expires_at = (
            datetime.utcfromtimestamp(tokens["expires_at"]) if "expires_at" in tokens
            else datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 21600))
        )
        db.commit()

    return conn.access_token


@router.post("/sync", response_model=List[schemas.WorkoutOut])
async def sync_strava(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    access_token = await _get_valid_access_token(db, user)
    activities = await strava_client.list_activities(access_token)

    synced = []
    for activity in activities:
        mapped = strava_client.map_strava_activity(activity)
        existing = (
            db.query(models.Workout)
            .filter(models.Workout.external_id == mapped["external_id"], models.Workout.user_id == user.id)
            .first()
        )
        if existing:
            for key, value in mapped.items():
                setattr(existing, key, value)
        else:
            existing = models.Workout(user_id=user.id, **mapped)
            db.add(existing)
        synced.append(existing)

    db.commit()
    for w in synced:
        db.refresh(w)
    return synced


@router.get("/workouts", response_model=List[schemas.WorkoutOut])
def list_workouts(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return (
        db.query(models.Workout)
        .filter(models.Workout.user_id == user.id)
        .order_by(models.Workout.performed_at.desc())
        .all()
    )


def settings_configured() -> bool:
    from app.config import settings
    return bool(settings.strava_client_id and settings.strava_client_secret)
