import React from "react";
import {
  AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, spring, staticFile,
  useCurrentFrame, useVideoConfig,
  type CalculateMetadataFunction,
} from "remotion";
import { ThemeCtx, resolveTheme, useTheme } from "./themes";
import { CardView } from "./cards";
import { sfxPlan } from "./sfx";
import type { Beat, Captions, Mode, Storyboard } from "./types";

export type ClaudeEditProps = {
  slug: string;
  /** Имя темы из THEMES. Меняет ВСЮ визуальную систему ролика одной строкой. */
  theme?: string;
  captions: Captions | null;
  storyboard: Storyboard | null;
  showVideo: boolean;
  sfx: boolean;
  musicBed: boolean;
};

export const calcClaudeEdit: CalculateMetadataFunction<ClaudeEditProps> = async ({ props }) => {
  const caps: Captions = await fetch(staticFile(`${props.slug}/captions.json`)).then((r) => r.json());
  let sb: Storyboard = { beats: [] };
  try {
    sb = await fetch(staticFile(`${props.slug}/storyboard.json`)).then((r) => r.json());
  } catch {
    // раскадровки ещё нет — собирается честный первый черновик «видео + сабы»
  }
  return {
    durationInFrames: caps.durationInFrames,
    fps: caps.fps,
    width: 1080,
    height: 1920,
    props: { ...props, captions: caps, storyboard: sb },
  };
};

const TR = 8; // кадров на переход split ↔ solo; в full и fullhim входим жёстко

/** Караоке: цвет + короткий поп на слове. Один цвет без движения читается как титры. */
const Karaoke: React.FC<{ caps: Captions; bottom: number }> = ({ caps, bottom }) => {
  const T = useTheme();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const chunk = caps.chunks.find((c) => t >= c.start && t < c.end);
  if (!chunk) return null;
  const hl = chunk.hl === "red" ? T.red : chunk.hl === "violet" ? T.violet : T.lime;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: bottom, paddingLeft: 70, paddingRight: 70 }}>
      <div style={{
        display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "10px 16px",
        fontFamily: T.font, fontWeight: T.wHead, fontSize: 76, lineHeight: 1.18, textAlign: "center",
      }}>
        {chunk.words.map((w, i) => {
          const spoken = t >= w.start;
          const pop = spoken
            ? spring({ frame: frame - Math.round(w.start * fps), fps, config: { damping: 11, stiffness: 220, mass: 0.5 }, durationInFrames: Math.round(fps * 0.3) })
            : 0;
          const color = chunk.hl && spoken ? hl : spoken ? T.white : "#8E8B83";
          return (
            <span key={i} style={{
              color,
              textShadow: "0 4px 26px rgba(0,0,0,.72)",
              display: "inline-block",
              transform: `scale(${spoken ? 1 + (1 - Math.min(1, pop)) * 0.16 : 0.97})`,
            }}>{w.text}</span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Vignette: React.FC = () => (
  <AbsoluteFill style={{ background: "linear-gradient(to top, rgba(0,0,0,.72) 0%, rgba(0,0,0,.28) 26%, rgba(0,0,0,0) 48%)" }} />
);

const Progress: React.FC = () => {
  const T = useTheme();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = interpolate(frame, [0, durationInFrames], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 8, background: "rgba(255,255,255,.14)" }}>
      <div style={{ height: "100%", width: `${p * 100}%`, background: T.lime }} />
    </div>
  );
};

/** Один режим кадра целиком. Переход между split и solo — кроссфейд двух таких слоёв. */
const Layout: React.FC<{
  mode: Mode; beat: Beat | null; slug: string; showVideo: boolean; punch: number; opacity: number;
}> = ({ mode, beat, slug, showVideo, punch, opacity }) => {
  const T = useTheme();
  const band = staticFile(`${slug}/band.mp4`);
  const vert = staticFile(`${slug}/vert.mp4`);
  const onDark = mode !== "split";
  // Ширина, в которую карточке реально есть куда расти: у split это бумажный
  // квадрат минус поля, у solo — узкий баннер, у fullhim и full — почти весь кадр.
  const boxWidth = mode === "split" ? 940 : mode === "solo" ? 900 : 960;
  const card = beat ? <CardView card={beat.card} beatStart={beat.start} onDark={onDark} boxWidth={boxWidth} /> : null;

  return (
    <AbsoluteFill style={{ opacity, background: mode === "split" ? T.paper : T.inkDeep }}>
      {showVideo && mode === "split" ? (
        <div style={{ position: "absolute", left: 0, top: 1080, width: 1080, height: 840, overflow: "hidden" }}>
          <OffthreadVideo src={band} muted style={{ width: 1080, height: 840, objectFit: "cover", transform: `scale(${punch})` }} />
        </div>
      ) : null}
      {showVideo && (mode === "fullhim" || mode === "solo") ? (
        <AbsoluteFill style={{ overflow: "hidden" }}>
          <OffthreadVideo src={vert} muted style={{ width: 1080, height: 1920, objectFit: "cover", transform: `scale(${punch})` }} />
        </AbsoluteFill>
      ) : null}

      {mode === "split" ? (
        <div style={{ position: "absolute", left: 0, top: 0, width: 1080, height: 1080, display: "flex", alignItems: "center", justifyContent: "center", padding: 70, boxSizing: "border-box" }}>
          {card}
        </div>
      ) : null}

      {mode === "solo" ? (
        <>
          <div style={{ position: "absolute", left: 0, top: 0, right: 0, height: 520, background: T.ink, display: "flex", alignItems: "center", justifyContent: "center", padding: "48px 60px", boxSizing: "border-box", color: T.white }}>
            {/* карточка в solo живёт в узком баннере — ужимаем, а не обрезаем */}
            <div style={{ transform: "scale(0.86)", transformOrigin: "center", width: "100%" }}>{card}</div>
          </div>
          <div style={{ position: "absolute", left: 0, bottom: 0, right: 0, height: 300, background: T.ink }} />
          <Vignette />
        </>
      ) : null}

      {mode === "fullhim" ? (
        <>
          <Vignette />
          <div style={{ position: "absolute", left: 60, right: 60, top: 180 }}>{card}</div>
          <Vignette />
        </>
      ) : null}

      {mode === "full" ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: 80, boxSizing: "border-box" }}>
          {card}
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

const ClaudeEditInner: React.FC<ClaudeEditProps> = ({ slug, captions, storyboard, showVideo, sfx, musicBed }) => {
  const T = useTheme();
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  if (!captions) return <AbsoluteFill style={{ background: T.inkDeep }} />;

  const beats = storyboard?.beats ?? [];
  const idx = beats.findIndex((b) => t >= b.start && t < b.end);
  const beat = idx >= 0 ? beats[idx] : null;
  const prev = idx > 0 ? beats[idx - 1] : null;
  const mode: Mode = beat?.mode ?? (showVideo ? "fullhim" : "full");

  // Плейбук: в full входим жёстким срезом, между split и solo — тянем.
  const tweenable =
    !!beat && !!prev &&
    ((prev.mode === "split" && beat.mode === "solo") || (prev.mode === "solo" && beat.mode === "split"));
  const since = beat ? frame - Math.round(beat.start * fps) : TR;
  const p = tweenable ? Math.min(1, Math.max(0, since / TR)) : 1;

  const punch = beat?.punch
    ? 1 + interpolate(frame - Math.round(beat.start * fps), [0, 4, 14], [0.06, 0.06, 0], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 1;

  const hits = sfx ? sfxPlan(storyboard, captions) : [];

  return (
    <AbsoluteFill style={{ background: T.inkDeep, fontFamily: T.font }}>
      {p < 1 && prev ? (
        <Layout mode={prev.mode} beat={prev} slug={slug} showVideo={showVideo} punch={punch} opacity={1 - p} />
      ) : null}
      <Layout mode={mode} beat={beat} slug={slug} showVideo={showVideo} punch={punch} opacity={p} />

      <Karaoke caps={captions} bottom={mode === "split" ? 120 : 260} />
      <Progress />

      {showVideo ? <Audio src={staticFile(`${slug}/voice.m4a`)} /> : null}
      {musicBed ? <Audio src={staticFile("sfx/pad.wav")} volume={0.1} loop /> : null}
      {hits.map((h, i) => {
        const from = Math.round(h.at * fps);
        if (from >= durationInFrames) return null;
        return (
          <Sequence key={i} from={Math.max(0, from)} durationInFrames={Math.round(fps * 1.6)} layout="none">
            <Audio src={staticFile(`claude-edit-sfx/${h.id}.wav`)} volume={h.gain} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

/** Тема — единственная точка входа в визуальную систему. */
export const ClaudeEdit: React.FC<ClaudeEditProps> = (props) => (
  <ThemeCtx.Provider value={resolveTheme(props.theme)}>
    <ClaudeEditInner {...props} />
  </ThemeCtx.Provider>
);
