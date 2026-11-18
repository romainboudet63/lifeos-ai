from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app import models, schemas, auth
from app.ai.engine import generate_reply
from app.ai import memory as memory_module
from app.ai import memory_extraction

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=schemas.ChatResponse)
async def chat(
    payload: schemas.ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    # historique
    db.add(models.ChatMessage(user_id=user.id, role="user", content=payload.message))
    db.commit()

    reply, used_memories = await generate_reply(db, user, payload.message)

    db.add(models.ChatMessage(user_id=user.id, role="assistant", content=reply))
    db.commit()

    # Mémoire automatique : en tâche de fond, pour ne pas retarder la réponse.
    # Sans clé API (mode démo) il n'y a pas de modèle à interroger.
    if settings.anthropic_api_key:
        background_tasks.add_task(memory_extraction.run_in_background, user.id, payload.message, reply)

    return schemas.ChatResponse(reply=reply, used_memories=used_memories)


@router.get("/chat/history", response_model=List[schemas.ChatMessageOut])
def chat_history(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == user.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )


@router.post("/memories", status_code=201)
def add_memory(
    content: str,
    category: str = "contexte",
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    mem = memory_module.add_memory(db, user.id, content, category)
    return {"id": mem.id, "content": mem.content, "category": mem.category}


@router.get("/memories", response_model=List[schemas.MemoryOut])
def list_memories(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    """Tout ce que l'assistant retient sur l'utilisateur, du plus récent au plus ancien."""
    return (
        db.query(models.Memory)
        .filter(models.Memory.user_id == user.id)
        .order_by(models.Memory.created_at.desc(), models.Memory.id)
        .all()
    )


@router.delete("/memories/{memory_id}", status_code=204)
def forget_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    memory = (
        db.query(models.Memory)
        .filter(models.Memory.id == memory_id, models.Memory.user_id == user.id)
        .first()
    )
    if not memory:
        raise HTTPException(status_code=404, detail="Souvenir introuvable")
    db.delete(memory)
    db.commit()
    return Response(status_code=204)


@router.delete("/memories", status_code=204)
def forget_everything(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    db.query(models.Memory).filter(models.Memory.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    return Response(status_code=204)
