#!/usr/bin/env python3
"""Подготовка заказа: дорожки из дублей + опись материала.

    python3 prepare.py                 # рабочая папка — текущая или ZAVOD_WORK

Ждёт исходные дубли в `raw/`. Кладёт:
    audio/<дубль>.wav    моно 16 кГц PCM — по нему считается речь и паузы
    probe.json           опись: длительность, разрешение, fps, поворот, кодек

Дальше: transcribe.py → energy.py → takes.py → tempo.py.
"""
import os, sys, glob, subprocess, shutil

EXT = ("mov", "mp4", "m4v", "mkv", "avi")


def work():
    return os.environ.get("ZAVOD_WORK") or os.getcwd()


def ff(name="ffmpeg"):
    return shutil.which(name) or os.path.expanduser(f"~/.whynot-bin/{name}")


def main():
    w = work()
    raw = os.path.join(w, "raw")
    if not os.path.isdir(raw):
        sys.exit(f"нет папки {raw} — положите туда исходные дубли")
    files = sorted({f for e in EXT for f in
                    glob.glob(os.path.join(raw, f"*.{e}")) + glob.glob(os.path.join(raw, f"*.{e.upper()}"))})
    if not files:
        sys.exit(f"в {raw} нет видеофайлов ({', '.join(EXT)})")

    out = os.path.join(w, "audio")
    os.makedirs(out, exist_ok=True)
    print(f"дублей: {len(files)}")
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        dst = os.path.join(out, f"{name}.wav")
        if os.path.exists(dst):
            print(f"  · {name} — дорожка уже есть"); continue
        r = subprocess.run([ff(), "-nostdin", "-v", "error", "-i", f,
                            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                            "-y", dst], capture_output=True, text=True)
        if r.returncode:
            print(f"  ⚠️ {name} — звук не извлёкся: {r.stderr.strip()[:120]}")
        else:
            print(f"  · {name} → audio/{name}.wav")

    here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([sys.executable, os.path.join(here, "probe.py")])
    print("\nдальше: transcribe.py (расшифровка) → energy.py (карта речи)")


if __name__ == "__main__":
    main()
