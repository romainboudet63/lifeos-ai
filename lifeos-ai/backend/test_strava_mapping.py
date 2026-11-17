from app.integrations.strava import map_strava_activity

# Exemple conforme à la documentation officielle de l'API Strava v3
# (structure d'un objet "SummaryActivity")
SAMPLE_RUN = {
    "id": 154504250376823,
    "name": "Happy Friday",
    "type": "Run",
    "sport_type": "Run",
    "distance": 24931.4,
    "moving_time": 4500,  # 75 minutes
    "start_date": "2026-08-15T18:02:00Z",
    "calories": 612,
}

SAMPLE_RIDE_NO_CALORIES = {
    "id": 999,
    "name": "Sortie vélo",
    "type": "Ride",
    "sport_type": "Ride",
    "distance": 15000,
    "moving_time": 1800,  # 30 minutes
    "start_date": "2026-08-16T07:00:00Z",
    # pas de "calories" — champ optionnel côté Strava selon le device
}

SAMPLE_UNKNOWN_SPORT = {
    "id": 42,
    "name": "Escalade",
    "type": "RockClimbing",
    "sport_type": "RockClimbing",
    "moving_time": 3600,
    "start_date": "2026-08-17T10:00:00Z",
}


def test_maps_known_sport_type_to_french_category():
    result = map_strava_activity(SAMPLE_RUN)
    assert result["type"] == "course"


def test_converts_moving_time_seconds_to_minutes():
    result = map_strava_activity(SAMPLE_RUN)
    assert result["duration_min"] == 75


def test_preserves_calories_when_present():
    result = map_strava_activity(SAMPLE_RUN)
    assert result["calories"] == 612


def test_handles_missing_calories_gracefully():
    result = map_strava_activity(SAMPLE_RIDE_NO_CALORIES)
    assert result["calories"] is None
    assert result["type"] == "cyclisme"
    assert result["duration_min"] == 30


def test_falls_back_to_lowercase_for_unknown_sport_type():
    result = map_strava_activity(SAMPLE_UNKNOWN_SPORT)
    assert result["type"] == "rockclimbing"


def test_parses_start_date_correctly():
    result = map_strava_activity(SAMPLE_RUN)
    assert result["performed_at"].year == 2026
    assert result["performed_at"].month == 8
    assert result["performed_at"].day == 15
    assert result["performed_at"].hour == 18


def test_external_id_is_string():
    result = map_strava_activity(SAMPLE_RUN)
    assert result["external_id"] == "154504250376823"
    assert isinstance(result["external_id"], str)


def test_source_is_always_strava():
    result = map_strava_activity(SAMPLE_RUN)
    assert result["source"] == "strava"


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
