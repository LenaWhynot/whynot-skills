# Рельс: Metricool

Рельс по умолчанию. Бесплатный тариф закрывает задачу целиком: платить не надо,
хостить нечего, коннектор ставится ссылкой.

## Подключение

**Claude → Settings → Connectors → Add custom connector →** `https://ai.metricool.com/mcp`
Вход по логину, ключей и `.env` не нужно.

Плюс для медиа: **Google Drive должен быть привязан в самом кабинете Metricool** —
иначе он не сможет скачать файл по ссылке. Это делает человек, один раз.

## Порядок вызовов

1. `getBrandSettings` → возьми `id` бренда (он же `blogId`) и `timezone`.
   Список подключённых сетей — в `networksData`.
2. `getBestTimeToPostByNetwork` (`brandId`, `socialNetwork`, `fromDate`, `toDate`, `timezone`).
3. `createScheduledPost` (`blogId`, `date`, `info`).
   В `info` минимум: `text`, `media` со ссылкой, `providers`, `publicationDate`
   и блок `networkData` для каждой сети из `providers`.
4. `getScheduledPosts` (`brandId`, `fromDate`, `toDate`, `timezone`) — убедиться, что встало.

## Площадки

| Умеет | Не умеет |
|---|---|
| Instagram (POST · REEL · **TRIAL_REEL** · STORY), Facebook, TikTok, YouTube, Threads, Pinterest, Google Business, Bluesky | **Telegram — вообще, никак.** LinkedIn и X — не на бесплатном тарифе |

`TRIAL_REEL` — пробный рилз: сначала виден только не-подписчикам. Формат по умолчанию
для непроверенной темы.

Флаги ИИ-контента: `isAiGenerated` в `instagramData`, `isAigc` в `tiktokData`
(только для видео), `isAiGeneratedContent` в `youtubeData`.

## Телефон

`autoPublish: false` — пост не уходит сам, вместо этого в мобильное приложение
Metricool прилетает уведомление, и человек публикует пальцем.
Это **не черновик**: черновик — `draft: true`.

## Лимиты и грабли

- **20 постов в месяц** на бесплатном тарифе. Счётчик сбрасывается 1-го числа.
  Пост в три сети считается за три.
- Часовой пояс правится в **Планировании, выпадашка рядом с текущим временем**;
  на уровне аккаунта — гамбургер вверху справа → настройки аккаунта.
- `videoThumbnailUrl` или `videoCoverMilliseconds`, посланные туда, где обложка
  не применима, роняют **весь** запрос ошибкой `VIDEO_THUMBNAIL_NOT_APPLICABLE`.
  Не слать спекулятивно.
- Story не имеет своей подписи: если Story — единственная сеть поста, текст не слать.
- «Лучшее время» в первые дни после подключения возвращает одинаковые значения
  на все семь дней. Это заглушка, а не аудитория. Не выдавать за персональный вывод.
- Первые сутки после подключения аналитика дырявая. Это нормально, не переподключать.
