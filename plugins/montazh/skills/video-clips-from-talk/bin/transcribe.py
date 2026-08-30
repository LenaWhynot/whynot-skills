#!/usr/bin/env python3
"""Расшифровка записи со временем. Рядом с видео кладёт .srt и .txt.

  python3 transcribe.py запись.mp4 [--model small|medium|large-v3] [--lang ru]

Использует локальный faster-whisper из ~/.whynot-asr/.venv. Нет его —
подсказывает, как поставить, и выходит. Облачный путь сюда не встроен намеренно:
ключ и сервис выбирает человек, а не скрипт.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys


def srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--model", default="small",
                    help="small — быстро и обычно достаточно; large-v3 — точнее и дольше")
    ap.add_argument("--lang", default="ru")
    args = ap.parse_args()

    src = pathlib.Path(args.video)
    if not src.exists():
        print(f"Нет файла: {src}")
        return 1
    if not shutil.which("ffmpeg"):
        print("Нет ffmpeg. macOS: brew install ffmpeg · Windows: winget install Gyan.FFmpeg")
        return 1

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("Локальное распознавание не установлено.")
        print("Поставить: bash bin/setup-local-asr.sh")
        print("Запускать этим питоном: ~/.whynot-asr/.venv/bin/python transcribe.py …")
        return 1

    wav = src.with_suffix(".16k.wav")
    print("Готовлю звук…")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(src),
                    "-ar", "16000", "-ac", "1", str(wav)], check=True)

    print(f"Распознаю моделью {args.model} — это дольше всего, час записи ≈ 5–15 минут…")
    model = WhisperModel(args.model, device="auto", compute_type="int8")
    segments, _ = model.transcribe(str(wav), language=args.lang, vad_filter=True)

    srt, txt = src.with_suffix(".srt"), src.with_suffix(".txt")
    with srt.open("w", encoding="utf-8") as fs, txt.open("w", encoding="utf-8") as ft:
        for i, seg in enumerate(segments, 1):
            line = seg.text.strip()
            fs.write(f"{i}\n{srt_time(seg.start)} --> {srt_time(seg.end)}\n{line}\n\n")
            ft.write(f"[{srt_time(seg.start)[:8]}] {line}\n")
            if i % 25 == 0:
                print(f"  …{srt_time(seg.start)[:8]}", flush=True)

    wav.unlink(missing_ok=True)
    print(f"Готово: {srt.name} и {txt.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
