#!/usr/bin/env python3
"""Уплотнитель. Из выбранных диапазонов выкидывает внутренние паузы и участки,
где взгляд ушёл. Границы кусков не ставит на моргание — это заметно на склейке."""
import wave, array, math, json, csv, os, sys, statistics

def _work():
    """Папка заказа: ZAVOD_WORK, иначе текущая."""
    import os as _o
    return _o.environ.get('ZAVOD_WORK') or _o.getcwd()


B = _work()
WIN = 0.05
MIN_PIECE   = 0.40   # короче — обрывок
KEEP_TAIL   = 0.12   # хвостик тишины, чтобы не рубить окончание слова
MIN_GAZE_OUT= 0.40   # уход взгляда короче считаем морганием
EDGE_GUARD  = 0.15   # на столько отступаем от границы, если там моргание

def rms(clip):
    w=wave.open(f'{B}/audio/{clip}.wav','rb'); sr=w.getframerate()
    d=array.array('h'); d.frombytes(w.readframes(w.getnframes())); w.close()
    step=int(sr*WIN); out=[]
    for i in range(0,len(d)-step,step):
        c=d[i:i+step]; s=sum(float(x)*x for x in c)/len(c)
        out.append((round(i/sr,3), 20*math.log10(math.sqrt(s)/32768) if s>0 else -90))
    return out

def gaze(clip):
    """-> (функция ok(t), функция score(t))"""
    p=f'{B}/gaze/{clip}_p.csv'
    if not os.path.exists(p): return (lambda t: True), (lambda t: 0.0)
    rows=list(csv.DictReader(open(p)))
    def n(r,k):
        try:
            v=float(r[k]); return None if v!=v else v
        except: return None
    # База — по кадрам, где голова смотрит прямо. По всему клипу медиана уезжает,
    # если человек подолгу смотрит в заметки.
    good=[r for r in rows if r['face']=='1' and n(r,'dx') is not None
          and abs(n(r,'yaw') or 9)<0.15 and abs(n(r,'pitch') or 9)<0.25]
    if len(good)<20:
        good=[r for r in rows if r['face']=='1' and n(r,'dx') is not None]
    mdx=statistics.median([n(r,'dx') for r in good]) if good else 0
    mdy=statistics.median([n(r,'dy') for r in good]) if good else 0
    tab={}
    for r in rows:
        t=float(r['t'])
        if r['face']=='0': tab[t]=9.9; continue
        dx,dy,eo=n(r,'dx'),n(r,'dy'),n(r,'eyeOpen')
        if dx is None or dy is None: tab[t]=9.9; continue
        s=max(abs(dx-mdx)/0.08, abs(dy-mdy)/0.15)
        if eo is not None and eo<0.15: s=max(s,1.5)
        tab[t]=s
    ks=sorted(tab)
    def score(t):
        if not ks: return 0.0
        k=min(ks,key=lambda x:abs(x-t)); return tab[k]
    return (lambda t: score(t)<=1.0), score

def densify(clip, ranges, thr_off=22.0, ignore_gaze=False):
    track=rms(clip); ok,score=gaze(clip); out=[]
    for a,b in ranges:
        seg=[(t,v) for t,v in track if a<=t<b]
        if not seg: continue
        peak=max(v for _,v in seg); thr=peak-thr_off
        voiced=[v>thr for _,v in seg]
        # маска: речь есть И взгляд не ушёл надолго
        gz=[True]*len(seg) if ignore_gaze else [ok(t) for t,_ in seg]
        run=0
        for i in range(len(gz)):
            if not gz[i]: run+=1
            else:
                if run*WIN<MIN_GAZE_OUT:            # короткий уход = моргание, прощаем
                    for j in range(i-run,i): gz[j]=True
                run=0
        if run and run*WIN<MIN_GAZE_OUT:
            for j in range(len(gz)-run,len(gz)): gz[j]=True
        keep=[voiced[i] and gz[i] for i in range(len(seg))]
        pieces=[]; st=None; gap=0
        for i,(t,_) in enumerate(seg):
            if keep[i]:
                if st is None: st=t
                gap=0
            elif st is not None:
                gap+=WIN
                if gap>=0.25:
                    pieces.append((st, t-gap+KEEP_TAIL)); st=None; gap=0
        if st is not None: pieces.append((st, seg[-1][0]+WIN))
        for s,e in pieces:
            if e-s<MIN_PIECE: continue
            # границу не ставим на моргание
            if not ignore_gaze:
                while score(s)>1.0 and e-s>MIN_PIECE: s+=EDGE_GUARD
                while score(e)>1.0 and e-s>MIN_PIECE: e-=EDGE_GUARD
            out.append((round(max(a,s-0.08),2), round(min(b,e+KEEP_TAIL),2)))
    merged=[]
    for s,e in out:
        if merged and s-merged[-1][1]<0.12: merged[-1]=(merged[-1][0],e)
        else: merged.append((s,e))
    return merged

if __name__=='__main__':
    clip=sys.argv[1]
    rngs=[tuple(map(float,x.split(':'))) for x in sys.argv[2:]]
    res=densify(clip,rngs)
    print(f'{clip}: {len(rngs)} → {len(res)} кусков, {sum(e-s for s,e in res):.1f} с')
    for s,e in res: print(f'  {s:>7.2f}–{e:<7.2f} {e-s:>4.1f}с')
