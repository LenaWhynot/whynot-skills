import { interpolate, spring, Easing } from "remotion";

/** Общий словарь движения. Плейбук: двигать только transform и opacity. */

export const SNAP = { damping: 200, stiffness: 140, mass: 0.7 };   // без отскока
export const POP = { damping: 12, stiffness: 190, mass: 0.55 };    // с перелётом
export const SOFT = { damping: 26, stiffness: 90, mass: 0.9 };

/** Пружина, начинающаяся с задержкой в кадрах. */
export const at = (
  f: number,
  fps: number,
  delayFrames = 0,
  config: Record<string, number> = SNAP
) => spring({ frame: f - delayFrames, fps, config, durationInFrames: Math.round(fps * 0.55) });

/** Вход снизу с перелётом: то, чем «дорогая» графика отличается от fade-in. */
export const riseIn = (f: number, fps: number, delayFrames = 0, dist = 34) => {
  const s = at(f, fps, delayFrames, POP);
  return { opacity: Math.min(1, s * 1.6), transform: `translateY(${(1 - s) * dist}px)` };
};

/** Вход сбоку. */
export const slideIn = (f: number, fps: number, delayFrames = 0, dist = 60) => {
  const s = at(f, fps, delayFrames, POP);
  return { opacity: Math.min(1, s * 1.6), transform: `translateX(${(1 - s) * dist}px)` };
};

/** Удар: короткая тряска после приземления элемента. Живёт 5 кадров. */
export const shake = (f: number, fps: number, atFrame: number, amp = 7) => {
  const k = f - atFrame;
  if (k < 0 || k > 6) return 0;
  return Math.sin(k * 2.1) * amp * (1 - k / 6);
};

/** Линейный прогресс в кадрах — для прорисовки линий и зачёркиваний. */
export const draw = (f: number, from: number, len: number) =>
  interpolate(f, [from, from + len], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
