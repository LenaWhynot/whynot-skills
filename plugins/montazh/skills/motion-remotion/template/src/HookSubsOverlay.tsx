import { AbsoluteFill } from "remotion";
import { Subtitles, SubWord } from "./ReelKit";
import { KineticText } from "./Kinetic";
import subsJson from "./subs.json";

// Прозрачный оверлей субтитров под липсинк-хук (текст vo-hook).
// Рендерится с альфа-каналом (ProRes 4444) и накладывается на hook во ffmpeg,
// чтобы не тащить hook-видео в public/. Тайминги — из vo-hook в subs.json,
// звук хука начинается с t=0 клипа → lead=0 (без сдвига входной анимации карты).
const HOOK_SUBS = (subsJson as Record<string, SubWord[]>)["vo-hook"];

export const HOOK_SUBS_FRAMES = 150; // 5.0с при 30fps = длина lipsync-hook-v3.mp4

export const HookSubsOverlay: React.FC = () => (
  <AbsoluteFill>
    <Subtitles subs={HOOK_SUBS} dur={HOOK_SUBS_FRAMES} lead={0} pos="bottom" />
  </AbsoluteFill>
);

// Кинетический вариант того же оверлея — под апгрейд Reel-final.
// anchor=bottom: стопка фраз идёт низом, чтобы не закрывать лицо в липсинке.
export const HookKineticOverlay: React.FC = () => (
  <AbsoluteFill>
    <KineticText
      subs={HOOK_SUBS}
      dur={HOOK_SUBS_FRAMES}
      lead={0}
      anchor="bottom"
      accentWords={["ии", "голос"]}
    />
  </AbsoluteFill>
);
