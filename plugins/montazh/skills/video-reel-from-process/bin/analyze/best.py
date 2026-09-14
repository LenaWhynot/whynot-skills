import sys, numpy as np
f=np.load(sys.argv[1]); A=float(sys.argv[2]); B=float(sys.argv[3]); d=float(sys.argv[4])
top=int(sys.argv[5]) if len(sys.argv)>5 else 6
hand=f["hand"]; shake=f["shake"]; sharp=f["sharp"]; bg=f["bg"]; skin=f["skin"]; white=f["white"]; n=int(f["n"])
P=lambda a,q: float(np.percentile(a,q))
L=int(d*10); rows=[]
for s in range(int(A*10), min(int(B*10), n-L)):
    w=slice(s,s+L)
    rows.append(dict(t=s/10, hand=hand[w].mean(), shake=shake[w].max(), sharp=sharp[w].mean(),
                     bg=bg[w].max(), skin=skin[w].mean(), white=white[w].mean()))
if not rows: print("  пусто"); sys.exit()
def filt(k):
    return [r for r in rows if r["shake"]<P(shake,min(99,55+k)) and r["hand"]>P(hand,max(1,62-k))
            and r["sharp"]>P(sharp,max(1,45-k)) and r["bg"]<P(bg,min(99,50+k))
            and (0.18-0.01*k/7)<r["skin"]<(0.47+0.01*k/7) and r["white"]<P(white,min(99,72+k))]
k=0; ok=filt(0)
while len(ok)<6 and k<42: k+=7; ok=filt(k)
ok.sort(key=lambda r:-r["hand"])
sel=[]
for r in ok:
    if all(abs(r["t"]-x["t"])>3.0 for x in sel): sel.append(r)
    if len(sel)>=top: break
print(f"[{A:.0f}-{B:.0f}с d={d}] ослабл={k//7}  тряска<{P(shake,min(99,55+k)):.3f} рука>{P(hand,max(1,62-k)):.2f}")
for r in sel:
    print(f"  @{r['t']:7.1f}  рука={r['hand']:6.2f} тряска={r['shake']:.3f} резк={r['sharp']:5.1f} кожа={r['skin']:.2f} фон={r['bg']:5.2f}")
