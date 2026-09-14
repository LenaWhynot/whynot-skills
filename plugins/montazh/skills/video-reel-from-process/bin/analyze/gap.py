import sys,subprocess,numpy as np,os
import shutil as _shutil, os as _os
def _ff(name="ffmpeg"):
    """ffmpeg из PATH, иначе из папки, куда его кладёт мастер настройки плагина."""
    return _shutil.which(name) or _os.path.expanduser(f"~/.whynot-bin/{name}")
FF = _ff()
W=os.environ.get("WORKDIR") or os.getcwd()
src=sys.argv[1]; T0=float(sys.argv[2]); T1=float(sys.argv[3]); d=float(sys.argv[4])
chosen=[float(x) for x in sys.argv[5:]]
GW,GH=64,114
raw=subprocess.run([FF,"-nostdin","-v","error","-i",f"{W}/proxy/{src}.mp4",
    "-vf",f"scale={GW}:{GH}","-pix_fmt","rgb24","-f","rawvideo","-"],capture_output=True).stdout
n=len(raw)//(GW*GH*3); a=np.frombuffer(raw[:n*GW*GH*3],np.uint8).reshape(n,GH,GW,3).astype(np.float32)
R,G,B=a[...,0],a[...,1],a[...,2]; lum=a.mean(3)
skin=((R>95)&(G>40)&(B>20)&(R>G)&(R>B)&((R-G)>15))
sg=np.where(skin,np.nan,lum)
# «волосы»: тёмно-коричневая масса — голова художника, лезет снизу/сверху
hair=((R>35)&(R<150)&(R>B)&(lum<115)).mean((1,2))
f=np.load(f"{W}/feat_{src}.npz")
hand=f["hand"]; shake=f["shake"]; sharp=f["sharp"]
P=lambda x,q: float(np.percentile(x,q))
L=int(d*10); best=[]
for s in range(int(T0*10),min(int(T1*10),n-L)):
    w=slice(s,s+L)
    if shake[w].max()>P(shake,82): continue
    if hand[w].mean()<P(hand,45): continue
    if sharp[w].mean()<P(sharp,30): continue
    if hair[w].max()>0.14: continue                 # голова в кадре
    with np.errstate(invalid='ignore'):
        dist=min(np.nanmean(np.abs(sg[min(s+L//2,n-1)]-sg[min(int(c*10),n-1)])) for c in chosen)
    best.append((dist,s/10,hand[w].mean(),shake[w].max(),hair[w].max()))
best.sort(reverse=True)
print(f"{src} [{T0:.0f}-{T1:.0f}] d={d}  дальше всего от {chosen}:")
sel=[]
for dist,t,h,sh,hr in best:
    if all(abs(t-x)>8 for x in sel): sel.append(t); print(f"  @{t:7.1f} расст={dist:6.2f} рука={h:5.2f} тряска={sh:.3f} волосы={hr:.3f}")
    if len(sel)>=5: break
