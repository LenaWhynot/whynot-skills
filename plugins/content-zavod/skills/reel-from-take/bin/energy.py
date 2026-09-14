import wave, array, math, os, glob, json

def _work():
    """Папка заказа: ZAVOD_WORK, иначе текущая."""
    import os as _o
    return _o.environ.get('ZAVOD_WORK') or _o.getcwd()


BASE = _work()
WIN = 0.25  # окно, с

def rms_track(path):
    w = wave.open(path, 'rb')
    sr, n = w.getframerate(), w.getnframes()
    data = array.array('h'); data.frombytes(w.readframes(n)); w.close()
    step = int(sr * WIN)
    out = []
    for i in range(0, len(data) - step, step):
        chunk = data[i:i+step]
        s = sum(float(x)*x for x in chunk) / len(chunk)
        db = 20*math.log10(math.sqrt(s)/32768) if s > 0 else -90
        out.append(db)
    return out, sr

res = {}
for f in sorted(glob.glob(f'{BASE}/audio/*.wav')):
    b = os.path.basename(f).replace('.wav','')
    track, sr = rms_track(f)
    if not track: continue
    peak = max(track)
    thr = peak - 22          # адаптивный порог: на 22 dB ниже пика клипа
    voiced = [i for i, v in enumerate(track) if v > thr]
    # склеиваем в блоки речи, паузу <0.6с игнорируем
    blocks = []
    if voiced:
        st = prev = voiced[0]
        for i in voiced[1:]:
            if (i - prev) * WIN > 0.6:
                blocks.append((st*WIN, (prev+1)*WIN)); st = i
            prev = i
        blocks.append((st*WIN, (prev+1)*WIN))
    blocks = [b_ for b_ in blocks if b_[1]-b_[0] >= 0.8]   # мусорные всплески вон
    res[b] = dict(peak=peak, thr=thr, blocks=blocks,
                  speech=sum(e-s for s,e in blocks), dur=len(track)*WIN)

json.dump(res, open(f'{BASE}/energy.json','w'), indent=1)

print(f"{'файл':<12} {'длит':>6} {'речь':>6} {'блоков':>7}  структура (границы блоков речи, с)")
print("-"*95)
for b, r in res.items():
    bl = r['blocks']
    s = "  ".join(f"{x:.0f}–{y:.0f}" for x, y in bl[:9])
    if len(bl) > 9: s += f"  …+{len(bl)-9}"
    print(f"{b:<12} {r['dur']:>5.0f}с {r['speech']:>5.0f}с {len(bl):>7}  {s}")
