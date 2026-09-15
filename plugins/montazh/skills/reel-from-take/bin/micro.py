#!/usr/bin/env python3
"""RMS с мелким окном в узком диапазоне — искать точки реза внутри фразы."""
import wave, array, math, sys, os

def _work():
    """Папка заказа: ZAVOD_WORK, иначе текущая."""
    import os as _o
    return _o.environ.get('ZAVOD_WORK') or _o.getcwd()

BASE=_work()
clip, lo, hi = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
win = float(sys.argv[4]) if len(sys.argv)>4 else 0.05
w=wave.open(f'{BASE}/audio/{clip}.wav','rb'); sr=w.getframerate()
w.setpos(int(lo*sr)); n=int((hi-lo)*sr)
d=array.array('h'); d.frombytes(w.readframes(n)); w.close()
step=int(sr*win); vals=[]
for i in range(0,len(d)-step,step):
    c=d[i:i+step]; s=sum(float(x)*x for x in c)/len(c)
    db=20*math.log10(math.sqrt(s)/32768) if s>0 else -90
    vals.append((lo+i/sr, db))
peak=max(v for _,v in vals)
print(f'пик {peak:.1f} dB · порог тишины {peak-24:.1f} dB · окно {win}с')
for t,v in vals:
    bar='█'*max(0,int((v+60)/2.2))
    quiet=' ← ТИХО' if v < peak-24 else ''
    print(f'{t:>7.2f} {v:>7.1f} {bar}{quiet}')
