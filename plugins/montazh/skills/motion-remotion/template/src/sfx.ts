import type { Beat, Captions, Storyboard } from "./types";

/** Один удар: когда, чем, с какой громкостью. */
export type Hit = { at: number; id: string; gain: number };

// Уровни из плейбука, выставленные против голоса, пикующего около −7 dB.
const G = {
  pop: 0.32, click: 0.34, whoosh: 0.30, whip: 0.30, stamp: 0.5, impact: 0.5,
  tick: 0.42, chaching: 0.4, shimmer: 0.3, ding: 0.34, riser: 0.28,
  scratch: 0.36, ignite: 0.34,
};

const MONEY = /[₽$%]|тысяч|рубл/i;

/**
 * Звук расставляется НЕ на такты, а на слова и на доли анимации:
 * тик каунт-апа совпадает со сменой цифры, зачёркивание — с прорисовкой линии.
 * Плейбук: «удар ставится на само слово, а не в начало предложения».
 */
export const sfxPlan = (sb: Storyboard | null, caps: Captions | null): Hit[] => {
  const hits: Hit[] = [];
  const beats: Beat[] = sb?.beats ?? [];

  beats.forEach((b, i) => {
    const prev = beats[i - 1];
    // вход такта: в full входим ударом, смена режима — хлыстом, иначе вуш
    if (b.mode === "full") hits.push({ at: b.start, id: "bass-impact", gain: G.impact });
    else if (prev && prev.mode !== b.mode) hits.push({ at: b.start, id: "whip", gain: G.whip });
    else hits.push({ at: b.start, id: "whoosh", gain: G.whoosh });

    const c = b.card;
    switch (c.type) {
      case "countup": {
        // тики идут ровно столько, сколько бежит счётчик (1.1 с)
        for (let t = 0.06; t < 1.1; t += 0.095) hits.push({ at: b.start + t, id: "tick", gain: G.tick });
        hits.push({ at: b.start + 1.12, id: c.tone === "red" ? "ding" : "shimmer", gain: G.shimmer });
        break;
      }
      case "stamp":
        hits.push({ at: b.start + 0.68, id: "stamp-slam", gain: G.stamp });
        break;
      case "list": {
        c.items.forEach((_, k) => {
          hits.push({ at: b.start + k * 0.4, id: "click", gain: G.click });
          hits.push({ at: b.start + k * 0.4 + 0.5, id: "pen-scratch", gain: G.scratch });
        });
        hits.push({ at: b.start + c.items.length * 0.4 + 0.5, id: "shimmer", gain: G.shimmer });
        break;
      }
      case "beforeafter":
        hits.push({ at: b.start + 0.02, id: "ui-pop", gain: G.pop });
        hits.push({ at: b.start + 0.55, id: "shimmer", gain: G.shimmer });
        break;
      case "takeover":
        hits.push({ at: b.start + 0.02, id: "ignite", gain: G.ignite });
        break;
      case "shot":
        hits.push({ at: b.start + 0.02, id: "ui-pop", gain: G.pop });
        if (c.highlight) hits.push({ at: b.start + 0.55, id: "click", gain: G.click });
        break;
      case "cta":
        hits.push({ at: Math.max(0, b.start - 1.1), id: "riser", gain: G.riser });
        hits.push({ at: b.start + 0.5, id: "ding", gain: G.ding });
        break;
      default:
        break;
    }
  });

  // денежная строка звучит кассой — на самом слове, не на фразе
  for (const ch of caps?.chunks ?? []) {
    if (ch.num || MONEY.test(ch.text)) {
      const w = ch.words.find((x) => MONEY.test(x.text) || /\d/.test(x.text)) ?? ch.words[0];
      if (w) hits.push({ at: w.start, id: "cha-ching", gain: G.chaching });
    }
  }

  return hits.sort((a, b) => a.at - b.at);
};
