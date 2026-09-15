"""Стабилизация одного шота: каждый кадр привязывается к ОПОРНОМУ (первому),
поэтому остаточного дрейфа нет вообще — для открывашки это то, что нужно.
Оценка на уменьшенной серой копии, применение — на нативном 4К.
"""
import sys, subprocess, numpy as np, cv2
import shutil as _shutil, os as _os
def _ff(name="ffmpeg"):
    """ffmpeg из PATH, иначе из папки, куда его кладёт мастер настройки плагина."""
    return _shutil.which(name) or _os.path.expanduser(f"~/.whynot-bin/{name}")
FF = _ff()
FF=FF
src, ss, dur, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
MARGIN = float(sys.argv[5]) if len(sys.argv)>5 else 0.06
SPEED  = float(sys.argv[6]) if len(sys.argv)>6 else 1.0   # для таймлапса
W,H,FPS = 2160,3840,30
VF=(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    + (f",setpts=PTS/{SPEED},fps={FPS}" if SPEED!=1.0 else f",fps={FPS}"))

def frames(scale=None):
    vf = VF + (f",scale={scale[0]}:{scale[1]}" if scale else "")
    w,h = scale if scale else (W,H)
    pix = "gray" if scale else "bgr24"; bpp = 1 if scale else 3
    p=subprocess.Popen([FF,"-nostdin","-v","error","-ss",str(ss),"-t",str(dur),"-i",src,
        "-vf",vf,"-pix_fmt",pix,"-f","rawvideo","-"],stdout=subprocess.PIPE)
    while True:
        buf=p.stdout.read(w*h*bpp)
        if len(buf)<w*h*bpp: break
        yield np.frombuffer(buf,np.uint8).reshape((h,w) if bpp==1 else (h,w,3))
    p.stdout.close(); p.wait()

# --- проход 1: оценка сдвига каждого кадра ОТНОСИТЕЛЬНО первого
SW,SH=270,480
small=[f.copy() for f in frames((SW,SH))]
ref=small[len(small)//2]
p0=cv2.goodFeaturesToTrack(ref,maxCorners=600,qualityLevel=0.01,minDistance=8,blockSize=7)
tr=[]
for f in small:
    p1,st,_=cv2.calcOpticalFlowPyrLK(ref,f,p0,None,winSize=(21,21),maxLevel=3)
    a,b=p0[st==1],p1[st==1]
    M,_=cv2.estimateAffinePartial2D(a,b,method=cv2.RANSAC,ransacReprojThreshold=2.0)
    if M is None: M=np.array([[1,0,0],[0,1,0]],np.float64)
    tr.append(M)
k=W/SW                                  # масштаб оценки → 4К
dx=[m[0,2]*k for m in tr]; dy=[m[1,2]*k for m in tr]
print(f"  кадров {len(small)} · сдвиг по X {min(dx):+.0f}…{max(dx):+.0f} px · "
      f"по Y {min(dy):+.0f}…{max(dy):+.0f} px (в 4К)")
need=max(max(abs(v) for v in dx), max(abs(v) for v in dy))/min(W,H)
print(f"  нужен запас {need*100:.1f}% · беру {MARGIN*100:.0f}%")

# --- проход 2: обратное преобразование + кроп полей + вывод 1080x1920
cw,ch=int(W*(1-2*MARGIN))//2*2, int(H*(1-2*MARGIN))//2*2
ox,oy=(W-cw)//2,(H-ch)//2
enc=subprocess.Popen([FF,"-nostdin","-v","error","-f","rawvideo","-pix_fmt","bgr24",
    "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-vf",f"crop={cw}:{ch}:{ox}:{oy},scale=1080:1920:flags=lanczos",
    "-an","-c:v","libx264","-preset","slow","-crf","19","-pix_fmt","yuv420p","-y",out],
    stdin=subprocess.PIPE)
for i,f in enumerate(frames()):
    M=tr[min(i,len(tr)-1)].copy()
    inv=cv2.invertAffineTransform(np.vstack([M,[0,0,1]])[:2])
    enc.stdin.write(cv2.warpAffine(f,inv,(W,H),flags=cv2.INTER_LANCZOS4,
                                   borderMode=cv2.BORDER_REPLICATE).tobytes())
enc.stdin.close(); enc.wait()
print("  →",out)
