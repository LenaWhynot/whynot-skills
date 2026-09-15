#!/usr/bin/env python3
"""Анимированные панели: корпус выезжает, элементы внутри появляются по очереди.
Отдаёт PNG-последовательность с альфой."""
from PIL import Image, ImageDraw, ImageFilter
import os, math, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panels import INK, HEAD, PAPER, LIME, MUTED, MONO, SANS, font, rounded

def ease(t):                      # плавный вход
    return 1-(1-t)**3

def frame(title, step, lines=None, body_img=None, width=1040, pad=28, prog=1.0):
    """prog 0..1 — фаза анимации: корпус, затем строки по очереди"""
    head_h=74
    if body_img is not None:
        bw=width-pad*2
        sc=bw/body_img.width
        body=body_img.resize((bw,int(body_img.height*sc)), Image.LANCZOS)
        body_h=body.height
    else:
        body=None; body_h=len(lines)*46+10
    H=head_h+body_h+pad*2

    canvas=Image.new("RGBA",(width+40,H+40),(0,0,0,0))
    # корпус появляется первым (0..0.35), с масштабом по высоте
    body_p=min(1.0, prog/0.35)
    if body_p<=0: return canvas
    ch=max(2,int(H*ease(body_p)))
    card=rounded((width,ch),26,INK+(252,))
    d=ImageDraw.Draw(card)
    if ch>head_h:
        d.rounded_rectangle([0,0,width-1,head_h+20],26,fill=HEAD+(255,))
        d.rectangle([0,head_h-2,width-1,head_h+20],fill=HEAD+(255,))
        for i,c in enumerate([(255,95,86),(255,189,46),(39,201,63)]):
            d.ellipse([pad+i*26,head_h//2-7,pad+i*26+14,head_h//2+7],fill=c+(255,))
        d.text((pad+100,head_h//2),title,font=font(MONO,30),fill=PAPER+(255,),anchor="lm")
        if step:
            bw_,bh_=62,44; bx=width-pad-bw_
            d.rounded_rectangle([bx,head_h//2-bh_//2,bx+bw_,head_h//2+bh_//2],12,fill=LIME+(255,))
            d.text((bx+bw_//2,head_h//2),step,font=font(SANS,28,idx=1),fill=INK+(255,),anchor="mm")
    # содержимое появляется после корпуса
    if prog>0.35 and ch>head_h+20:
        inner=prog-0.35; span=0.65
        y=head_h+pad
        if body is not None:
            a=min(1.0,inner/(span*0.6))
            b=body.convert("RGBA").copy()
            alpha=b.split()[3].point(lambda v:int(v*ease(a)))
            b.putalpha(alpha)
            off=int(14*(1-ease(a)))
            card.paste(b,(pad,y+off),b)
        else:
            n=len(lines)
            for i,(txt,style) in enumerate(lines):
                start=i*(span/max(1,n)); a=(inner-start)/(span/max(1,n))
                if a<=0: continue
                a=min(1.0,a); yy=y+i*46+int(12*(1-ease(a)))
                col=LIME if style=="acc" else (PAPER if style=="norm" else MUTED)
                al=int(255*ease(a))
                d.text((pad+8,yy),f"{i+1}",font=font(MONO,24),fill=MUTED+(al,))
                d.text((pad+58,yy),txt,font=font(MONO,30),fill=col+(al,))
    sh=Image.new("RGBA",(width+40,H+40),(0,0,0,0))
    sd=ImageDraw.Draw(sh)
    sd.rounded_rectangle([20,26,width+19,ch+25],26,fill=(0,0,0,150))
    sh=sh.filter(ImageFilter.GaussianBlur(14))
    sh.paste(card,(20,20+(H-ch)),card)
    return sh

def render_seq(outdir, fps=30, dur_anim=1.1, **kw):
    os.makedirs(outdir, exist_ok=True)
    n=int(fps*dur_anim)
    for i in range(n):
        im=frame(prog=(i+1)/n, **kw)
        im.save(f"{outdir}/{i:04d}.png")
    return n, im.size
