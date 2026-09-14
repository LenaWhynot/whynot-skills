#!/usr/bin/env python3

def _work():
    """Папка заказа: ZAVOD_WORK, иначе текущая."""
    import os as _o
    return _o.environ.get('ZAVOD_WORK') or _o.getcwd()

"""Чистка звука через Adobe Podcast Enhance Speech — обвязка вокруг ручного шага.

Adobe Enhance живёт только в браузере и требует входа в аккаунт, API у бесплатного
тарифа нет. Поэтому шаг ручной, а скрипт закрывает всё вокруг него.

  enhance_audio.py export IMG_6887 [IMG_6886 ...]
      Достаёт дорожку из исходника в `enhance-in/` как mp3 192k — это то,
      что кладётся в Adobe Podcast (https://podcast.adobe.com/en/enhance).

  enhance_audio.py ingest IMG_6887 ~/Downloads/IMG_6887\\ (enhanced).wav
      Кладёт результат в `raw-clean/IMG_6887.wav`, выровняв длину под исходник.
      Дальше `assemble.py` берёт звук ОТТУДА автоматически и отключает свой
      шумодав (иначе двойная обработка даёт «телефонный» голос).

  enhance_audio.py status
      Что уже почищено, а что нет.

⚠️ Длина результата должна совпадать с исходником с точностью до кадра — все планы
считаны по таймкодам исходника. Скрипт проверяет и подрезает/добивает тишиной,
но расхождение больше 0,3 с — это другой файл, и он его не примет.
"""
import os, subprocess, sys

B = _work()
RAW, IN, OUT = f'{B}/raw', f'{B}/enhance-in', f'{B}/raw-clean'


def dur(path):
    r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                        '-of','csv=p=0', path], capture_output=True, text=True)
    return float(r.stdout.strip())


def export(clips):
    os.makedirs(IN, exist_ok=True)
    for c in clips:
        src = f'{RAW}/{c}.MOV'
        if not os.path.exists(src):
            print(f'нет исходника: {c}'); continue
        dst = f'{IN}/{c}.mp3'
        subprocess.run(['ffmpeg','-nostdin','-v','error','-i',src,'-vn','-ac','1',
                        '-ar','48000','-c:a','libmp3lame','-b:a','192k','-y',dst],
                       check=True)
        print(f'{c}: {dur(src):.2f} с → {dst} ({os.path.getsize(dst)/1e6:.1f} МБ)')
    print(f'\nЗагрузить в https://podcast.adobe.com/en/enhance, результат вернуть:'
          f'\n  enhance_audio.py ingest <клип> <файл>')


def ingest(clip, path):
    src = f'{RAW}/{clip}.MOV'
    want, got = dur(src), dur(path)
    if abs(want - got) > 0.3:
        print(f'⚠️ длина не сходится: исходник {want:.2f} с, файл {got:.2f} с — '
              f'это точно тот клип?'); return
    os.makedirs(OUT, exist_ok=True)
    dst = f'{OUT}/{clip}.wav'
    # apad+t: добить тишиной или подрезать ровно под исходник
    subprocess.run(['ffmpeg','-nostdin','-v','error','-i',path,
                    '-af','apad','-t',f'{want:.3f}','-ac','1','-ar','48000',
                    '-c:a','pcm_s16le','-y',dst], check=True)
    print(f'{clip}: {got:.2f} → {dur(dst):.2f} с · {dst}')
    print('assemble.py теперь возьмёт звук отсюда и выключит свой шумодав.')


def status():
    have = {f[:-4] for f in os.listdir(OUT)} if os.path.isdir(OUT) else set()
    clips = sorted(f[:-4] for f in os.listdir(RAW) if f.endswith('.MOV'))
    for c in clips:
        print(f'{"✓" if c in have else " "} {c}')
    print(f'\nпочищено {len(have)} из {len(clips)}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'export':   export(sys.argv[2:])
    elif cmd == 'ingest': ingest(sys.argv[2], os.path.expanduser(sys.argv[3]))
    elif cmd == 'status': status()
    else: print(__doc__)
