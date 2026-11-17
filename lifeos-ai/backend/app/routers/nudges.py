from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app import models, schemas, auth
from app.nudges import HabitInfo, TaskInfo, build_nudges

router = APIRouter(prefix="/nudges", tags=["nudges"])

# Les séries plus longues que cette fenêtre sont tronquées (sans conséquence pour les règles).
HISTORY_DAYS = 400


def _now(zone: ZoneInfo) -> datetime:
    return datetime.now(zone)  # isolé pour pouvoir figer l'heure dans les tests


def _zone(tz: Optional[str]) -> ZoneInfo:
    name = tz or settings.default_timezone
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail=f"Fuseau horaire inconnu : {name}")


@router.get("", response_model=List[schemas.NudgeOut])
def list_nudges(
    tz: Optional[str] = Query(None, description="Fuseau IANA du client, ex. Europe/Paris"),
    dismissed: List[str] = Query(default=[], description="Clés des rappels déjà masqués aujourd'hui"),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Rappels du moment (4 au maximum), calculés à partir des tâches et habitudes."""
    now = _now(_zone(tz))
    today = now.date()

    tasks = [
        TaskInfo(
            title=t.title,
            due=t.due_date.date() if t.due_date else None,
            priority=t.priority or "medium",
        )
        for t in db.query(models.Task).filter(models.Task.user_id == user.id, models.Task.status != "done")
    ]

    habits = db.query(models.Habit).filter(models.Habit.user_id == user.id).all()
    done_days = defaultdict(set)
    if habits:
        rows = (
            db.query(models.HabitLog.habit_id, models.HabitLog.date)
            .filter(
                models.HabitLog.habit_id.in_([h.id for h in habits]),
                models.HabitLog.completed.is_(True),
                models.HabitLog.date >= today - timedelta(days=HISTORY_DAYS),
            )
            .all()
        )
        for habit_id, day in rows:
            done_days[habit_id].add(day)

    infos = [
        HabitInfo(name=h.name, target_frequency=h.target_frequency or 7, done_days=done_days[h.id])
        for h in habits
    ]
    nudges = build_nudges(now, tasks, infos, dismissed=set(dismissed))
    return [schemas.NudgeOut(key=n.key, view=n.view, text=n.text, warn=n.warn) for n in nudges]
