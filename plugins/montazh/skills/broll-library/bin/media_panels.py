#!/usr/bin/env python3
"""Панели-вставки из ваших материалов: картинки и видео, несколько кадров на шаг.

    python3 media_panels.py ИСХОДНИК.mp4 ВЫХОД.mp4 [spec.json]

Материалы берутся из папки `screens/` в папке заказа (и из библиотеки, см. SKILL.md).
Нужные места на скриншотах подсвечивайте заранее сами — рамки скрипт не рисует."""
import os, sys, subprocess, shutil, json
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panels import INK, HEAD, PAPER, LIME, SANS, font

B=os.environ.get('ZAVOD_WORK') or os.getcwd()
S=f'{B}/screens'
TMP=f'{B}/.media'
W=int(os.environ.get('FRAME_WIDTH', 1080)); VH=720; HEAD_H=66
# панель делали выше по опыту: скринкаст в 600 px не читался
Y_BOTTOM=int(os.environ.get('PANEL_Y_BOTTOM', 1840))   # низ панели; 1920 = вплотную к краю
SLIDE=0.30                     # выезд снизу; 0 = панель просто появляется
PH=HEAD_H+VH                   # пересчитывается в main(), если спека задаёт свои
# «Карточка» — приём, снятый с удачного ролика: скриншот лежит не встык к краям,
# а скруглённой карточкой с полями, вокруг видно кадр.
CARD=None                      # {"margin":40,"radius":30} из спеки
PW=W                           # ширина панели: у карточки уже, чем кадр

# шаг: (номер, заголовок, начало, конец, [(файл, доля_времени, старт_в_видео, кроп)])
# SPEC приходит из JSON третьим аргументом (см. load_spec).
SPEC=[
 ('01','Проект',      3.35, 6.90,  [('01-proekt.jpg',1.65,None,None),
                                    ('01-proekt-2.jpg',1.0,None,None),
                                    ('01-proekt-3.jpg',0.9,None,None)]),
 ('02','Инструкции',  6.95,15.10,  [('02-instructions-1.jpg',2.05,None,None),
                                    ('02-instructions-2.mp4',6.10,2.0,(500,205,1570,800))]),
 ('03','Контекст',   15.25,24.00,  [('03-context.jpg',1.55,None,None),
                                    ('03-context-2.mp4',3.0,0.1,(1050,320,2060,882)),
                                    ('05-schedule.jpg',4.20,None,(1330,520,2090,942))]),
 ('04','Скиллы',     24.20,32.10,  [('04-skills.jpg',1,None,None)]),
 ('05','Расписание', 32.35,33.45,  [('05-schedule.jpg',1,None,'fit')]),
 ('06','Коннекторы', 33.70,37.20,  [('06-connectors.jpg',1,None,'fit')]),
]

def header(title, step):
    im=Image.new('RGBA',(W,HEAD_H+8),INK+(252,))
    d=ImageDraw.Draw(im)
    bw,bh=62,40
    d.rounded_rectangle([40,HEAD_H//2-bh//2,40+bw,HEAD_H//2+bh//2],11,fill=LIME+(255,))
    d.text((40+bw//2,HEAD_H//2),step,font=font(SANS,25,idx=1),fill=INK+(255,),anchor="mm")
    d.text((40+bw+20,HEAD_H//2),title.upper(),font=font(SANS,27,idx=1),fill=PAPER+(255,),anchor="lm")
    return im

VF=(f"scale={W}:{VH}:force_original_aspect_ratio=increase,"
    f"crop={W}:{VH},setsar=1,format=rgba")
VF_FIT=(f"scale={W}:{VH}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{VH}:(ow-iw)/2:(oh-ih)/2:color=0x131517,setsar=1,format=rgba")

def load_spec(path):
    """JSON: {"screens":"<папка>", "steps":[{"step","title","from","to",
    "items":[{"file","weight","start","len","crop"}]}]}.
    crop — [x0,y0,x1,y1] либо "fit"; len — сколько секунд исходного видео брать
    (без него берётся весь хвост и он ускоряется в кашу)."""
    d=json.load(open(path))
    spec=[]
    for st in d['steps']:
        items=[(it['file'], it.get('weight',1), it.get('start'),
                tuple(it['crop']) if isinstance(it.get('crop'),list) else it.get('crop'),
                it.get('len'))
               for it in st['items']]
        spec.append((st['step'], st['title'], st['from'], st['to'], items,
                     st.get('full', False), st.get('height')))
    return d.get('screens'), spec

def main(src,dst,spec_path=None):
    global S, SPEC, VH, Y_BOTTOM, SLIDE, PH, VF, VF_FIT, HEAD_H, CARD, PW
    if spec_path:
        d=json.load(open(spec_path))
        screens, SPEC = load_spec(spec_path)
        if screens: S = screens if os.path.isabs(screens) else f'{B}/{screens}'
        VH=d.get('panel_height',VH); Y_BOTTOM=d.get('bottom',Y_BOTTOM)
        SLIDE=d.get('slide',SLIDE)
        if d.get('header',True) is False: HEAD_H=0     # панель без шапки: только скринкаст
        PH=HEAD_H+VH
        CARD=d.get('card')
        PW=W-2*CARD.get('margin',40) if CARD else W
        VF=(f"scale={PW}:{VH}:force_original_aspect_ratio=increase,"
            f"crop={PW}:{VH},setsar=1,format=rgba")
        VF_FIT=(f"scale={PW}:{VH}:force_original_aspect_ratio=decrease,"
                f"pad={PW}:{VH}:(ow-iw)/2:(oh-ih)/2:color=0x131517,setsar=1,format=rgba")
    shutil.rmtree(TMP,ignore_errors=True); os.makedirs(TMP)
    clips=[]
    for entry in SPEC:
        step,title,rs,re_,items = entry[:5]
        full = entry[5] if len(entry) > 5 else False
        # шаг «во всю ширину»: без полей и без скругления, вплотную к низу кадра
        pw = W if full else PW
        vh = (entry[6] if len(entry) > 6 and entry[6] else VH)   # своя высота у шага
        ph = HEAD_H + vh
        vf_fill = (f"scale={pw}:{vh}:force_original_aspect_ratio=increase,"
                   f"crop={pw}:{vh},setsar=1,format=rgba")
        vf_fit  = (f"scale={pw}:{vh}:force_original_aspect_ratio=decrease,"
                   f"pad={pw}:{vh}:(ow-iw)/2:(oh-ih)/2:color=0x131517,setsar=1,format=rgba")
        dur=re_-rs
        items=[it if len(it)==5 else (*it,None) for it in items]
        wsum=sum(it[1] for it in items)
        hdr=None
        if HEAD_H:
            hdr=f'{TMP}/h{step}.png'; header(title,step).save(hdr)
        parts=[]
        for i,(fname,w,vstart,crop,vlen) in enumerate(items):
            seg=dur*w/wsum
            path=f'{S}/{fname}'
            out=f'{TMP}/{step}_{i}.mov'
            if fname.lower().endswith(('.mp4','.mov')):
                srcdur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                    '-of','csv=p=0',path],capture_output=True,text=True).stdout)
                avail=min(vlen or 1e9, srcdur-(vstart or 0))
                sp=max(0.25, avail/seg)          # ускоряем, чтобы весь фрагмент влез
                cf=''
                # 'fit' и для видео тоже: широкий экран 16:9 в панели 1,37 нельзя
                # заполнять — срезает половину интерфейса
                vf_v=vf_fill
                if crop=='fit':
                    vf_v=vf_fit
                elif crop:
                    cx0,cy0,cx1,cy1=crop
                    cf=f'crop={cx1-cx0}:{cy1-cy0}:{cx0}:{cy0},'
                cmd=['ffmpeg','-nostdin','-v','error','-ss',str(vstart or 0),'-i',path,
                     '-t',f'{min(avail, seg*sp):.2f}',
                     '-vf',f'setpts=PTS/{sp:.4f},{cf}{vf_v}','-an','-c:v','qtrle','-y',out]
            else:
                vf=vf_fit if crop=='fit' else vf_fill
                cf=''
                if isinstance(crop,tuple):
                    cx0,cy0,cx1,cy1=crop
                    cf=f'crop={cx1-cx0}:{cy1-cy0}:{cx0}:{cy0},'
                cmd=['ffmpeg','-nostdin','-v','error','-loop','1','-t',f'{seg:.2f}','-i',path,
                     '-vf',cf+vf,'-c:v','qtrle','-y',out]
            subprocess.run(cmd,capture_output=True)
            parts.append(out)
        # склейка кадров шага + шапка сверху
        lst=f'{TMP}/l{step}.txt'
        open(lst,'w').write('\n'.join(f"file '{p}'" for p in parts)+'\n')
        body=f'{TMP}/b{step}.mov'
        subprocess.run(['ffmpeg','-nostdin','-v','error','-f','concat','-safe','0','-i',lst,
                        '-c','copy','-y',body],capture_output=True)
        panel=f'{TMP}/p{step}.mov'
        if hdr:
            cmd2=['ffmpeg','-nostdin','-v','error','-i',body,'-i',hdr,
                '-filter_complex',
                f"color=c=0x131517:s={pw}x{ph}:d={dur:.2f},format=rgba[bg];"
                f"[0:v]format=rgba[v];[1:v]format=rgba[h];"
                f"[bg][v]overlay=x=0:y={HEAD_H}[t1];[t1][h]overlay=x=0:y=0[o]",
                '-map','[o]']
        else:
            cmd2=['ffmpeg','-nostdin','-v','error','-i',body,
                '-filter_complex',
                f"color=c=0x131517:s={pw}x{ph}:d={dur:.2f},format=rgba[bg];"
                f"[0:v]format=rgba[v];[bg][v]overlay=x=0:y=0[o]",
                '-map','[o]']
        subprocess.run(cmd2+['-t',f'{dur:.2f}','-c:v','qtrle','-y',panel],capture_output=True)
        if CARD and not full:          # скруглить углы карточки маской
            mask=f'{TMP}/mask_{pw}x{ph}.png'
            if not os.path.exists(mask):
                m=Image.new('L',(pw*4,ph*4),0)
                ImageDraw.Draw(m).rounded_rectangle([0,0,pw*4-1,ph*4-1],
                                                    int(CARD.get('radius',30))*4,fill=255)
                m.resize((pw,ph),Image.LANCZOS).save(mask)
            rounded=f'{TMP}/c{step}.mov'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-i',panel,'-i',mask,
                '-filter_complex','[0:v]format=rgba[v];[1:v]format=gray[m];[v][m]alphamerge[o]',
                '-map','[o]','-c:v','qtrle','-y',rounded],capture_output=True)
            panel=rounded
        clips.append((panel,rs,re_,0 if full else (CARD.get('margin',40) if CARD else 0),
                      (1920 if full else Y_BOTTOM)-ph, ph))
        print(f'  {step} {title:<12} {len(items)} кадр(ов)  {rs:.2f}–{re_:.2f}')
    cmd=['ffmpeg','-nostdin','-v','error','-i',src]
    for c,*_ in clips: cmd+=['-i',c]
    fc=[]; last='0:v'
    for i,(c,rs,re_,xoff,ytop,ph) in enumerate(clips,1):
        fc.append(f"[{i}:v]setpts=PTS+{rs}/TB[q{i}]")
        if SLIDE>0:   # выезд снизу с замедлением
            y=f"'if(lt(t-{rs},{SLIDE}),{ytop}+{ph}*pow(1-(t-{rs})/{SLIDE},3),{ytop})'"
        else:
            y=str(ytop)
        fc.append(f"[{last}][q{i}]overlay=x={xoff}:y={y}:enable='between(t,{rs},{re_})'[w{i}]")
        last=f'w{i}'
    cmd+=['-filter_complex',';'.join(fc),'-map',f'[{last}]','-map','0:a',
          '-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p',
          '-c:a','copy','-movflags','+faststart','-y',dst]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: print(r.stderr[-900:]); sys.exit(1)
    shutil.rmtree(TMP,ignore_errors=True); print('готово:',dst)

if __name__=='__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else None)
