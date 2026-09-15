#!/usr/bin/env python3
"""Субтитры .srt из расшифровки — для YouTube отдельным файлом.

    python3 srt.py tc/rec1.json subs.srt [сдвиг_в_секундах]

Вход — то, что делает transcribe.py: {"transcription": [{"offsets": {"from","to"}, "text"}]}
Слова группируются в строки: до 42 знаков и не дольше 3,5 с, разрыв на паузе > 0,7 с.

Сдвиг нужен, когда блок в готовом видео стоит не там, где был в записи: передайте
секунду, с которой этот блок начинается в финальном файле, минус его начало в записи.
"""
import sys, json

MAX_CHARS = 42
MAX_DUR = 3.5
GAP = 0.7


def ts(t):
    t = max(0.0, t)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def main(src, dst, shift=0.0):
    words = json.load(open(src))["transcription"]
    if not words:
        sys.exit("расшифровка пустая")
    lines, cur = [], []
    for w in words:
        a, b = w["offsets"]["from"] / 1000, w["offsets"]["to"] / 1000
        text = w["text"].strip()
        if not text:
            continue
        if cur:
            same = (len(" ".join(x[2] for x in cur)) + 1 + len(text) <= MAX_CHARS
                    and b - cur[0][0] <= MAX_DUR
                    and a - cur[-1][1] <= GAP)
            if not same:
                lines.append(cur); cur = []
        cur.append((a, b, text))
    if cur:
        lines.append(cur)

    with open(dst, "w") as f:
        for i, ln in enumerate(lines, 1):
            start, end = ln[0][0] + shift, ln[-1][1] + shift
            f.write(f"{i}\n{ts(start)} --> {ts(end)}\n{' '.join(x[2] for x in ln)}\n\n")
    dur = lines[-1][-1][1] + shift
    print(f"{dst}: {len(lines)} строк, до {ts(dur)}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.0)
