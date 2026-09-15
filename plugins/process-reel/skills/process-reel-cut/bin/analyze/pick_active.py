# Кандидаты, отобранные по ЖИВОСТИ окна: минимум «мёртвых» кадров (рука ниже p40),
# при ограничении на тряску. Именно это правило я упустил, когда чинил тряску:
# устойчивое окно легко оказывается окном, где рука стоит.
import sys, numpy as np
f=np.load(sys.argv[1]); A=float(sys.argv[2]); B=float(sys.argv[3]); d=float(sys.argv[4])
top=int(sys.argv[5]) if len(sys.argv)>5 else 6
hand=f["hand"]; shake=f["shake"]; sharp=f["sharp"]; bg=f["bg"]; skin=f["skin"]; n=int(f["n"])
P=lambda a,q: float(np.percentile(a,q))
# пороги СТАДИИ, а не всего файла: во второй половине рука двигается тише в принципе,
# и глобальный p40 красит всю позднюю часть в «мёртвую»
seg=hand[int(A*10):int(B*10)]
DEAD=float(np.percentile(seg,45)); SH=P(shake,75); SP=P(sharp,40); BG=P(bg,70)
L=int(d*10); rows=[]
for s in range(int(A*10), min(int(B*10), n-L)):
    w=slice(s,s+L)
    if shake[w].max()>SH: continue
    if sharp[w].mean()<SP: continue
    if bg[w].max()>BG: continue
    if not (0.20<skin[w].mean()<0.47): continue
    rows.append((float((hand[w]<DEAD).mean()), -float(hand[w].mean()), s/10,
                 float(shake[w].max()), float(hand[w].min())))
if not rows: print("  пусто (ослабь окно)"); sys.exit()
rows.sort()
sel=[]
for r in rows:
    if all(abs(r[2]-x[2])>2.5 for x in sel): sel.append(r)
    if len(sel)>=top: break
print(f"[{A:.0f}-{B:.0f}с d={d}]  мёртвый кадр = рука<{DEAD:.2f} · тряска<{SH:.3f}")
for dead,negh,t,sh,hmin in sel:
    print(f"  @{t:7.1f}  мёртвых={dead*100:3.0f}%  рука ср={-negh:5.2f} min={hmin:5.2f}  тряска={sh:.3f}")
