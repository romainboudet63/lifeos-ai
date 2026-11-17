from datetime import date, datetime, timedelta

from app.nudges import HabitInfo, TaskInfo, build_nudges, habit_streak

MONDAY = date(2026, 11, 9)


def at(hour, day=MONDAY):
    return datetime(day.year, day.month, day.day, hour, 0)


def keys(nudges):
    return [n.key for n in nudges]


def days_before(n, start=MONDAY):
    return {start - timedelta(days=i) for i in range(1, n + 1)}


def test_streak_counts_until_yesterday_when_not_done_today():
    habit = HabitInfo("Méditation", done_days=days_before(4))
    assert habit_streak(habit, MONDAY) == 4
    habit.done_days.add(MONDAY)
    assert habit_streak(habit, MONDAY) == 5
    assert habit_streak(HabitInfo("Vide"), MONDAY) == 0


def test_streak_stops_at_the_first_gap():
    habit = HabitInfo("Lire", done_days={MONDAY - timedelta(days=1), MONDAY - timedelta(days=3)})
    assert habit_streak(habit, MONDAY) == 1


def test_late_and_due_today_tasks():
    tasks = [
        TaskInfo("Payer la facture", due=MONDAY - timedelta(days=2)),
        TaskInfo("Appeler le notaire", due=MONDAY),
        TaskInfo("Déjà fait", due=MONDAY - timedelta(days=5), done=True),
        TaskInfo("Plus tard", due=MONDAY + timedelta(days=3)),
        TaskInfo("Sans échéance"),
    ]
    out = build_nudges(at(9), tasks, [])
    assert keys(out) == ["late", "due"]
    assert out[0].warn and "Payer la facture" in out[0].text
    assert not out[1].warn and "Appeler le notaire" in out[1].text
    assert out[0].view == out[1].view == "tasks"


def test_late_message_names_the_oldest_then_highest_priority_task():
    tasks = [
        TaskInfo("Récente", due=MONDAY - timedelta(days=1), priority="high"),
        TaskInfo("Ancienne basse", due=MONDAY - timedelta(days=4), priority="low"),
        TaskInfo("Ancienne haute", due=MONDAY - timedelta(days=4), priority="high"),
    ]
    (nudge,) = build_nudges(at(9), tasks, [])
    assert nudge.text == "3 tâches sont en retard, à commencer par « Ancienne haute »."


def test_plural_due_today():
    tasks = [TaskInfo("A", due=MONDAY), TaskInfo("B", due=MONDAY)]
    assert build_nudges(at(9), tasks, [])[0].text == "2 tâches à terminer aujourd'hui."


def test_streak_in_danger_only_from_5pm():
    habit = HabitInfo("Marche 30 min", done_days=days_before(11))
    assert build_nudges(at(16), [], [habit]) == []
    evening = build_nudges(at(17), [], [habit])
    assert keys(evening) == ["streak"]
    assert evening[0].warn and evening[0].view == "habits"
    assert "11 jours" in evening[0].text


def test_streak_rule_takes_over_from_the_plain_reminder():
    risky = HabitInfo("Marche", done_days=days_before(5))
    plain = HabitInfo("Lire")
    assert keys(build_nudges(at(19), [], [risky, plain])) == ["streak"]  # un seul des deux


def test_plain_habit_reminder_from_6pm():
    assert build_nudges(at(17), [], [HabitInfo("Lire")]) == []
    out = build_nudges(at(18), [], [HabitInfo("Lire"), HabitInfo("Étirements")])
    assert [n.text for n in out] == ["Il reste 2 habitudes à cocher aujourd'hui."]
    out = build_nudges(at(18), [], [HabitInfo("Lire")])
    assert out[0].text == "Il reste une habitude à cocher : « Lire »."


def test_done_and_non_daily_habits_never_nag():
    done = HabitInfo("Fait", done_days=days_before(5) | {MONDAY})
    weekly = HabitInfo("Piscine", target_frequency=1)
    assert build_nudges(at(22), [], [done, weekly]) == []


def test_dismissed_rules_are_hidden_and_output_is_capped():
    tasks = [TaskInfo("A", due=MONDAY - timedelta(days=1)), TaskInfo("B", due=MONDAY)]
    habit = HabitInfo("H", done_days=days_before(5))
    assert keys(build_nudges(at(21), tasks, [habit])) == ["late", "due", "streak"]
    assert keys(build_nudges(at(21), tasks, [habit], dismissed={"late"})) == ["due", "streak"]
    assert keys(build_nudges(at(21), tasks, [habit], limit=2)) == ["late", "due"]
