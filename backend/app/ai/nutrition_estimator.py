"""
Estimation calories/macros à partir d'une description texte.

Deux modes :
1. Mode IA (si ANTHROPIC_API_KEY configurée) : demande à Claude une
   estimation structurée en JSON. C'est la vraie fonctionnalité prévue
   au cahier des charges — je n'ai pas pu tester cet appel de bout en
   bout avec une vraie clé (je n'en ai pas dans ce sandbox), mais le
   réseau vers api.anthropic.com est joignable ici (contrairement à
   Google/Strava) et le code réutilise exactement le même pattern
   d'appel que app/ai/engine.py, déjà utilisé et fonctionnel pour le
   chat. À confirmer avec ta propre clé.
2. Mode heuristique (fallback sans clé, ou si l'appel IA échoue) : une
   petite base d'aliments courants avec des valeurs nutritionnelles
   typiques par portion. Grossier mais utile pour développer/tester
   sans dépendre d'une clé API — et 100% local, donc testé ici avec de
   vrais cas (voir test_nutrition_estimator.py).
"""
import json
import re
import unicodedata
from typing import Optional

import httpx

from app.config import settings

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-5"

# Valeurs nutritionnelles typiques PAR PORTION usuelle (pas par 100g,
# pour éviter d'avoir à estimer un poids en plus du reste).
# Source : ordres de grandeur usuels, à affiner si besoin.
FOOD_DATABASE = {
    "pomme": {"calories": 80, "protein_g": 0.4, "carbs_g": 21, "fat_g": 0.3},
    "banane": {"calories": 105, "protein_g": 1.3, "carbs_g": 27, "fat_g": 0.4},
    "oeuf": {"calories": 70, "protein_g": 6, "carbs_g": 0.6, "fat_g": 5},
    "riz": {"calories": 200, "protein_g": 4, "carbs_g": 44, "fat_g": 0.4},
    "pates": {"calories": 220, "protein_g": 8, "carbs_g": 43, "fat_g": 1.3},
    "pain": {"calories": 80, "protein_g": 3, "carbs_g": 15, "fat_g": 1},
    "poulet": {"calories": 165, "protein_g": 31, "carbs_g": 0, "fat_g": 3.6},
    "saumon": {"calories": 208, "protein_g": 20, "carbs_g": 0, "fat_g": 13},
    "salade": {"calories": 20, "protein_g": 1.5, "carbs_g": 4, "fat_g": 0.2},
    "avocat": {"calories": 240, "protein_g": 3, "carbs_g": 12, "fat_g": 22},
    "fromage": {"calories": 110, "protein_g": 7, "carbs_g": 1, "fat_g": 9},
    "yaourt": {"calories": 60, "protein_g": 5, "carbs_g": 7, "fat_g": 1.5},
    "chocolat": {"calories": 150, "protein_g": 2, "carbs_g": 17, "fat_g": 8},
    "pizza": {"calories": 285, "protein_g": 12, "carbs_g": 36, "fat_g": 10},
    "burger": {"calories": 295, "protein_g": 17, "carbs_g": 30, "fat_g": 14},
    "frites": {"calories": 312, "protein_g": 3.5, "carbs_g": 41, "fat_g": 15},
    "lait": {"calories": 65, "protein_g": 3.4, "carbs_g": 5, "fat_g": 3.6},
    "cafe": {"calories": 5, "protein_g": 0.3, "carbs_g": 0, "fat_g": 0},
    "soupe": {"calories": 120, "protein_g": 4, "carbs_g": 15, "fat_g": 4},
}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def estimate_nutrition_heuristic(description: str) -> dict:
    """Cherche des aliments connus dans la description, avec un
    multiplicateur optionnel ("2 oeufs" -> x2). Additionne les valeurs
    trouvées. Renvoie found=False si rien n'est reconnu."""
    text = _strip_accents(description.lower())
    words = re.findall(r"\d+|[a-z]+", text)

    total = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    matched_foods = []
    pending_multiplier = 1

    for word in words:
        if word.isdigit():
            pending_multiplier = int(word)
            continue

        # tolère un 's' final (pluriel simple)
        key = word[:-1] if word.endswith("s") and word not in FOOD_DATABASE else word
        food = FOOD_DATABASE.get(word) or FOOD_DATABASE.get(key)
        if food:
            multiplier = pending_multiplier
            for k in total:
                total[k] += food[k] * multiplier
            matched_foods.append(word)
        pending_multiplier = 1  # le multiplicateur ne s'applique qu'au mot juste après

    if not matched_foods:
        return {
            "found": False,
            "calories": None,
            "protein_g": None,
            "carbs_g": None,
            "fat_g": None,
            "matched_foods": [],
            "source": "heuristique",
        }

    return {
        "found": True,
        "calories": round(total["calories"]),
        "protein_g": round(total["protein_g"], 1),
        "carbs_g": round(total["carbs_g"], 1),
        "fat_g": round(total["fat_g"], 1),
        "matched_foods": matched_foods,
        "source": "heuristique",
    }


async def estimate_nutrition_ai(description: str) -> Optional[dict]:
    """Demande à Claude une estimation structurée. Renvoie None si pas
    de clé API configurée ou si l'appel échoue (le routeur retombe
    alors sur l'heuristique)."""
    if not settings.anthropic_api_key:
        return None

    system_prompt = (
        "Tu es un nutritionniste. On te donne la description d'un repas. "
        "Réponds UNIQUEMENT avec un objet JSON valide (rien avant, rien après), "
        'au format exact : {"calories": <nombre>, "protein_g": <nombre>, '
        '"carbs_g": <nombre>, "fat_g": <nombre>}. '
        "Donne ta meilleure estimation même si la description est vague."
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": DEFAULT_MODEL,
                    "max_tokens": 200,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": description}],
                },
            )
            response.raise_for_status()
            data = response.json()
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            parsed = json.loads(text)
            return {
                "found": True,
                "calories": parsed.get("calories"),
                "protein_g": parsed.get("protein_g"),
                "carbs_g": parsed.get("carbs_g"),
                "fat_g": parsed.get("fat_g"),
                "matched_foods": [],
                "source": "ia",
            }
    except (httpx.HTTPError, json.JSONDecodeError, KeyError):
        return None


async def estimate_nutrition(description: str) -> dict:
    ai_result = await estimate_nutrition_ai(description)
    if ai_result is not None:
        return ai_result
    return estimate_nutrition_heuristic(description)
