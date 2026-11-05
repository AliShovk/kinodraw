#!/usr/bin/env python3
"""OpenAI-совместимый /v1/audio/speech на Silero для KinoDraw."""
import json
import os
import re
import sys
import tempfile
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, '/opt/qantcore/minibot')
sys.path.insert(0, '/opt/qc-video')
from minibot.voice import Narrator  # noqa: E402

LATIN = {'qwen': 'Квен', 'composio': 'Композио', 'autogen': 'Автоджен', 'microsoft': 'Майкрософт',
         'github': 'Гитхаб', 'slack': 'Слак', 'gmail': 'Джимейл', 'notion': 'Ноушн', 'openai': 'Опен Эй Ай',
         'api': 'эй пи ай', 'pip': 'пип', 'install': 'инсталл', 'max': 'макс', 'gguf': 'гэ гэ у эф',
         'lm': 'эл эм', 'studio': 'студио', 'moE': 'моэ', 'moe': 'моэ', 'oauth': 'о-авт', 'docker': 'докер'}


def qc_speech_text(text):
    out = []
    for w in text.split():
        key = w.strip('.,!?;:()').lower()
        out.append(LATIN.get(key, w if not any(c.isascii() and c.isalpha() for c in w) else ''))
    return ' '.join(x for x in out if x)

VOICES = {'eugene': 'eugene', 'aidar': 'aidar', 'baya': 'baya'}
PORT = int(os.environ.get('PORT', '8123'))
LOCK = threading.Lock()
NAR = {}


def clean(text: str) -> str:
    t = qc_speech_text(text) if qc_speech_text else text
    t = re.sub(r'[^\w\sа-яА-ЯёЁ.,!?;:—-]', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t).strip()
    return t


def get_narrator(voice):
    # новый Narrator на каждый запрос: он накапливает реплики внутри себя
    return Narrator(speaker=voice, lead=0.05, gap=0.08)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        if not self.path.rstrip('/').endswith('/audio/speech'):
            self.send_error(404)
            return
        n = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(n) or b'{}')
        raw = (body.get('input') or '').strip()
        voice = VOICES.get(str(body.get('voice') or 'eugene').lower(), 'eugene')
        if not raw:
            self.send_error(400)
            return
        tmp = tempfile.mktemp(suffix='.wav')
        try:
            with LOCK:
                nar = get_narrator(voice)
                done = False
                for candidate in (clean(raw), re.sub(r'[^а-яА-ЯёЁ\s.,!?]', ' ', raw), 'Дальше — на сайте.'):
                    if not candidate.strip():
                        continue
                    try:
                        nar.add(candidate)
                        done = True
                        break
                    except Exception:
                        continue
                if not done:
                    raise RuntimeError('silero не осилил текст')
                nar.write(tmp)
            with open(tmp, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'audio/wav')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            print('ERROR:', raw[:100], flush=True)
            traceback.print_exc()
            msg = b'tts failed'
            self.send_response(500)
            self.send_header('Content-Length', str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


if __name__ == '__main__':
    print(f'silero tts on :{PORT}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
