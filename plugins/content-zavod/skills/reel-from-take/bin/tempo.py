#!/usr/bin/env python3
"""Честный темп речи: слова считаем только внутри блоков речи (энергия),
повторы дублей схлопываем, галлюцинации whisper отбрасываем."""
import json, os, re, sys

def _work():
    """Папка заказа: ZAVOD_WORK, иначе текущая."""
    import os as _o
    return _o.environ.get('ZAVOD_WORK') or _o.getcwd()

B=_work()
HALLU=re.compile(r'dimatorzok|субтитры|аплодисмент|продолжение следует|редактор субтитров|'
                 r'спасибо за (просмотр|внимание)|я не могу', re.I)

def norm(t):
    return re.sub(r'[^а-яёa-z ]','',t.lower()).strip()

def tempo(clip):
    energy=json.load(open(f'{B}/energy.json'))[clip]
    segs=[(s['offsets']['from']/1000,s['offsets']['to']/1000,s['text'].strip())
          for s in json.load(open(f'{B}/tc/{clip}.json'))['transcription']]
    seen=set(); words=0; dur=0.0; kept=[]
    for bs,be in energy['blocks']:
        txt=' '.join(t for (ss,se,t) in segs if se>bs and ss<be and t).strip()
        if not txt or HALLU.search(txt): continue
        key=norm(txt)[:60]
        if not key or key in seen: continue      # повтор того же дубля не считаем дважды
        seen.add(key)
        n=len(re.findall(r'[А-Яа-яЁёA-Za-z]+',txt))
        if n==0: continue
        words+=n; dur+=be-bs
        kept.append((bs,be,n,(be-bs),txt))
    return words,dur,kept

print(f'{"клип":<12} {"полезн.речь":>11} {"слов":>5} {"слов/мин":>9} {"сек/фразу":>10}  тема')
print('-'*78)
TOPIC={'IMG_6866':'A агент 5 шагов','IMG_6867':'A агент 20 минут','IMG_6880':'A агент 5 шагов',
       'IMG_6873':'H ремонт телефона','IMG_6874':'B вакансии','IMG_6875':'B вакансии',
       'IMG_6885':'F ассистент','IMG_6877':'C разбор кодекса','IMG_6882':'E AliExpress'}
rows=[]
for c in ['IMG_6866','IMG_6867','IMG_6880','IMG_6873','IMG_6874','IMG_6875','IMG_6885','IMG_6877','IMG_6882']:
    if not os.path.exists(f'{B}/tc/{c}.json'): continue
    w,d,kept=tempo(c)
    if d==0: continue
    wpm=w/(d/60)
    rows.append((wpm,c,w,d,len(kept)))
    print(f'{c:<12} {d:>10.0f}с {w:>5} {wpm:>9.0f} {d/max(1,len(kept)):>9.1f}с  {TOPIC.get(c,"")}')
print()
rows.sort(reverse=True)
print('самые динамичные:', ', '.join(f'{c} ({w:.0f})' for w,c,_,_,_ in rows[:3]))
