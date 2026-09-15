#!/usr/bin/env python3
import json, csv, os, sys

def _work():
    """Папка заказа: ZAVOD_WORK, иначе текущая."""
    import os as _o
    return _o.environ.get('ZAVOD_WORK') or _o.getcwd()

BASE = _work()

def gaze(clip):
    out={}
    for r in csv.DictReader(open(f'{BASE}/gaze/{clip}.csv')):
        t=float(r['t'])
        if r['face']=='0': out[t]=False; continue
        def n(k):
            try:
                v=float(r[k]); return None if v!=v else v
            except: return None
        e,p,y=n('eyeOpen'),n('pitch'),n('yaw')
        out[t]=bool(e is not None and p is not None and e>=0.24 and p<0.38 and (y is None or abs(y)<0.45))
    return out

def pct(g,a,b):
    ks=[t for t in g if a-0.125<=t<b+0.125]
    return None if not ks else sum(1 for t in ks if g[t])/len(ks)*100

clip=sys.argv[1]
g=gaze(clip)
segs=[(s['offsets']['from']/1000, s['offsets']['to']/1000, s['text'].strip())
      for s in json.load(open(f'{BASE}/tc/{clip}.json'))['transcription']]
blocks=json.load(open(f'{BASE}/energy.json'))[clip]['blocks']
print(f'=== {clip} — фразы по блокам речи ===')
print(f'{"#":>3} {"время":<15} {"длит":>5} {"взгляд":>7}  текст')
print('-'*100)
prev=None
for i,(bs,be) in enumerate(blocks,1):
    txt=' '.join(t for (ss,se,t) in segs if se>bs and ss<be and t).strip()
    p=pct(g,bs,be)
    gap=f'  ⏸{bs-prev:.1f}с' if prev is not None and bs-prev>0.4 else ''
    mark='—' if p is None else f'{p:.0f}%'
    print(f'{i:>3} {bs:>6.2f}–{be:<7.2f} {be-bs:>4.1f}с {mark:>7}  {txt[:78]}{gap}')
    prev=be
