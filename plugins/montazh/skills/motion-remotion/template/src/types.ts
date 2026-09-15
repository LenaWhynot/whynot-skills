export type Mode = "split" | "solo" | "fullhim" | "full";

export type Card =
  | { type: "none" }
  | { type: "countup"; to: number; from?: number; prefix?: string; suffix?: string; label?: string; tone?: "lime" | "red" }
  | { type: "stamp"; text: string; stamp: string; sub?: string }
  | { type: "beforeafter"; before: string; after: string; beforeLabel?: string; afterLabel?: string }
  | { type: "list"; items: string[]; answer: string }
  | { type: "takeover"; word: string; tone?: "lime" | "red" | "violet" }
  | { type: "proof"; value: string; label: string; sub?: string }
  | { type: "shot"; src: string; caption?: string;
      highlight?: { x: number; y: number; w: number; h: number } }
  | { type: "cta"; title: string; line: string; button: string };

export type Beat = {
  start: number;          // секунды от начала ролика
  end: number;
  mode: Mode;
  card: Card;
  punch?: boolean;        // зум-панч на ключевом слове
};

export type Storyboard = { beats: Beat[] };

export type CaptionWord = { text: string; start: number; end: number };
export type CaptionChunk = {
  text: string;
  start: number;
  end: number;
  num?: boolean;
  hl?: "lime" | "red" | "violet";
  words: CaptionWord[];
};
export type Captions = {
  fps: number;
  duration: number;
  durationInFrames: number;
  chunks: CaptionChunk[];
};
