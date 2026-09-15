import React from "react";
import { Composition } from "remotion";
import { ClaudeEdit, calcClaudeEdit } from "./ClaudeEdit";

// Реестр композиций: каждая <Composition> видна в студии и рендерится по своему id.
export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="ClaudeEdit"
      component={ClaudeEdit}
      calculateMetadata={calcClaudeEdit}
      durationInFrames={900}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        // slug = папка в public/. Тайминги, размер и длительность приходят
        // из public/<slug>/captions.json через calculateMetadata.
        slug: "demo",
        theme: "editorial",
        captions: null,
        storyboard: null,
        // false = рендерим ТОЛЬКО графику, прозрачным слоем: футаж кладётся
        // потом одной командой ffmpeg. true — если хотите видеть видео в студии
        // (тогда положите его в public/<slug>/vert.mp4).
        showVideo: false,
        // Звуковые акценты просят свои файлы в public/claude-edit-sfx/.
        // Для прозрачного слоя они не нужны: звук приходит из вашего футажа.
        sfx: false,
        musicBed: false,
      }}
    />
  </>
);
