#!/bin/sh
# Собирает короткие ролики KinoDraw: голос Silero, схемы/графики, подпись Qantcore в конце.
set -e
cd /opt/kinodraw
export TTS_BACKEND=openai_compatible TTS_API_BASE=http://127.0.0.1:8123/v1 TTS_MODEL=silero TTS_VOICE=eugene
PY=./.venv/bin/kinodraw

for pair in "windsurf:Windsurf" "lark:Lark" "devin:Devin" "dify:Dify"; do
  slug=${pair%%:*}
  name=${pair#*:}
  rm -rf "$slug"
  printf '# %s\n\nкороткий ролик\n' "$name" > /tmp/$slug.md
  $PY new /tmp/$slug.md -o "$slug" --aspect 9:16 >/dev/null
  python3 - "$slug" <<'EOF'
import json, sys
p = f'/opt/kinodraw/{sys.argv[1]}/project.json'
d = json.load(open(p))
d['credit'] = True
d['lang'] = 'en'
json.dump(d, open(p, 'w'), ensure_ascii=False, indent=1)
EOF
  logo=$(ls /root/logos4/$slug.png 2>/dev/null || true)
  [ -n "$logo" ] && cp "$logo" "$slug/logo.png"
  python3 ru_build.py "specs/$slug-short.json" "$slug" >> /root/qc-topics/build.log 2>&1
  $PY voice "$slug" --voice-server http://127.0.0.1:8123/v1 --server-model silero --server-voice eugene >> /root/qc-topics/build.log 2>&1
  $PY render "$slug" --aspect 9:16 >> /root/qc-topics/build.log 2>&1
  $PY finish "$slug" >> /root/qc-topics/build.log 2>&1
  mp4=$(ls "$slug"/*vertical*.mp4 | head -1)
  out="/root/short-${slug}.mp4"
  ./.venv/bin/python make_bg.py "$slug" >/dev/null 2>&1 || true
  ffmpeg -y -v error -i "$mp4" -i "/root/bg-${slug}.png" -filter_complex \
    "[0:v]scale=918:1632,pad=1080:1920:81:144:color=0xE2E0DC[v];[v][1:v]overlay" \
    -af "loudnorm=I=-16:TP=-1.2:LRA=11" -c:v libx264 -crf 20 -preset veryfast -c:a aac -b:a 160k "$out"
  echo "OK $out $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")" >> /root/qc-topics/build.log
done
echo DONE
