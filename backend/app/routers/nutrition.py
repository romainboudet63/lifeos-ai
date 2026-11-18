from datetime import date as date_type, datetime, time
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.ai.nutrition_estimator import estimate_nutrition

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.post("/estimate", response_model=schemas.NutritionEstimateResponse)
async def estimate(
    payload: schemas.NutritionEstimateRequest,
    user: models.User = Depends(auth.get_current_user),
):
    """Estime calories/macros à partir d'une description texte. Utilise
    l'IA si une clé Anthropic est configurée, sinon une heuristique
    locale basée sur une petite base d'aliments courants. Ne persiste
    rien — l'utilisateur confirme ensuite via POST /nutrition avec les
    valeurs (éventuellement corrigées)."""
    result = await estimate_nutrition(payload.description)
    return schemas.NutritionEstimateResponse(**result)


@router.get("", response_model=List[schemas.NutritionLogOut])
def list_logs(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return (
        db.query(models.NutritionLog)
        .filter(models.NutritionLog.user_id == user.id)
        .order_by(models.NutritionLog.logged_at.desc())
        .limit(100)
        .all()
    )


@router.post("", response_model=schemas.NutritionLogOut, status_code=201)
def create_log(
    payload: schemas.NutritionLogCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    log = models.NutritionLog(user_id=user.id, **payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/daily", response_model=schemas.NutritionDailySummary)
def daily_summary(
    for_date: date_type = Query(default_factory=date_type.today),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    day_start = datetime.combine(for_date, time.min)
    day_end = datetime.combine(for_date, time.max)

    entries = (
        db.query(models.NutritionLog)
        .filter(
            models.NutritionLog.user_id == user.id,
            models.NutritionLog.logged_at >= day_start,
            models.NutritionLog.logged_at <= day_end,
        )
        .order_by(models.NutritionLog.logged_at)
        .all()
    )

    return schemas.NutritionDailySummary(
        date=for_date,
        total_calories=sum(e.calories or 0 for e in entries),
        total_protein_g=sum(e.protein_g or 0 for e in entries),
        total_carbs_g=sum(e.carbs_g or 0 for e in entries),
        total_fat_g=sum(e.fat_g or 0 for e in entries),
        entries=entries,
    )
