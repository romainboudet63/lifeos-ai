from app.ai.workout_planner import (
    generate_program_heuristic,
    _detect_category,
    _extract_weeks,
)


def test_detects_marathon_as_course():
    assert _detect_category("Courir un marathon dans 6 mois") == "course"


def test_detects_semi_marathon_as_course():
    assert _detect_category("Je veux faire un semi-marathon") == "course"


def test_detects_musculation():
    assert _detect_category("Prendre de la masse musculaire") == "musculation"


def test_detects_cardio_from_perte_de_poids():
    assert _detect_category("Perdre du poids avant l'été") == "cardio"


def test_unknown_objective_falls_back_to_generique():
    assert _detect_category("Améliorer mon bien-être général") == "generique"


def test_extract_weeks_from_explicit_semaines():
    assert _extract_weeks("Un programme sur 10 semaines") == 10


def test_extract_weeks_from_mois_converts_to_weeks():
    assert _extract_weeks("Courir un marathon dans 6 mois") == 24


def test_extract_weeks_default_when_no_duration_mentioned():
    assert _extract_weeks("Courir plus vite") == 8  # DEFAULT_WEEKS


def test_extract_weeks_clamped_to_reasonable_range():
    assert _extract_weeks("Programme sur 200 semaines") == 52
    assert _extract_weeks("Programme sur 0 semaines") == 2


def test_generate_program_heuristic_has_correct_week_count():
    program = generate_program_heuristic("Courir un 10k dans 4 semaines")
    assert len(program["weeks"]) == 4


def test_generate_program_heuristic_source_is_heuristique():
    program = generate_program_heuristic("Musculation, prise de force")
    assert program["source"] == "heuristique"


def test_generate_program_running_has_progressive_long_run():
    program = generate_program_heuristic("Semi-marathon dans 8 semaines")
    weeks = program["weeks"]
    long_run_week1 = next(s for s in weeks[0]["sessions"] if s["type"] == "Sortie longue")
    long_run_week3 = next(s for s in weeks[2]["sessions"] if s["type"] == "Sortie longue")
    assert long_run_week3["duration_min"] > long_run_week1["duration_min"], \
        "la sortie longue doit progresser dans le temps (hors semaines de récupération)"


def test_generate_program_respects_explicit_weeks_override():
    # même si l'objectif mentionne "6 mois" (24 semaines), le paramètre
    # explicite doit avoir la priorité
    program = generate_program_heuristic("Marathon dans 6 mois", weeks=3)
    assert len(program["weeks"]) == 3


def test_every_week_has_at_least_one_session():
    program = generate_program_heuristic("Bouger un peu plus")
    assert all(len(w["sessions"]) >= 1 for w in program["weeks"])


def test_title_includes_the_objective():
    program = generate_program_heuristic("Courir un marathon de New York")
    assert "New York" in program["title"]


if __name__ == "__main__":
    import sys
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"OK   {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} tests passés")
    sys.exit(1 if failed else 0)
