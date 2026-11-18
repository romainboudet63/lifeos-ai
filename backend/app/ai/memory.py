"""
Système de mémoire longue durée pour l'IA (RAG maison).

IMPORTANT — limite connue et assumée de ce prototype :
Ce module n'utilise PAS de vrai modèle d'embeddings neuronal. Le sandbox de
développement n'a pas accès au hub Hugging Face (huggingface.co retourne
403 Forbidden), donc aucun modèle pré-entraîné ne peut être téléchargé ici.

À la place, on combine deux heuristiques pour un prototype raisonnablement
utile :
1. N-grammes de caractères (3-4 lettres) : capte les variantes
   morphologiques d'un même mot ("courir" / "course" / "coureur"
   partagent des sous-chaînes).
2. Expansion par thésaurus de catégories : une petite liste de mots reliés
   par thème (sport, sommeil, travail...) est étiquetée avec un tag de
   catégorie commun, ce qui permet de faire le lien entre vrais synonymes
   que les n-grammes de caractères ne peuvent pas capter seuls
   ("entraîner" et "course" ne partagent aucune sous-chaîne, mais sont
   tous deux tagués `sport`).

Ce n'est PAS une recherche sémantique générale : un mot absent du
thésaurus et morphologiquement différent de la mémoire stockée ne sera
toujours pas retrouvé. Avant la mise en production, remplacer
`embed_text` par un appel à une vraie API d'embeddings (OpenAI, Voyage,
Cohere...) et stocker les vecteurs dans la colonne `vector` pgvector du
schéma de production (voir database/schema.sql) plutôt que du JSON.
"""
import hashlib
import re
import unicodedata
from typing import List

import numpy as np
from sqlalchemy.orm import Session

from app import models

EMBEDDING_DIM = 512
NGRAM_SIZES = (3, 4)

# Petit thésaurus de démonstration par catégorie. À enrichir/faire évoluer
# selon les domaines réels de l'app (sport, sommeil, travail, nutrition,
# finance, état mental). Chaque mot listé ajoute un tag de catégorie
# partagé à l'embedding, ce qui relie les synonymes entre eux.
CATEGORY_SYNONYMS = {
    "sport": [
        "sport", "courir", "course", "coureur", "running", "jogging",
        "marathon", "entrainement", "entrainer", "musculation", "fitness",
        "cyclisme", "velo", "natation", "exercice", "seance",
    ],
    "sommeil": [
        "sommeil", "dormir", "dodo", "coucher", "nuit", "fatigue",
        "insomnie", "reveil", "sieste", "reposer",
    ],
    "travail": [
        "travail", "travailler", "boulot", "job", "developpeur", "coder",
        "code", "bureau", "reunion", "collegue", "projet", "deadline",
    ],
    "nutrition": [
        "nutrition", "manger", "repas", "alimentation", "calorie",
        "regime", "cuisine", "recette", "proteine",
    ],
    "finance": [
        "finance", "argent", "budget", "depense", "epargne", "salaire",
        "facture",
    ],
    "mental": [
        "stress", "anxiete", "mental", "meditation", "relaxation",
        "humeur", "emotion", "motivation",
    ],
}
# Inverse lookup : mot normalisé -> catégorie
_WORD_TO_CATEGORY = {
    word: cat for cat, words in CATEGORY_SYNONYMS.items() for word in words
}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _tokens(text: str) -> List[str]:
    text = _strip_accents(text.lower())
    return re.findall(r"[a-z0-9]+", text)


def _char_ngrams(word: str) -> List[str]:
    padded = f"_{word}_"
    grams = []
    for n in NGRAM_SIZES:
        grams.extend(padded[i:i + n] for i in range(len(padded) - n + 1))
    return grams


def _hash_into(vector: np.ndarray, key: str, weight: float = 1.0) -> None:
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    idx = h % EMBEDDING_DIM
    sign = 1.0 if (h // EMBEDDING_DIM) % 2 == 0 else -1.0
    vector[idx] += sign * weight


def embed_text(text: str) -> List[float]:
    vector = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    words = _tokens(text)

    for word in words:
        # n-grammes de caractères : variantes morphologiques du même mot
        for gram in _char_ngrams(word):
            _hash_into(vector, f"ng:{gram}", weight=1.0)

        # tag de catégorie partagé : relie les vrais synonymes du thésaurus
        category = _WORD_TO_CATEGORY.get(word)
        if category:
            _hash_into(vector, f"cat:{category}", weight=2.0)

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.tolist()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    denom = (np.linalg.norm(a_arr) * np.linalg.norm(b_arr))
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


def add_memory(db: Session, user_id: str, content: str, category: str = "contexte") -> models.Memory:
    memory = models.Memory(
        user_id=user_id,
        content=content,
        category=category,
        embedding=embed_text(content),
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def retrieve_relevant_memories(
    db: Session, user_id: str, query: str, top_k: int = 5, min_score: float = 0.12
) -> List[models.Memory]:
    """Récupère les souvenirs les plus pertinents pour une requête donnée."""
    query_vec = embed_text(query)
    all_memories = db.query(models.Memory).filter(models.Memory.user_id == user_id).all()

    scored = []
    for mem in all_memories:
        if not mem.embedding:
            continue
        score = cosine_similarity(query_vec, mem.embedding)
        if score >= min_score:
            scored.append((score, mem))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [mem for _, mem in scored[:top_k]]
