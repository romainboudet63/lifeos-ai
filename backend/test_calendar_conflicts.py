from datetime import datetime
from app.calendar_utils import TimeRange, find_conflicts, overlaps


def dt(h, m=0):
    return datetime(2026, 9, 1, h, m)


def test_overlaps_true_when_ranges_cross():
    a = TimeRange(dt(10), dt(11), "A")
    b = TimeRange(dt(10, 30), dt(11, 30), "B")
    assert overlaps(a, b) is True


def test_overlaps_false_when_adjacent():
    a = TimeRange(dt(10), dt(11), "A")
    b = TimeRange(dt(11), dt(12), "B")
    assert overlaps(a, b) is False, "deux événements qui se touchent pile ne sont pas en conflit"


def test_overlaps_false_when_far_apart():
    a = TimeRange(dt(9), dt(10), "A")
    b = TimeRange(dt(14), dt(15), "B")
    assert overlaps(a, b) is False


def test_overlaps_true_when_fully_contained():
    a = TimeRange(dt(9), dt(17), "Journée bureau")
    b = TimeRange(dt(12), dt(13), "Déjeuner")
    assert overlaps(a, b) is True


def test_find_conflicts_returns_only_overlapping():
    candidate = TimeRange(dt(10), dt(11), "Nouveau RDV")
    existing = [
        TimeRange(dt(8), dt(9), "Café"),
        TimeRange(dt(10, 30), dt(11, 30), "Réunion"),  # chevauche
        TimeRange(dt(14), dt(15), "Autre"),
    ]
    conflicts = find_conflicts(candidate, existing)
    assert len(conflicts) == 1
    assert conflicts[0].label == "Réunion"


def test_find_conflicts_empty_when_no_overlap():
    candidate = TimeRange(dt(20), dt(21), "Sport")
    existing = [TimeRange(dt(9), dt(10), "Travail")]
    assert find_conflicts(candidate, existing) == []


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
