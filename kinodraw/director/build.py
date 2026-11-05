"""Article → storyboard 2.0 (director block + beats the renderer understands)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import ai

DOODLE_BY_CATEGORY = {
    'chat': ['speech_bubbles', 'robot', 'lightbulb_idea'],
    'image': ['lightbulb_idea', 'cloud_upload', 'scroll'],
    'automation': ['people_network', 'key_lock', 'database'],
    'code': ['code_window', 'laptop', 'memory_chip'],
    'data': ['database', 'chart_up', 'scroll'],
    'general': ['lightbulb_idea', 'robot', 'chart_up'],
}
DOODLES = ['lightbulb_idea', 'robot', 'database', 'code_window', 'chart_up', 'people_network',
           'key_lock', 'memory_chip', 'scroll', 'speech_bubbles', 'laptop', 'bullseye']
PCT = re.compile(r'(\d[\d\s.,]*)\s*%')


def _txt(s: str) -> dict:
    return {'en': s, 'ru': s}


def _doodles(category: str, n: int = 3) -> list[str]:
    base = DOODLE_BY_CATEGORY.get(category, DOODLE_BY_CATEGORY['general'])
    out = []
    for i in range(n):
        out.append(base[i % len(base)] if i < len(base) else DOODLES[i % len(DOODLES)])
    return out


def _bars_from_text(text: str, category: str):
    nums = PCT.findall(text)
    if len(nums) < 2:
        return None
    rows = []
    for i, n in enumerate(nums[:4]):
        try:
            val = float(n.replace(' ', '').replace(',', '.'))
        except ValueError:
            continue
        rows.append({'label': _txt(f'показатель {i + 1}'), 'value': val, 'display': _txt(f'{n}%')})
    return {'title': _txt('цифры из обзора'), 'rows': rows} if len(rows) >= 2 else None


def visual_for(scene: dict, analysis: dict, text: str) -> dict | None:
    t = scene['type']
    cat = analysis.get('category', 'general')
    d = _doodles(cat, 3)
    if t == 'hero_reveal':
        return {'type': 'hero_reveal', 'caption': _txt(analysis.get('title') or ''), 'doodle': d[0]}
    if t == 'feature_explosion':
        return {'type': 'feature_explosion', 'doodle': d[0],
                'features': [_txt(x) for x in _features(analysis)[:5]]}
    if t == 'browser_window':
        return {'type': 'browser_window', 'doodle': d[0], 'url': 'qantcore.space',
                'caption': _txt(_short(text))}
    if t == 'product_showcase':
        return {'type': 'product_showcase', 'doodle': d[0],
                'callouts': [_txt(x) for x in _features(analysis)[:3]]}
    if t == 'phone_mockup':
        return {'type': 'phone_mockup', 'doodle': d[0], 'labels': [_txt(_short(text))]}
    if t == 'image_gallery':
        return {'type': 'image_gallery', 'images': [
            {'image': '', 'doodle': d[i], 'caption': _txt(_short(text))} for i in range(3)]}
    if t == 'before_after':
        return {'type': 'before_after',
                'before': {'doodle': d[0], 'label': _txt('было')},
                'after': {'doodle': d[1], 'label': _txt('стало')}}
    if t in ('flow', 'data_flow'):
        return {'type': 'flow', 'layout': 'chain', 'title': _txt('как это работает'),
                'nodes': [{'id': str(i), 'doodle': d[i], 'label': _txt(_short(x, 3))}
                          for i, x in enumerate(_steps(text)[:3])],
                'edges': [{'from': '0', 'to': '1'}, {'from': '1', 'to': '2'}]}
    if t == 'bars':
        b = _bars_from_text(text, cat)
        return {'type': 'bars', **b} if b else {'type': 'cluster',
                                                'items': [{'doodle': d[0], 'label': _txt(_short(text))}]}
    if t == 'split':
        return {'type': 'split', 'left': {'who': _txt('так'), 'text': _txt(_short(text, 5)), 'doodle': d[0]},
                'right': {'who': _txt('иначе'), 'text': _txt('без этого'), 'doodle': d[1]}}
    if t == 'pros_cons':
        return {'type': 'pros_cons',
                'pros': [_txt(x) for x in _features(analysis)[:3]] or [_txt('работает')],
                'cons': [_txt(x) for x in analysis.get('limitations', [])[:3]] or [_txt('ограничения')]}
    if t == 'rating_scene':
        return {'type': 'rating_scene', 'score': '4,5', 'label': _txt('оценка Qantcore')}
    if t == 'final_verdict':
        return {'type': 'final_verdict', 'score': '4,5', 'title': _txt(analysis.get('title') or ''),
                'text': _txt(_short(text, 12))}
    if t == 'lanes':
        return {'type': 'flow', 'layout': 'chain', 'title': _txt('этапы'),
                'nodes': [{'id': str(i), 'doodle': d[i], 'label': _txt(_short(x, 2))}
                          for i, x in enumerate(_steps(text)[:3])],
                'edges': [{'from': '0', 'to': '1'}, {'from': '1', 'to': '2'}]}
    if t == 'stat':
        return {'type': 'stat', 'value': _txt(_number(text) or '1'), 'label': _txt('из обзора')}
    return {'type': 'cluster', 'items': [{'doodle': d[i], 'label': _txt(_short(text, 3))}
                                         for i in range(min(3, len(d)))]}


def _features(analysis: dict) -> list[str]:
    out = []
    for b in analysis['blocks']:
        if b['role'] in ('feature', 'advantage'):
            out.append(_short(analysis['texts'][analysis['blocks'].index(b)], 6))
    return out[:5]


def _steps(text: str) -> list[str]:
    parts = re.split(r'(?:,\s*|;\s*|\s+затем\s+|\s+потом\s+)', text)
    parts = [p.strip(' .') for p in parts if len(p.strip()) > 3]
    if len(parts) >= 3:
        return parts[:3]
    words = text.split()
    k = max(1, len(words) // 3)
    return [' '.join(words[:k]), ' '.join(words[k:2 * k]), ' '.join(words[2 * k:])]


def _short(text: str, n: int = 5) -> str:
    words = re.sub(r'\s+', ' ', text).strip().split()
    return ' '.join(words[:n]) + ('…' if len(words) > n else '')


def _number(text: str) -> str | None:
    m = re.search(r'\d[\d\s.,]*(?:%|₽|млн|млрд|трлн|ГБ|ТБ)?', text)
    return m.group(0).strip() if m else None


def storyboard_from_article(article: str, *, title: str = '', duration: float = 55,
                            aspect: str = '9:16', project_dir=None, history=None,
                            concept=None, structure=None, language: str = 'ru') -> dict:
    """Full storyboard: director block + beats, ready for voice/render."""
    analysis = ai.analyze(article, title)
    history = history if history is not None else (ai.load_history(project_dir) if project_dir else [])
    p = ai.plan(analysis, duration=duration, aspect=aspect, history=history,
                concept=concept, structure=structure)
    if history:
        worst = max((ai.similarity(ai.fingerprint(p), ai.fingerprint(h)) for h in history), default=0.0)
        if worst >= 0.75:
            p = ai.revise(analysis, p, history, duration=duration, aspect=aspect)
    chapters = [{'id': 'intro', 'kind': 'intro', 'label': _txt(title or analysis.get('title') or ''),
                 'title': _txt('')},
                {'id': 'agenda', 'kind': 'agenda', 'label': _txt('Что разберём'), 'title': _txt('')},
                {'id': 's1', 'kind': 'section', 'label': _txt(''), 'title': _txt('')},
                {'id': 'outro', 'kind': 'outro', 'label': _txt('Итог'), 'title': _txt('')}]
    beats = []
    scenes = p['scenes']
    head = scenes[0] if scenes and scenes[0]['role'] == 'hook' else None
    beats.append({'id': 'b001', 'chapter': 'intro', 'kind': 'title',
                  'display': _txt(title or analysis.get('title') or ''),
                  'spoken': _txt(analysis['texts'][0] if analysis['texts'] else title),
                  'visuals': [{'id': 'b001v0', 'type': 'hero_reveal',
                               'caption': _txt(title or analysis.get('title') or ''),
                               'doodle': 'lightbulb_idea'}],
                  'music': True})
    beats.append({'id': 'b002', 'chapter': 'agenda', 'kind': 'agenda',
                  'display': _txt('Что разберём.'), 'spoken': _txt('Что разберём.'),
                  'visuals': [], 'music': True})
    n = 2
    for sc in (scenes[1:] if head else scenes):
        n += 1
        vis = visual_for(sc, analysis, sc['text'])
        beats.append({'id': f'b{n:03d}', 'chapter': 's1', 'kind': 'narration',
                      'display': _txt(sc['text']), 'spoken': _txt(sc['text']),
                      'visuals': [{'id': f'b{n:03d}v0', **vis}] if vis else [], 'music': True})
        first = False
    n += 1
    beats.append({'id': f'b{n:03d}', 'chapter': 'outro', 'kind': 'closing',
                  'display': _txt('Подробнее на сайте Qantcore.Space.'),
                  'spoken': _txt('Подробнее на сайте Qantcore.Space.'),
                  'visuals': [], 'music': True})
    return {
        'version': 1, 'lang': language, 'title': _txt(title or analysis.get('title') or ''),
        'narrator': 'narrator',
        'ui': {'en': {'agenda': 'Что разберём', 'takeaway': 'ГЛАВНОЕ', 'sign': '',
                      'thanks': 'Подробнее на сайте'}},
        'director': p['director'],
        'scenes': p['scenes'],
        'chapters': chapters, 'beats': beats,
        'analysis': analysis,
    }


def write_storyboard(article: str, project_dir, **kw) -> dict:
    board = storyboard_from_article(article, project_dir=project_dir, **kw)
    Path(project_dir, 'storyboard.json').write_text(
        json.dumps(board, ensure_ascii=False, indent=1), encoding='utf-8')
    return board
