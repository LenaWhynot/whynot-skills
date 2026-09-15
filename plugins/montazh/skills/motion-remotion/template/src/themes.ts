import React from "react";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadGolos } from "@remotion/google-fonts/GolosText";

// Шаг «Steal the brand» из плейбука, включённый обратно: вся визуальная система
// ролика живёт в ОДНОМ блоке токенов. Навести тот же монтаж на другой бренд —
// это добавить сюда тему, а не переписывать карточки.
//
// Здесь лежат две темы:
//   editorial  — спокойная типографская, дефолт
//   neon-pink  — контрастная; её палитра снята ПИПЕТКОЙ со скриншота-референса,
//                а не подобрана на глаз, и это правило стоит повторить для своей темы
// Делаете ролик для другого автора — соберите тему с его сайта, а не подгоняйте на глаз.

const inter = loadInter("normal", { weights: ["700", "800", "900"], subsets: ["latin", "cyrillic"] });
const golos = loadGolos("normal", { weights: ["600", "700", "800", "900"], subsets: ["latin", "cyrillic"] });

export type Theme = {
  name: string;
  ink: string;        // плотный тёмный фон
  inkDeep: string;    // сцена под видео
  paper: string;      // светлый фон
  paper2: string;     // поверхность карточки
  lime: string;       // ДЕЙСТВИЕ / выигрыш / активное состояние
  limeWash: string;   // заливка-подсветка под акцентом
  violet: string;     // мета / пояснение
  muted: string;      // пояснения на светлом
  mutedOnDark: string;// пояснения на тёмном
  line: string;       // тонкие границы
  red: string;        // статус-риск
  onAccent: string;   // текст ПОВЕРХ акцентной заливки: на лайме тёмный, на розовом белый
  white: string;
  font: string;
  wHead: number;      // насыщенность крупного: заголовки, счётчики, захваты
  wUi: number;        // насыщенность мелкого: лейблы, подписи, строки списка
  pill: number;       // радиус кнопки CTA
  caps: boolean;      // крупные заголовки капсом
};

export const THEMES: Record<string, Theme> = {
  editorial: {
    name: "editorial",
    ink: "#17160F", inkDeep: "#0E0E0E", paper: "#FBFAF6", paper2: "#FFFFFF",
    lime: "#C6F24E", limeWash: "#EAF7B8", violet: "#6D5AE6",
    muted: "#6C6B61", mutedOnDark: "#B5B2A8", line: "#E7E5DB",
    red: "#C8453B", onAccent: "#17160F", white: "#FFFFFF",
    font: inter.fontFamily, wHead: 900, wUi: 800, pill: 10, caps: false,
  },
  // Палитра снята с трёх кадров референса пипеткой (Pillow, топ цветов области
  // слайда): фон #1A1A1A · бумага #F2EFE8 · акцент #EB427B · подпись #D1D1D1 ·
  // погашенный текст #3A3A3A. Ничего не додумано на глаз.
  "neon-pink": {
    name: "neon-pink",
    ink: "#1A1A1A", inkDeep: "#101010", paper: "#F2EFE8", paper2: "#FFFFFF",
    lime: "#EB427B", limeWash: "#FBE0EB", violet: "#F58BB0",
    muted: "#8A8A8A", mutedOnDark: "#D1D1D1", line: "#E3DFD6",
    red: "#EB427B", onAccent: "#FFFFFF", white: "#FFFFFF",
    // Golos на 900 в капсе перетяжелён — заголовки 800, мелкое 700.
    font: golos.fontFamily, wHead: 800, wUi: 700, pill: 999, caps: true,
  },
};

export const ThemeCtx = React.createContext<Theme>(THEMES.editorial);
export const useTheme = () => React.useContext(ThemeCtx);
export const resolveTheme = (name?: string): Theme => THEMES[name ?? "editorial"] ?? THEMES.editorial;
