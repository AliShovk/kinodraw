"""Originality Engine: fingerprints, similarity, variety, revision."""
import json
from pathlib import Path

from kinodraw.director import ai


def plan_with(concept, structure, types, layouts=None, motions=None):
    scenes = []
    for i, t in enumerate(types):
        scenes.append({'id': f'scene_{i + 1:03d}', 'role': 'explanation', 'type': t,
                       'duration': 6.0, 'text': 'x',
                       'composition': {'layout': (layouts or ['center_focus'] * len(types))[i]},
                       'animation': {'entrance': (motions or ['reveal'] * len(types))[i]}})
    return {'director': {'version': 2, 'concept': concept, 'narrative_structure': structure,
                         'visual_style': concept, 'motion_profile': 'measured'},
            'scenes': scenes}


def test_identical_plans_are_similar():
    a = plan_with('editorial', 'demo_first', ['hero_reveal', 'flow', 'final_verdict'])
    b = plan_with('editorial', 'demo_first', ['hero_reveal', 'flow', 'final_verdict'])
    assert ai.similarity(ai.fingerprint(a), ai.fingerprint(b)) == 1.0


def test_different_plans_score_lower():
    a = plan_with('editorial', 'demo_first', ['hero_reveal', 'flow', 'final_verdict'])
    b = plan_with('minimal', 'walkthrough', ['browser_window', 'pros_cons', 'rating_scene'],
                  ['two_columns'] * 3, ['wipe'] * 3)
    assert ai.similarity(ai.fingerprint(a), ai.fingerprint(b)) < 0.4


def test_variety_counts_pairs():
    a = plan_with('editorial', 'demo_first', ['hero_reveal', 'flow', 'final_verdict'])
    b = plan_with('minimal', 'walkthrough', ['browser_window', 'pros_cons', 'rating_scene'])
    v = ai.variety([a, b])
    assert v['structure_variety'] == 1.0
    assert v['scene_variety'] == 1.0
    assert len(v['pairwise']) == 1


def test_revise_avoids_history():
    art = """Агент умеет думать, но не умеет подключаться к сервисам.
    Разработчик вручную пишет обёртки над API и разбирается с OAuth.
    Сначала вы ставите пакет, затем добавляете сервисы одной командой.
    Готовые инструменты есть для полутора тысяч сервисов.
    Преимущество — скорость: интеграция занимает минуты.
    Итог: быстрый способ связать агента с сервисами."""
    analysis = ai.analyze(art)
    first = ai.plan(analysis, duration=60, concept='editorial', structure='demo_first')
    history = [first]
    revised = ai.revise(analysis, first, history, duration=60)
    sim = ai.similarity(ai.fingerprint(revised), ai.fingerprint(first))
    assert sim < 0.75
    assert revised['director']['concept'] != first['director']['concept']
