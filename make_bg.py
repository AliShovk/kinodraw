#!/usr/bin/env python3
"""Фон-обои: сетка тематических дудлов, чтобы кадр не был полупустым."""
import io
import random
import sys
from pathlib import Path

from PIL import Image
import resvg_py

sys.path.insert(0, '/opt/kinodraw')
from kinodraw.library import resolve

W, H = 1080, 1920
SET = ['robot', 'laptop', 'database', 'code_window', 'shield', 'key_lock',
       'memory_chip', 'scroll', 'bullseye', 'speech_bubbles', 'people_network',
       'cloud_upload', 'lightbulb_idea', 'gpu_rack', 'chart_up', 'database']


def render(did, size):
    p = resolve(did)
    if not p:
        return None
    data = Path(p).read_text(encoding='utf-8')
    png = resvg_py.svg_to_bytes(svg_string=data, width=size, height=size)
    im = Image.open(io.BytesIO(bytes(png))).convert('RGBA')
    im.putalpha(im.getchannel('A').point(lambda a: int(a * 0.10)))
    return im


def build(slug):
    random.seed(slug)
    bg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    cols, rows = 4, 7
    cw, ch = W // cols, H // rows
    n = 0
    for r in range(rows):
        for c in range(cols):
            did = SET[(r * cols + c + random.randint(0, 3)) % len(SET)]
            size = random.randint(110, 170)
            img = render(did, size)
            if img is None:
                continue
            x = c * cw + random.randint(-20, max(0, cw - size - 6))
            y = r * ch + random.randint(-20, max(0, ch - size - 6))
            bg.alpha_composite(img, (max(0, min(x, W - size)), max(0, min(y, H - size))))
            n += 1
    out = f'/root/bg-{slug}.png'
    bg.save(out)
    print(out, n)


if __name__ == '__main__':
    for slug in sys.argv[1:] or ['demo']:
        build(slug)
