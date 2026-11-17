from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import auth, models
from app.ai import engine, memory_extraction
from app.ai.memory import add_memory
from app.config import settings
from app.database import get_db
from app.routers import ai_chat
from app.routers import nudges as nudges_router
from conftest import make_user


def build_client(db, current_user=None):
    app = FastAPI()
    app.include_router(ai_chat.router)
    app.include_router(nudges_router.router)
    app.dependency_overrides[get_db] = lambda: db
    if current_user is not None:
        app.dependency_overrides[auth.get_current_user] = lambda: current_user
    return TestClient(app)


@pytest.fixture
def client(db, user):
    return build_client(db, user)


# ---------- mémoire : liste / suppression ----------

def test_endpoints_require_authentication(db):
    anonymous = build_client(db)
    for method, url in [("get", "/ai/memories"), ("delete", "/ai/memories"), ("delete", "/ai/memories/x"), ("get", "/nudges")]:
        assert getattr(anonymous, method)(url).status_code == 401, url


def test_list_memories_newest_first_and_only_mine(db, user, other_user, client):
    older = add_memory(db, user.id, "Premier")
    older.created_at = datetime(2026, 1, 1)
    add_memory(db, user.id, "Second").created_at = datetime(2026, 6, 1)
    add_memory(db, other_user.id, "Pas à moi")
    db.commit()
    body = client.get("/ai/memories").json()
    assert [m["content"] for m in body] == ["Second", "Premier"]
    assert set(body[0]) == {"id", "content", "category", "created_at"}  # pas d'embedding dans la réponse


def test_forget_one_memory(db, user, other_user, client):
    mine = add_memory(db, user.id, "À oublier")
    theirs = add_memory(db, other_user.id, "À eux")
    assert client.delete(f"/ai/memories/{mine.id}").status_code == 204
    assert client.delete(f"/ai/memories/{mine.id}").status_code == 404
    assert client.delete(f"/ai/memories/{theirs.id}").status_code == 404  # pas le droit, pas d'indice
    assert db.query(models.Memory).filter_by(id=theirs.id).count() == 1


def test_forget_everything_only_affects_me(db, user, other_user, client):
    add_memory(db, user.id, "A")
    add_memory(db, user.id, "B")
    add_memory(db, other_user.id, "C")
    assert client.delete("/ai/memories").status_code == 204
    assert client.get("/ai/memories").json() == []
    assert db.query(models.Memory).filter_by(user_id=other_user.id).count() == 1


def test_existing_manual_add_still_works(db, user, client):
    r = client.post("/ai/memories", params={"content": "Aime le thé", "category": "preference"})
    assert r.status_code == 201 and r.json()["category"] == "preference"
    assert [m["content"] for m in client.get("/ai/memories").json()] == ["Aime le thé"]


# ---------- mémoire : extraction après /ai/chat ----------

def fake_claude(monkeypatch, *replies):
    queue, calls = list(replies), []

    async def _call(messages, system=None, max_tokens=1024):
        calls.append({"system": system, "prompt": messages[0]["content"]})
        return queue.pop(0)

    monkeypatch.setattr(engine, "_call_claude", _call)
    return calls


def test_chat_extracts_memory_in_the_background(db, user, client, session_factory, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(memory_extraction, "SessionLocal", session_factory)
    calls = fake_claude(monkeypatch, "Super projet, bon courage !", '{"add": ["Prépare un semi-marathon"], "remove": []}')

    r = client.post("/ai/chat", json={"message": "Je prépare un semi-marathon en mars"})
    assert r.status_code == 200 and r.json()["reply"] == "Super projet, bon courage !"

    assert len(calls) == 2
    assert calls[0]["system"] and "Souvenirs pertinents" in calls[0]["system"]  # appel de chat inchangé
    assert calls[1]["system"] is None and "Super projet" in calls[1]["prompt"]  # appel d'extraction
    assert [m["content"] for m in client.get("/ai/memories").json()] == ["Prépare un semi-marathon"]

    # le souvenir sert dès l'échange suivant
    fake_claude(monkeypatch, "Tu as dit que tu préparais un semi.", '{"add": [], "remove": []}')
    nxt = client.post("/ai/chat", json={"message": "Comment m'entraîner à courir cette semaine ?"}).json()
    assert nxt["used_memories"] == ["Prépare un semi-marathon"]


def test_chat_without_api_key_never_calls_the_model(db, user, client, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    calls = fake_claude(monkeypatch)
    r = client.post("/ai/chat", json={"message": "Un message assez long pour être analysé"})
    assert r.status_code == 200 and "Mode démo" in r.json()["reply"]
    assert calls == [] and client.get("/ai/memories").json() == []


def test_extraction_failure_does_not_affect_the_chat_reply(db, user, client, session_factory, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(memory_extraction, "SessionLocal", session_factory)
    queue = ["Voici ma réponse."]

    async def _call(messages, system=None, max_tokens=1024):
        if queue:
            return queue.pop(0)
        raise RuntimeError("API en panne")

    monkeypatch.setattr(engine, "_call_claude", _call)
    r = client.post("/ai/chat", json={"message": "Un message assez long pour être analysé"})
    assert r.status_code == 200 and r.json()["reply"] == "Voici ma réponse."
    assert client.get("/ai/memories").json() == []


# ---------- rappels ----------

# 2026-11-09 23:30 UTC = lundi 9 nov. 15:30 à Los Angeles, mardi 10 nov. 00:30 à Paris.
INSTANT = datetime(2026, 11, 9, 23, 30, tzinfo=timezone.utc)


@pytest.fixture
def frozen_now(monkeypatch):
    def set_instant(instant):
        monkeypatch.setattr(nudges_router, "_now", lambda zone: instant.astimezone(zone))

    set_instant(INSTANT)
    return set_instant


def add_task(db, user, title, due=None, status="todo"):
    db.add(models.Task(user_id=user.id, title=title, due_date=due, status=status))
    db.commit()


def add_habit(db, user, name, done_days=(), target=7, completed=True):
    habit = models.Habit(user_id=user.id, name=name, target_frequency=target)
    db.add(habit)
    db.commit()
    for day in done_days:
        db.add(models.HabitLog(habit_id=habit.id, date=day, completed=completed))
    db.commit()
    return habit


def test_nudges_follow_the_clients_timezone(db, user, client, frozen_now):
    add_task(db, user, "Rendre le dossier", due=datetime(2026, 11, 9, 0, 0))
    paris = client.get("/nudges", params={"tz": "Europe/Paris"}).json()  # il est déjà le 10 : en retard
    assert paris == [{"key": "late", "view": "tasks", "text": "Une tâche est en retard : « Rendre le dossier ».", "warn": True}]
    la = client.get("/nudges", params={"tz": "America/Los_Angeles"}).json()  # il est encore le 9 : pour aujourd'hui
    assert [n["key"] for n in la] == ["due"]


def test_default_timezone_comes_from_settings(db, user, client, frozen_now, monkeypatch):
    add_task(db, user, "Rendre le dossier", due=datetime(2026, 11, 9, 0, 0))
    monkeypatch.setattr(settings, "default_timezone", "America/Los_Angeles")
    assert [n["key"] for n in client.get("/nudges").json()] == ["due"]
    monkeypatch.setattr(settings, "default_timezone", "Europe/Paris")
    assert [n["key"] for n in client.get("/nudges").json()] == ["late"]


def test_unknown_timezone_is_a_422(client, frozen_now):
    assert client.get("/nudges", params={"tz": "Mars/Base"}).status_code == 422
    assert client.get("/nudges", params={"tz": "../etc/passwd"}).status_code == 422


def test_nudges_ignore_done_tasks_and_other_users(db, user, other_user, client, frozen_now):
    long_ago = datetime(2026, 11, 1)
    add_task(db, user, "Terminée", due=long_ago, status="done")
    add_task(db, other_user, "À quelqu'un d'autre", due=long_ago)
    assert client.get("/nudges").json() == []


def test_habit_nudges_use_real_logs(db, user, other_user, client, frozen_now):
    today = date(2026, 11, 10)  # côté Paris
    # série de 5 jours se terminant hier, pas encore faite aujourd'hui
    add_habit(db, user, "Marche 30 min", done_days=[today - timedelta(days=i) for i in range(1, 6)])
    add_habit(db, user, "Piscine", target=1)  # hebdomadaire : jamais de rappel quotidien
    add_habit(db, user, "Lire", done_days=[today - timedelta(days=1)], completed=False)  # log "non fait"
    add_habit(db, other_user, "Pas à moi", done_days=[today - timedelta(days=i) for i in range(1, 9)])

    frozen_now(datetime(2026, 11, 10, 19, 0, tzinfo=timezone.utc))  # 20 h à Paris
    out = client.get("/nudges", params={"tz": "Europe/Paris"}).json()
    assert [n["key"] for n in out] == ["streak"]
    assert "Marche 30 min" in out[0]["text"] and "5 jours" in out[0]["text"] and out[0]["view"] == "habits"

    # la même habitude cochée aujourd'hui : plus de série en jeu, reste "Lire"
    habit = db.query(models.Habit).filter_by(name="Marche 30 min").one()
    db.add(models.HabitLog(habit_id=habit.id, date=today, completed=True))
    db.commit()
    out = client.get("/nudges", params={"tz": "Europe/Paris"}).json()
    assert [n["text"] for n in out] == ["Il reste une habitude à cocher : « Lire »."]


def test_dismissed_rules_are_filtered_server_side(db, user, client, frozen_now):
    add_task(db, user, "A", due=datetime(2026, 11, 1))
    add_task(db, user, "B", due=datetime(2026, 11, 10))
    assert [n["key"] for n in client.get("/nudges", params={"tz": "Europe/Paris"}).json()] == ["late", "due"]
    r = client.get("/nudges", params=[("tz", "Europe/Paris"), ("dismissed", "late")])
    assert [n["key"] for n in r.json()] == ["due"]
    r = client.get("/nudges", params=[("tz", "Europe/Paris"), ("dismissed", "late"), ("dismissed", "due")])
    assert r.json() == []
