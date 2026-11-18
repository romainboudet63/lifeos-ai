"""
Génération de programmes sportifs à partir d'un objectif en texte libre
(ex: "courir un semi-marathon dans 3 mois").

Même architecture que nutrition_estimator.py :
1. Mode IA (si ANTHROPIC_API_KEY configurée) : Claude génère un programme
   structuré en JSON. Non testé de bout en bout ici faute de clé, mais
   le réseau vers api.anthropic.com est joignable (vérifié) et le code
   réutilise le pattern déjà éprouvé du chat et de l'estimation
   nutritionnelle.
2. Mode heuristique (fallback local, testé réellement) : détecte la
   catégorie d'objectif par mots-clés (course, musculation, perte de
   poids...) et génère un plan progressif sur N semaines à partir d'un
   petit gabarit par catégorie. Grossier mais cohérent et 100% testable
   hors-ligne (voir test_workout_planner.py).
"""
import json
import re
import unicodedata
from typing import Optional

import httpx

from app.config import settings

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-5"

DEFAULT_WEEKS = 8
DEFAULT_SESSIONS_PER_WEEK = 3


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _detect_category(objective: str) -> str:
    text = _strip_accents(objective.lower())
    if any(k in text for k in ["marathon", "semi-marathon", "semi marathon", "10k", "5k", "course a pied", "courir"]):
        return "course"
    if any(k in text for k in ["musculation", "force", "masse musculaire", "prise de masse"]):
        return "musculation"
    if any(k in text for k in ["perte de poids", "maigrir", "perdre du poids", "cardio"]):
        return "cardio"
    return "generique"


def _extract_weeks(objective: str, default: int = DEFAULT_WEEKS) -> int:
    """Cherche "X mois" ou "X semaines" dans le texte pour déduire la
    durée du programme. 1 mois ≈ 4 semaines."""
    text = _strip_accents(objective.lower())
    match_weeks = re.search(r"(\d+)\s*semaine", text)
    if match_weeks:
        return max(2, min(52, int(match_weeks.group(1))))
    match_months = re.search(r"(\d+)\s*mois", text)
    if match_months:
        return max(2, min(52, int(match_months.group(1)) * 4))
    return default


def _running_week(week_number: int, total_weeks: int) -> dict:
    # Progression linéaire simple de la distance de la sortie longue,
    # avec une semaine de récupération toutes les 4 semaines (règle
    # classique en course à pied pour éviter les blessures).
    is_recovery = week_number % 4 == 0
    base_km = 5 + (week_number * 1.5)
    long_run_km = round(base_km * (0.7 if is_recovery else 1.0), 1)

    return {
        "week_number": week_number,
        "focus": "Récupération" if is_recovery else f"Semaine {week_number} — endurance progressive",
        "sessions": [
            {"day_label": "Mardi", "type": "Fractionné", "duration_min": 35, "description": "Endurance fondamentale, allure facile"},
            {"day_label": "Jeudi", "type": "Endurance", "duration_min": 40, "description": "Footing à allure modérée"},
            {"day_label": "Dimanche", "type": "Sortie longue", "duration_min": round(long_run_km * 6), "description": f"Sortie longue ~{long_run_km} km à allure confortable"},
        ],
    }


def _musculation_week(week_number: int, total_weeks: int) -> dict:
    is_deload = week_number % 4 == 0
    return {
        "week_number": week_number,
        "focus": "Décharge (deload)" if is_deload else f"Semaine {week_number} — surcharge progressive",
        "sessions": [
            {"day_label": "Lundi", "type": "Haut du corps", "duration_min": 50, "description": "Push : pecs, épaules, triceps"},
            {"day_label": "Mercredi", "type": "Bas du corps", "duration_min": 50, "description": "Squat, fentes, ischios"},
            {"day_label": "Vendredi", "type": "Full body", "duration_min": 45, "description": "Tirage, dos, gainage"},
        ],
    }


def _cardio_week(week_number: int, total_weeks: int) -> dict:
    return {
        "week_number": week_number,
        "focus": f"Semaine {week_number} — cardio progressif",
        "sessions": [
            {"day_label": "Lundi", "type": "Cardio modéré", "duration_min": 30, "description": "Marche rapide, vélo ou elliptique"},
            {"day_label": "Mercredi", "type": "HIIT", "duration_min": 20, "description": "Intervalles courts haute intensité"},
            {"day_label": "Samedi", "type": "Cardio long", "duration_min": 40, "description": "Séance continue à intensité modérée"},
        ],
    }


def _generique_week(week_number: int, total_weeks: int) -> dict:
    return {
        "week_number": week_number,
        "focus": f"Semaine {week_number}",
        "sessions": [
            {"day_label": "Lundi", "type": "Activité physique", "duration_min": 30, "description": "Séance au choix selon la forme du jour"},
            {"day_label": "Jeudi", "type": "Activité physique", "duration_min": 30, "description": "Séance au choix selon la forme du jour"},
        ],
    }


CATEGORY_GENERATORS = {
    "course": _running_week,
    "musculation": _musculation_week,
    "cardio": _cardio_week,
    "generique": _generique_week,
}

CATEGORY_TITLES = {
    "course": "Programme course à pied",
    "musculation": "Programme musculation",
    "cardio": "Programme cardio",
    "generique": "Programme d'activité physique",
}


def generate_program_heuristic(objective: str, weeks: Optional[int] = None) -> dict:
    category = _detect_category(objective)
    total_weeks = weeks or _extract_weeks(objective)
    generator = CATEGORY_GENERATORS[category]

    return {
        "title": f"{CATEGORY_TITLES[category]} — objectif : {objective.strip()}",
        "source": "heuristique",
        "weeks": [generator(w, total_weeks) for w in range(1, total_weeks + 1)],
    }


async def generate_program_ai(objective: str, weeks: Optional[int] = None) -> Optional[dict]:
    if not settings.anthropic_api_key:
        return None

    total_weeks = weeks or _extract_weeks(objective)
    system_prompt = (
        "Tu es un coach sportif. On te donne un objectif d'entraînement. "
        f"Génère un programme sur {total_weeks} semaines. "
        "Réponds UNIQUEMENT avec un objet JSON valide (rien avant, rien après), au format exact : "
        '{"title": "<titre court>", "weeks": [{"week_number": 1, "focus": "<texte>", '
        '"sessions": [{"day_label": "<jour>", "type": "<type de séance>", "duration_min": <nombre>, "description": "<texte>"}]}]}. '
        "Adapte la progression et l'intensité à l'objectif décrit."
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": DEFAULT_MODEL,
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": objective}],
                },
            )
            response.raise_for_status()
            data = response.json()
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            parsed = json.loads(text)
            parsed["source"] = "ia"
            return parsed
    except (httpx.HTTPError, json.JSONDecodeError, KeyError):
        return None


async def generate_program(objective: str, weeks: Optional[int] = None) -> dict:
    ai_result = await generate_program_ai(objective, weeks)
    if ai_result is not None:
        return ai_result
    return generate_program_heuristic(objective, weeks)
