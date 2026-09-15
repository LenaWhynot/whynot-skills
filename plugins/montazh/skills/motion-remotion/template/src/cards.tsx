import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { fitText } from "@remotion/layout-utils";

import { R } from "./tokens";
import { useTheme } from "./themes";
import { at, riseIn, slideIn, shake, draw, POP, SNAP } from "./motion";
import type { Card } from "./types";

// Всё считается от useCurrentFrame(): никаких CSS-переходов, setTimeout и Math.random.
// Разница между «плашка появилась» и «карточка сделана» — в том, сколько
// НЕЗАВИСИМЫХ элементов внутри карточки едут по своим таймингам. Плейбук на 18
// карточек держит ~280 твинов; ниже каждая карточка разложена на слои со сдвигом.

export const useLocal = (beatStart: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return { f: frame - Math.round(beatStart * fps), fps };
};

const mixWash = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

const onDarkFg = (T: ReturnType<typeof useTheme>, onDark?: boolean) => (onDark ? T.white : T.ink);
const onDarkMuted = (T: ReturnType<typeof useTheme>, onDark?: boolean) => (onDark ? T.mutedOnDark : T.muted);

const Label: React.FC<{ children: React.ReactNode; color?: string; style?: React.CSSProperties }> = ({
  children, color, style,
}) => {
  const T = useTheme();
  return (
    <div style={{ fontSize: 26, fontWeight: T.wUi, letterSpacing: 4, textTransform: "uppercase", color: color ?? T.muted, ...style }}>
      {children}
    </div>
  );
};

/** Текст, вылетающий по словам со сдвигом — так «оживает» любая длинная строка. */
const WordsIn: React.FC<{
  text: string; f: number; fps: number; delay?: number; step?: number; style?: React.CSSProperties;
}> = ({ text, f, fps, delay = 0, step = 2, style }) => (
  <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 0.28em", ...style }}>
    {text.split(" ").map((w, i) => {
      const s = at(f, fps, delay + i * step, POP);
      return (
        <span key={i} style={{ display: "inline-block", opacity: Math.min(1, s * 1.7), transform: `translateY(${(1 - s) * 26}px)` }}>
          {w}
        </span>
      );
    })}
  </div>
);

// ── каунт-ап ───────────────────────────────────────────────────────────
// Слои: цифра считается · на каждой смене цифры короткий поп · подпись
// прилетает ПОСЛЕ · снизу тонкая линия дорисовывается под счёт.
const CountUp: React.FC<{ c: Extract<Card, { type: "countup" }>; beatStart: number; onDark?: boolean }> = ({ c, beatStart, onDark }) => {
  const T = useTheme();
  const { f, fps } = useLocal(beatStart);
  const dur = Math.round(fps * 1.1);
  const p = interpolate(f, [0, dur], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic),
  });
  const from = c.from ?? 0;
  const value = Math.round(from + (c.to - from) * p);
  const prev = Math.round(from + (c.to - from) * interpolate(f - 1, [0, dur], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic),
  }));
  const changed = value !== prev && f <= dur;
  const kick = changed ? 1 : interpolate(f % 1, [0, 1], [0, 0]);
  const settle = at(f, fps, dur, POP); // финальный доводочный поп, когда счёт встал
  const scale = 1 + kick * 0.035 + (f > dur ? (1 - Math.abs(1 - settle)) * 0.0 : 0);
  const tone = c.tone === "red" ? T.red : c.tone === "lime" ? T.lime : onDarkFg(T, onDark);
  const line = draw(f, 0, dur);

  return (
    <div style={{ textAlign: "center" }}>
      <div style={{
        fontSize: 220, fontWeight: T.wHead, letterSpacing: -8, lineHeight: 1, color: tone,
        transform: `scale(${scale})`, fontVariantNumeric: "tabular-nums",
      }}>
        {c.prefix ?? ""}{value.toLocaleString("ru-RU")}{c.suffix ?? ""}
      </div>
      <div style={{
        height: 6, background: c.tone === "red" ? T.red : T.lime, borderRadius: 3,
        margin: "18px auto 0", width: 360, transform: `scaleX(${line})`, transformOrigin: "left center",
      }} />
      {c.label ? (
        <div style={{ marginTop: 22, ...riseIn(f, fps, dur - 4, 18) }}>
          <Label color={onDarkMuted(T, onDark)}>{c.label}</Label>
        </div>
      ) : null}
    </div>
  );
};

// ── штамп ──────────────────────────────────────────────────────────────
// Слои: карточка поднимается · штамп прилетает с поворотом и перелётом ·
// на приземлении вся карточка коротко трясётся · подпись после.
const Stamp: React.FC<{ c: Extract<Card, { type: "stamp" }>; beatStart: number; onDark?: boolean }> = ({ c, beatStart, onDark }) => {
  const T = useTheme();
  const { f, fps } = useLocal(beatStart);
  const hit = Math.round(fps * 0.5);
  const card = at(f, fps, 0, SNAP);
  const s = at(f, fps, hit, POP);
  const sx = shake(f, fps, hit + Math.round(fps * 0.18), 8);
  return (
    <div style={{ position: "relative", width: "100%", textAlign: "center", transform: `translateX(${sx}px)` }}>
      <div style={{
        background: T.paper2, border: `2px solid ${T.line}`, borderRadius: R.card,
        padding: "48px 40px", fontSize: 56, fontWeight: T.wUi, lineHeight: 1.2, color: T.ink,
        opacity: Math.min(1, card * 1.6), transform: `translateY(${(1 - card) * 28}px)`,
      }}>
        {c.text}
      </div>
      <div style={{
        position: "absolute", left: "68%", top: "50%",
        transform: `translate(-50%,-50%) rotate(${-42 + 31 * s}deg) scale(${1.7 - 0.7 * s})`,
        opacity: Math.min(1, s * 2.2),
        border: `7px solid ${T.red}`, color: T.red, borderRadius: 12,
        padding: "10px 28px", fontSize: 66, fontWeight: T.wHead, letterSpacing: 2,
        background: "rgba(251,250,246,.92)",
      }}>
        {c.stamp}
      </div>
      {c.sub ? (
        <div style={{ marginTop: 74, ...riseIn(f, fps, hit + 8, 16) }}>
          <Label color={onDarkMuted(T, onDark)}>{c.sub}</Label>
        </div>
      ) : null}
    </div>
  );
};

// ── было → стало ───────────────────────────────────────────────────────
// Слои: левый блок слева · стрелка дорисовывается · правый справа ·
// на приходе правого — лаймовая вспышка заливки.
const BeforeAfter: React.FC<{ c: Extract<Card, { type: "beforeafter" }>; beatStart: number }> = ({ c, beatStart }) => {
  const T = useTheme();
  const { f, fps } = useLocal(beatStart);
  const dB = 0;
  const dArrow = Math.round(fps * 0.35);
  const dA = Math.round(fps * 0.55);
  const flash = interpolate(f, [dA, dA + 5, dA + 20], [0, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const box = (text: string, label: string, accent: string, bg: string, mv: React.CSSProperties) => (
    <div style={{
      flex: 1, background: bg, border: `2px solid ${accent}`, borderRadius: R.card, padding: "30px 26px", ...mv,
    }}>
      <Label color={accent}>{label}</Label>
      <div style={{ marginTop: 14, fontSize: 44, fontWeight: T.wUi, lineHeight: 1.15, color: T.ink }}>{text}</div>
    </div>
  );
  const arrow = draw(f, dArrow, Math.round(fps * 0.3));
  return (
    <div style={{ display: "flex", alignItems: "stretch", gap: 20, width: "100%" }}>
      {box(c.before, c.beforeLabel ?? "было", T.red, T.paper2, slideIn(f, fps, dB, -70))}
      <div style={{ alignSelf: "center", width: 64, position: "relative", height: 8 }}>
        <div style={{ position: "absolute", inset: 0, background: T.ink, borderRadius: 4, transform: `scaleX(${arrow})`, transformOrigin: "left center" }} />
        <div style={{
          position: "absolute", right: -2, top: -12, width: 0, height: 0,
          borderTop: "16px solid transparent", borderBottom: "16px solid transparent",
          borderLeft: `20px solid ${T.ink}`, opacity: arrow > 0.92 ? 1 : 0,
        }} />
      </div>
      {box(c.after, c.afterLabel ?? "стало", T.lime, mixWash(T.limeWash, 0.35 + flash * 0.55), slideIn(f, fps, dA, 70))}
    </div>
  );
};

// ── список с зачёркиванием ─────────────────────────────────────────────
// Слои: каждая строка въезжает своим сдвигом · через полсекунды по ней
// прорисовывается зачёркивание и она гаснет · ответ приходит последним
// с раскрывающейся лаймовой заливкой.
const ListStrike: React.FC<{ c: Extract<Card, { type: "list" }>; beatStart: number }> = ({ c, beatStart }) => {
  const T = useTheme();
  const { f, fps } = useLocal(beatStart);
  const step = Math.round(fps * 0.4);
  const strikeAfter = Math.round(fps * 0.5);
  return (
    <div style={{ width: "100%" }}>
      {c.items.map((it, i) => {
        const inAt = i * step;
        const mv = slideIn(f, fps, inAt, -40);
        const st = draw(f, inAt + strikeAfter, Math.round(fps * 0.22));
        return (
          <div key={i} style={{
            position: "relative", marginBottom: 16, background: T.paper2, border: `2px solid ${T.line}`,
            borderRadius: R.control, padding: "20px 24px", fontSize: 44, fontWeight: T.wUi,
            color: T.muted, opacity: (mv.opacity as number) * (1 - st * 0.45), transform: mv.transform,
          }}>
            {it}
            <div style={{
              position: "absolute", left: 24, right: 24, top: "50%", height: 5, background: T.red,
              transform: `scaleX(${st})`, transformOrigin: "left center",
            }} />
          </div>
        );
      })}
      {(() => {
        const aAt = c.items.length * step + strikeAfter;
        const s = at(f, fps, aAt, POP);
        const wash = draw(f, aAt, Math.round(fps * 0.35));
        return (
          <div style={{
            position: "relative", marginTop: 26, border: `3px solid ${T.lime}`, borderRadius: R.card,
            padding: "26px 26px", fontSize: 52, fontWeight: T.wHead, color: T.ink, overflow: "hidden",
            opacity: Math.min(1, s * 1.6), transform: `translateY(${(1 - s) * 24}px)`,
          }}>
            <div style={{
              position: "absolute", inset: 0, background: T.limeWash,
              transform: `scaleX(${wash})`, transformOrigin: "left center",
            }} />
            <span style={{ position: "relative" }}>{c.answer}</span>
          </div>
        );
      })()}
    </div>
  );
};

// ── полноэкранный захват одним словом ──────────────────────────────────
// Слои: буквы вылетают по одной с перелётом · слово слегка дышит после.
const Takeover: React.FC<{ c: Extract<Card, { type: "takeover" }>; beatStart: number; boxWidth?: number }> = ({ c, beatStart, boxWidth = 920 }) => {
  const T = useTheme();
  const { f, fps } = useLocal(beatStart);
  const color = c.tone === "red" ? T.red : c.tone === "violet" ? T.violet : T.lime;
  const letters = c.word.split("");
  const drift = 1 + Math.sin(Math.max(0, f - fps) / fps * 1.6) * 0.008;
  // Найдено глазами на витрине: «КОНВЕЙЕР» на фиксированных 200px переносился
  // как «КОНВЕЙЕ / Р». Размер теперь считается под ширину, перенос запрещён.
  const { fontSize } = fitText({
    text: c.word, withinWidth: boxWidth, fontFamily: T.font, fontWeight: 900, letterSpacing: "-6px",
  });
  const size = Math.min(fontSize, 210);
  return (
    <div style={{
      display: "flex", justifyContent: "center", lineHeight: 1, whiteSpace: "nowrap",
      fontSize: size, fontWeight: T.wHead, letterSpacing: -6, color, textAlign: "center",
      textTransform: T.caps ? "uppercase" : "none",
      transform: `scale(${drift})`,
    }}>
      {letters.map((ch, i) => {
        const s2 = at(f, fps, i * 1.6, POP);
        return (
          <span key={i} style={{
            display: "inline-block", whiteSpace: "pre",
            opacity: Math.min(1, s2 * 2), transform: `translateY(${(1 - s2) * 60}px) scale(${0.7 + s2 * 0.3})`,
          }}>{ch}</span>
        );
      })}
    </div>
  );
};

// ── пруф ───────────────────────────────────────────────────────────────
const Proof: React.FC<{ c: Extract<Card, { type: "proof" }>; beatStart: number }> = ({ c, beatStart }) => {
  const T = useTheme();
  const { f, fps } = useLocal(beatStart);
  const card = riseIn(f, fps, 0, 30);
  return (
    <div style={{
      background: T.paper2, border: `2px solid ${T.line}`, borderRadius: R.card, padding: "40px 34px",
      textAlign: "center", width: "100%", ...card,
    }}>
      <div style={{ fontSize: 128, fontWeight: T.wHead, letterSpacing: -4, color: T.ink, lineHeight: 1, ...riseIn(f, fps, 4, 18) }}>
        {c.value}
      </div>
      <div style={{ marginTop: 16, ...riseIn(f, fps, 9, 14) }}><Label>{c.label}</Label></div>
      {c.sub ? (
        <div style={{ marginTop: 18, fontSize: 34, color: T.muted, lineHeight: 1.35, ...riseIn(f, fps, 14, 12) }}>{c.sub}</div>
      ) : null}
    </div>
  );
};

// ── реальный скриншот в белой карточке ─────────────────────────────────
// Плейбук: настоящий скрин читается как доказательство, мокап — как реклама.
// Рамка приезжает, картинка проявляется чуть позже, подсветка области —
// последней, чтобы глаз успел за ней пойти.
const Shot: React.FC<{ c: Extract<Card, { type: "shot" }>; beatStart: number; onDark?: boolean }> = ({ c, beatStart, onDark }) => {
  const T = useTheme();
  const { f, fps } = useLocal(beatStart);
  const card = riseIn(f, fps, 0, 34);
  const img = at(f, fps, 5, SNAP);
  const hl = c.highlight;
  const hlP = at(f, fps, Math.round(fps * 0.55), POP);
  return (
    <div style={{ width: "100%", ...card }}>
      <div style={{
        position: "relative", background: T.paper2, border: `2px solid ${T.line}`,
        borderRadius: R.card, padding: 14, overflow: "hidden",
      }}>
        <Img src={staticFile(c.src)} style={{
          width: "100%", display: "block", borderRadius: 10,
          opacity: img, transform: `scale(${0.985 + img * 0.015})`,
        }} />
        {hl ? (
          <div style={{
            position: "absolute", left: `${hl.x}%`, top: `${hl.y}%`, width: `${hl.w}%`, height: `${hl.h}%`,
            border: `5px solid ${T.lime}`, borderRadius: 10, boxShadow: "0 0 0 9999px rgba(23,22,15,.35)",
            opacity: Math.min(1, hlP * 1.6), transform: `scale(${1.12 - hlP * 0.12})`,
          }} />
        ) : null}
      </div>
      {c.caption ? (
        <div style={{ marginTop: 20, textAlign: "center", ...riseIn(f, fps, Math.round(fps * 0.7), 14) }}>
          <Label color={onDarkMuted(T, onDark)}>{c.caption}</Label>
        </div>
      ) : null}
    </div>
  );
};

// ── CTA ────────────────────────────────────────────────────────────────
const Cta: React.FC<{ c: Extract<Card, { type: "cta" }>; beatStart: number; onDark?: boolean }> = ({ c, beatStart, onDark }) => {
  const T = useTheme();
  const { f, fps } = useLocal(beatStart);
  const btn = at(f, fps, Math.round(fps * 0.5), POP);
  const pulse = 1 + Math.sin((f / fps) * Math.PI * 2.2) * 0.022;
  const bounce = Math.abs(Math.sin((f / fps) * Math.PI * 1.6)) * 14;
  return (
    <div style={{ textAlign: "center", width: "100%" }}>
      <div style={riseIn(f, fps, 0, 16)}>
        <Label color={onDark ? "#A99BFF" : T.violet}>{c.title}</Label>
      </div>
      <WordsIn text={c.line} f={f} fps={fps} delay={4} step={2}
        style={{ marginTop: 20, fontSize: 62, fontWeight: T.wHead, lineHeight: 1.1, color: onDarkFg(T, onDark),
                 textTransform: T.caps ? "uppercase" : "none" }} />
      <div style={{
        marginTop: 34, display: "inline-block", background: T.lime, color: T.onAccent,
        padding: "22px 48px", fontSize: 44, fontWeight: T.wHead, borderRadius: T.pill,
        opacity: Math.min(1, btn * 1.8), transform: `scale(${(0.8 + btn * 0.2) * pulse})`,
      }}>
        {c.button}
      </div>
      <div style={{
        marginTop: 18, fontSize: 46, color: onDarkFg(T, onDark),
        opacity: Math.min(1, btn), transform: `translateY(${bounce}px)`,
      }}>↓</div>
    </div>
  );
};

export const CardView: React.FC<{ card: Card; beatStart: number; onDark?: boolean; boxWidth?: number }> = ({ card, beatStart, onDark, boxWidth }) => {
  switch (card.type) {
    case "countup": return <CountUp c={card} beatStart={beatStart} onDark={onDark} />;
    case "stamp": return <Stamp c={card} beatStart={beatStart} onDark={onDark} />;
    case "beforeafter": return <BeforeAfter c={card} beatStart={beatStart} />;
    case "list": return <ListStrike c={card} beatStart={beatStart} />;
    case "takeover": return <Takeover c={card} beatStart={beatStart} boxWidth={boxWidth} />;
    case "proof": return <Proof c={card} beatStart={beatStart} />;
    case "shot": return <Shot c={card} beatStart={beatStart} onDark={onDark} />;
    case "cta": return <Cta c={card} beatStart={beatStart} onDark={onDark} />;
    default: return null;
  }
};
