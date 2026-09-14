import json,subprocess,numpy as np,os
import shutil as _shutil, os as _os
def _ff(name="ffmpeg"):
    """ffmpeg из PATH, иначе из папки, куда его кладёт мастер настройки плагина."""
    return _shutil.which(name) or _os.path.expanduser(f"~/.whynot-bin/{name}")
FF = _ff()
W=os.environ.get("WORKDIR") or os.getcwd()
plan=json.load(open(f"{W}/cut.json")); GW,GH=64,114
cache={}
def frames(src):
    if src in cache: return cache[src]
    raw=subprocess.run([FF,"-nostdin","-v","error","-i",f"{W}/proxy/{src}.mp4",
        "-vf",f"scale={GW}:{GH}","-pix_fmt","rgb24","-f","rawvideo","-"],capture_output=True).stdout
    n=len(raw)//(GW*GH*3); a=np.frombuffer(raw[:n*GW*GH*3],np.uint8).reshape(n,GH,GW,3).astype(np.float32)
    R,G,B=a[...,0],a[...,1],a[...,2]; lum=a.mean(3)
    skin=((R>95)&(G>40)&(B>20)&(R>G)&(R>B)&((R-G)>15))
    cache[src]=(np.where(skin,np.nan,lum),n); return cache[src]
def sig(src,t):
    s,n=frames(src); i=min(int(t*10),n-1); return s[i]
diffs=[]
print("состояние работы: разница с ПРЕДЫДУЩИМ шотом (только внутри одного исходника)")
for i in range(1,len(plan)):
    a,b=plan[i-1],plan[i]
    if a["src"]!=b["src"]: print(f"  {i-1:02d}→{i:02d}  — смена исходника"); continue
    ta=a["ss"]+a.get("span",a["d"])/2; tb=b["ss"]+b.get("span",b["d"])/2
    with np.errstate(invalid='ignore'):
        d=float(np.nanmean(np.abs(sig(a["src"],tb)-sig(a["src"],ta))))
    diffs.append((i,d)); print(f"  {i-1:02d}→{i:02d}  разница={d:6.2f}   {b.get('kind','')[:38]}")
if diffs:
    vals=[d for _,d in diffs]; p35=float(np.percentile(vals,35))
    print(f"\nп35 = {p35:.2f}  → подозрительные пары (одно состояние):")
    flag=[(i,d) for i,d in diffs if d<p35]
    for i,d in flag: print(f"  ⚠️  {i-1:02d}→{i:02d}  {d:.2f}  «{plan[i].get('kind','')}»")
    if not flag: print("  нет")
