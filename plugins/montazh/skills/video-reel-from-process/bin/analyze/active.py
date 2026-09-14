# Окна, где рука РЕАЛЬНО работает: ранжирование по перцентилю активности внутри файла.
# Ловит две частые правки приёмки: «тут не рисует» и «увеличил на недоделанный результат».
import sys, numpy as np
import os
W=os.environ.get("WORKDIR") or os.getcwd()
src,A,B,d = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
top=int(sys.argv[5]) if len(sys.argv)>5 else 5
f=np.load(f"{W}/feat_{src}.npz")
hand,act,shake,sharp,bg,skin,lum=f["hand"],f["d"],f["shake"],f["sharp"],f["bg"],f["skin"],f["lum"]
n=int(f["n"]); L=int(d*10)
dark = np.median(skin)<0.15                 # тёмный файл — «рука» мертва, берём общее движение
metric = act if dark else hand
rows=[]
for s in range(int(A*10), min(int(B*10), n-L)):
    w=slice(s,s+L)
    mp=float((metric<metric[w].mean()).mean()*100)   # перцентиль активности внутри файла
    rows.append((mp, s/10, shake[w].mean(), shake[w].max(), sharp[w].mean(), bg[w].max(), skin[w].mean()))
rows=[r for r in rows if r[3]<0.45 and r[5]<4.5]     # без рывков камеры и без движения в фоне
sel=[]
for r in sorted(rows,key=lambda r:-r[0]):
    if all(abs(r[1]-x[1])>2.5 for x in sel): sel.append(r)
    if len(sel)>=top: break
print(f"[{src} {A:.0f}-{B:.0f}с d={d}] {'ТЁМНЫЙ, метрика=движение' if dark else 'метрика=рука'}")
for mp,t,shm,shx,sp,b,sk in sel:
    print(f"  @{t:6.1f}  активность={mp:3.0f}%  тряска ср={shm:.3f} max={shx:.3f}  резк={sp:5.1f} фон={b:4.2f} кожа={sk:.2f}")
