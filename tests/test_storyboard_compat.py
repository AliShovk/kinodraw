"""Обратная совместимость: старый storyboard без director/scenes продолжает работать."""
import json
from pathlib import Path

from kinodraw.director.validate import validate
from kinodraw.director import build

OLD = {
    'version': 1, 'lang': 'en', 'title': {'en': 'Old project'},
    'narrator': 'narrator',
    'chapters': [
        {'id': 'intro', 'kind': 'intro', 'label': {'en': 'Old project'}, 'title': {'en': ''}},
        {'id': 'agenda', 'kind': 'agenda', 'label': {'en': "What we'll cover"}, 'title': {'en': ''}},
        {'id': 's1', 'kind': 'section', 'label': {'en': 'Part 1'}, 'title': {'en': 'Idea'}},
        {'id': 'outro', 'kind': 'outro', 'label': {'en': 'Wrap-up'}, 'title': {'en': ''}},
    ],
    'beats': [
        {'id': 'b001', 'chapter': 'intro', 'kind': 'title', 'display': {'en': 'Old project'},
         'spoken': {'en': 'Old project'}, 'visuals': [], 'music': True},
        {'id': 'b002', 'chapter': 'agenda', 'kind': 'agenda', 'display': {'en': 'What we will cover.'},
         'spoken': {'en': 'What we will cover.'}, 'visuals': [], 'music': True},
        {'id': 'b003', 'chapter': 's1', 'kind': 'narration', 'display': {'en': 'A short idea.'},
         'spoken': {'en': 'A short idea.'}, 'music': True,
         'visuals': [{'id': 'b003v0', 'type': 'cluster', 'items': [{'doodle': 'robot'}]}]},
        {'id': 'b004', 'chapter': 'outro', 'kind': 'closing', 'display': {'en': 'Thanks for watching!'},
         'spoken': {'en': 'Thanks for watching!'}, 'visuals': [], 'music': True},
    ],
}


def test_old_storyboard_still_validates():
    res = validate(OLD, None)
    assert res['ok'], res['errors']


def test_old_storyboard_has_no_new_keys_but_renders_shape():
    assert 'director' not in OLD and 'scenes' not in OLD
    b = build.storyboard_from_article('Text about a tool. It works locally.', title='New', duration=30)
    assert 'director' in b and 'scenes' in b
    # оба проходят один и тот же валидатор
    assert validate(b, None)['ok']


def test_new_fields_are_optional_for_the_engine():
    # движок читает только beats/chapters, поэтому лишние поля не мешают
    board = json.loads(json.dumps(OLD))
    board['director'] = {'version': 2, 'concept': 'editorial'}
    assert validate(board, None)['ok']
