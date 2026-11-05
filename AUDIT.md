# AUDIT — KinoDraw 2.0 (AI Video Director)

Дата: 05.11.2026. Базовая точка: ветка `feature/ai-video-director` от коммита
`97bec4abec2a0ab55cab9cc82ed1232370ae1ee6` (upstream `edwardaiwang-svg/kinodraw`).
Резервная копия: `/root/backups/kinodraw-pre2.0-20261105-1200.tar.gz` (325 МБ, без `.venv`).

Аудит сделан по коду, а не по README: все утверждения ниже проверены чтением
исходников и запуском (`python -c`, `pytest`, рендер стилл-кадров).

## 1. Как сейчас устроен конвейер

```
ingest.py → script.py → director/rules.py (offline) или director/llm/* (сеть)
          → validate.py → storyboard.json → voice.py → timeline.py
          → engine/render.py → package.py
```

- `ingest.py`: разбор `.txt/.md/.docx`, определение языка (`detect_lang`), секции по заголовкам.
- `script.py`: жёсткий скелет раскадровки — титул, агенда, на каждую секцию
  `opener → narration… → take`, финал. Это первая и главная причина однообразия:
  **структура ролика задана кодом, а не содержанием**. Никакой режиссуры на этом уровне нет.
- `director/rules.py`: офлайн-режиссёр уровня **бита**: подбирает дудлы к словам,
  иногда строит `bars/flow/split/timeline` по числам и перечислениям. Он не решает,
  какой будет ролик: он заполняет уже готовую сетку.
- `director/llm/schema.py`: JSON-схема для LLM тоже уровневая — `cluster`, `stat`,
  `quote`, `glossary`, `bars`, `grid100`, `timeline`, `flow`, `split`. Это выбор
  картинки внутри бита, а не планирование сцен.
- `validate.py`: проверяет структуру, паритет display/spoken, триггеры, дудлы.
- `timeline.py`: расставляет биты на таймлайне, считает паузы, главы, субтитры.
- `engine/render.py`: камера по бесконечной ленте бумаги, режимы board/zoom/agenda/stock.
- `package.py`: мукс, главы, QA, обложка, файлы.

## 2. Реализованные сцены (проверено по реестрам)

Полноэкранные страницы (`BUILDERS`):

| Тип | Файл |
|---|---|
| `bars`, `coins`, `grid100` | `engine/pages_quant.py` |
| `lanes`, `range`, `calendar` | `engine/pages_time.py` |
| `dial`, `flow` (chain/loop), `split` | `engine/pages_logic.py` |
| `ladder`, `table`, `levels`, `zones` | `engine/scenes.py` (`PAGE_BUILDERS`) |

Слотовые визуалы (`SLOT_BUILDERS`, `engine/scenes.py`): `cluster`, `quote`,
`glossary`, `stat`.

Служебные сцены (`SCENES` в `engine/auto_scenes.py`): `title_board`, `agenda`,
`section_opener`, `take_note`, `end_card`, `credit` — по одной реализации на
landscape и portrait.

Чего из ТЗ **нет в коде**: `hero_reveal`, `product_showcase`, `interface_demo`,
`browser_window`, `phone_mockup`, `feature_explosion`, `data_flow`,
`before_after`, `zoom_detail`, `spotlight`, `image_gallery`, `pros_cons`,
`rating_scene`, `final_verdict`. Часть из них достижима комбинацией примитивов,
но отдельных билдеров и типов в схеме нет.

## 3. Подтверждённые причины однообразия

1. **Скелет один на все ролики.** `script.py` строит одинаковую последовательность
   глав и битов; режиссёр не может её изменить — только наполнить.
2. **Одна колонка композиции.** `engine/geometry.py` задаёт фиксированные полосы
   (`title_band`, `board_band`, `caption_band`, `rail`) — все сцены верстаются в них.
3. **Фиксированные константы вёрстки.** `CARD_STRIP = .3`, `DECOR_DUR = 1.0`
   (`auto_scenes.py`), `PAUSE_MAX` (`render.py`), размеры стикеров и заголовков.
4. **Нет параметров композиции в storyboard.** Бит содержит только `visuals`
   (`type` + поля); нет `composition`, `layers`, `animation`, `camera`.
5. **Нет истории проектов.** Никто не сравнивает новый ролик с предыдущими:
   в `pipeline.py` нет ни чтения прошлых раскадровок, ни метрик разнообразия.
6. **Палитра ≠ режиссура.** `styles/registry.json` переключает «look» (цвет,
   фактура), но раскладка и порядок сцен остаются прежними.
7. **LLM ограничен схемой.** `director/llm/schema.py` не позволяет модели
   предложить сцену, которой нет в enum, — даже если она осмысленна.
8. **Русский язык не реализован системно.** `detect_lang` знает только `en/zh/es`;
   `script.TEXT` не имеет `ru`; `numbers.normalize` умеет `en/zh/es`; в
   `director/rules.py` и `annotate.py` десятки веток `lang == 'es'` без `ru`.
   Мы добавили русскую вертикаль патчами (см. коммит `bb56e1e`), но это не
   системная поддержка: числа, валюты, проценты и даты в русском тексте
   обрабатываются как английские.

## 4. Что есть для AI-режиссёра

- `director/llm/providers.py` — провайдеры (OpenAI, Anthropic, compatible, Cloud).
- `director/llm/director.py` — пошаговый вызов на секцию + проверка ответа.
- `director/validate.py` — детерминированная валидация.
- `engine/motion.py` — примитивы движения (появление, ход руки, камера).

Ограничение: всё это работает на уровне «какие картинки в бите», а не «какие
сцены и в каком порядке». Поэтому LLM-режиссура не влияет на структуру ролика.

## 5. План изменений (этапы 2–6)

1. `director/ai.py` — Content Analyzer + AI Video Director:
   - анализ статьи на смысловые блоки с ролями (`hook`, `problem`, `feature`,
     `comparison`, `statistics`, `workflow`, `use_case`, `advantage`,
     `disadvantage`, `conclusion`, `CTA`) и `importance`;
   - выбор концепции (`editorial`, `tech_explainer`, `product_showcase`,
     `digital_lab`, `minimal`, `kinetic_type`, `documentary`, `motion_infographic`);
   - построение плана сцен из реализованных типов с параметрами
     `composition`/`animation`;
   - детерминированный fallback без LLM.
2. `engine/pages_media.py` — новые типы сцен на существующих примитивах:
   `browser_window`, `phone_mockup`, `image_gallery`, `before_after`,
   `hero_reveal`, `product_showcase`, `spotlight`, `pros_cons`, `rating_scene`,
   `final_verdict`, `data_flow` (flow с движением по стрелкам), `feature_explosion`.
3. `director/originality.py` — отпечатки прошлых раскадровок и метрики
   (`scene_variety`, `composition_variety`, `motion_variety`, `structure_variety`);
   пересборка плана при сходстве выше порога.
4. Расширение схемы storyboard: необязательный блок `director` и `scenes`
   с обратной совместимостью (старые файлы читаются как раньше).
5. Русский язык: `ru` в `detect_lang`, `script.TEXT`, `sentences`, `numbers`
   (проценты, рубли, даты), подписи и субтитры.
6. Тесты: `tests/test_ai_director.py`, `tests/test_originality.py`,
   `tests/test_storyboard_compat.py`; три демо-ролика с разной режиссурой.

## 6. Риски

- Движок рисует «одной рукой» и пропускает то, что не успевает; новые сцены
  должны укладываться в бюджет времени бита, иначе будут выпадать.
- Схема `storyboard.json` используется валидатором и Studio; новые поля — только
  опциональные, старые проекты не трогаем.
- LLM-провайдеры могут быть недоступны: режиссёр обязан работать офлайн.
