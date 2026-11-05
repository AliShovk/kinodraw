"""Русский язык: определение, числа, валидатор."""
from kinodraw.ingest import detect_lang
from kinodraw.numbers import normalize
from kinodraw.director.validate import validate
from kinodraw.director import build


def test_detect_russian():
    assert detect_lang('Это русский текст про локальные модели и агентов.') == 'ru'
    assert detect_lang('This is an English sentence about agents.') == 'en'


def test_russian_numbers():
    assert 'двадцать пять процентов' in normalize('25%', 'ru').spoken
    assert 'рублей' in normalize('1 500 ₽', 'ru').spoken
    assert 'гигабайт' in normalize('12 ГБ', 'ru').spoken


def test_russian_storyboard_passes_validator():
    art = ('Сервис работает локально и поддерживает любые модели. '
           'Установка занимает десять минут. '
           'Данные не уходят в облако, доступ закрыт паролем. '
           'В итоге это бесплатная замена облачному чату.')
    b = build.storyboard_from_article(art, title='Обзор', duration=40, language='ru')
    res = validate(b, None)
    assert res['ok'], res['errors']


def test_russian_beats_have_both_languages():
    b = build.storyboard_from_article('Простой текст про инструмент. Он работает локально.',
                                      title='Тест', duration=30, language='ru')
    for beat in b['beats']:
        assert 'ru' in beat['display'] and 'en' in beat['display']
