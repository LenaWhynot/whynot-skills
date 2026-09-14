# Reel Decode — техчасть и грабли

## Что где

| Кусок | Где |
|---|---|
| Скачивание + нарезка + транскрипт | `scripts/reel_fetch.sh` |
| Транскрипция (faster-whisper) | `scripts/reel_transcribe.py` |
| Кэш видео/кадров | `~/.reel-cache/<id>/` (вне репо) |
| Банк разборов | папка `razbory/` в рабочем каталоге |
| Instagram без логина: подпись, метрики, слайды, хуки с обложек | [ig-bez-logina.md](ig-bez-logina.md) |

## Зависимости

- `yt-dlp`, `ffmpeg` — обязательны.
- `faster-whisper` в каком-нибудь python — опционально: без него будут кадры и подпись, но без речи.
  Берётся любой python, где он установлен; путь можно задать переменной `REEL_PY=/path/to/python`.
- Модель: `REEL_WHISPER` (по умолчанию `small`; на слабой машине или сервере с 2 ГБ RAM — `base`).

## Ручной путь — когда `scripts/` в скилле нет

Проверено 30.08.2026 (mac, публичный рилз, без cookies). Скрипт — обёртка ровно над этим,
так что при его отсутствии не искать и не переписывать, а выполнить четыре шага.

```bash
ID=<код_из_URL>; mkdir -p ~/.reel-cache/$ID && cd ~/.reel-cache/$ID
yt-dlp --no-warnings --merge-output-format mp4 --write-info-json   -o "video.%(ext)s" "https://www.instagram.com/reel/$ID/"
ffmpeg -v error -y -i video.mp4 -vn -ac 1 -ar 16000 audio.wav
```

Метрики и подпись — из `video.info.json`: `description` (подпись целиком), `like_count`,
`comment_count`, `uploader`, `upload_date`. `view_count` у Instagram обычно `None`,
длительности там нет — брать `ffprobe`.

Транскрипт (питон, в котором стоит faster-whisper):

```python
from faster_whisper import WhisperModel
m = WhisperModel('small', device='cpu', compute_type='int8')
segs, _ = m.transcribe('audio.wav', language='ru', vad_filter=True)
print('\n'.join(f'[{int(s.start//60)}:{int(s.start%60):02d}] {s.text.strip()}' for s in segs))
```

Кадры при необходимости: `ffmpeg -i video.mp4 -vf fps=<N>,tile=3x3 sheets/%02d.jpg`.

## Грабли

- **Из некоторых стран Instagram не отвечает**: `curl` может отдавать 200, а `yt-dlp` — виснуть на сессии. Тогда нужен VPN или машина в другой стране.
- **Публичный рилз качается БЕЗ логина и без cookies** — проверено 25.07.2026. Cookies нужны только для приватных/возрастных: `REEL_COOKIES=~/cookies.txt`.
- **Instagram отдаёт DASH** (видео и аудио отдельными потоками) — поэтому в скрипте `--merge-output-format mp4`, ffmpeg обязателен, иначе нет звука.
- **Длительности нет в info.json** у Instagram → берём из `ffprobe`, не из метаданных.
- Кадров всегда ≤60 (потолок), частота считается от длительности: короткий рилз ≈ 2 кадра/сек.
- Контактные листы `tile=3x3` → 9 кадров на картинку. Читать их, а не 46 отдельных кадров: те же данные, в разы меньше контекста.

## Если что-то сломалось

| Симптом | Причина / что делать |
|---|---|
| `Unable to download webpage ... Read timed out` | нет доступа к Instagram (VPN выключен / сеть режет) |
| `Requested content is not available` | пост приватный или удалён — сказать об этом честно |
| `transcript: faster-whisper не установлен` | поставить в venv или задать `REEL_PY` |
| пустой transcript при живом аудио | музыка без речи — это нормально, разбирать по кадрам |
| Не хватает памяти | `REEL_WHISPER=base` (или `tiny`), не `small`/`large` |

## Чистка кэша

`~/.reel-cache` растёт (~5 МБ на рилз). Раз в месяц: `find ~/.reel-cache -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +`
