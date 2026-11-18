"""
Mémoire automatique de l'assistant.

Après chaque échange avec l'utilisateur, un second appel à Claude décide s'il y a
quelque chose de durable à retenir (préférence, proche, projet, contrainte...), à
corriger ou à oublier. Les souvenirs sont stockés dans la table `memories`
existante et retrouvés ensuite par `retrieve_relevant_memories` (app/ai/memory.py).

Garde-fous :
- au plus MAX_ADDED_PER_EXCHANGE nouveaux souvenirs par échange ;
- le modèle désigne les souvenirs à retirer par un numéro (1..n) dans la liste de
  CET utilisateur : il ne peut jamais toucher aux souvenirs d'un autre ;
- une réponse mal formée ne change rien ;
- au-delà de MAX_MEMORIES, une consolidation fusionne les doublons, et son résultat
  est rejeté s'il paraît suspect (mal formé, ou qui supprime trop).

Confidentialité : chaque extraction envoie à l'API Claude le message de l'utilisateur,
la réponse de l'assistant et les souvenirs déjà enregistrés. Les journaux n'écrivent
que des compteurs, jamais le contenu des souvenirs.
"""
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import models
from app.ai import engine
from app.ai.memory import embed_text
from app.database import SessionLocal

logger = logging.getLogger(__name__)

Completer = Callable[[str], Awaitable[str]]

MAX_MEMORIES = 40
MAX_ADDED_PER_EXCHANGE = 3
MAX_LENGTH = 200
MIN_MESSAGE_LENGTH = 12  # en dessous, on ne dérange pas le modèle (sauf "retiens"/"oublie")
CATEGORY = "contexte"

EXTRACTION_INSTRUCTIONS = (
    "Tu gères la mémoire longue durée d'un assistant personnel. À partir de l'échange "
    "ci-dessous, décide quoi retenir sur la personne. Retiens uniquement des informations "
    "durables et utiles pour l'aider plus tard : préférences, habitudes de vie, proches et "
    "leur rôle, projets en cours, contraintes, décisions prises, objectifs. Ne retiens pas : "
    "l'humeur du moment, les questions ponctuelles, ce qui figure déjà dans l'application "
    "(tâches, habitudes, objectifs, calendrier, sport, nutrition, finances), ni jamais de "
    "mots de passe, numéros de carte ou de pièce d'identité. Si la personne demande "
    "explicitement de retenir quelque chose, retiens-le ; si elle demande d'oublier quelque "
    "chose, retire le souvenir correspondant. Si un souvenir existant est contredit ou "
    "périmé, retire-le et ajoute la version à jour. Écris chaque souvenir en français, en "
    "une phrase courte, neutre et autonome (par exemple « Préfère faire du sport le matin »). "
    "Réponds UNIQUEMENT avec du JSON valide, sans markdown, au format "
    '{"add": ["..."], "remove": [numéros]}, où les numéros sont ceux de la liste des '
    "souvenirs existants, avec des listes vides s'il n'y a rien à changer."
)

CONSOLIDATION_INSTRUCTIONS = (
    "Voici les souvenirs d'un assistant personnel sur une personne. Fusionne les doublons, "
    "supprime ce qui est périmé ou redondant, et garde au plus 30 souvenirs courts, sans "
    "perdre l'essentiel. Réponds UNIQUEMENT avec un tableau JSON de chaînes, sans markdown."
)


@dataclass
class Changes:
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)


def normalize(text: str) -> str:
    """Forme comparable d'un souvenir : sans accents, ponctuation ni casse."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text)).strip()


def parse_json_loose(raw: str, opening: str, closing: str):
    """Premier bloc JSON entre deux délimiteurs, même entouré de texte ou de markdown."""
    cleaned = (raw or "").replace("```json", "").replace("```", "")
    start, end = cleaned.find(opening), cleaned.rfind(closing)
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None


def should_extract(user_message: str) -> bool:
    text = (user_message or "").strip()
    return len(text) >= MIN_MESSAGE_LENGTH or bool(re.search(r"retiens|oublie", text, re.I))


def _list_memories(db: Session, user_id: str) -> List[models.Memory]:
    return (
        db.query(models.Memory)
        .filter(models.Memory.user_id == user_id)
        .order_by(models.Memory.created_at, models.Memory.id)
        .all()
    )


def _new_memory(user_id: str, content: str) -> models.Memory:
    return models.Memory(user_id=user_id, content=content, category=CATEGORY, embedding=embed_text(content))


def build_extraction_prompt(known: List[models.Memory], user_message: str, reply: str) -> str:
    listing = "\n".join(f"{i}: {m.content}" for i, m in enumerate(known, start=1)) or "(aucun)"
    return (
        f"{EXTRACTION_INSTRUCTIONS}\n\nSouvenirs existants :\n{listing}\n\n"
        f"Message de la personne : {user_message}\n\nRéponse de l'assistant : {reply}"
    )


def parse_changes(raw: str, known: List[models.Memory]) -> Tuple[List[str], List[models.Memory]]:
    """Traduit la réponse du modèle en (textes à ajouter, souvenirs à retirer)."""
    data = parse_json_loose(raw, "{", "}")
    if not isinstance(data, dict):
        return [], []

    raw_add, raw_remove = data.get("add"), data.get("remove")
    if not isinstance(raw_add, list):  # ex. "add": "texte" : on ne parcourt surtout pas la chaîne
        raw_add = []
    if not isinstance(raw_remove, list):
        raw_remove = []

    to_add = []
    for item in raw_add:
        if isinstance(item, str) and item.strip():
            to_add.append(item.strip()[:MAX_LENGTH])
    to_add = to_add[:MAX_ADDED_PER_EXCHANGE]

    to_remove: List[models.Memory] = []
    for item in raw_remove:
        if isinstance(item, bool):
            continue
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= len(known) and known[number - 1] not in to_remove:
            to_remove.append(known[number - 1])
    return to_add, to_remove


async def update_memory_from_exchange(
    db: Session,
    user_id: str,
    user_message: str,
    reply: str,
    complete: Optional[Completer] = None,
) -> Changes:
    changes = Changes()
    if not should_extract(user_message):
        return changes
    complete = complete or engine.complete

    known = _list_memories(db, user_id)
    raw = await complete(build_extraction_prompt(known, user_message, reply))
    to_add, to_remove = parse_changes(raw, known)

    for memory in to_remove:
        db.delete(memory)
        changes.removed.append(memory.content)

    removed_ids = {m.id for m in to_remove}
    existing = {normalize(m.content) for m in known if m.id not in removed_ids}
    for text in to_add:
        key = normalize(text)
        if not key or key in existing:
            continue
        db.add(_new_memory(user_id, text))
        existing.add(key)
        changes.added.append(text)

    if changes.added or changes.removed:
        db.commit()  # une seule transaction pour tout l'échange

    if len(known) - len(to_remove) + len(changes.added) > MAX_MEMORIES:
        await consolidate(db, user_id, complete)
    return changes


async def consolidate(db: Session, user_id: str, complete: Optional[Completer] = None) -> bool:
    """Fusionne les souvenirs ; renvoie False (sans rien changer) si la réponse est suspecte."""
    complete = complete or engine.complete
    before = _list_memories(db, user_id)
    prompt = CONSOLIDATION_INSTRUCTIONS + "\n\n" + "\n".join(f"- {m.content}" for m in before)
    merged = parse_json_loose(await complete(prompt), "[", "]")
    if not isinstance(merged, list) or not all(isinstance(x, str) for x in merged):
        return False

    cleaned, seen = [], set()
    for text in merged:
        text = text.strip()[:MAX_LENGTH]
        key = normalize(text)
        if key and key not in seen:
            seen.add(key)
            cleaned.append(text)

    minimum = -(-len(before) * 2 // 5)  # au moins 40 % des souvenirs d'origine (arrondi au-dessus)
    if len(cleaned) < minimum or len(cleaned) > MAX_MEMORIES:
        return False

    for memory in before:
        db.delete(memory)
    for text in cleaned:
        db.add(_new_memory(user_id, text))
    db.commit()
    return True


async def run_in_background(user_id: str, user_message: str, reply: str) -> None:
    """Tâche de fond lancée après /ai/chat.

    Ouvre sa propre session : celle de la requête est déjà fermée quand la tâche démarre.
    Ne lève jamais d'exception (l'utilisateur a déjà sa réponse).
    """
    db = SessionLocal()
    try:
        changes = await update_memory_from_exchange(db, user_id, user_message, reply)
        if changes.added or changes.removed:
            logger.info("Mémoire mise à jour : +%d / -%d", len(changes.added), len(changes.removed))
    except Exception:
        db.rollback()
        logger.exception("Mise à jour de la mémoire impossible")
    finally:
        db.close()
