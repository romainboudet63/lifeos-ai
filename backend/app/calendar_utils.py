"""Détection de chevauchements entre événements de calendrier.

Logique volontairement séparée du router pour pouvoir être testée sans
base de données ni serveur HTTP (voir test_calendar_conflicts.py).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class TimeRange:
    start: datetime
    end: datetime
    label: str = ""


def overlaps(a: TimeRange, b: TimeRange) -> bool:
    return a.start < b.end and b.start < a.end


def find_conflicts(candidate: TimeRange, existing: List[TimeRange]) -> List[TimeRange]:
    """Retourne les événements existants qui chevauchent `candidate`."""
    return [e for e in existing if overlaps(candidate, e)]
