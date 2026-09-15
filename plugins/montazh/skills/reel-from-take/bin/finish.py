#!/usr/bin/env python3
"""Финальный проход: шумодав + нормализация + фейды против щелчка на старте."""
import subprocess, sys, os

def dur(p):
    return float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
        '-of','csv=p=0',p],capture_output=True,text=True).stdout.strip())

def finish(src, dst):
    d=dur(src)
    af=('highpass=f=85,'
        'afftdn=nf=-25,'
        'equalizer=f=200:t=q:w=1.0:g=-2.5,'      # убираем бубнёж
        'equalizer=f=3500:t=q:w=1.2:g=3,'        # разборчивость
        'highshelf=f=8500:g=3,'                  # воздух
        'loudnorm=I=-14:TP=-1.5:LRA=11,'
        f'afade=t=in:st=0:d=0.10,'
        f'afade=t=out:st={max(0,d-0.25):.2f}:d=0.25')
    r=subprocess.run(['ffmpeg','-nostdin','-v','error','-i',src,'-af',af,
                      '-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000',
                      '-movflags','+faststart','-y',dst],capture_output=True,text=True)
    if r.returncode: print(r.stderr[-500:]); sys.exit(1)
    print(f'готово: {dst} ({dur(dst):.1f} с)')

if __name__=='__main__':
    finish(sys.argv[1], sys.argv[2])
