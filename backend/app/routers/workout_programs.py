from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.ai.workout_planner import generate_program

router = APIRouter(prefix="/workouts/programs", tags=["workout-programs"])


@router.post("", response_model=schemas.WorkoutProgramOut, status_code=201)
async def create_program(
    payload: schemas.WorkoutProgramCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Génère un programme d'entraînement à partir d'un objectif en
    texte libre (ex: "courir un semi-marathon dans 3 mois") et le
    sauvegarde. Utilise l'IA si une clé Anthropic est configurée, sinon
    une heuristique locale (voir app/ai/workout_planner.py)."""
    result = await generate_program(payload.objective, payload.weeks)

    program = models.WorkoutProgram(
        user_id=user.id,
        objective=payload.objective,
        title=result["title"],
        source=result["source"],
        weeks_json=result["weeks"],
    )
    db.add(program)
    db.commit()
    db.refresh(program)

    return schemas.WorkoutProgramOut(
        id=program.id,
        objective=program.objective,
        title=program.title,
        source=program.source,
        weeks=program.weeks_json,
        created_at=program.created_at,
    )


@router.get("", response_model=List[schemas.WorkoutProgramSummary])
def list_programs(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    programs = (
        db.query(models.WorkoutProgram)
        .filter(models.WorkoutProgram.user_id == user.id)
        .order_by(models.WorkoutProgram.created_at.desc())
        .all()
    )
    return [
        schemas.WorkoutProgramSummary(
            id=p.id,
            objective=p.objective,
            title=p.title,
            source=p.source,
            week_count=len(p.weeks_json),
            created_at=p.created_at,
        )
        for p in programs
    ]


@router.get("/{program_id}", response_model=schemas.WorkoutProgramOut)
def get_program(program_id: str, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    program = (
        db.query(models.WorkoutProgram)
        .filter(models.WorkoutProgram.id == program_id, models.WorkoutProgram.user_id == user.id)
        .first()
    )
    if not program:
        raise HTTPException(status_code=404, detail="Programme introuvable")

    return schemas.WorkoutProgramOut(
        id=program.id,
        objective=program.objective,
        title=program.title,
        source=program.source,
        weeks=program.weeks_json,
        created_at=program.created_at,
    )
