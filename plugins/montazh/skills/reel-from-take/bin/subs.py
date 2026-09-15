#!/usr/bin/env python3
"""Субтитры по словам из whisper-JSON — ОДИН рендерер, стиль = JSON из styles/.

    subs.py <whisper.json> <out.mov|out.ass> <hook_end> [y] [--style vishnya]
            [--hook "СТРОКА 1|СТРОКА 2"] [--styles-dir DIR]

Два движка, выбирается полем "engine" стиля:
  plate — плашка под словом рисуется PIL-ом в PNG-последовательность и собирается
          в .mov с альфой (qtrle). Так делается цветная плашка под словом.
  ass   — обычный .ass для libass: белые/обводка/тень/акцент цветом.

Раньше это были три скрипта (sub_plates.py, make_subs.py, make_subs_min.py) — теперь
новый стиль = новый JSON, код не трогать. Тайминг слова внутри фразы — пропорционально
длине слова, минимум 0,16 с; после хука первые 0,25 с без сабов (как и было).
"""
import json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
MIN_WORD = 0.16
AFTER_HOOK = 0.25


# ---------- общее ----------

def load_style(name, styles_dir=None):
    d = styles_dir or os.path.join(HERE, 'styles')
    p = os.path.join(d, f'{name}.json')
    if not os.path.exists(p):
        have = sorted(f[:-5] for f in os.listdir(d) if f.endswith('.json'))
        sys.exit(f'нет стиля «{name}». Есть: {", ".join(have)}')
    return json.load(open(p, encoding='utf-8'))


def clean(w):
    return w.rstrip('.,').strip()


def casing(w, mode):
    return w.upper() if mode == 'upper' else w.lower() if mode == 'lower' else w


def collect(js, hook_end):
    """[(start, end, word)] — по одному слову, тайминг пропорционально длине."""
    segs = json.load(open(js, encoding='utf-8'))['transcription']
    items, prev = [], 0.0
    for s in segs:
        a = s['offsets']['from'] / 1000
        b = s['offsets']['to'] / 1000
        t = s['text'].strip()
        if not t or b <= hook_end + AFTER_HOOK:
            continue
        a = max(a, prev, hook_end + AFTER_HOOK)
        if b <= a:
            continue
        words = [w for w in (clean(x) for x in t.split()) if w]
        if not words:
            continue
        total = sum(len(w) for w in words)
        cur = a
        for w in words:
            we = min(b, cur + max(MIN_WORD, (b - a) * len(w) / total))
            items.append((cur, we, w))
            cur = we
        prev = b
    return items


# ---------- движок ASS ----------

def ass_color(hexrgb, alpha='00'):
    """'#RRGGBB' → '&HAABBGGRR' (ASS хранит наоборот)."""
    h = hexrgb.lstrip('#')
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f'&H{alpha}{b}{g}{r}'.upper()


def ts(s):
    h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
    return f'{h}:{m:02d}:{sec:05.2f}'


def build_ass(js, out, hook_end, st, hook_lines, y_override=None):
    pos = dict(st['position'])
    if y_override:
        pos['y'] = y_override
    outline = st.get('outline') or {'color': '#000000', 'width': 0}
    shadow = st.get('shadow', 0)
    sh_alpha = st.get('shadow_alpha', '50')
    align = {'left': 4, 'center': 5, 'right': 6}[pos.get('anchor', 'center')]
    hk = st.get('hook') or {}
    hk_outline = hk.get('outline', 0); hk_shadow = hk.get('shadow', 0)

    styles = (
        '[V4+ Styles]\n'
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, '
        'BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, '
        'BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
        f"Style: Sub,{st['font']},{st['size']},{ass_color(st['color'])},{ass_color(st['color'])},"
        f"{ass_color(outline['color'])},{ass_color('#000000', sh_alpha)},0,0,0,0,100,100,0,0,1,"
        f"{outline.get('width', 0)},{shadow},{align},0,0,0,204\n"
    )
    if hk:
        styles += (
            f"Style: Hook,{hk['font']},{hk['size']},{ass_color(st['color'])},{ass_color(st['color'])},"
            f"{ass_color('#000000')},{ass_color('#000000', sh_alpha)},-1,0,0,0,100,100,0,0,1,"
            f"{hk_outline},{hk_shadow},7,0,0,0,204\n"
        )
    head = ('[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n'
            'WrapStyle: 2\nScaledBorderAndShadow: yes\n\n' + styles +
            '\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')

    ev = []
    if hk and hook_lines:
        fi, fo = hk.get('fade_ms', [0, 200])
        lines = [casing(l, hk.get('case', 'upper')) for l in hook_lines]
        if hk.get('per_line'):
            step = int(hk['size'] * hk.get('lead', 0.92))
            for i, line in enumerate(lines):
                ev.append(f"Dialogue: 1,{ts(0.02)},{ts(hook_end)},Hook,,0,0,0,,"
                          f"{{\\an7\\pos({hk['x']},{hk['y'] + i * step})\\fad({fi},{fo})}}{line}")
        else:
            ev.append(f"Dialogue: 1,{ts(0.02)},{ts(hook_end)},Hook,,0,0,0,,"
                      f"{{\\an8\\pos({hk['x']},{hk['y']})\\fad({fi},{fo})}}" + '\\N'.join(lines))

    acc = st.get('accent')
    keys = tuple(k.lower() for k in (acc or {}).get('keywords_prefix', []))
    fi, fo = st.get('fade_ms', [0, 0])
    for a, b, w in collect(js, hook_end):
        core = re.sub(r'^[^\wА-Яа-яЁё]+|[^\wА-Яа-яЁё]+$', '', w).lower()
        col = ''
        if acc and keys and core.startswith(keys):
            col = f"\\c{ass_color(acc['color'])}"
        ev.append(f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,"
                  f"{{\\an{align}\\pos({pos['x']},{pos['y']}){col}\\fad({fi},{fo})}}"
                  f"{casing(w, st.get('case', 'lower'))}")
    open(out, 'w', encoding='utf-8').write(head + '\n'.join(ev) + '\n')
    print(f'{st["name"]}: {len(ev)} событий → {out}')


# ---------- движок плашки ----------

def hex_rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def build_plate(js, out_mov, hook_end, st, y_override=None, fps=30):
    from PIL import Image, ImageDraw, ImageFont
    font_path = os.path.expanduser(st['font'])
    size = st['size']; pl = st['plate']
    padx, pady, radius = pl.get('padx', 26), pl.get('pady', 15), pl.get('radius', 24)
    fill = hex_rgb(pl['color']) + (255,); fg = hex_rgb(st['color']) + (255,)
    x0 = st['position']['x']; cy = y_override or st['position']['y']

    items = [(a, b, casing(w, st.get('case', 'lower'))) for a, b, w in collect(js, hook_end)]
    if not items:
        print('нет слов'); return
    f = ImageFont.truetype(font_path, size)
    d = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    mw = mh = 0
    for _, _, w in items:                      # один размер на всё — по самому широкому слову
        bb = d.textbbox((0, 0), w, font=f)
        mw = max(mw, bb[2] - bb[0]); mh = max(mh, bb[3] - bb[1])
    pw, ph = mw + padx * 2, mh + pady * 2

    def frame(word):
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
        y0 = cy - ph // 2
        dr.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius, fill=fill)
        if word:
            dr.text((x0 + pw // 2, cy), word, font=f, fill=fg, anchor='mm')
        return im

    tmp = '/tmp/_subs_plate'; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    uniq = {}
    for _, _, w in items:
        if w not in uniq:
            p = f'{tmp}/w{len(uniq):04d}.png'; frame(w).save(p); uniq[w] = p
    frame('').save(f'{tmp}/empty.png')
    start = items[0][0]; lines = []; t = start
    for a, b, w in items:
        if a - t > 0.04:
            lines.append((f'{tmp}/empty.png', a - t))
        lines.append((uniq[w], b - a)); t = b
    lst = f'{tmp}/list.txt'
    with open(lst, 'w') as fh:
        for p, dur in lines:
            fh.write(f"file '{p}'\nduration {max(0.04, dur):.3f}\n")
        fh.write(f"file '{lines[-1][0]}'\n")
    body = f'{tmp}/body.mov'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-r', str(fps), '-c:v', 'qtrle', '-y', body], check=True)
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', body,
                    '-vf', f'tpad=start_duration={start:.2f}:start_mode=add:color=0x00000000,format=rgba',
                    '-c:v', 'qtrle', '-y', out_mov], check=True)
    print(f'{st["name"]}: плашка {pw}x{ph}, слов {len(items)}, уникальных {len(uniq)} → {out_mov}')


# ---------- CLI ----------

def main(argv):
    args, opts = [], {}
    it = iter(argv)
    for a in it:
        if a.startswith('--'):
            opts[a[2:]] = next(it, '')      # значение опции — не позиционный аргумент
        else:
            args.append(a)
    if len(args) < 3:
        sys.exit(__doc__)
    js, out, hook_end = args[0], args[1], float(args[2])
    y = int(args[3]) if len(args) > 3 else (int(opts['y']) if 'y' in opts else None)
    st = load_style(opts.get('style', 'vishnya'), opts.get('styles-dir'))
    hook_lines = [l.strip() for l in opts['hook'].split('|')] if opts.get('hook') else []
    if st['engine'] == 'plate':
        build_plate(js, out, hook_end, st, y)
    else:
        build_ass(js, out, hook_end, st, hook_lines, y)


if __name__ == '__main__':
    main(sys.argv[1:])
