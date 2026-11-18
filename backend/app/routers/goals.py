from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=List[schemas.GoalOut])
def list_goals(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Goal).filter(models.Goal.user_id == user.id).all()


@router.post("", response_model=schemas.GoalOut, status_code=201)
def create_goal(
    payload: schemas.GoalCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    goal = models.Goal(user_id=user.id, **payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.patch("/{goal_id}/progress", response_model=schemas.GoalOut)
def update_progress(
    goal_id: str,
    progress: float,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.user_id == user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Objectif introuvable")

    goal.progress = max(0.0, min(1.0, progress))
    if goal.progress >= 1.0:
        goal.status = "done"
    db.commit()
    db.refresh(goal)
    return goal
