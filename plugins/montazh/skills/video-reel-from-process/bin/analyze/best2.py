# Вариант best.py для ТЁМНОГО исходника (яркость порядка 50-110):
# тёмная студия, цветной свет. Абсолютный порог яркости там выкашивает всё.
# Две замены, обе по SKILL.md:
#  1) коридор кожи — перцентили ЭТОГО файла, а не абсолютные 0.18-0.47:
#     детектор кожи требует R>95 и в темноте почти не срабатывает (медиана 0.059).
#  2) метрика активности — общее движение d, а не "движение кожи": там,
#     где маска кожи пустая, hand вырождается в шум.
import sys, numpy as np
f=np.load(sys.argv[1]); A=float(sys.argv[2]); B=float(sys.argv[3]); d=float(sys.argv[4])
top=int(sys.argv[5]) if len(sys.argv)>5 else 6
act=f["d"]; shake=f["shake"]; sharp=f["sharp"]; bg=f["bg"]; skin=f["skin"]; white=f["white"]
hand=f["hand"]; lum=f["lum"]; n=int(f["n"])
P=lambda a,q: float(np.percentile(a,min(99,max(1,q))))
SLO,SHI=P(skin,22),P(skin,92)
L=int(d*10); rows=[]
for s in range(int(A*10), min(int(B*10), n-L)):
    w=slice(s,s+L)
    rows.append(dict(t=s/10, act=act[w].mean(), hand=hand[w].mean(), shake=shake[w].max(),
                     sharp=sharp[w].mean(), bg=bg[w].max(), skin=skin[w].mean(),
                     white=white[w].mean(), lum=lum[w].mean()))
if not rows: print(f"[{A:.0f}-{B:.0f}] пусто"); sys.exit()
def filt(k):
    lo=SLO*(1-0.06*k/7); hi=SHI*(1+0.06*k/7)
    return [r for r in rows if r["shake"]<P(shake,55+k) and r["act"]>P(act,62-k)
            and r["sharp"]>P(sharp,45-k) and r["bg"]<P(bg,50+k)
            and lo<r["skin"]<hi and r["white"]<P(white,72+k)]
k=0; ok=filt(0)
while len(ok)<6 and k<42: k+=7; ok=filt(k)
ok.sort(key=lambda r:-r["act"])
sel=[]
for r in ok:
    if all(abs(r["t"]-x["t"])>3.0 for x in sel): sel.append(r)
    if len(sel)>=top: break
print(f"[{A:.0f}-{B:.0f}с d={d}] ослабл={k//7} кожа {SLO:.3f}-{SHI:.3f}  найдено {len(ok)}")
for r in sel:
    print(f"  @{r['t']:7.1f}  движ={r['act']:6.2f} рука={r['hand']:5.2f} тряска={r['shake']:.3f} "
          f"резк={r['sharp']:5.1f} кожа={r['skin']:.3f} фон={r['bg']:5.2f} ярк={r['lum']:5.1f}")
