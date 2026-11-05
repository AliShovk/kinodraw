# FINAL REPORT — KinoDraw 2.0 (AI Video Director)

Дата: 05.11.2026. Ветка: `feature/ai-video-director`. База: `97bec4a` (upstream
`edwardaiwang-svg/kinodraw`). Резервная копия до изменений:
`/root/backups/kinodraw-pre2.0-20261105-1200.tar.gz`.

## 1. Что обнаружено в исходной архитектуре

Полный разбор — в `AUDIT.md`. Коротко, с подтверждением кодом:

- `script.py` задаёт единственный скелет ролика: титул → агенда → секции
  (`opener → narration → take`) → финал. Режиссёр мог наполнять биты, но не
  менять структуру.
- `director/rules.py` и `director/llm/schema.py` работают на уровне бита:
  выбирают дудлы и один из десяти визуалов. Сцен как единиц планирования нет.
- `engine/geometry.py` фиксирует полосы (`title_band`, `board_band`, `caption_band`),
  `CARD_STRIP`, `DECOR_DUR`, `PAUSE_MAX` — композиция одна для всех роликов.
- В `storyboard.json` нет ни `director`, ни `scenes`, ни `composition/animation`.
- Нет истории проектов и метрик сходства: каждый ролик планировался с нуля.
- Русский язык отсутствовал системно: `en/zh/es` в `detect_lang`, `script.TEXT`,
  `numbers.normalize`, `voice.CLAUSE`, `package.mux`, `UI_DEFAULTS`, `CREDIT_LINE`.

## 2. Какие причины однообразия подтверждены

1. Жёсткий скелет `script.py` — подтверждено чтением и запуском.
2. Единая геометрия и константы вёрстки — подтверждено `engine/geometry.py`.
3. Отсутствие сцен верхнего уровня — подтверждено схемой LLM-директора.
4. Отсутствие истории/оригинальности — подтверждено `pipeline.py` (нет чтения
   прошлых раскадровок).
5. Стиль менял палитру, но не режиссуру — `styles/registry.json`.

## 3. Что добавлено

| Модуль | Назначение |
|---|---|
| `kinodraw/director/ai.py` | Content Analyzer (роли, важность, цифры), выбор концепции и структуры, планирование сцен, fingerprint/сходство/вариативность, `revise()` |
| `kinodraw/director/build.py` | статья → `storyboard.json` 2.0: блок `director` + `scenes` + биты, совместимые с движком |
| `kinodraw/engine/pages_media.py` | 12 новых типов сцен: `hero_reveal`, `product_showcase`, `browser_window`, `phone_mockup`, `before_after`, `image_gallery`, `feature_explosion`, `spotlight`, `pros_cons`, `rating_scene`, `final_verdict`, `data_flow` |
| CLI `kinodraw plan <article> <project>` | планирование и запись раскадровки 2.0 |

## 4. Изменённые существующие модули

- `director/validate.py`: разрешены `lang='ru'` и новые типы сцен.
- `engine/scenes.py`: `pages_media` подключён к `PAGE_BUILDERS`.
- `engine/auto_scenes.py`: `UI_DEFAULTS['ru']`, `CREDIT_LINE['ru']`.
- `engine/ink.py`: `ru` использует латинский рукописный шрифт (кириллица в нём есть).
- `engine/pages_quant.py`, `engine/scenes.py`: русские подписи в существующих страницах.
- `ingest.py`: определение русского по доле кириллицы.
- `script.py`: `TEXT['ru']`, подсчёт слов для `ru`.
- `numbers.py`: `normalize_ru` — проценты, рубли, доллары, ГБ/ТБ, склонения.
- `voice.py`: `CLAUSE['ru']`, запись `LANGS['ru']` (Kokoro русского не умеет — читает сервер).
- `package.py`: ISO-код субтитров `rus`.
- `cli.py`: команда `plan`.

## 5. Как работает AI Video Director

1. `ai.analyze()` режет статью на смысловые блоки, присваивает роль
   (`hook/problem/feature/comparison/statistics/workflow/limitation/conclusion/CTA`…),
   важность и найденные числа. Работает офлайн, без сети.
2. `ai._structure()` выбирает нарратив по категории и истории: `problem_solution`,
   `demo_first`, `walkthrough`, `comparison_study`, `case_story`.
3. `ai._order_blocks()` строит порядок: хук первым, вывод последним, ограничения
   ближе к концу; для `walkthrough` сохраняется хронология статьи.
4. `ai.plan()` назначает каждой сцене тип из `SCENE_FOR[role]`, следит, чтобы
   тяжёлые типы не повторялись, считает длительность из доли слов и пишет
   `composition`, `animation`, `duration`, `text`.
5. `build.storyboard_from_article()` превращает план в биты движка: титул, агенда,
   наррация (по сцене на бит), финал; `director`/`scenes` — опциональные поля.

LLM-провайдеры не подключались в этом этапе: директор полностью детерминированный.
Существующий `director/llm/*` не изменялся и продолжает работать для выбора дудлов.

## 6. Originality Engine

- `fingerprint()` — концепция, структура, типы сцен, раскладки, входные анимации.
- `similarity()` — среднее из: совпадение концепции, совпадение структуры,
  Jaccard биграмм типов, Jaccard раскладок, Jaccard анимаций.
- `variety()` — те же метрики по всем парам роликов.
- `revise()` — если сходство с историей ≥ 0.75, план пересобирается с другой
  концепцией/структурой (до 6 попыток), выбирается самый далёкий вариант.
- `load_history()` читает `director`-блоки прошлых `storyboard.json` в каталоге проектов.

## 7. Русский язык

Сделано: определение языка, `TEXT['ru']`, числа и склонения (25% → «двадцать пять
процентов», 1 500 ₽ → «одна тысяча пятьсот рублей», 12 ГБ → «двенадцать гигабайт»),
русские подписи UI и кредита, ISO `rus`, шрифты с кириллицей, субтитры.

Не сделано: собственный русский голос Kokoro (используется внешний сервер Silero),
проверка произношения аббревиатур и названий продуктов (например, «GLM», «MoE»)
остаётся на стороне TTS-сервера.

## 8. Тесты

`pytest` — 16 тестов, все зелёные:

- `tests/test_ai_director.py` — роли, детерминизм, состав сцен, вывод последним,
  отсутствие повторов типов, форма раскадровки.
- `tests/test_originality.py` — одинаковые планы = 1.0, разные < 0.4, `variety`,
  `revise()` уводит от истории.
- `tests/test_storyboard_compat.py` — старый `storyboard.json` без `director/scenes`
  проходит тот же валидатор; новые поля необязательны.
- `tests/test_russian.py` — определение языка, числа, валидация русской раскадровки.

## 9. Тестовые ролики

| Ролик | Концепция | Структура | Порядок сцен |
|---|---|---|---|
| A — чат (Open WebUI) | `tech_explainer` | `problem_solution` | hero → before_after → feature_explosion → product_showcase → browser_window → flow → final_verdict |
| B — генератор картинок | `product_showcase` | `demo_first` | hero → feature_explosion → browser_window → before_after → product_showcase → flow → final_verdict |
| C — автоматизация (Composio) | `motion_infographic` | `walkthrough` | hero → before_after → browser_window → feature_explosion → flow → data_flow → final_verdict |

Метрики (`ai.variety`): `structure_variety = 1.0`, попарное сходство 0.36–0.42
(порог пересборки — 0.75). Видео: `/root/kd2/video-a-chat.mp4`,
`video-b-image.mp4`, `video-c-auto.mp4` (1080×1920, русский голос).

## 10. Ограничения, которые остались

- Сцены рисуются «одной рукой»; на 6–10 секунд бита часть элементов не успевает
  появиться. Визуально ролики остаются разреженными: это ограничение движка,
  а не плана.
- `finish` падает на построении превью для русского проекта; финальный мукс
  сделан вручную (`silent.mp4` + `mix.wav`), поэтому в тестовых роликах нет
  автоматической обложки и глав.
- `render --workers 2` падает на новых сценах; тесты рендерились с `--workers 1`.
- LLM-режиссура (провайдеры, structured output, повторные попытки) не включена:
  план детерминированный. Существующий LLM-директор дудлов не тронут.
- Скриншоты реальных интерфейсов поддержаны в сценах (`browser_window`,
  `phone_mockup`, `image_gallery`), но автоматического сбора скриншотов нет:
  картинки кладутся в `assets/` проекта вручную.
- Комбинирование сцен в одном бите не реализовано: один бит — одна сцена.

## 11. Файлы и коммиты

Коммиты ветки: `bb56e1e` (база: русская вертикаль), `af4952b` (аудит),
далее — этап 2–6 (директор, сцены, оригинальность, русский, тесты).

Новые файлы: `AUDIT.md`, `FINAL_REPORT.md`, `kinodraw/director/ai.py`,
`kinodraw/director/build.py`, `kinodraw/engine/pages_media.py`,
`tests/test_ai_director.py`, `tests/test_originality.py`,
`tests/test_storyboard_compat.py`, `tests/test_russian.py`.
