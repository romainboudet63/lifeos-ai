from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("", response_model=List[schemas.HabitOut])
def list_habits(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Habit).filter(models.Habit.user_id == user.id).all()


@router.post("", response_model=schemas.HabitOut, status_code=201)
def create_habit(
    payload: schemas.HabitCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    habit = models.Habit(user_id=user.id, **payload.model_dump())
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


@router.post("/{habit_id}/log", response_model=schemas.HabitLogOut, status_code=201)
def log_habit(
    habit_id: str,
    payload: schemas.HabitLogCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id, models.Habit.user_id == user.id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habitude introuvable")

    log_data = payload.model_dump()
    if log_data.get("date") is None:
        log_data.pop("date")
    log = models.HabitLog(habit_id=habit.id, **log_data)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/{habit_id}/logs", response_model=List[schemas.HabitLogOut])
def get_habit_logs(
    habit_id: str, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)
):
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id, models.Habit.user_id == user.id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habitude introuvable")
    return db.query(models.HabitLog).filter(models.HabitLog.habit_id == habit_id).order_by(models.HabitLog.date.desc()).all()
