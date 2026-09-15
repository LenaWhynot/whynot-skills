#!/usr/bin/env python3
"""Расшифровка дублей в формат, который ждёт takes.py.

    python3 transcribe.py            # все дорожки из audio/
    python3 transcribe.py take1      # только одну

Кладёт `tc/<дубль>.json` с пословными таймкодами:
    {"transcription": [{"offsets": {"from": мс, "to": мс}, "text": "..."}]}

Нужен faster-whisper. Если его нет — скажет, как поставить, и остановится:
    python3 -m pip install --user faster-whisper

Модель: ZAVOD_WHISPER (по умолчанию `small`; `base` быстрее и грубее,
`large-v3` точнее и тяжелее). Язык определяется сам — не форсируйте его:
неверно forced-язык не падает с ошибкой, а выдаёт правдоподобную кашу.
"""
import os, sys, json, glob


def work():
    return os.environ.get("ZAVOD_WORK") or os.getcwd()


def main():
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("нет faster-whisper. Поставьте:\n"
                 "  python3 -m pip install --user faster-whisper")

    w = work()
    files = sorted(glob.glob(os.path.join(w, "audio", "*.wav")))
    if len(sys.argv) > 1:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0] in sys.argv[1:]]
    if not files:
        sys.exit("нет дорожек в audio/ — сначала prepare.py")

    os.makedirs(os.path.join(w, "tc"), exist_ok=True)
    size = os.environ.get("ZAVOD_WHISPER", "small")
    print(f"модель {size} (меняется переменной ZAVOD_WHISPER)")
    model = WhisperModel(size, device="cpu", compute_type="int8")

    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        dst = os.path.join(w, "tc", f"{name}.json")
        if os.path.exists(dst):
            print(f"  · {name} — расшифровка уже есть"); continue
        segs, info = model.transcribe(f, word_timestamps=True, vad_filter=True)
        rows = []
        for s in segs:
            for word in (s.words or []):
                rows.append({"offsets": {"from": int(word.start * 1000),
                                         "to": int(word.end * 1000)},
                             "text": word.word.strip()})
            if not s.words:
                rows.append({"offsets": {"from": int(s.start * 1000),
                                         "to": int(s.end * 1000)},
                             "text": s.text.strip()})
        json.dump({"transcription": rows}, open(dst, "w"), ensure_ascii=False, indent=1)
        print(f"  · {name} → tc/{name}.json  ({len(rows)} слов, язык {info.language})")

    print("\nдальше: energy.py → takes.py → tempo.py")


if __name__ == "__main__":
    main()
