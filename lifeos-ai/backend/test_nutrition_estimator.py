from app.ai.nutrition_estimator import estimate_nutrition_heuristic, FOOD_DATABASE


def test_single_known_food():
    result = estimate_nutrition_heuristic("une pomme")
    assert result["found"] is True
    assert result["calories"] == 80
    assert "pomme" in result["matched_foods"]


def test_unknown_food_returns_not_found():
    result = estimate_nutrition_heuristic("un plat de licorne arc-en-ciel")
    assert result["found"] is False
    assert result["calories"] is None


def test_multiplier_applied_correctly():
    result = estimate_nutrition_heuristic("2 oeufs")
    single = FOOD_DATABASE["oeuf"]
    assert result["calories"] == single["calories"] * 2
    assert result["protein_g"] == round(single["protein_g"] * 2, 1)


def test_multiple_foods_summed():
    result = estimate_nutrition_heuristic("riz et poulet")
    expected_calories = FOOD_DATABASE["riz"]["calories"] + FOOD_DATABASE["poulet"]["calories"]
    assert result["calories"] == expected_calories
    assert set(result["matched_foods"]) == {"riz", "poulet"}


def test_plural_form_recognized():
    # "oeufs" doit être reconnu même si la base de données a la clé au singulier
    result = estimate_nutrition_heuristic("des oeufs")
    assert result["found"] is True
    assert "oeufs" in result["matched_foods"]


def test_accents_stripped_before_matching():
    result = estimate_nutrition_heuristic("un café")
    assert result["found"] is True


def test_mixed_known_and_unknown_still_matches_known():
    result = estimate_nutrition_heuristic("pizza et licorne")
    assert result["found"] is True
    assert result["calories"] == FOOD_DATABASE["pizza"]["calories"]


def test_source_is_heuristique():
    result = estimate_nutrition_heuristic("une banane")
    assert result["source"] == "heuristique"


def test_multiplier_only_applies_to_immediately_following_food():
    # "3 pommes et un oeuf" -> 3x pomme, 1x oeuf (pas 3x oeuf)
    result = estimate_nutrition_heuristic("3 pommes et un oeuf")
    expected = FOOD_DATABASE["pomme"]["calories"] * 3 + FOOD_DATABASE["oeuf"]["calories"]
    assert result["calories"] == expected


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
