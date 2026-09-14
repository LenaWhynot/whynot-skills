#!/usr/bin/env python3
"""Анимированные панели поверх видео.

Каждая панель — своя PNG-последовательность (корпус выезжает, строки появляются
по одной), продлённая статикой до конца своего окна и с фейдом на выходе.

    python3 build_anim.py ИСХОДНИК.mp4 ВЫХОД.mp4 panels.json

panels.json — список панелей. На каждую: заголовок, номер шага, окно показа
и содержимое — либо строки текста, либо скриншот с рамкой обрезки.

[
  {"n": "p1", "title": "Новый проект", "step": "01", "t": [3.35, 8.05],
   "shot": {"file": "img/01.png", "box": [60, 40, 1560, 420]}},

  {"n": "p2", "title": "INSTRUCTIONS.md", "step": "02", "t": [8.50, 15.25],
   "lines": [["первая строка", "acc"], ["вторая строка", "norm"],
             ["# комментарий", "mut"]]}
]

Стили строк: acc — акцентная, norm — обычная, mut — приглушённая.
Окружение: PANEL_FPS, PANEL_ANIM (длительность выезда), PANEL_Y_BOTTOM,
FRAME_WIDTH, плюс палитра и шрифты из panels.py.
"""
import os, sys, json, shutil, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panels_anim import render_seq
from panels import crop_shot

FPS       = int(os.environ.get("PANEL_FPS", 30))
ANIM      = float(os.environ.get("PANEL_ANIM", 1.10))
Y_BOTTOM  = int(os.environ.get("PANEL_Y_BOTTOM", 1830))
W_FRAME   = int(os.environ.get("FRAME_WIDTH", 1080))
PANEL_W   = int(os.environ.get("PANEL_WIDTH", 1040))


def main(src, dst, spec_path):
    spec = json.load(open(spec_path))
    if not spec:
        sys.exit("panels.json пустой — нечего накладывать")
    base = os.path.dirname(os.path.abspath(spec_path))
    tmp = os.path.join(os.path.dirname(os.path.abspath(dst)) or ".", ".anim")
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp, exist_ok=True)

    clips = []
    for i, s in enumerate(spec, 1):
        name = s.get("n") or f"p{i:02d}"
        kw = dict(title=s.get("title", ""), step=s.get("step", ""), width=PANEL_W)
        if s.get("shot"):
            f = s["shot"]["file"]
            f = f if os.path.isabs(f) else os.path.join(base, f)
            kw["body_img"] = crop_shot(f, tuple(s["shot"]["box"]))
        else:
            kw["lines"] = [tuple(x) for x in s.get("lines", [])]
        seq = os.path.join(tmp, name)
        n, size = render_seq(seq, fps=FPS, dur_anim=ANIM, **kw)
        st, en = float(s["t"][0]), float(s["t"][1])
        mov = os.path.join(tmp, f"{name}.mov")
        dur = en - st
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-framerate", str(FPS),
                        "-i", os.path.join(seq, "%04d.png"),
                        "-vf", f"tpad=stop_mode=clone:stop_duration={max(0.1, dur - ANIM):.2f},"
                               f"fade=out:st={max(0, dur - 0.25):.2f}:d=0.25:alpha=1,format=rgba",
                        "-c:v", "qtrle", "-y", mov], capture_output=True)
        clips.append((mov, st, en, size))
        print(f"  {name} {size[0]}x{size[1]}  {st:.2f}–{en:.2f}")

    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", src]
    for m, _, _, _ in clips:
        cmd += ["-i", m]
    fc = []; last = "0:v"
    for i, (m, st, en, size) in enumerate(clips, 1):
        x = (W_FRAME - size[0]) // 2
        ytop = Y_BOTTOM - size[1]
        fc.append(f"[{i}:v]setpts=PTS+{st}/TB[q{i}]")
        yexpr = f"{ytop}+18*max(0\\,1-(t-{st})/0.30)"
        fc.append(f"[{last}][q{i}]overlay=x={x}:y='{yexpr}':enable='between(t,{st},{en})'[w{i}]")
        last = f"w{i}"
    cmd += ["-filter_complex", ";".join(fc), "-map", f"[{last}]"]
    # звук исходника переносим, если он есть
    has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                                "-show_entries", "stream=index", "-of", "csv=p=0", src],
                               capture_output=True, text=True).stdout.strip()
    if has_audio:
        cmd += ["-map", "0:a", "-c:a", "copy"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-y", dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-1200:]); sys.exit(1)
    shutil.rmtree(tmp, ignore_errors=True)
    print("готово:", dst)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
