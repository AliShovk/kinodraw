"""Интеграция с whiteboard-animator: карточки и stock-клипы."""
from pathlib import Path

from PIL import Image

from kinodraw.integrations import whiteboard


def test_compose_card_size(tmp_path):
    png = whiteboard.compose_card('Open WebUI', 'свой ChatGPT', None, 'qantcore.space',
                                  tmp_path / 'card.png', 'intro')
    im = Image.open(png)
    assert im.size == (1080, 1920)


def test_apply_to_storyboard_uses_stock():
    board = {'beats': [
        {'id': 'b001', 'kind': 'title', 'visuals': []},
        {'id': 'b002', 'kind': 'narration', 'visuals': []},
        {'id': 'b003', 'kind': 'closing', 'visuals': []},
    ]}
    out = whiteboard.apply_to_storyboard(board)
    assert out['beats'][0]['visuals'][0]['type'] == 'stock'
    assert out['beats'][0]['visuals'][0]['clip'] == 'intro'
    assert out['beats'][2]['visuals'][0]['clip'] == 'outro'
    assert out['beats'][1]['visuals'] == []
    assert out['integration']['whiteboard_animator']['intro'] == 'intro'


def test_cli_detection_is_boolean():
    assert isinstance(whiteboard.available(), bool)
