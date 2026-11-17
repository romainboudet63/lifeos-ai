"""
Rappels intelligents (règles contextuelles).

Fonction pure : ni base de données ni réseau, donc facile à tester. Le router
(app/routers/nudges.py) la branche sur les vraies tables.

Règles actuelles (mêmes que le prototype web, limitées à ce que le backend stocke) :
- tâche(s) en retard ;
- tâche(s) à terminer aujourd'hui ;
- série d'une habitude quotidienne en jeu (à partir de 17 h, série >= 3 jours) ;
- habitudes quotidiennes restantes (à partir de 18 h).

Les rappels « sommeil », « journal » et « bilan du dimanche » du prototype web ne sont
pas repris : le backend n'a pas encore de suivi du sommeil ni de journal (voir ROADMAP,
phase 5).
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import AbstractSet, List, Optional, Set

MAX_NUDGES = 4
DAILY = 7  # Habit.target_frequency == 7 : tous les jours
STREAK_MIN_DAYS = 3
STREAK_HOUR = 17
HABITS_HOUR = 18
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class TaskInfo:
    title: str
    due: Optional[date] = None
    done: bool = False
    priority: str = "medium"


@dataclass
class HabitInfo:
    name: str
    target_frequency: int = DAILY
    done_days: Set[date] = field(default_factory=set)


@dataclass
class Nudge:
    key: str
    view: str  # écran à ouvrir : "tasks" | "habits"
    text: str
    warn: bool = False


def habit_streak(habit: HabitInfo, today: date) -> int:
    """Série en cours ; si l'habitude n'est pas faite aujourd'hui, on compte jusqu'à hier."""
    cursor = today if today in habit.done_days else today - timedelta(days=1)
    n = 0
    while cursor in habit.done_days:
        n += 1
        cursor -= timedelta(days=1)
    return n


def build_nudges(
    now: datetime,
    tasks: List[TaskInfo],
    habits: List[HabitInfo],
    dismissed: AbstractSet[str] = frozenset(),
    limit: int = MAX_NUDGES,
) -> List[Nudge]:
    """`now` doit être exprimé dans le fuseau de l'utilisateur."""
    today, hour = now.date(), now.hour
    out: List[Nudge] = []

    open_tasks = [t for t in tasks if not t.done]

    late = sorted(
        (t for t in open_tasks if t.due and t.due < today),
        key=lambda t: (t.due, PRIORITY_ORDER.get(t.priority, 1)),
    )
    if late:
        text = (
            f"Une tâche est en retard : « {late[0].title} »."
            if len(late) == 1
            else f"{len(late)} tâches sont en retard, à commencer par « {late[0].title} »."
        )
        out.append(Nudge("late", "tasks", text, warn=True))

    due_today = [t for t in open_tasks if t.due == today]
    if due_today:
        text = (
            f"À terminer aujourd'hui : « {due_today[0].title} »."
            if len(due_today) == 1
            else f"{len(due_today)} tâches à terminer aujourd'hui."
        )
        out.append(Nudge("due", "tasks", text))

    daily_open = [h for h in habits if h.target_frequency == DAILY and today not in h.done_days]
    at_risk = sorted(
        (h for h in daily_open if habit_streak(h, today) >= STREAK_MIN_DAYS),
        key=lambda h: -habit_streak(h, today),
    )
    if hour >= STREAK_HOUR and at_risk:
        top = at_risk[0]
        text = f"Votre série « {top.name} » ({habit_streak(top, today)} jours) est en jeu ce soir."
        out.append(Nudge("streak", "habits", text, warn=True))
    elif hour >= HABITS_HOUR and daily_open:
        text = (
            f"Il reste une habitude à cocher : « {daily_open[0].name} »."
            if len(daily_open) == 1
            else f"Il reste {len(daily_open)} habitudes à cocher aujourd'hui."
        )
        out.append(Nudge("habits", "habits", text))

    return [n for n in out if n.key not in dismissed][:limit]
