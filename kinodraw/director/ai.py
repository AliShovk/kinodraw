"""AI Video Director: content analysis, scene planning, originality.

Offline by default (deterministic heuristics, no network). If a provider is
configured (`KINODRAW_LLM=openai|anthropic|compatible`), `analyze_with_llm`
asks the model for the same JSON and validates it; any failure falls back to
the heuristics. The director never invents product facts: it only re-uses
sentences from the article and numbers that are present in it.
"""
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field

ROLES = ('hook', 'problem', 'explanation', 'feature', 'demonstration', 'comparison',
         'statistics', 'workflow', 'use_case', 'advantage', 'disadvantage',
         'limitation', 'conclusion', 'CTA')

CONCEPTS = ('editorial', 'tech_explainer', 'product_showcase', 'digital_lab',
            'minimal', 'kinetic_type', 'documentary', 'motion_infographic')

# role -> scene types that can carry it, best first
SCENE_FOR = {
    'hook': ['hero_reveal', 'feature_explosion', 'stat'],
    'problem': ['before_after', 'pros_cons', 'flow', 'split'],
    'explanation': ['browser_window', 'product_showcase', 'flow', 'cluster'],
    'feature': ['feature_explosion', 'product_showcase', 'browser_window', 'cluster'],
    'demonstration': ['browser_window', 'phone_mockup', 'image_gallery', 'product_showcase'],
    'comparison': ['split', 'before_after', 'bars'],
    'statistics': ['bars', 'rating_scene', 'grid100', 'stat'],
    'workflow': ['flow', 'data_flow', 'lanes'],
    'use_case': ['image_gallery', 'browser_window', 'cluster'],
    'advantage': ['pros_cons', 'rating_scene', 'cluster'],
    'disadvantage': ['pros_cons', 'split'],
    'limitation': ['pros_cons', 'spotlight'],
    'conclusion': ['final_verdict', 'rating_scene', 'stat'],
    'CTA': ['final_verdict', 'cluster'],
}

MOTION_FOR = {
    'hook': {'entrance': 'scale_reveal', 'camera': 'push_in', 'emphasis': 'pulse', 'transition': 'match_cut'},
    'problem': {'entrance': 'wipe', 'camera': 'slow_push', 'emphasis': 'hold', 'transition': 'cut'},
    'explanation': {'entrance': 'reveal', 'camera': 'static', 'emphasis': 'none', 'transition': 'pan'},
    'feature': {'entrance': 'sequence', 'camera': 'slow_push', 'emphasis': 'pulse', 'transition': 'cut'},
    'demonstration': {'entrance': 'wipe', 'camera': 'static', 'emphasis': 'spotlight', 'transition': 'cut'},
    'comparison': {'entrance': 'split_reveal', 'camera': 'static', 'emphasis': 'none', 'transition': 'match_cut'},
    'statistics': {'entrance': 'count_up', 'camera': 'push_in', 'emphasis': 'pulse', 'transition': 'cut'},
    'workflow': {'entrance': 'sequential_reveal', 'camera': 'follow', 'emphasis': 'pulse', 'transition': 'pan'},
    'use_case': {'entrance': 'wipe', 'camera': 'static', 'emphasis': 'spotlight', 'transition': 'cut'},
    'advantage': {'entrance': 'sequence', 'camera': 'static', 'emphasis': 'none', 'transition': 'cut'},
    'disadvantage': {'entrance': 'sequence', 'camera': 'static', 'emphasis': 'none', 'transition': 'cut'},
    'limitation': {'entrance': 'wipe', 'camera': 'push_in', 'emphasis': 'spotlight', 'transition': 'cut'},
    'conclusion': {'entrance': 'scale_reveal', 'camera': 'pull_back', 'emphasis': 'hold', 'transition': 'fade'},
    'CTA': {'entrance': 'fade', 'camera': 'static', 'emphasis': 'none', 'transition': 'fade'},
}

NARRATIVES = ('problem_solution', 'demo_first', 'walkthrough', 'comparison_study', 'case_story')

NUM = re.compile(r'\d[\d\s.,]*(?:%|₽|\$|€|млн|млрд|трлн|тыс|ГБ|ТБ|МБ)?')
SENT = re.compile(r'(?<=[.!?])\s+(?=[А-ЯЁA-Z0-9«"(])')

KEY = {
    'problem': ('проблем', 'вручную', 'сложно', 'дорого', 'медленно', 'приходится', 'теря', 'ошиб'),
    'comparison': ('против', 'вместо', 'по сравнению', 'vs', 'лучше', 'хуже', 'отлича'),
    'statistics': ('%', 'процент', 'миллион', 'миллиард', 'трлн', 'звёзд', 'пользовател'),
    'workflow': ('сначала', 'затем', 'потом', 'шаг', 'процесс', 'цепочк', 'поток', 'автоматиз'),
    'use_case': ('например', 'кейс', 'использ', 'сценари', 'примен'),
    'advantage': ('бесплат', 'быстрее', 'проще', 'удобн', 'эконом', 'плюс'),
    'disadvantage': ('минус', 'недостат', 'мешает', 'раздража', 'слабое'),
    'limitation': ('ограничен', 'только', 'не умеет', 'требует', 'нельзя', 'зависит'),
    'conclusion': ('итог', 'вывод', 'в целом', 'стоит ли', 'рекоменд'),
    'CTA': ('попроб', 'скачать', 'ссылк', 'подключ', 'зарегистр'),
    'feature': ('умеет', 'поддерж', 'функци', 'возможност', 'позволя', 'интегр'),
}


@dataclass
class Block:
    text: str
    role: str = 'explanation'
    importance: float = 0.5
    topic: str = ''
    numbers: list = field(default_factory=list)

    def as_dict(self):
        return {'role': self.role, 'importance': round(self.importance, 2), 'topic': self.topic,
                'visual_intent': SCENE_FOR[self.role][0], 'numbers': self.numbers}


def _sentences(text: str) -> list[str]:
    text = re.sub(r'\s+', ' ', text).strip()
    parts = SENT.split(text)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def _classify(sentence: str) -> tuple[str, float]:
    low = sentence.lower()
    best, hits = 'explanation', 0
    for role, keys in KEY.items():
        n = sum(low.count(k) for k in keys)
        if n > hits:
            best, hits = role, n
    if re.search(r'не умеет|нельзя|без .* не|ограничен|только .* (разреш|для)', low):
        best = 'limitation'
    if re.search(r'поддерживает|умеет|позволяет|есть роли', low) and best == 'explanation':
        best = 'feature'
    score = 0.45 + min(.4, .12 * hits)
    if NUM.search(sentence):
        score += .1
    if len(sentence.split()) > 22:
        score -= .05
    return best, max(.2, min(.98, score))


def analyze(article: str, title: str = '') -> dict:
    """Content analysis: blocks with roles, plus the review's key points."""
    article = re.sub(r'^#+\s*', '', article, flags=re.M)
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', article) if p.strip() and not p.strip().startswith('#')]
    sents = []
    for p in paragraphs:
        sents.extend(_sentences(p))
    if not sents:
        sents = [article.strip()[:400]]
    blocks = []
    for i, s in enumerate(sents[:40]):
        role, imp = _classify(s)
        if i == 0:
            role, imp = 'hook', .98
        blocks.append(Block(s, role, imp, topic='', numbers=NUM.findall(s)))
    # the last third is conclusion-ish if nothing else claimed it
    if blocks and not any(b.role == 'conclusion' for b in blocks[-3:]):
        blocks[-1].role = 'conclusion'
    roles = [b.role for b in blocks]
    problem = next((b.text for b in blocks if b.role == 'problem'), '')
    advantage = next((b.text for b in blocks if b.role in ('advantage', 'feature')), '')
    limits = [b.text for b in blocks if b.role in ('disadvantage', 'limitation')]
    return {
        'title': title,
        'blocks': [b.as_dict() for b in blocks],
        'texts': [b.text for b in blocks],
        'roles': roles,
        'problem': problem,
        'advantage': advantage,
        'limitations': limits[:3],
        'has_numbers': any(b.numbers for b in blocks),
        'category': _category(article),
    }


def _category(text: str) -> str:
    low = text.lower()
    table = [('chat', ('чат', 'ассистент', 'chat', 'gpt')), ('image', ('изображен', 'картин', 'image', 'генерац')),
             ('automation', ('автоматиз', 'workflow', 'интеграц', 'процесс')),
             ('code', ('код', 'ide', 'разработ', 'репозитор')), ('data', ('база', 'вектор', 'rag', 'данн'))]
    for name, keys in table:
        if sum(low.count(k) for k in keys) >= 2:
            return name
    return 'general'


def choose_concept(analysis: dict, history: list[dict] | None = None) -> str:
    """Concept from content, then the least used one among equally good fits."""
    cat = analysis.get('category')
    fit = {'chat': ['tech_explainer', 'editorial'], 'image': ['product_showcase', 'editorial'],
           'automation': ['motion_infographic', 'tech_explainer'], 'code': ['technical' if False else 'tech_explainer', 'minimal'],
           'data': ['tech_explainer', 'documentary'], 'general': ['editorial', 'minimal']}[cat]
    used = [h.get('director', {}).get('concept') for h in (history or [])]
    for c in fit:
        if used.count(c) == 0:
            return c
    return fit[len(used) % len(fit)]


def _structure(analysis: dict, history: list[dict] | None = None) -> str:
    """Structure from the content, then the least used among those that fit."""
    used = [h.get('director', {}).get('narrative_structure') for h in (history or [])]
    by_cat = {'chat': ['problem_solution', 'walkthrough', 'demo_first'],
              'image': ['demo_first', 'comparison_study', 'walkthrough'],
              'automation': ['walkthrough', 'problem_solution', 'demo_first'],
              'code': ['problem_solution', 'walkthrough', 'comparison_study'],
              'data': ['walkthrough', 'comparison_study', 'problem_solution'],
              'general': ['case_story', 'problem_solution', 'walkthrough']}
    order = by_cat.get(analysis.get('category'), by_cat['general'])
    for x in order:
        if used.count(x) == 0:
            return x
    return order[len(used) % len(order)]


def _order_blocks(analysis: dict, structure: str) -> list[int]:
    blocks = analysis['blocks']
    idx = list(range(len(blocks)))
    hook = [i for i in idx if blocks[i]['role'] == 'hook']
    body = [i for i in idx if blocks[i]['role'] != 'hook']
    concl = [i for i in body if blocks[i]['role'] == 'conclusion']
    mid = [i for i in body if i not in concl]
    lim = [i for i in mid if blocks[i]['role'] in ('limitation', 'disadvantage')]
    rest = [i for i in mid if i not in lim]
    if structure == 'demo_first':
        demo = [i for i in rest if blocks[i]['role'] in ('demonstration', 'feature')]
        mid = ([demo[0]] if demo else []) + [i for i in rest if not demo or i != demo[0]] + lim
    elif structure == 'problem_solution':
        prob = [i for i in rest if blocks[i]['role'] == 'problem']
        feat = [i for i in rest if blocks[i]['role'] in ('feature', 'workflow', 'demonstration')]
        other = [i for i in rest if i not in prob and i not in feat]
        mid = prob + feat + other + lim
    elif structure == 'comparison_study':
        comp = [i for i in rest if blocks[i]['role'] in ('comparison', 'statistics')]
        other = [i for i in rest if i not in comp]
        mid = comp + other + lim
    elif structure == 'walkthrough':
        mid = rest + lim
    else:
        mid = rest + lim
    return hook + mid + concl


def plan(analysis: dict, *, duration: float = 55, aspect: str = '9:16',
         available: tuple = (), history: list[dict] | None = None,
         concept: str | None = None, structure: str | None = None) -> dict:
    """Director's plan: concept, structure, motion profile, scenes with timings."""
    concept = concept or choose_concept(analysis, history)
    structure = structure or _structure(analysis, history)
    order = _order_blocks(analysis, structure)
    blocks = analysis['blocks']
    texts = analysis['texts']
    concl = [i for i in order if blocks[i]['role'] == 'conclusion']
    keep = order[:7]
    if concl and concl[0] not in keep:
        keep = keep[:-1] + [concl[0]]
    if not concl and keep:
        keep[-1] = order[-1]
    scenes, used_types = [], []
    t = 0.0
    total_words = max(1, sum(len(texts[i].split()) for i in order))
    for n, i in enumerate(keep):
        b = blocks[i]
        types = [x for x in SCENE_FOR[b['role']] if not available or x in available or x in
                 ('cluster', 'stat', 'bars', 'flow', 'split', 'lanes', 'quote', 'pros_cons',
                  'final_verdict', 'rating_scene')]
        fresh = [x for x in types if x not in used_types]
        pick = fresh[0] if fresh else next((x for x in types if x != (used_types[-1] if used_types else None)), types[0])
        used_types.append(pick)
        share = len(texts[i].split()) / total_words
        dur = max(6.0, min(14.0, duration * share))
        scenes.append({
            'id': f'scene_{n + 1:03d}',
            'role': b['role'],
            'type': pick,
            'duration': round(dur, 2),
            'text': texts[i],
            'visual_description': f"{b['role']} → {pick}",
            'composition': {'layout': _layout_for(b['role'], pick)},
            'animation': MOTION_FOR[b['role']],
            'start': round(t, 2),
        })
        t += dur
    return {
        'director': {
            'version': 2,
            'concept': concept,
            'visual_style': concept,
            'narrative_structure': structure,
            'motion_profile': 'dynamic' if structure == 'demo_first' else 'measured',
            'aspect': aspect,
            'duration': round(t, 2),
            'originality_seed': analysis.get('title', '')[:40],
        },
        'scenes': scenes,
    }


def _layout_for(role: str, scene_type: str) -> str:
    if scene_type in ('browser_window', 'phone_mockup', 'product_showcase'):
        return 'center_focus'
    if scene_type in ('split', 'before_after', 'pros_cons'):
        return 'two_columns'
    if scene_type in ('flow', 'data_flow'):
        return 'left_to_right'
    if scene_type in ('bars', 'grid100', 'rating_scene', 'stat'):
        return 'big_number'
    if scene_type in ('image_gallery',):
        return 'row'
    return 'center_focus'


# ---------------------------------------------------------------- originality
def fingerprint(plan: dict) -> dict:
    scenes = plan['scenes']
    return {
        'concept': plan['director']['concept'],
        'structure': plan['director']['narrative_structure'],
        'types': [s['type'] for s in scenes],
        'roles': [s['role'] for s in scenes],
        'layouts': [s['composition']['layout'] for s in scenes],
        'motions': [s['animation']['entrance'] for s in scenes],
    }


def _jaccard(a: list, b: list) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def _bigrams(seq: list) -> list:
    return [f'{a}->{b}' for a, b in zip(seq, seq[1:])]


def similarity(fp1: dict, fp2: dict) -> float:
    parts = [
        (1.0 if fp1['concept'] == fp2['concept'] else 0.0),
        (1.0 if fp1['structure'] == fp2['structure'] else 0.0),
        _jaccard(_bigrams(fp1['types']), _bigrams(fp2['types'])),
        _jaccard(fp1['layouts'], fp2['layouts']),
        _jaccard(fp1['motions'], fp2['motions']),
    ]
    return round(sum(parts) / len(parts), 3)


def variety(plans: list[dict]) -> dict:
    """How different the planned videos are from each other (0..1)."""
    if len(plans) < 2:
        return {'scene_variety': 1.0, 'composition_variety': 1.0,
                'motion_variety': 1.0, 'structure_variety': 1.0, 'pairwise': []}
    fps = [fingerprint(p) for p in plans]
    pairs = [(fps[i], fps[j]) for i in range(len(fps)) for j in range(i + 1, len(fps))]
    sims = [similarity(a, b) for a, b in pairs]
    return {
        'scene_variety': round(1 - sum(_jaccard(a['types'], b['types']) for a, b in pairs) / len(pairs), 3),
        'composition_variety': round(1 - sum(_jaccard(a['layouts'], b['layouts']) for a, b in pairs) / len(pairs), 3),
        'motion_variety': round(1 - sum(_jaccard(a['motions'], b['motions']) for a, b in pairs) / len(pairs), 3),
        'structure_variety': round(1 - sum(1.0 if a['structure'] == b['structure'] else 0.0 for a, b in pairs) / len(pairs), 3),
        'pairwise': [{'sim': s, 'same_concept': a['concept'] == b['concept']} for s, (a, b) in zip(sims, pairs)],
    }


def revise(analysis: dict, plan1: dict, history: list[dict], *, threshold: float = 0.75,
           available: tuple = (), duration: float = 55, aspect: str = '9:16') -> dict:
    """Re-plan with another concept/structure while the plan is too close to history."""
    used_concepts = {h.get('director', {}).get('concept') for h in history}
    used_struct = {h.get('director', {}).get('narrative_structure') for h in history}
    alt_concepts = [c for c in CONCEPTS if c not in used_concepts] or list(CONCEPTS)
    alt_struct = [s for s in NARRATIVES if s not in used_struct] or list(NARRATIVES)
    best = plan1
    for i in range(min(6, len(alt_concepts) * 2)):
        p = plan(analysis, duration=duration, aspect=aspect, available=available,
                 history=history, concept=alt_concepts[i % len(alt_concepts)],
                 structure=alt_struct[i % len(alt_struct)])
        fp = fingerprint(p)
        worst = max((similarity(fp, fingerprint(h)) for h in history), default=0.0)
        if worst < threshold:
            return p
        best = p
    return best


def load_history(project_dir) -> list[dict]:
    """Previous storyboards of the project folder (their `director` blocks)."""
    from pathlib import Path
    root = Path(project_dir)
    out = []
    for p in sorted(root.glob('*/storyboard.json')):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        if isinstance(d.get('director'), dict) and isinstance(d.get('scenes'), list):
            out.append(d)
    return out
