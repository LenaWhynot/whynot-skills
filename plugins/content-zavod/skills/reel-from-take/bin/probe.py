import json, subprocess, os, glob, datetime

def _work():
    """Папка заказа: ZAVOD_WORK, иначе текущая."""
    import os as _o
    return _o.environ.get('ZAVOD_WORK') or _o.getcwd()


RAW = os.path.join(_work(), 'raw')
EXT = ('mov', 'mp4', 'm4v', 'mkv', 'avi')
files = sorted({f for e in EXT for f in
                glob.glob(os.path.join(RAW, f'*.{e}')) + glob.glob(os.path.join(RAW, f'*.{e.upper()}'))})

print(f"{'файл':<14} {'снято':<6} {'длит':>6} {'разрешение':<11} {'fps':>4} {'звук':<5} {'поворот':<8} {'кодек'}")
print("-" * 84)
total = 0.0
rows = []
for f in files:
    out = subprocess.run(['ffprobe','-v','error','-print_format','json',
                          '-show_format','-show_streams', f],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print(f"{os.path.basename(f):<14} ОШИБКА ffprobe: {out.stderr.strip()[:50]}")
        continue
    d = json.loads(out.stdout)
    v = next(s for s in d['streams'] if s['codec_type'] == 'video')
    a = [s for s in d['streams'] if s['codec_type'] == 'audio']
    dur = float(d['format']['duration'])
    total += dur
    rot = 0
    for sd in v.get('side_data_list', []) or []:
        if 'rotation' in sd:
            rot = sd['rotation']
    num, den = v.get('r_frame_rate', '0/1').split('/')
    fps = round(float(num)/float(den)) if float(den) else 0
    t = datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime('%H:%M')
    name = os.path.basename(f)
    print(f"{name:<14} {t:<6} {int(dur)//60}:{int(dur)%60:02d}".ljust(28) +
          f"{v['width']}x{v['height']:<6} {fps:>4} {'да' if a else 'НЕТ':<5} "
          f"{rot:<8} {v['codec_name']}")
    rows.append(dict(name=name, time=t, dur=dur, w=v['width'], h=v['height'],
                     fps=fps, audio=bool(a), rot=rot, codec=v['codec_name']))

print("-" * 84)
print(f"ИТОГО: {len(rows)} файлов, {int(total)//60} мин {int(total)%60} с материала")
json.dump(rows, open(os.path.join(_work(), 'probe.json'), 'w'),
          ensure_ascii=False, indent=1)
