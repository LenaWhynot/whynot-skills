#!/usr/bin/env python3
"""Разведка: кто снимает про вашу тему прямо сейчас.

    APIFY_TOKEN=... python3 scan.py вайбкодинг vibecoding нейросети
    APIFY_TOKEN=... python3 scan.py --limit 15 --out razvedka.json слово1 слово2

Дёргает актор apify/instagram-hashtag-scraper, чистит выдачу и ранжирует у себя:
сортировки по популярности у актора НЕТ, приходит «как легло».

Что делает сверх сбора:
  · выбрасывает дубли (один пост приходит по двум близким словам — платится дважды);
  · отбрасывает likesCount = -1 (это не ноль, а «автор скрыл счётчик»);
  · считает отношение комментарии/лайки — больше 1 обычно значит воронку
    «напиши слово в комментарии»;
  · помечает язык подписи, чтобы отсеять чужие рынки (в пробе шума было 37%).

⚠️ Число подписчиков актор не отдаёт. Без него нельзя сказать, держится автор на приёме
или на тираже: к/л > 1 у большого аккаунта ничего не значит. Подписчиков добирать
вручную по тем, кого берёте в разбор.
⚠️ Данные в Apify живут 7 дней на бесплатном плане — выгружайте сразу, этот скрипт
и пишет файл.
"""
import json, os, re, sys, urllib.request, urllib.error

ACTOR = "apify~instagram-hashtag-scraper"
API = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"


def run(tags, limit, token):
    body = json.dumps({"hashtags": tags, "resultsType": "reels",
                       "resultsLimit": limit}).encode()
    req = urllib.request.Request(f"{API}?token={token}", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Apify ответил {e.code}: {e.read().decode()[:300]}")


def lang(text):
    if re.search(r'[一-鿿]', text): return "zh"
    if re.search(r'[؀-ۿ]', text): return "fa/ar"
    if re.search(r'[а-яё]', text, re.I): return "ru"
    if re.search(r'[ãõáéçñ]', text, re.I): return "pt/es"
    return "en"


def main():
    args = sys.argv[1:]
    limit, out = 15, "razvedka.json"
    tags = []
    it = iter(range(len(args)))
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--limit": limit = int(args[i+1]); i += 2
        elif a == "--out": out = args[i+1]; i += 2
        else: tags.append(a); i += 1
    if not tags:
        sys.exit(__doc__)
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("нет APIFY_TOKEN в окружении")

    print(f"слов: {len(tags)} × {limit} постов ≈ ${len(tags)*limit*0.0026:.2f}")
    items = run(tags, limit, token)
    print(f"пришло записей: {len(items)}")

    seen, rows = set(), []
    for it_ in items:
        sc = it_.get("shortCode") or it_.get("id")
        if not sc or sc in seen:
            continue
        seen.add(sc)
        likes = it_.get("likesCount")
        likes = None if likes in (None, -1) else likes
        views = it_.get("videoPlayCount") or it_.get("igPlayCount") or 0
        comm = it_.get("commentsCount") or 0
        cap = (it_.get("caption") or "").replace("\n", " ")
        rows.append({
            "просмотры": views, "лайки": likes, "комментарии": comm,
            "к/л": round(comm / likes, 2) if likes else None,
            "дата": (it_.get("timestamp") or "")[:10],
            "сек": round(it_.get("videoDuration") or 0),
            "автор": it_.get("ownerUsername"),
            "язык": lang(cap),
            "подпись": cap[:110],
            "ссылка": f"https://www.instagram.com/reel/{sc}/",
            "видео": it_.get("videoUrl"),
        })

    rows.sort(key=lambda r: -r["просмотры"])
    json.dump(rows, open(out, "w"), ensure_ascii=False, indent=1)
    dupes = len(items) - len(rows)

    print(f"уникальных: {len(rows)} (дублей {dupes})  → {out}\n")
    print(f"{'просм':>7} {'к/л':>5} {'сек':>4} {'язык':<6} {'автор':<22} подпись")
    print("-" * 100)
    for r in rows[:25]:
        kl = f"{r['к/л']:.2f}" if r["к/л"] is not None else "  —"
        print(f"{r['просмотры']:>7} {kl:>5} {r['сек']:>4} {r['язык']:<6} "
              f"{(r['автор'] or '')[:22]:<22} {r['подпись'][:52]}")
    ru = [r for r in rows if r["язык"] == "ru"]
    print(f"\nна русском: {len(ru)} из {len(rows)}")
    funnel = [r for r in rows if (r["к/л"] or 0) > 1]
    if funnel:
        print("воронка в комментариях (к/л > 1) — проверить подписчиков вручную:")
        for r in funnel:
            print(f"  @{r['автор']}  к/л {r['к/л']}  {r['просмотры']} просм  {r['ссылка']}")


if __name__ == "__main__":
    main()
