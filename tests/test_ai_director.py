"""AI Video Director: analysis, planning, originality (KinoDraw 2.0)."""
import json
from pathlib import Path

from kinodraw.director import ai, build

ART_CHAT = """Open WebUI — интерфейс как у ChatGPT, только на вашем сервере.
Команда платит за подписки, а история уходит в облако — это проблема.
Сервис поддерживает локальные модели через Ollama и облачные через API.
Установка занимает десять минут: одна команда Docker поднимает контейнер.
Данные не уходят в облако, доступ закрыт паролем. Без сервера не обойтись.
В итоге это бесплатная замена облачному чату для команды."""

ART_IMAGE = """Генераторы картинок считают каждую картинку и берут деньги за запрос.
Модель рисует локально и поддерживает текстовые запросы и референсы.
Пример: кадр 768 на 512 считается две минуты сорок секунд на восьми ядрах.
Сравнение с облаком: качество сопоставимо, но данные остаются у вас.
Ограничение — лицензия разрешает только некоммерческое использование.
Вывод: хороший инструмент для эскизов."""

ART_AUTO = """Агент умеет думать, но не умеет подключаться к сервисам.
Разработчик вручную пишет обёртки над API и разбирается с OAuth.
Сначала вы ставите пакет, затем добавляете сервисы одной командой.
Готовые инструменты есть для полутора тысяч сервисов.
Преимущество — скорость: интеграция занимает минуты.
Недостаток — зависимость от чужого облака.
Итог: быстрый способ связать агента с сервисами."""


def board(text, history=None, title='Обзор'):
    return build.storyboard_from_article(text, title=title, duration=60, history=history or [])


def test_analyze_marks_roles_and_numbers():
    a = ai.analyze(ART_IMAGE)
    roles = {b['role'] for b in a['blocks']}
    assert 'hook' in roles
    assert any(b['role'] in ('limitation', 'disadvantage') for b in a['blocks'])
    assert a['category'] == 'image'
    assert all(0.2 <= b['importance'] <= 0.98 for b in a['blocks'])


def test_plan_has_scenes_and_conclusion_last():
    p = ai.plan(ai.analyze(ART_CHAT), duration=60)
    assert 4 <= len(p['scenes']) <= 8
    assert p['scenes'][-1]['role'] == 'conclusion'
    assert p['director']['concept'] in ai.CONCEPTS
    assert all(s['type'] for s in p['scenes'])
    # нет двух одинаковых тяжёлых сцен подряд
    types = [s['type'] for s in p['scenes']]
    assert all(a != b for a, b in zip(types, types[1:]))


def test_plan_is_deterministic():
    a = ai.analyze(ART_AUTO)
    p1 = ai.plan(a, duration=55)
    p2 = ai.plan(a, duration=55)
    assert [s['type'] for s in p1['scenes']] == [s['type'] for s in p2['scenes']]


def test_variety_grows_with_history():
    hist = []
    for text in (ART_CHAT, ART_IMAGE, ART_AUTO):
        b = board(text, hist)
        hist.append(b)
    v = ai.variety(hist)
    assert v['structure_variety'] > 0.5
    assert all(p['sim'] < 0.75 for p in v['pairwise'])


def test_storyboard_is_renderable_shape():
    b = board(ART_CHAT)
    assert b['beats'][0]['kind'] == 'title'
    assert b['beats'][-1]['kind'] == 'closing'
    for beat in b['beats']:
        assert 'display' in beat and 'spoken' in beat
        assert isinstance(beat.get('visuals'), list)
    # параметры режиссуры необязательны для движка
    assert b['director']['version'] == 2
    assert b['scenes'][0]['duration'] > 0
