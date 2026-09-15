import sys, subprocess, os
import shutil as _shutil, os as _os
def _ff(name="ffmpeg"):
    """ffmpeg из PATH, иначе из папки, куда его кладёт мастер настройки плагина."""
    return _shutil.which(name) or _os.path.expanduser(f"~/.whynot-bin/{name}")
FF = _ff()
# strips.py <proxy> <out.png> <d> <t1> <t2> ...
src=sys.argv[1]; out=sys.argv[2]; d=float(sys.argv[3])
ts=[float(x) for x in sys.argv[4:]]; tmp=os.path.dirname(out); rows=[]
for i,t in enumerate(ts):
    o=f"{tmp}/_st{i:02d}.png"
    subprocess.run([FF,"-nostdin","-v","error","-ss",f"{t:.2f}","-t",f"{d:.2f}","-i",src,"-vf",
      f"fps={6/d:.3f},scale=150:267,drawtext=text='{t:.0f}':fontcolor=yellow:fontsize=20"
      f":box=1:boxcolor=black@0.9:x=2:y=2,tile=6x1:padding=2:color=0x222222",
      "-frames:v","1","-y",o],check=True); rows.append(o)
subprocess.run([FF,"-nostdin","-v","error"]+sum([["-i",r] for r in rows],[])+
  ["-filter_complex",f"{''.join(f'[{k}:v]' for k in range(len(rows)))}vstack={len(rows)}","-y",out],check=True)
print(out, len(rows),"полос")
