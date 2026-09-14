#!/usr/bin/env python3
"""Список дублей: границы берём из карты энергии (точные по звуку),
текст — из whisper (перекрывающиеся сегменты)."""
import json, os, sys

def _work():
    """Папка заказа: ZAVOD_WORK, иначе текущая."""
    import os as _o
    return _o.environ.get('ZAVOD_WORK') or _o.getcwd()


BASE = _work()
energy = json.load(open(f'{BASE}/energy.json'))
PAD_IN, PAD_OUT = 0.30, 0.45     # запас, чтобы не срезать первый/последний звук

def segments(clip):
    p = f'{BASE}/tc/{clip}.json'
    if not os.path.exists(p): return None
    d = json.load(open(p))
    return [(s['offsets']['from']/1000, s['offsets']['to']/1000, s['text'].strip())
            for s in d.get('transcription', [])]

def takes(clip):
    segs = segments(clip)
    if segs is None: return None
    blocks = energy[clip]['blocks']
    out = []
    for bs, be in blocks:
        # текст всех сегментов, пересекающихся с блоком
        parts = [t for (ss, se, t) in segs if se > bs and ss < be and t]
        txt = ' '.join(parts).strip()
        out.append(dict(start=max(0, bs - PAD_IN), end=be + PAD_OUT,
                        dur=be - bs + PAD_IN + PAD_OUT, text=txt))
    return out

if __name__ == '__main__':
    clips = sys.argv[1:]
    for c in clips:
        t = takes(c)
        if t is None:
            print(f'{c}: ещё нет транскрипта'); continue
        print(f'════ {c} — {len(t)} дублей ════')
        for i, d in enumerate(t, 1):
            print(f'  {i:>2}. {d["start"]:>6.2f}–{d["end"]:<6.2f} ({d["dur"]:>4.1f}с)  {d["text"][:110]}')
        print()
