#!/usr/bin/env python3
"""Собирает storyboard.json для KinoDraw из простого русского сценария.

Зачем: планировщик KinoDraw англоязычный, на русском тексте он не находит
дудлы и вставляет английские служебные фразы. Здесь мы задаём раскадровку
сами: главы, реплики, картинки и подписи к ним.

Запуск:
    python3 ru_build.py spec.json /path/to/project
"""
import json
import sys
from pathlib import Path


def txt(s):
    return {'en': s}


def build(spec):
    chapters, beats = [], []
    chapters.append({'id': 'intro', 'kind': 'intro', 'label': txt(spec['title']), 'title': txt('')})
    short = spec.get('mode') == 'short'
    if spec.get('mode') != 'short':
        chapters.append({'id': 'agenda', 'kind': 'agenda', 'label': txt('Что разберём'), 'title': txt('')})
    for i, ch in enumerate(spec['chapters'], 1):
        chapters.append({'id': f's{i}', 'kind': 'section',
                         'label': txt('') if spec.get('mode') == 'short' else txt(f'Часть {i}'),
                         'title': txt(ch['title']), 'number': i, 'color': ch.get('color') or ['orange','blue','green','purple','red','teal'][(i-1) % 6]})
    chapters.append({'id': 'outro', 'kind': 'outro', 'label': txt('Итог'), 'title': txt('')})

    n = 0

    def nid():
        nonlocal n
        n += 1
        return f'b{n:03d}'

    def cluster(bid, items, k=0):
        return {'id': f'{bid}v{k}', 'type': 'cluster',
                'items': [{'doodle': d['id'], **({'label': txt(d['label'])} if d.get('label') else {}),
                           **({'trigger': txt(d['trigger'])} if d.get('trigger') else {})} for d in items],
                'relation': spec.get('relation', 'none')}

    # титул
    bid = nid()
    beats.append({'id': bid, 'chapter': 'intro', 'kind': 'title',
                  'display': txt(spec['title']), 'spoken': txt(spec.get('hook') or spec['title']),
                  'visuals': [cluster(bid, spec.get('title_visuals', []))] if spec.get('title_visuals') else [],
                  'music': True})
    # агенда (только в длинном формате)
    for i, ch in enumerate([] if spec.get('mode') == 'short' else spec['chapters']):
        bid = nid()
        beats.append({'id': bid, 'chapter': 'agenda', 'kind': 'agenda',
                      'display': txt(f'{ch["title"]}.'), 'spoken': txt(f'{ch["title"]}.'),
                      'visuals': [], 'music': True})
    # главы
    for i, ch in enumerate(spec['chapters'], 1):
        bid = nid()
        if spec.get('mode') != 'short':
            beats.append({'id': bid, 'chapter': f's{i}', 'kind': 'opener',
                          'display': txt(f'Часть {i}: {ch["title"]}'), 'spoken': txt(f'Часть {i}. {ch["title"]}.'),
                          'visuals': [], 'music': True})
            bid = nid()
        for k, block in enumerate(ch['blocks']):
            bid = nid()
            vis = []
            for j, v in enumerate(block.get('visuals') or []):
                if v.get('type') and v['type'] != 'cluster':      # схема/график — как есть
                    vis.append({**v, 'id': f'{bid}v{j}'})
                elif v:
                    vis.append(cluster(bid, [v], j) if 'id' in v and 'items' not in v else cluster(bid, v.get('items') or [], j))
            if spec.get('robot'):
                vis.append({'id': f'{bid}vR', 'type': 'cluster',
                            'items': [{'doodle': 'robot'}], 'size': 'margin'})
            beats.append({'id': bid, 'chapter': f's{i}', 'kind': 'narration',
                          'display': txt(block['text']),
                          'spoken': txt(block['text']),
                          'visuals': vis, 'music': True})
        bid = nid()
        if spec.get('no_take'):
            continue
        if spec.get('mode') == 'short':
            stat = {'id': f'{bid}v0', 'type': 'stat',
                    'value': txt(ch.get('take_value') or ch['take']),
                    'label': txt(ch.get('take_label') or ' ')}
            beats.append({'id': bid, 'chapter': f's{i}', 'kind': 'narration',
                          'display': txt(ch['take']), 'spoken': txt(ch['take']),
                          'visuals': [stat], 'music': True})
        else:
            beats.append({'id': bid, 'chapter': f's{i}', 'kind': 'take',
                          'display': txt(f'Главное: {ch["take"]}'), 'spoken': txt(f'Главное. {ch["take"]}'),
                          'take': {'headline': txt(ch['take'])},
                          'visuals': [], 'music': True})
    # финал
    bid = nid()
    beats.append({'id': bid, 'chapter': 'outro', 'kind': 'closing',
                  'display': txt(spec.get('closing', 'Спасибо за просмотр!')),
                  'spoken': txt(spec.get('closing', 'Спасибо за просмотр!')),
                  'visuals': [cluster(bid, spec.get('closing_visuals', []))] if spec.get('closing_visuals') else [],
                  'music': True})

    out = {'version': 1, 'lang': 'en', 'title': txt(spec['title']), 'subtitle': txt(spec['subtitle']) if spec.get('subtitle') else None, 'narrator': spec.get('narrator', 'narrator'),
            'ui': {'en': {'agenda': 'Что разберём', 'takeaway': 'ГЛАВНОЕ', 'sign': '',
                          'thanks': spec.get('closing', 'Спасибо за просмотр')}},
            'chapters': chapters, 'beats': beats}
    if spec.get('logo'):
        out['logo'] = spec['logo']
    return out


if __name__ == '__main__':
    spec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    out = Path(sys.argv[2]) / 'storyboard.json'
    out.write_text(json.dumps(build(spec), ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'storyboard: {out} — {len(build(spec)["beats"])} битов')
