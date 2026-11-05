"""Media scenes for reviews: real screenshots in drawn chrome, galleries, verdicts.

Every builder takes (v, beat, box, ctx) like the other pages_*.py modules and
returns nothing: it adds drawings to the board through ``ctx``. All of them
degrade to a doodle when the picture is missing, and never invent UI.
"""
from __future__ import annotations

import math
from pathlib import Path

from . import ink
from .scenes import SOFT_INK, mix, page_title, footnote


# ---------------------------------------------------------------- helpers
def _trig(ctx, beat, item, fallback):
    return ctx.time_of(beat, item.get('trigger')) if item and item.get('trigger') else fallback


def _put(ctx, polys, t, color=None, width=6, fills=None, max_dur=.6, after=None):
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    bx, by = min(xs), min(ys)
    local = [[(x - bx, y - by) for x, y in poly] for poly in polys]
    lf = [[[(x - bx, y - by) for x, y in poly], c] for poly, c in (fills or [])]
    dr = ctx.strokes((int(max(1, max(xs) - bx + 8)), int(max(1, max(ys) - by + 8))),
                     local, color=color or ink.INK, width=width, fills=lf or None, max_dur=max_dur)
    return ctx.add(dr, bx, by, t, after=after)


def _text(ctx, raw, size, max_w, color=ink.INK, lines=3, align='left', pace=1.3):
    return ctx.text(ctx.T(raw), size, color=color, max_w=max_w, max_lines=lines,
                    align=align, pace=pace, min_size=max(24, int(size * .7)))


def _picture(ctx, name, box):
    """Own picture of the project (assets/screenshots/…) or a doodle stand-in."""
    if not name:
        return None
    p = Path(ctx.project_dir) / name if ctx.project_dir else Path(name)
    if p.is_file():
        try:
            return ink.picture_drawing(p, box, speed=1600., min_dur=.5, max_dur=1.1)
        except Exception:
            return None
    return None


def _fallback(ctx, doodle, box):
    return ctx.doodle(doodle or 'laptop', (int(box[0]), int(box[1])), max_dur=1.6)


# ---------------------------------------------------------------- scenes
def build_browser_window(v, beat, box, ctx):
    """A screenshot inside a hand-drawn browser window with a URL bar."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    _, top = page_title(ctx, v, box, t0)
    fw = min(w - 40, 1180)
    fh = min(h - (top - y0) - 80, fw * .62)
    fx = x0 + (w - fw) / 2
    fy = top + 24
    r = 18
    frame = [(fx + r, fy), (fx + fw - r, fy), (fx + fw, fy + r), (fx + fw, fy + fh - r),
             (fx + fw - r, fy + fh), (fx + r, fy + fh), (fx, fy + fh - r), (fx, fy + r), (fx + r, fy)]
    made = [_put(ctx, [frame], t0, width=7, fills=[(frame[:-1], (255, 255, 255))], max_dur=1.1)]
    bar = [(fx, fy + 54), (fx + fw, fy + 54)]
    made.append(_put(ctx, [bar], t0 + .5, color=SOFT_INK, width=4, max_dur=.4))

    url = v.get('url')
    if url:
        u = ctx.text(url, 26, color=SOFT_INK, max_w=fw - 220, max_lines=1, min_size=20)
        made.append(ctx.add(u, fx + 130, fy + 16, t0 + .7))
    inner = (fw - 24, fh - 54 - 18)
    pic = _picture(ctx, v.get('image'), inner)
    pic = pic or _fallback(ctx, v.get('doodle'), inner)
    made.append(ctx.add(pic, fx + 12, fy + 62, t0 + 1.0))
    cap = v.get('caption')
    if cap:
        c = _text(ctx, cap, 40, fw - 40, color=ink.INK, lines=2, align='center')
        made.append(ctx.add(c, fx + (fw - c.size[0]) / 2, fy + fh + 14, t0 + 1.8))
    ctx.register(v.get('id'), 'all', made)
    ctx.register(v.get('id'), 0, made)
    footnote(ctx, v, box, t0 + 2.2)


def build_phone_mockup(v, beat, box, ctx):
    """A screenshot inside a phone frame; labels on the free side."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    _, top = page_title(ctx, v, box, t0)
    avail = h - (top - y0) - 40
    ph = min(avail, 900)
    pw = ph * .49
    px = x0 + (w - pw) / 2
    py = top + (avail - ph) / 2
    r = 54
    body = [(px + r, py), (px + pw - r, py), (px + pw, py + r), (px + pw, py + ph - r),
            (px + pw - r, py + ph), (px + r, py + ph), (px, py + ph - r), (px, py + r), (px + r, py)]
    made = [_put(ctx, [body], t0, width=8, fills=[(body[:-1], (255, 255, 255))], max_dur=1.2)]
    notch = [(px + pw * .34, py + 18), (px + pw * .66, py + 18), (px + pw * .66, py + 34),
             (px + pw * .34, py + 34), (px + pw * .34, py + 18)]
    made.append(_put(ctx, [notch], t0 + .6, width=5, fills=[(notch[:-1], ink.INK)], max_dur=.5))
    inner = (pw - 34, ph - 100)
    pic = _picture(ctx, v.get('image'), inner) or _fallback(ctx, v.get('doodle'), inner)
    made.append(ctx.add(pic, px + 17, py + 60, t0 + 1.0))
    for i, item in enumerate((v.get('labels') or [])[:2]):
        lab = _text(ctx, item.get('text') if isinstance(item, dict) else item, 40, 420, lines=2)
        lx = px + pw + 40 if i % 2 == 0 else px - lab.size[0] - 40
        ly = py + 120 + i * 190
        made.append(ctx.add(lab, lx, ly, t0 + 1.6 + .5 * i))
    ctx.register(v.get('id'), 'all', made)
    ctx.register(v.get('id'), 0, made)
    footnote(ctx, v, box, t0 + 2.4)


def build_image_gallery(v, beat, box, ctx):
    """Two or three pictures side by side, each labelled."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    _, top = page_title(ctx, v, box, t0)
    items = (v.get('images') or [])[:3]
    if not items:
        return
    n = len(items)
    gap = 36
    cw = (w - 40 - gap * (n - 1)) / n
    ch = min(h - (top - y0) - 110, cw * .78)
    made = []
    for i, it in enumerate(items):
        cx = x0 + 20 + i * (cw + gap)
        cy = top + 20
        pic = _picture(ctx, it.get('image'), (cw, ch)) or _fallback(ctx, it.get('doodle'), (cw, ch))
        ti = t0 + .4 + i * 1.1
        made.append(ctx.add(pic, cx, cy, ti))
        if it.get('caption'):
            cap = _text(ctx, it['caption'], 36, cw, lines=2, align='center')
            made.append(ctx.add(cap, cx + (cw - cap.size[0]) / 2, cy + ch + 10, ti + .3))
    ctx.register(v.get('id'), 'all', made)
    for i in range(n):
        ctx.register(v.get('id'), i, [made[i]])
    footnote(ctx, v, box, t0 + 3.2)


def build_before_after(v, beat, box, ctx):
    """Two pictures with «до» and «после» and a dashed divider."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    _, top = page_title(ctx, v, box, t0)
    half = w / 2 - 30
    ch = min(h - (top - y0) - 120, half * .72)
    made = []
    for i, key in enumerate(('before', 'after')):
        it = v.get(key) or {}
        cx = x0 + 20 + i * (half + 20)
        pic = _picture(ctx, it.get('image'), (half, ch)) or _fallback(ctx, it.get('doodle'), (half, ch))
        ti = t0 + .4 + i * 1.4
        made.append(ctx.add(pic, cx, top + 40, ti))
        lab = _text(ctx, it.get('label') or ('до' if i == 0 else 'после'), 44, half, lines=1, align='center')
        made.append(ctx.add(lab, cx + (half - lab.size[0]) / 2, top + 10, ti - .2))
    div = x0 + w / 2
    dashes = [[(div, top + 30 + k * 40), (div, min(y0 + h - 40, top + 30 + k * 40 + 22))] for k in range(12)]
    made.append(_put(ctx, dashes, t0, color=SOFT_INK, width=5, max_dur=.7))
    ctx.register(v.get('id'), 'all', made)
    footnote(ctx, v, box, t0 + 3)


def build_hero_reveal(v, beat, box, ctx):
    """The product picture, big, with rays and one line under it."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    _, top = page_title(ctx, v, box, t0)
    pw = min(w * .72, 820)
    pic = _picture(ctx, v.get('image'), (pw, pw * .66)) or _fallback(ctx, v.get('doodle'), (pw, pw * .66))
    made = []
    if pic:
        px = x0 + (w - pic.size[0]) / 2
        py = top + 30
        made.append(ctx.add(pic, px, py, t0))

    if v.get('caption'):
        cap = _text(ctx, v['caption'], 48, w - 80, lines=2, align='center')
        made.append(ctx.add(cap, x0 + (w - cap.size[0]) / 2, top + (pic.size[1] if pic else 0) + 44, t0 + 1.4))
    ctx.register(v.get('id'), 'all', made)
    footnote(ctx, v, box, t0 + 2.4)


def build_product_showcase(v, beat, box, ctx):
    """A screenshot with callouts pointing at its parts."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    _, top = page_title(ctx, v, box, t0)
    pw = min(w * .78, 1000)
    ph = min(h - (top - y0) - 90, pw * .62)
    pic = _picture(ctx, v.get('image'), (pw, ph)) or _fallback(ctx, v.get('doodle'), (pw, ph))
    px, py = x0 + (w - pw) / 2, top + 20
    made = [ctx.add(pic, px, py, t0)]
    for i, item in enumerate((v.get('callouts') or [])[:2]):
        lab = _text(ctx, item.get('text') if isinstance(item, dict) else item, 36, 300, lines=2)
        lx = px - lab.size[0] - 30 if i % 2 == 0 else px + pw + 30
        ly = py + 60 + i * 120
        made.append(ctx.add(lab, lx, ly, t0 + 1.2 + .4 * i))
    ctx.register(v.get('id'), 'all', made)
    footnote(ctx, v, box, t0 + 2.8)


def build_spotlight(v, beat, box, ctx):
    """The picture with one circled detail and an arrow to it."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    _, top = page_title(ctx, v, box, t0)
    pw = min(w * .74, 900)
    pic = _picture(ctx, v.get('image'), (pw, pw * .62)) or _fallback(ctx, v.get('doodle'), (pw, pw * .62))
    px, py = x0 + (w - pic.size[0]) / 2, top + 30
    made = [ctx.add(pic, px, py, t0)]
    spot = v.get('spot') or {}
    cx = px + pic.size[0] * float(spot.get('x', .5))
    cy = py + pic.size[1] * float(spot.get('y', .5))
    rad = min(pic.size) * float(spot.get('r', .18))
    ring = [[(cx + rad * math.cos(a), cy + rad * math.sin(a)) for a in [k * math.pi / 24 for k in range(49)]]]
    made.append(_put(ctx, ring, t0 + 1.2, color=ctx.color, width=8, max_dur=.9))
    if spot.get('label'):
        lab = _text(ctx, spot['label'], 40, 380, lines=2)
        made.append(ctx.add(lab, cx + rad + 20, cy - lab.size[1] / 2, t0 + 1.7))
    ctx.register(v.get('id'), 'all', made)
    footnote(ctx, v, box, t0 + 2.6)


def build_pros_cons(v, beat, box, ctx):
    """Two columns: what is good, what is not. No pictures, only marks."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    _, top = page_title(ctx, v, box, t0)
    cols = (('pros', 'плюсы', (67, 160, 71)), ('cons', 'минусы', (229, 57, 53)))
    made = []
    for i, (key, title, color) in enumerate(cols):
        items = (v.get(key) or [])[:3]
        cx = x0 + 30 + i * (w / 2)
        ttl = _text(ctx, title.upper(), 44, w / 2 - 60, lines=1, color=color)
        made.append(ctx.add(ttl, cx, top + 10, t0 + .2 + i * .4))
        y = top + 80
        for j, it in enumerate(items):
            mark = '+' if key == 'pros' else '−'
            m = ctx.text(mark, 40, color=color, max_w=60, max_lines=1)
            made.append(ctx.add(m, cx, y, t0 + .6 + j * .5))
            tx = _text(ctx, it, 38, w / 2 - 130, lines=2)
            made.append(ctx.add(tx, cx + 46, y, t0 + .8 + j * .5))
            y += max(tx.size[1], 44) + 26
    ctx.register(v.get('id'), 'all', made)
    footnote(ctx, v, box, t0 + 3.2)


def build_rating_scene(v, beat, box, ctx):
    """A big score with the verdict word under it."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    score = str(v.get('score') or '')
    made = []
    num = ctx.text(score, 240, color=ctx.color, max_w=w - 200, max_lines=1, min_size=120)
    made.append(ctx.add(num, x0 + (w - num.size[0]) / 2, y0 + 120, t0, hand=False))
    if v.get('label'):
        lab = _text(ctx, v['label'], 56, w - 200, lines=2, align='center')
        made.append(ctx.add(lab, x0 + (w - lab.size[0]) / 2, y0 + 140 + num.size[1], t0 + .8))
    ctx.register(v.get('id'), 'all', made)
    footnote(ctx, v, box, t0 + 2)


def build_final_verdict(v, beat, box, ctx):
    """Score + verdict text + the product name, as an end card."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    made = []
    score = str(v.get('score') or '')
    num = ctx.text(score, 200, color=ctx.color, max_w=420, max_lines=1, min_size=100)
    made.append(ctx.add(num, x0 + 40, y0 + 80, t0, hand=False))
    if v.get('title'):
        ttl = _text(ctx, v['title'], 54, w - 480, lines=2)
        made.append(ctx.add(ttl, x0 + 480, y0 + 100, t0 + .5))
    if v.get('text'):
        body = _text(ctx, v['text'], 42, w - 80, lines=5)
        made.append(ctx.add(body, x0 + 40, y0 + 300 if num.size[1] < 260 else y0 + num.size[1] + 60, t0 + 1.0))
    ctx.register(v.get('id'), 'all', made)


def build_data_flow(v, beat, box, ctx):
    """A chain of nodes with dots travelling along the arrows."""
    from .pages_logic import build_flow
    build_flow(v, beat, box, ctx)


def build_feature_explosion(v, beat, box, ctx):
    """Centre picture and features flying out around it."""
    x0, y0, w, h = box
    t0 = ctx.time_of(beat, v.get('trigger'))
    _, top = page_title(ctx, v, box, t0)
    cs = min(w * .34, 380)
    pic = _picture(ctx, v.get('image'), (cs, cs * .8)) or _fallback(ctx, v.get('doodle'), (cs, cs * .8))
    cx, cy = x0 + w / 2, top + (h - (top - y0)) / 2
    made = [ctx.add(pic, cx - pic.size[0] / 2, cy - pic.size[1] / 2, t0)]
    feats = (v.get('features') or [])[:3]
    for i, f in enumerate(feats):
        lab = _text(ctx, f, 32, min(320, w / 2 - 60), lines=3, align='center')
        left = i % 2 == 0
        lx = x0 + 20 if left else x0 + w - lab.size[0] - 20
        ly = top + 40 + (i // 2) * (lab.size[1] + 40)
        ly = max(top + 10, min(ly, y0 + h - lab.size[1] - 10))
        made.append(ctx.add(lab, lx, ly, t0 + 1.0 + i * .35))
        # короткая стрелка к картинке
        ax = lx + lab.size[0] if left else lx

    ctx.register(v.get('id'), 'all', made)
    footnote(ctx, v, box, t0 + 3)


BUILDERS = {
    'browser_window': build_browser_window,
    'phone_mockup': build_phone_mockup,
    'image_gallery': build_image_gallery,
    'before_after': build_before_after,
    'hero_reveal': build_hero_reveal,
    'product_showcase': build_product_showcase,
    'spotlight': build_spotlight,
    'pros_cons': build_pros_cons,
    'rating_scene': build_rating_scene,
    'final_verdict': build_final_verdict,
    'data_flow': build_data_flow,
    'feature_explosion': build_feature_explosion,
}
