import asyncio
import json

import pytest

from app import models
from app.ai import memory_extraction as mx
from app.ai.memory import add_memory, retrieve_relevant_memories


def run(coro):
    return asyncio.run(coro)


def scripted(*replies):
    """Faux modèle : renvoie les réponses dans l'ordre et garde les prompts reçus."""
    queue, prompts = list(replies), []

    async def complete(prompt):
        prompts.append(prompt)
        return queue.pop(0) if queue else "{}"

    complete.prompts = prompts
    return complete


def contents(db, user):
    rows = db.query(models.Memory).filter(models.Memory.user_id == user.id).order_by(models.Memory.created_at, models.Memory.id)
    return [m.content for m in rows]


def update(db, user, message, reply, *llm_replies):
    complete = scripted(*llm_replies)
    changes = run(mx.update_memory_from_exchange(db, user.id, message, reply, complete))
    return changes, complete


def test_adds_a_memory_with_embedding_and_default_category(db, user):
    changes, _ = update(db, user, "Je préfère courir le matin avant le travail", "Noté !",
                        '{"add": ["Préfère courir le matin"], "remove": []}')
    assert changes.added == ["Préfère courir le matin"]
    memory = db.query(models.Memory).one()
    assert memory.category == "contexte"
    assert memory.embedding and len(memory.embedding) == 512  # retrouvable par la recherche existante


def test_auto_memory_is_found_by_existing_retrieval(db, user):
    update(db, user, "Je préfère courir le matin avant le travail", "Noté !",
           '{"add": ["Préfère courir le matin"], "remove": []}')
    found = retrieve_relevant_memories(db, user.id, "Quand dois-je aller courir ?")
    assert [m.content for m in found] == ["Préfère courir le matin"]


def test_markdown_fenced_json_is_accepted(db, user):
    changes, _ = update(db, user, "Mon frère s'appelle Antoine, il vit à Lyon", "Super",
                        '```json\n{"add": ["Son frère Antoine vit à Lyon"], "remove": []}\n```')
    assert changes.added == ["Son frère Antoine vit à Lyon"]


def test_duplicates_are_ignored_ignoring_case_accents_and_punctuation(db, user, other_user):
    add_memory(db, user.id, "Préfère courir le matin")
    add_memory(db, other_user.id, "Habite à Lyon")  # même texte chez un autre utilisateur : sans effet
    changes, _ = update(db, user, "Je cours toujours le matin, vraiment", "ok",
                        '{"add": ["prefere COURIR le matin !", "Habite à Lyon"], "remove": []}')
    assert changes.added == ["Habite à Lyon"]
    assert contents(db, user) == ["Préfère courir le matin", "Habite à Lyon"]


def test_removal_uses_numbers_from_the_users_own_list(db, user):
    add_memory(db, user.id, "Habite à Lyon")
    add_memory(db, user.id, "Aime le thé")
    changes, complete = update(db, user, "Je n'habite plus à Lyon, j'ai déménagé", "ok",
                               '{"add": ["Habite à Clermont-Ferrand"], "remove": [1]}')
    assert changes.removed == ["Habite à Lyon"]
    assert contents(db, user) == ["Aime le thé", "Habite à Clermont-Ferrand"]
    assert "1: Habite à Lyon" in complete.prompts[0] and "2: Aime le thé" in complete.prompts[0]


@pytest.mark.parametrize("bad", ["0", "99", '"abc"', "true", "null", "-1", "1.5e9"])
def test_invalid_removal_numbers_are_ignored(db, user, bad):
    add_memory(db, user.id, "Aime le thé")
    changes, _ = update(db, user, "Une phrase assez longue pour déclencher", "ok", f'{{"add": [], "remove": [{bad}]}}')
    assert changes.removed == []
    assert contents(db, user) == ["Aime le thé"]


def test_model_cannot_touch_another_users_memories(db, user, other_user):
    add_memory(db, other_user.id, "Secret de l'autre utilisateur")
    mine = add_memory(db, user.id, "Aime le thé")
    changes, complete = update(db, user, "Oublie tout ce que tu sais sur moi", "ok", '{"add": [], "remove": [1, 2, 3]}')
    assert changes.removed == [mine.content]
    assert contents(db, other_user) == ["Secret de l'autre utilisateur"]
    assert "Secret de l'autre" not in complete.prompts[0]  # jamais envoyé dans le prompt non plus


def test_short_messages_skip_the_model_unless_explicit(db, user):
    changes, complete = update(db, user, "merci", "de rien")
    assert complete.prompts == []
    _, complete = update(db, user, "retiens ça", "ok")
    assert len(complete.prompts) == 1


def test_malformed_or_hostile_output_changes_nothing(db, user):
    add_memory(db, user.id, "Aime le thé")
    for raw in ["désolé, je ne peux pas", "{cassé", '["pas", "un", "objet"]', '{"add": "texte", "remove": 3}', ""]:
        changes, _ = update(db, user, "Je bois du café maintenant, plus du thé", "ok", raw)
        assert (changes.added, changes.removed) == ([], [])
    assert contents(db, user) == ["Aime le thé"]


def test_adds_per_exchange_are_capped_and_trimmed(db, user):
    long_text = "x" * 500
    changes, _ = update(db, user, "Voici plein de choses à retenir sur moi", "ok",
                        json.dumps({"add": ["a1", "  ", 42, long_text, "a2", "a3"], "remove": []}))
    assert changes.added == ["a1", "x" * mx.MAX_LENGTH, "a2"]  # 3 max, vides/non-textes écartés


def test_model_failure_propagates_but_changes_nothing(db, user):
    async def boom(prompt):
        raise RuntimeError("API indisponible")

    add_memory(db, user.id, "Aime le thé")
    with pytest.raises(RuntimeError):
        run(mx.update_memory_from_exchange(db, user.id, "Un message suffisamment long", "ok", boom))
    assert contents(db, user) == ["Aime le thé"]


def test_consolidation_triggers_above_limit_and_replaces_memories(db, user):
    for i in range(mx.MAX_MEMORIES):
        add_memory(db, user.id, f"Souvenir numéro {i}")
    merged = [f"Fusion {i}" for i in range(25)]
    changes, complete = update(db, user, "Une information durable de plus à retenir", "ok",
                               '{"add": ["Un nouveau souvenir"], "remove": []}', json.dumps(merged))
    assert changes.added == ["Un nouveau souvenir"]
    assert len(complete.prompts) == 2  # extraction puis consolidation
    assert contents(db, user) == merged
    assert all(m.embedding for m in db.query(models.Memory))  # ré-embarqués


def test_consolidation_rejects_suspicious_answers_and_keeps_everything(db, user):
    for i in range(10):
        add_memory(db, user.id, f"Souvenir {i}")
    for raw in ['["un seul"]', "n'importe quoi", "[1, 2, 3]", "[]", json.dumps([f"x{i}" for i in range(60)])]:
        assert run(mx.consolidate(db, user.id, scripted(raw))) is False
    assert len(contents(db, user)) == 10


def test_consolidation_minimum_is_forty_percent_rounded_up(db, user):
    for i in range(15):
        add_memory(db, user.id, f"Souvenir {i}")
    assert run(mx.consolidate(db, user.id, scripted(json.dumps([f"a{i}" for i in range(5)])))) is False  # 5 < 6
    assert run(mx.consolidate(db, user.id, scripted(json.dumps([f"a{i}" for i in range(6)])))) is True


def test_consolidation_dedupes_and_does_not_touch_other_users(db, user, other_user):
    for i in range(10):
        add_memory(db, user.id, f"Souvenir {i}")
    add_memory(db, other_user.id, "Reste intact")
    ok = run(mx.consolidate(db, user.id, scripted(json.dumps(["A b", "a B!", "Autre", "Encore", "Et un autre"]))))
    assert ok is True
    assert contents(db, user) == ["A b", "Autre", "Encore", "Et un autre"]
    assert contents(db, other_user) == ["Reste intact"]


def test_background_job_uses_its_own_session_and_never_raises(db, user, session_factory, monkeypatch):
    monkeypatch.setattr(mx, "SessionLocal", session_factory)
    replies = iter(['{"add": ["Prépare un semi-marathon"], "remove": []}'])

    async def fake_complete(prompt):
        return next(replies)

    monkeypatch.setattr(mx.engine, "complete", fake_complete)
    run(mx.run_in_background(user.id, "Je prépare un semi-marathon en mars", "Super projet !"))
    assert contents(db, user) == ["Prépare un semi-marathon"]

    async def boom(prompt):
        raise RuntimeError("réseau coupé")

    monkeypatch.setattr(mx.engine, "complete", boom)
    run(mx.run_in_background(user.id, "Un autre message assez long", "ok"))  # ne lève pas
    assert contents(db, user) == ["Prépare un semi-marathon"]


def test_normalize():
    assert mx.normalize("  Préfère  COURIR, le matin !! ") == "prefere courir le matin"
    assert mx.normalize("!!!") == ""
