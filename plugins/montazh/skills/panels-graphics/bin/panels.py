#!/usr/bin/env python3
"""Карточки-панели в стиле референса: тёмное окно с шапкой, номером шага
и содержимым (скриншот интерфейса или текст)."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

def _rgb(env, default):
    """Цвет из переменной окружения: #rrggbb или rrggbb. Иначе — значение по умолчанию."""
    v = (os.environ.get(env) or "").strip().lstrip("#")
    if len(v) == 6:
        try: return tuple(int(v[i:i+2], 16) for i in (0, 2, 4))
        except ValueError: pass
    return default

# Палитра карточки. Переопределяется без правки кода:
#   PANEL_INK / PANEL_HEAD / PANEL_PAPER / PANEL_ACCENT / PANEL_MUTED
INK   = _rgb("PANEL_INK",    (19, 21, 23))     # корпус карточки
HEAD  = _rgb("PANEL_HEAD",   (33, 35, 37))     # шапка
PAPER = _rgb("PANEL_PAPER",  (242, 239, 230))  # текст
LIME  = _rgb("PANEL_ACCENT", (224, 219, 102))  # акцент: бейдж шага, выделенная строка
MUTED = _rgb("PANEL_MUTED",  (150, 152, 150))

def _first_font(*paths):
    for p in paths:
        if p and os.path.exists(p): return p
    return ""

# Шрифты: сначала переменная окружения, потом типовые пути macOS / Linux / Windows.
MONO = os.environ.get("PANEL_FONT_MONO") or _first_font(
    "/System/Library/Fonts/Menlo.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "C:/Windows/Fonts/consola.ttf")
SANS = os.environ.get("PANEL_FONT_SANS") or _first_font(
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf")

def font(path, size, idx=0):
    try: return ImageFont.truetype(path, size, index=idx)
    except Exception: return ImageFont.load_default()

def rounded(size, radius, color):
    im = Image.new("RGBA", size, (0,0,0,0))
    ImageDraw.Draw(im).rounded_rectangle([0,0,size[0]-1,size[1]-1], radius, fill=color)
    return im

def card(title, step, body_img=None, lines=None, width=920, pad=26):
    """body_img — PIL.Image (скриншот), lines — список (текст, стиль) для кода"""
    head_h = 74
    if body_img is not None:
        bw = width - pad*2
        scale = bw / body_img.width
        body = body_img.resize((bw, int(body_img.height*scale)), Image.LANCZOS)
        body_h = body.height
    else:
        f = font(MONO, 30)
        body_h = len(lines)*44 + 10
        body = None
    H = head_h + body_h + pad*2
    card_im = rounded((width, H), 26, INK + (252,))
    d = ImageDraw.Draw(card_im)
    # шапка
    d.rounded_rectangle([0,0,width-1,head_h+20], 26, fill=HEAD+(255,))
    d.rectangle([0,head_h-2,width-1,head_h+20], fill=HEAD+(255,))
    for i,c in enumerate([(255,95,86),(255,189,46),(39,201,63)]):
        d.ellipse([pad+i*26, head_h//2-7, pad+i*26+14, head_h//2+7], fill=c+(255,))
    d.text((pad+100, head_h//2), title, font=font(MONO,30), fill=PAPER+(255,), anchor="lm")
    # бейдж шага
    if step:
        bw_, bh_ = 62, 44
        bx = width - pad - bw_
        d.rounded_rectangle([bx, head_h//2-bh_//2, bx+bw_, head_h//2+bh_//2], 12, fill=LIME+(255,))
        d.text((bx+bw_//2, head_h//2), step, font=font(SANS,28,idx=1), fill=INK+(255,), anchor="mm")
    # содержимое
    y = head_h + pad
    if body is not None:
        card_im.paste(body.convert("RGBA"), (pad, y), body.convert("RGBA"))
    else:
        fm = font(MONO, 30); fb = font(MONO, 30)
        for i,(txt,style) in enumerate(lines):
            yy = y + i*44
            d.text((pad+8, yy), f"{i+1}", font=font(MONO,24), fill=MUTED+(255,))
            col = LIME if style=="acc" else (PAPER if style=="norm" else MUTED)
            d.text((pad+58, yy), txt, font=fb, fill=col+(255,))
    # мягкая тень
    shadow = Image.new("RGBA", (width+40, H+40), (0,0,0,0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([20,26,width+19,H+25], 26, fill=(0,0,0,150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    shadow.paste(card_im, (20,20), card_im)
    return shadow

def crop_shot(path, box=None, max_h=None):
    im = Image.open(path).convert("RGB")
    if box: im = im.crop(box)
    if max_h and im.height > max_h:
        s = max_h/im.height
        im = im.resize((int(im.width*s), max_h), Image.LANCZOS)
    return im
