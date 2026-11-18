"""
Moteur IA conversationnel de LifeOS.

Construit un prompt système personnalisé à partir :
- des souvenirs long-terme pertinents (mémoire vectorielle)
- des tâches / habitudes / objectifs actifs de l'utilisateur

puis appelle l'API Claude. Si aucune clé API n'est configurée
(ANTHROPIC_API_KEY absente), une réponse de secours est renvoyée pour
que le prototype reste testable sans clé.
"""
from typing import List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app import models
from app.ai.memory import retrieve_relevant_memories

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
# Vérifier le nom de modèle actuel dans la documentation Claude avant mise en prod.
DEFAULT_MODEL = "claude-sonnet-4-5"


async def _call_claude(messages: List[dict], system: Optional[str] = None, max_tokens: int = 1024) -> str:
    """Appel brut à l'API Claude ; renvoie le texte de la réponse."""
    body = {
        "model": settings.anthropic_model or DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        body["system"] = system

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        data = response.json()
    return "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")


async def complete(prompt: str, max_tokens: int = 600) -> str:
    """Un prompt, une réponse : pour les tâches internes (ex. extraction de souvenirs)."""
    return await _call_claude([{"role": "user", "content": prompt}], max_tokens=max_tokens)


def build_system_prompt(db: Session, user: models.User, memories: List[models.Memory]) -> str:
    active_tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user.id, models.Task.status != "done")
        .limit(10)
        .all()
    )
    active_goals = (
        db.query(models.Goal)
        .filter(models.Goal.user_id == user.id, models.Goal.status == "active")
        .limit(10)
        .all()
    )

    memory_block = "\n".join(f"- {m.content}" for m in memories) or "- (aucun souvenir pertinent trouvé)"
    tasks_block = "\n".join(f"- {t.title} (priorité: {t.priority}, statut: {t.status})" for t in active_tasks) or "- Aucune tâche en cours"
    goals_block = "\n".join(f"- {g.title} (progression: {int(g.progress * 100)}%)" for g in active_goals) or "- Aucun objectif actif"

    return f"""Tu es l'assistant personnel IA de {user.full_name or user.email} dans l'application LifeOS.
Tu es un coach bienveillant, concret et concis. Tu t'appuies sur le contexte
ci-dessous pour personnaliser tes réponses, sans jamais l'inventer.

Souvenirs pertinents sur l'utilisateur :
{memory_block}

Tâches actives :
{tasks_block}

Objectifs actifs :
{goals_block}

Réponds toujours en français, de façon actionnable."""


async def generate_reply(db: Session, user: models.User, user_message: str) -> Tuple[str, List[str]]:
    memories = retrieve_relevant_memories(db, user.id, user_message)
    system_prompt = build_system_prompt(db, user, memories)

    if not settings.anthropic_api_key:
        # Mode dégradé sans clé API : permet de tester le prototype de bout en bout.
        fallback = (
            "[Mode démo - aucune clé ANTHROPIC_API_KEY configurée]\n"
            f"J'ai bien reçu : « {user_message} ». "
            "Ajoute ANTHROPIC_API_KEY dans la configuration du serveur pour activer les vraies réponses IA."
        )
        return fallback, [m.content for m in memories]

    reply = await _call_claude(
        [{"role": "user", "content": user_message}], system=system_prompt, max_tokens=1024
    )
    return reply, [m.content for m in memories]
