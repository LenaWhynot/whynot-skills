#!/usr/bin/env python3
"""Полная сборка вариантов рилса: тело один раз, дальше каждый заголовок
получает свои панели, субтитры и экранный текст.

  assemble.py <plan.json> <spec.json> [id ...]

plan: body + hooks; у заголовка кроме src/in/out есть "lines" — текст на экране
(он НЕ обязан совпадать с речью). Заголовок с src=null = вариант без заголовка.
У заголовка может быть "pieces": [[in,out],...] — несколько кусков (так вырезается
пауза внутри самого заголовка) и "drop": [i,...] — номера кусков тела, которые в этом
варианте не нужны (например когда тело дублирует мысль из заголовка).
spec: раскладка панелей, тайминги отсчитаны от НАЧАЛА ТЕЛА (без заголовка) —
сдвиг на длину конкретного заголовка скрипт делает сам.
"""
import json, os, subprocess, sys, shutil, tempfile


def _work():
    """Папка заказа: ZAVOD_WORK, иначе текущая."""
    return os.environ.get('ZAVOD_WORK') or os.getcwd()


B = _work()
SC = os.path.dirname(os.path.abspath(__file__))

# Папка со шрифтами субтитров (ZAVOD_FONTS), модель whisper.cpp для сабов (ZAVOD_MODEL).
FONTS = os.environ.get('ZAVOD_FONTS') or os.path.join(B, 'fonts')
MODEL = os.environ.get('ZAVOD_MODEL') or os.path.expanduser('~/models/whisper/ggml-large-v3-turbo.bin')  # путь по умолчанию, меняется ZAVOD_MODEL

VF = ('scale=1080:1920:force_original_aspect_ratio=increase,'
      'crop=1080:1920,fps=30,setsar=1')

# Правки расшифровки: слова, которые ваш whisper слышит неверно.
# Кладите в файл `fixes.json` в папке заказа: {"как слышит": "как надо"}.
_fx = os.path.join(B, 'fixes.json')
FIX = json.load(open(_fx)) if os.path.exists(_fx) else {}

SFX = os.path.join(B, 'sfx')

# Общая коррекция картинки. Пустая строка — не трогать кадр.
# Пример приглушённой экспозиции: LOOK="eq=brightness=-0.07"
LOOK = os.environ.get('ZAVOD_LOOK', '')

def run(cmd, label=''):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(f'ОШИБКА {label}:\n{r.stderr[-700:]}'); sys.exit(1)
    return r

def dur(p):
    return float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
        '-of','csv=p=0',p], capture_output=True, text=True).stdout.strip())

CLEAN = os.path.join(_work(), 'raw-clean')
USED_CLEAN = set()      # клипы, у которых звук взят из raw-clean (Adobe Enhance)


def render(src, tin, tout, dst):
    """Звук берём из `raw-clean/<клип>.wav`, если он там есть: это дорожка,
    прогнанная через Adobe Podcast Enhance Speech. Дорожка той же длины, что и
    исходник, поэтому -ss у обоих входов одинаковый."""
    clean = f'{CLEAN}/{src}.wav'
    cmd = ['ffmpeg','-nostdin','-v','error','-ss',str(tin),'-i',f'{B}/raw/{src}.MOV']
    if os.path.exists(clean):
        cmd += ['-ss',str(tin),'-i',clean,'-map','0:v','-map','1:a']
        USED_CLEAN.add(src)
    cmd += ['-t',str(round(tout-tin,3)),'-vf',VF,'-c:v','libx264','-preset','medium',
            '-crf','19','-pix_fmt','yuv420p','-af','aresample=async=1:first_pts=0',
            '-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-y',dst]
    run(cmd, dst)

def concat(parts, dst, tmp):
    lst = f'{tmp}/l_{os.path.basename(dst)}.txt'
    open(lst,'w').write(''.join(f"file '{p}'\n" for p in parts))
    run(['ffmpeg','-nostdin','-v','error','-f','concat','-safe','0','-i',lst,
         '-c','copy','-y',dst], 'concat')

def hook_ass(lines, end, path, size=104, x=80, y0=1130, step=95,
             outro=None, total=0.0):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Unbounded,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,204

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def tc(t):
        return f'{int(t//3600)}:{int(t//60)%60:02d}:{t%60:05.2f}'
    def ev(lines, a, b, x, y0, step):
        return ''.join(
            f'Dialogue: 1,{tc(a)},{tc(b)},Hook,,0,0,0,,'
            f'{{\\an7\\pos({x},{y0+i*step})\\fad(240,240)}}{t}\n'
            for i, t in enumerate(lines))
    body = ev(lines, 0.02, end, x, y0, step)
    # аутро — тот же крупный кегль, что у хука, но в конце ролика:
    # финальный призыв должен читаться так же крупно, как заголовок.
    if outro:
        o = outro
        osz = o.get('size', size)
        body += ev(o['lines'], max(0.1, total - o.get('len', 4.0)), total,
                   o.get('x', x), o.get('y', y0), int(osz * 0.91))
    open(path,'w').write(head+body)

def af_chain(total, enhanced):
    """enhanced=True — звук уже прошёл Adobe Enhance: свой шумодав НЕ включаем,
    иначе поверх уже вычищенной речи получается «телефонный» голос."""
    fades = f'afade=t=in:st=0:d=0.10,afade=t=out:st={max(0, total-0.25):.2f}:d=0.25'
    if enhanced:
        return ('highpass=f=95,equalizer=f=200:t=q:w=1.0:g=-1.5,'
                'loudnorm=I=-14:TP=-1.5:LRA=11,' + fades)
    return ('highpass=f=125,afftdn=nf=-40:nr=26,anlmdn=s=0.0006:p=0.004,'
            'agate=threshold=0.012:ratio=3:attack=10:release=220,'
            'equalizer=f=200:t=q:w=1.0:g=-2.5,'
            'equalizer=f=3500:t=q:w=1.2:g=3,highshelf=f=8500:g=3,'
            'loudnorm=I=-14:TP=-1.5:LRA=11,' + fades)


def subs_json(video, tmp):
    wav = f'{tmp}/a.wav'
    run(['ffmpeg','-nostdin','-v','error','-i',video,'-vn','-ac','1','-ar','16000','-y',wav],'wav')
    run(['whisper-cli','-m',MODEL,'-f',wav,'-l','ru','-oj','-of',f'{tmp}/subs'],'whisper')
    p = f'{tmp}/subs.json'; d = json.load(open(p))
    for s in d['transcription']:
        for a, b in FIX.items(): s['text'] = s['text'].replace(a, b)
    json.dump(d, open(p,'w'), ensure_ascii=False)
    return p

def shift_spec(spec_path, offset, tmp, cut=None):
    """cut — [(начало_в_теле, длительность)] выброшенных кусков: всё, что после них,
    едет назад ровно на их сумму."""
    d = json.load(open(spec_path))
    for s in d['steps']:
        back = sum(dd for st, dd in (cut or []) if st < s['from'])
        s['from'] = round(s['from']+offset-back, 2); s['to'] = round(s['to']+offset-back, 2)
    # логотипы-бейджи заданы в той же шкале, что и панели — двигаем вместе с ними
    for g in d.get('logos', []):
        back = sum(dd for st, dd in (cut or []) if st < g['start'])
        g['start'] = round(g['start']+offset-back, 2)
    p = f'{tmp}/spec.json'; json.dump(d, open(p,'w'), ensure_ascii=False)
    return p, d.get('sub_cy', 1260)

def main(plan_path, spec_path, only=None):
    plan = json.load(open(plan_path))
    out = f'{B}/versions'; os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='assemble_')
    try:
        parts = []
        for i, c in enumerate(plan['body']):
            p = f'{tmp}/b{i:03d}.mp4'; render(c['src'], c['in'], c['out'], p); parts.append(p)
        body = f'{tmp}/body.mp4'; concat(parts, body, tmp)
        print(f'тело: {len(parts)} кусков, {dur(body):.2f} с')
        # начало каждого куска в таймлайне тела — нужно, чтобы пересчитать панели при drop
        starts = []; acc = 0.0
        for c in plan['body']:
            starts.append(acc); acc += c['out']-c['in']

        made = []
        for h in plan['hooks']:
            if only and h['id'] not in only: continue
            raw = f'{tmp}/raw_{h["id"]}.mp4'
            drop = set(h.get('drop', []))
            if drop:   # в этом варианте тело своё — часть кусков выброшена
                keep = [p for i, p in enumerate(parts) if i not in drop]
                vbody = f'{tmp}/body_{h["id"]}.mp4'; concat(keep, vbody, tmp)
                print(f'    тело варианта: -{len(drop)} кусков, {dur(vbody):.2f} с')
            else:
                vbody = body
            if h.get('src'):
                hps = []
                for j, (a, b) in enumerate(h.get('pieces') or [(h['in'], h['out'])]):
                    hp = f'{tmp}/h_{h["id"]}_{j}.mp4'; render(h['src'], a, b, hp); hps.append(hp)
                hcat = f'{tmp}/hook_{h["id"]}.mp4'
                concat(hps, hcat, tmp) if len(hps) > 1 else shutil.copy(hps[0], hcat)
                concat([hcat, vbody], raw, tmp); hlen = dur(hcat)
            else:
                shutil.copy(vbody, raw); hlen = 0.0

            # все ли куски этого варианта взяли почищенный звук
            srcs = {c['src'] for c in plan['body']} | ({h['src']} if h.get('src') else set())
            enhanced = srcs.issubset(USED_CLEAN)
            clean = f'{tmp}/clean_{h["id"]}.mp4'
            run(['ffmpeg','-nostdin','-v','error','-i',raw,
                 '-af', af_chain(dur(raw), enhanced),
                 '-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000',
                 '-movflags','+faststart','-y',clean], 'finish')

            cut = [(starts[i], plan['body'][i]['out']-plan['body'][i]['in']) for i in sorted(drop)]
            # «дыхание» кадра: очень медленный наезд-отъезд, чтобы держать внимание.
            # Делается ДО панелей — панель не должна ездить вместе с лицом.
            spec_all = json.load(open(spec_path))
            text_end = max(hlen-0.25, 2.6)   # сколько держится текст на экране
            breathe = spec_all.get('breathe')
            look = spec_all.get('look', LOOK)     # '' в спеке = не трогать картинку
            if breathe or look:
                vf = []
                if breathe:
                    amp = breathe.get('amp', 0.03); per = breathe.get('period', 12)
                    vf.append(f"zoompan=z='{1.0+amp:.3f}+{amp:.3f}*sin(2*PI*on/(30*{per}))':"
                              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30")
                if look:
                    vf.append(look)
                # под крупным белым текстом хука кадр притемняем сильнее и плавно
                # отпускаем — иначе на светлой уличной съёмке текст «плывёт»
                dim = spec_all.get('hook_dim', 0.0)   # экспозиция ровная на весь ролик
                if dim and text_end > 0.3:
                    vf.append("eq=eval=frame:brightness='-%.3f*min(1\\,max(0\\,(%.2f-t)/0.5))'"
                              % (dim, text_end))
                graded = f'{tmp}/look_{h["id"]}.mp4'
                run(['ffmpeg','-nostdin','-v','error','-i',clean,'-vf',','.join(vf),
                     '-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p',
                     '-c:a','copy','-y',graded],'экспозиция/дыхание')
                clean = graded

            # Мягкая тень снизу под текстом хука. Притемнять весь кадр нельзя —
            # выглядит грязно; кладём градиент от прозрачного к тёмному к низу,
            # тогда белые буквы на светлой съёмке перестают «плыть».
            shade = spec_all.get('hook_shade')
            if shade and text_end > 0.3:
                from PIL import Image as _Im
                top = int(shade.get('top', 940))          # откуда начинается затемнение
                power = float(shade.get('strength', 0.45))  # 0..1 — сколько внизу
                png = f'{tmp}/shade_{h["id"]}.png'
                im = _Im.new('RGBA', (1080, 1920), (0, 0, 0, 0))
                px = im.load()
                for y in range(top, 1920):
                    t = (y - top) / max(1, 1919 - top)
                    a = int(255 * power * (t * t * (3 - 2 * t)))   # smoothstep
                    for x in range(1080):
                        px[x, y] = (0, 0, 0, a)
                im.save(png)
                shaded = f'{tmp}/shade_{h["id"]}.mp4'
                run(['ffmpeg','-nostdin','-v','error','-i',clean,'-i',png,
                     '-filter_complex',
                     f"[1:v]format=rgba,fade=t=out:st={max(0.1, text_end-0.45):.2f}:d=0.45:alpha=1[sh];"
                     f"[0:v][sh]overlay=0:0:enable='lt(t,{text_end:.2f})'[o]",
                     '-map','[o]','-map','0:a','-c:v','libx264','-preset','medium','-crf','19',
                     '-pix_fmt','yuv420p','-c:a','copy','-y',shaded],'тень под хуком')
                clean = shaded

            sp, cy = shift_spec(spec_path, hlen, tmp, cut)
            media = f'{tmp}/media_{h["id"]}.mp4'
            # низ кадра — либо запись экрана, либо нарисованные карточки
            builder = ('build_scenes.py' if json.load(open(spec_path)).get('kind') == 'scenes'
                       else 'media_panels.py')
            run(['python3',f'{SC}/{builder}',clean,media,sp], builder)

            # текст на экране держим либо весь заголовок, либо 2.6 с в варианте без него;
            # субтитры стартуют ПОСЛЕ него, иначе плашка лезет прямо в хук
            js = subs_json(clean, tmp)
            mov = f'{tmp}/subs_{h["id"]}.mov'
            run(['python3',f'{SC}/subs.py',js,mov,f'{text_end:.2f}',str(cy),'--style',spec.get('sub_style','vishnya')],'subs')

            ass = f'{tmp}/hook_{h["id"]}.ass'
            sz=h.get('size',104)
            hook_ass(h.get('lines',[]), text_end, ass, size=sz, step=int(sz*0.91),
                     outro=spec_all.get('outro'), total=dur(media))

            # логотип бренда в лок-ап с заголовком: держится ровно столько же,
            # сколько текст хука, и встаёт НАД первой строкой
            hl_cfg = spec_all.get('hook_logo')
            if hl_cfg:
                d_sp = json.load(open(sp, encoding='utf-8'))
                sz = hl_cfg.get('size', 150)
                d_sp.setdefault('logos', []).append({
                    'name': hl_cfg['name'], 'start': 0.05,
                    'len': round(max(0.6, text_end - 0.15), 2), 'at': 'xy',
                    'x': hl_cfg.get('x', 80),
                    'y': hl_cfg.get('y', 1130 - sz - 28), 'size': sz})
                json.dump(d_sp, open(sp, 'w', encoding='utf-8'), ensure_ascii=False)

            # логотипы брендов: руками из спеки или сами, там где бренд звучит
            lgm = f'{tmp}/logos_{h["id"]}.mov'
            run(['python3',f'{SC}/logo_badge.py',lgm,sp,js,'0',f'{text_end:.2f}'],'логотипы')

            final = f'{out}/reel_{h["id"]}.mp4'
            cmd = ['ffmpeg','-nostdin','-v','error','-i',media,'-i',mov]
            fc = ['[1:v]format=rgba[s]','[0:v][s]overlay=0:0:shortest=1[o]']
            if os.path.exists(lgm):
                cmd += ['-i',lgm]
                # eof_action=pass: слой логотипов короче ролика, shortest=1 обрезал бы ВИДЕО
                # по последнему бейджу — звук оставался, картинка кончалась
                fc += ['[2:v]format=rgba[g]','[o][g]overlay=0:0:eof_action=pass[o2]']
                last = '[o2]'
            else:
                last = '[o]'
            fc.append(f'{last}subtitles={ass}:fontsdir={FONTS}[v]')
            run(cmd + ['-filter_complex',';'.join(fc),
                 '-map','[v]','-map','0:a','-c:v','libx264','-preset','medium','-crf','19',
                 '-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart','-y',final],'final')
            sfx = spec_all.get('sfx', {'click_db': -22})
            if sfx and os.path.isdir(SFX):
                marks = [round(st['from'] + hlen - sum(dd for s0, dd in (cut or []) if s0 < st['from']), 2)
                         for st in spec_all.get('steps', [])]
                marks = [m for m in marks if 0.05 < m < dur(final) - 0.2]
                if marks:
                    withsfx = f'{tmp}/sfx_{h["id"]}.mp4'
                    cmd = ['ffmpeg','-nostdin','-v','error','-i',final]
                    for _ in marks: cmd += ['-i', f'{SFX}/click.wav']
                    fc = []
                    for j, m in enumerate(marks, 1):
                        fc.append(f'[{j}:a]adelay={int(m*1000)}|{int(m*1000)},'
                                  f'volume={sfx.get("click_db",-22)}dB[c{j}]')
                    fc.append('[0:a]' + ''.join(f'[c{j}]' for j in range(1, len(marks)+1))
                              + f'amix=inputs={len(marks)+1}:duration=first:dropout_transition=0:'
                                'normalize=0[a]')
                    cmd += ['-filter_complex', ';'.join(fc), '-map', '0:v', '-map', '[a]',
                            '-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000',
                            '-movflags','+faststart','-y', withsfx]
                    run(cmd, 'клики')
                    shutil.move(withsfx, final)
                    print(f'    кликов подмешано: {len(marks)}')

            made.append((h['id'], dur(final)))
            print(f'  ✓ {h["id"]:<20} {dur(final):5.2f} с  «{" ".join(h.get("lines",[]))}»')
        return made
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or None)
