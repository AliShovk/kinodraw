"""whiteboard-animator integration: hand-drawn intro/outro clips for KinoDraw.

The two engines split the work: whiteboard-animator writes the title and the end
card by hand (its craft), KinoDraw draws the scenes and owns the timeline. Clips
land in ``project/stock`` and are played by KinoDraw's stock mode.

CLI: set WB_ANIMATE to the executable, or install the package next to KinoDraw
(``/opt/whiteboard-animator/.venv/bin/whiteboard-animate``).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PAPER = (247, 244, 234)
INK = (29, 29, 29)
ACCENT = (47, 107, 255)
FONT_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
HAND = FONT_DIR / 'PlaypenSans-Bold.ttf'

DEFAULT_CLI = '/opt/whiteboard-animator/.venv/bin/whiteboard-animate'


def cli_path() -> str | None:
    cand = os.environ.get('WB_ANIMATE') or DEFAULT_CLI
    return cand if Path(cand).is_file() else None


def available() -> bool:
    return cli_path() is not None


def _font(size: int):
    try:
        return ImageFont.truetype(str(HAND), size)
    except Exception:
        return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ''
    for w in words:
        trial = (cur + ' ' + w).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def compose_card(title: str, subtitle: str = '', logo: Path | None = None,
                 footer: str = '', out: Path = Path('/tmp/card.png'), variant: str = 'intro') -> Path:
    """A whiteboard-style 1080×1920 card for whiteboard-animator to draw."""
    img = Image.new('RGB', (1080, 1920), PAPER)
    d = ImageDraw.Draw(img)
    y = 520 if variant == 'intro' else 560
    if logo and Path(logo).is_file():
        lg = Image.open(logo).convert('RGBA')
        lg.thumbnail((520, 300))
        img.paste(lg, ((1080 - lg.width) // 2, y - lg.height - 60), lg)
    f = _font(96 if len(title) <= 14 else 72)
    lines = _wrap(d, title, f, 900)
    for line in lines:
        w = d.textlength(line, font=f)
        d.text(((1080 - w) / 2, y), line, font=f, fill=INK)
        y += int(f.size * 1.35)
    d.line([(300, y + 18), (780, y + 14)], fill=ACCENT, width=8)
    y += 60
    if subtitle:
        fs = _font(56)
        for line in _wrap(d, subtitle, fs, 880):
            w = d.textlength(line, font=fs)
            d.text(((1080 - w) / 2, y), line, font=fs, fill=(70, 70, 80))
            y += int(fs.size * 1.2)
    if footer:
        ff = _font(52)
        fw = d.textlength(footer, font=ff)
        d.text(((1080 - fw) / 2, 1600), footer, font=ff, fill=(40, 44, 52))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def animate(png: Path, seconds: float, out_mp4: Path, quality: str = 'high') -> Path:
    exe = cli_path()
    if not exe:
        raise RuntimeError('whiteboard-animate не найден: задайте WB_ANIMATE')
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [exe, str(png), '--duration', str(seconds), '--quality', quality, '-o', str(out_mp4)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if res.returncode != 0 or not out_mp4.is_file():
        raise RuntimeError(f'whiteboard-animate: {res.returncode} {res.stderr[-300:]}')
    return out_mp4


def install_stock(project_dir: Path, *, title: str, subtitle: str = '', logo: Path | None = None,
                  footer: str = 'qantcore.space', intro_s: float = 5.0, outro_s: float = 4.0,
                  quality: str = 'high') -> dict:
    """Render intro/outro cards with whiteboard-animator and write the manifest."""
    project_dir = Path(project_dir)
    stock = project_dir / 'stock'
    stock.mkdir(parents=True, exist_ok=True)
    intro_png = compose_card(title, subtitle, logo, '', stock / 'intro.png', 'intro')
    outro_png = compose_card('Подробнее на сайте', footer, None, 'Qantcore.Space', stock / 'outro.png', 'outro')
    animate(intro_png, intro_s, stock / 'intro.mp4', quality)
    animate(outro_png, outro_s, stock / 'outro.mp4', quality)
    manifest = {'clips': [
        {'path': str(stock / 'intro.mp4'), 'matches_line': 'intro', 'status': 'recommended',
         'rank': 1, 'in_s': 0, 'out_s': intro_s, 'duration': intro_s},
        {'path': str(stock / 'outro.mp4'), 'matches_line': 'outro', 'status': 'recommended',
         'rank': 1, 'in_s': 0, 'out_s': outro_s, 'duration': outro_s},
    ]}
    (stock / 'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    return manifest


def apply_to_storyboard(board: dict, *, clip_in: str = 'intro', clip_out: str = 'outro') -> dict:
    """Point the title beat and the closing at the whiteboard clips."""
    for beat in board.get('beats', []):
        if beat.get('kind') == 'title':
            beat['visuals'] = [{'id': f"{beat['id']}stock", 'type': 'stock', 'clip': clip_in}]
        elif beat.get('kind') == 'closing':
            beat['visuals'] = [{'id': f"{beat['id']}stock", 'type': 'stock', 'clip': clip_out}]
    board.setdefault('integration', {})['whiteboard_animator'] = {'intro': clip_in, 'outro': clip_out}
    return board
