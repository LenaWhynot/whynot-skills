import sys, subprocess, numpy as np
import shutil as _shutil, os as _os
def _ff(name="ffmpeg"):
    """ffmpeg из PATH, иначе из папки, куда его кладёт мастер настройки плагина."""
    return _shutil.which(name) or _os.path.expanduser(f"~/.whynot-bin/{name}")
FF = _ff()
# признаки по прокси: сетка 64x114 (портрет), 10 fps
src=sys.argv[1]; W,H=64,114
raw=subprocess.run([FF,"-nostdin","-v","error","-i",src,
    "-vf",f"scale={W}:{H}","-pix_fmt","rgb24","-f","rawvideo","-"],
    capture_output=True).stdout
n=len(raw)//(W*H*3)
a=np.frombuffer(raw[:n*W*H*3],np.uint8).reshape(n,H,W,3).astype(np.float32)
R,G,B=a[...,0],a[...,1],a[...,2]
lum=a.mean(3)
mx=a.max(3); mn=a.min(3)
sat=np.where(mx>0,(mx-mn)/np.maximum(mx,1),0)
skin=((R>95)&(G>40)&(B>20)&(R>G)&(R>B)&((R-G)>15))
d=np.zeros(n); shake=np.zeros(n); hand=np.zeros(n)
diff=np.abs(np.diff(lum,axis=0))
GTHR=np.percentile(diff,80)          # ГЛОБАЛЬНЫЙ порог по всему файлу
for i in range(1,n):
    dv=diff[i-1]
    d[i]=dv.mean()
    shake[i]=(dv>GTHR).mean()        # доля клеток выше него = едет камера
    s=skin[i-1]
    hand[i]=(dv*s).sum()/max(s.sum(),1)
skinfrac=skin.mean((1,2))
# резкость
gx=np.abs(np.diff(lum,axis=2)).mean((1,2)); gy=np.abs(np.diff(lum,axis=1)).mean((1,2))
sharp=gx+gy
# фон: движение в верхней трети (дальний план на макро) и правой трети
bg=np.zeros(n)
for i in range(1,n): bg[i]=diff[i-1][:H//3,:].mean()
white=((sat<0.16)&(lum>145)).mean((1,2))
np.savez(sys.argv[2], d=d, shake=shake, hand=hand, skin=skinfrac, sharp=sharp,
         bg=bg, white=white, lum=lum.mean((1,2)), sat=sat.mean((1,2)), n=n)
print(f"{src}: {n} кадров ({n/10:.1f}с)")
print(f"  тряска p55={np.percentile(shake,55):.4f} | рука p62={np.percentile(hand,62):.3f} | кожа медиана={np.median(skinfrac):.3f}")
print(f"  резкость p45={np.percentile(sharp,45):.2f} | фон p45={np.percentile(bg,45):.3f} | яркость медиана={np.median(lum.mean((1,2))):.0f}")
