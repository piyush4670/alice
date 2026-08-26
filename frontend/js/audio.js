/* The Audio Visualiser: ALICE's real-time voice/speech detection wave.

A canvas that renders a mirrored frequency field. It is driven by a live
microphone level when ALICE is listening, by a steady broadcast envelope
while she speaks, and by a gentle ambient idle otherwise. It is pure view —
the level comes from `level.js`, never from the DOM.
*/

import { level } from "./level.js";
import { state } from "./state.js";

let canvas;
let ctx;
let raf;
let t = 0;

const COLORS = {
  idle: "#4fd9ff",
  thinking: "#78e1ff",
  speaking: "#38e6c4",
  listening: "#8fb0ff",
  working: "#4fd9ff",
  waiting: "#ffc861",
  boot: "#4fd9ff",
};

function color() {
  return COLORS[state.aliceState] || COLORS.idle;
}

function hexToRgb(hex) {
  const value = hex.replace("#", "");
  const big = parseInt(value, 16);
  return [(big >> 16) & 255, (big >> 8) & 255, big & 255];
}

function rgba(rgb, a) {
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${a})`;
}

function smooth(prev, next, k) {
  return prev + (next - prev) * k;
}

// A slowly moving simulated envelope used when there is no live source.
function ambient() {
  return 0.08 + 0.05 * Math.sin(t * 1.7) + 0.03 * Math.sin(t * 3.1 + 1.3);
}

function envelope() {
  if (state.aliceState === "listening" || state.listening) {
    return Math.max(level.value, 0.12);
  }
  if (state.aliceState === "speaking" || state.speaking) {
    // Broadcast pulse: a rounded, repeated swell while she talks.
    const phase = (t * 1.6) % 1;
    return 0.28 + 0.34 * Math.pow(Math.max(0, Math.sin(phase * Math.PI)), 2);
  }
  return ambient();
}

function draw() {
  if (!ctx) return;

  t += 0.02;

  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;

  ctx.clearRect(0, 0, w, h);

  const lvl = envelope();
  const rgb = hexToRgb(color());
  const bars = 56;
  const barW = (w - 20) / bars;

  // mirrored frequency bars
  const amp = Math.max(2, lvl * (h * 0.42));

  for (let i = 0; i < bars; i++) {
    const x = 10 + i * barW;
    const falloff = 1 - Math.abs(i - bars / 2) / (bars / 2); // bell across
    const wobble = 0.82 + 0.18 * Math.sin(t * 6 + i * 0.55);
    const top = Math.max(1.5, amp * falloff * wobble);

    const grad = ctx.createLinearGradient(0, cy - top, 0, cy);
    grad.addColorStop(0, rgba(rgb, 0.9));
    grad.addColorStop(1, rgba(rgb, 0.05));

    ctx.fillStyle = grad;
    ctx.shadowColor = rgba(rgb, 0.55);
    ctx.shadowBlur = 8;
    ctx.fillRect(x, cy - top, barW * 0.62, top);
    ctx.fillRect(x, cy, barW * 0.62, top);
  }

  ctx.shadowBlur = 0;

  // a scanning centre line
  ctx.strokeStyle = rgba(rgb, 0.35);
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(10, cy);
  ctx.lineTo(w - 10, cy);
  ctx.stroke();

  // a soft glow dot at the centre
  ctx.fillStyle = rgba(rgb, 0.4);
  ctx.shadowColor = rgba(rgb, 0.9);
  ctx.shadowBlur = 16;
  ctx.beginPath();
  ctx.arc(cx, cy, 2.2 + lvl * 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  raf = requestAnimationFrame(draw);
}

const MIN_SIZE = 40;

export function initAudio() {
  canvas = document.getElementById("voiceWave");
  if (!canvas) return;
  ctx = canvas.getContext("2d");

  const ratio = window.devicePixelRatio || 1;

  // The app is hidden during boot, so the canvas may report zero size;
  // clamp to a minimum so the visualiser always has a surface to draw on.
  canvas.width = Math.max(canvas.getBoundingClientRect().width, MIN_SIZE) * ratio;
  canvas.height = Math.max(canvas.getBoundingClientRect().height, MIN_SIZE) * ratio;

  window.addEventListener("resize", () => {
    const r = canvas.getBoundingClientRect();
    canvas.width = Math.max(r.width, MIN_SIZE) * ratio;
    canvas.height = Math.max(r.height, MIN_SIZE) * ratio;
  });

  draw();
}
