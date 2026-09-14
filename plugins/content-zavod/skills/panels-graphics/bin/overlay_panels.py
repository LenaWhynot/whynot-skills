#!/usr/bin/env python3
"""Накладывает панели на видео: появление с фейдом и лёгким подъёмом."""
import json, subprocess, sys, os
# Низ панели в кадре и длительность фейда — через окружение, если надо иначе.
Y_BOTTOM=int(os.environ.get('PANEL_Y_BOTTOM', 1830))   # панель прижата к низу кадра
FADE=float(os.environ.get('PANEL_FADE', 0.22))
W_FRAME=int(os.environ.get('FRAME_WIDTH', 1080))

def main(src,dst,panels_json):
    P=json.load(open(panels_json))
    cmd=['ffmpeg','-nostdin','-v','error','-i',src]
    for p in P:
        d=p['end']-p['start']
        cmd+=['-loop','1','-t',f"{d:.3f}",'-i',p['file']]
    fc=[]; last='0:v'
    for i,p in enumerate(P,1):
        d=p['end']-p['start']; st=p['start']
        x=(W_FRAME-p['w'])//2
        ytop=Y_BOTTOM-p['h']
        fc.append(f"[{i}:v]format=rgba,"
                  f"fade=in:st=0:d={FADE}:alpha=1,"
                  f"fade=out:st={max(0,d-FADE):.3f}:d={FADE}:alpha=1,"
                  f"setpts=PTS+{st}/TB[p{i}]")
        out=f'v{i}'
        # лёгкий подъём при появлении
        yexpr=f"{ytop}+18*max(0\\,1-(t-{st})/0.30)"
        fc.append(f"[{last}][p{i}]overlay=x={x}:y='{yexpr}':"
                  f"enable='between(t,{st},{p['end']})'[{out}]")
        last=out
    cmd+=['-filter_complex',';'.join(fc),'-map',f'[{last}]','-map','0:a',
          '-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p',
          '-c:a','copy','-movflags','+faststart','-y',dst]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode:
        print(r.stderr[-1200:]); sys.exit(1)
    print('готово:',dst)

if __name__=='__main__':
    main(sys.argv[1],sys.argv[2],sys.argv[3])
