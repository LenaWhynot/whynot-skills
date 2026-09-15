import { loadFont as loadOswald } from "@remotion/google-fonts/Oswald";
import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FPS, LIME, SUB_LEAD, type SubWord } from "./ReelKit";

// ─────────────────────────────────────────────────────────────
// Кинетическая типографика в духе референса @anyway.julia.
// Вместо ленты-караоке снизу — фразы падают стопкой сверху вниз,
// каждая попает В ТАКТ голосу (пословные тайминги whisper из subs.json).
// Две гарнитуры: жирный гротеск строчными (нарратив) + сериф-курсив
// на смысловых акцентах. Акцент — лаймовый токен системы, не выдуманный цвет.
//
// Кириллица: Anton из референса её не знает, поэтому гротеск = Oswald
// (узкий, тяжёлый, кириллица есть), сериф = Playfair Display italic.
// ─────────────────────────────────────────────────────────────

const { fontFamily: GROTESK } = loadOswald("normal", {
  weights: ["500", "700"],
  subsets: ["latin", "cyrillic"],
});

const { fontFamily: SERIF } = loadPlayfair("italic", {
  weights: ["500", "700"],
  subsets: ["latin", "cyrillic"],
});

export type KineticPhrase = { words: SubWord[]; accent: boolean };

// Куда прижать стопку фраз внутри кадра.
export type KineticAnchor = "center" | "top" | "bottom";

const BREAK_AFTER = /[,.:;!?…]$/;
const strip = (w: string) => w.replace(/[^\p{L}\p{N}]/gu, "").toLowerCase();

// Строка не может заканчиваться служебным словом — иначе предлог висит
// в конце фразы, а его существительное уезжает на следующую.
const NO_HANG = new Set([
  "в", "во", "на", "над", "под", "за", "из", "от", "до", "по", "про", "у", "к", "ко",
  "с", "со", "о", "об", "при", "для", "без", "через", "и", "а", "но", "или", "да",
  "что", "чтобы", "как", "если", "когда", "чем", "то", "же", "бы", "ли", "не", "ни",
  "мой", "моя", "мои", "ваш", "ваша", "ваши", "свой", "своя", "свои", "этот", "эта",
  "эти", "весь", "вся", "всё", "все", "который", "которая", "которые", "себе", "ещё",
]);

// Разбивка реплики на фразы: рвём по знакам препинания и по длине,
// чтобы строка влезала в кадр и читалась одним взглядом.
export const toPhrases = (
  subs: SubWord[],
  accentWords: string[] = [],
  maxWords = 3,
  maxChars = 22,
): KineticPhrase[] => {
  const accents = new Set(accentWords.map(strip));
  const out: KineticPhrase[] = [];
  let cur: SubWord[] = [];
  const flush = () => {
    if (!cur.length) return;
    out.push({ words: cur, accent: cur.some((w) => accents.has(strip(w.w))) });
    cur = [];
  };
  for (const w of subs) {
    cur.push(w);
    const chars = cur.reduce((n, x) => n + x.w.length + 1, 0);
    const wantBreak = BREAK_AFTER.test(w.w) || cur.length >= maxWords || chars >= maxChars;
    // предлог/союз в конце строки не оставляем — тянем до знаменательного слова
    const hangs = NO_HANG.has(strip(w.w)) && !BREAK_AFTER.test(w.w);
    if (wantBreak && (!hangs || cur.length >= maxWords + 2)) flush();
  }
  flush();
  return out;
};

// Кегль под ширину кадра: Oswald узкий (~0.42em на символ), Playfair шире.
// Кегль под ширину кадра. Оценка ширины символа с запасом: Playfair italic
// заметно шире Oswald, а строка не должна упираться в края даже со сдвигом.
const NUDGE = 46;
const fitSize = (text: string, accent: boolean) => {
  const usable = 940 - NUDGE;
  const perChar = accent ? 0.58 : 0.46;
  const ideal = accent ? 116 : 110;
  return Math.min(ideal, Math.round(usable / (perChar * Math.max(text.length, 1))));
};

const Phrase: React.FC<{
  phrase: KineticPhrase;
  index: number;
  t: number;
  cardOpacity: number;
}> = ({ phrase, index, t, cardOpacity }) => {
  const { fps } = useVideoConfig();
  const text = phrase.words.map((w) => w.w).join(" ");
  const start = phrase.words[0].s;
  // попадание в такт: пружина стартует ровно на первом слове фразы
  const pop = spring({
    frame: (t - start) * fps,
    fps,
    config: { damping: 14, mass: 0.5, stiffness: 140 },
    durationInFrames: 14,
  });
  const appeared = t >= start;
  const scale = interpolate(pop, [0, 1], [0.86, 1]);
  const shiftY = interpolate(pop, [0, 1], [26, 0]);
  const size = fitSize(text, phrase.accent);
  // Лёгкий разброс по горизонтали, чтобы стопка не выглядела списком.
  // Длинную строку (кегль ужат под ширину) не двигаем — уедет за край.
  const wide = size < (phrase.accent ? 116 : 110);
  const nudge = wide ? 0 : index % 3 === 1 ? -NUDGE : index % 3 === 2 ? NUDGE : 0;

  return (
    <div
      style={{
        fontFamily: phrase.accent ? SERIF : GROTESK,
        fontStyle: phrase.accent ? "italic" : "normal",
        fontWeight: 700,
        fontSize: size,
        maxWidth: 940,
        lineHeight: 1.06,
        letterSpacing: phrase.accent ? "0.01em" : "-0.01em",
        color: phrase.accent ? LIME : "#FFFFFF",
        textShadow: "0 3px 18px rgba(0,0,0,0.6)",
        opacity: (appeared ? pop : 0) * cardOpacity,
        transform: `translateX(${nudge}px) translateY(${shiftY}px) scale(${scale})`,
        transformOrigin: "center",
        whiteSpace: "pre",
      }}
    >
      {text}
    </div>
  );
};

// Слой кинетического текста поверх карточки. Занимает место всеми фразами
// сразу (прозрачными), поэтому появление новой строки не сдвигает предыдущие.
export const KineticText: React.FC<{
  subs: SubWord[];
  dur: number;
  accentWords?: string[];
  anchor?: KineticAnchor;
  lead?: number;
}> = ({ subs, dur, accentWords = [], anchor = "center", lead = SUB_LEAD }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS - lead;
  const phrases = toPhrases(subs, accentWords);

  const cardOpacity =
    interpolate(frame, [0, 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) *
    interpolate(frame, [dur - 7, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const box: React.CSSProperties =
    anchor === "top"
      ? { justifyContent: "flex-start", padding: "260px 70px 0" }
      : anchor === "bottom"
        ? { justifyContent: "flex-end", padding: "0 70px 300px" }
        : { justifyContent: "center", padding: "180px 70px 240px" };

  return (
    <>
      {/* мягкий подпал под текст: на светлых фото белый гротеск иначе тонет */}
      <AbsoluteFill
        style={{
          background:
            anchor === "top"
              ? "linear-gradient(180deg, rgba(10,10,9,0.62) 0%, rgba(10,10,9,0.34) 45%, rgba(10,10,9,0) 75%)"
              : anchor === "bottom"
                ? "linear-gradient(0deg, rgba(10,10,9,0.66) 0%, rgba(10,10,9,0.34) 40%, rgba(10,10,9,0) 72%)"
                : "radial-gradient(120% 62% at 50% 50%, rgba(10,10,9,0.62) 0%, rgba(10,10,9,0.42) 55%, rgba(10,10,9,0) 100%)",
          opacity: cardOpacity,
        }}
      />
      <AbsoluteFill style={{ ...box, alignItems: "center", textAlign: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          {phrases.map((p, i) => (
            <Phrase key={i} phrase={p} index={i} t={t} cardOpacity={cardOpacity} />
          ))}
        </div>
      </AbsoluteFill>
    </>
  );
};
