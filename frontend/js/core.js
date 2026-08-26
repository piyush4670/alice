/* Alice Core — the living centre of the interface.
   A canvas orb that breathes when idle, spins when thinking,
   and radiates when she speaks. State lives in the store. */

import { state, subscribe } from "./state.js";
import { level } from "./level.js";

const COLORS = {
  idle: [79, 217, 255],
  thinking: [120, 225, 255],
  speaking: [56, 230, 196],
  listening: [143, 176, 255],
  working: [79, 217, 255],
  waiting: [255, 200, 97],
  boot: [79, 217, 255],
};

let canvas;
let ctx;
let target = COLORS.idle;
let current = [...COLORS.idle];
let t = 0;

function mix(a, b, k) {
  return a.map((v, i) => v + (b[i] - v) * k);
}

function rgba(color, alpha) {
  return `rgba(${color[0] | 0}, ${color[1] | 0}, ${color[2] | 0}, ${alpha})`;
}

function ring(radius, dash, speed, width, alpha, phase) {

  const w = canvas.width;
  const x = w / 2;

  ctx.save();
  ctx.translate(x, x);
  ctx.rotate(t * speed + phase);
  ctx.setLineDash(dash);
  ctx.lineWidth = width;
  ctx.strokeStyle = rgba(current, alpha);
  ctx.shadowColor = rgba(current, alpha * 0.8);
  ctx.shadowBlur = 12;
  ctx.beginPath();
  ctx.arc(0, 0, radius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

function draw() {

  const w = canvas.width;
  const c = w / 2;
  const mode = state.aliceState;

  const speedBy = { idle: 1, thinking: 3.2, working: 2.2, speaking: 1.6, listening: 2.6, waiting: 0.7, boot: 1 };

  t += 0.006 * (speedBy[mode] || 1);

  current = mix(current, target, 0.06);

  ctx.clearRect(0, 0, w, w);

  const active = mode !== "idle";
  const micBoost = mode === "listening" ? level.value : 0;
  const breathe = 1 + Math.sin(t * 2.2) * (active ? 0.05 : 0.025) + micBoost * 0.22;

  // halo
  const halo = ctx.createRadialGradient(c, c, 10, c, c, c * 0.95);
  halo.addColorStop(0, rgba(current, active ? 0.32 : 0.2));
  halo.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = halo;
  ctx.fillRect(0, 0, w, w);

  // core
  const core = ctx.createRadialGradient(c - 14, c - 16, 4, c, c, 52 * breathe);
  core.addColorStop(0, "rgba(235,252,255,0.95)");
  core.addColorStop(0.35, rgba(current, 0.85));
  core.addColorStop(1, rgba(current, 0));
  ctx.fillStyle = core;
  ctx.beginPath();
  ctx.arc(c, c, 52 * breathe, 0, Math.PI * 2);
  ctx.fill();

  // core nucleus
  ctx.fillStyle = "rgba(240,253,255,0.9)";
  ctx.shadowColor = rgba(current, 1);
  ctx.shadowBlur = 22;
  ctx.beginPath();
  ctx.arc(c, c, 13 * breathe, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  // rings
  const base = w / 2;

  ring(base * 0.44, [2, 10], 0.35, 1.5, 0.85, 0);
  ring(base * 0.58, [26, 14, 4, 14], -0.22, 1, 0.5, 1.4);
  ring(base * 0.72, [1, 7], 0.14, 1, 0.4, 2.6);

  if (mode === "thinking" || mode === "working") {
    ring(base * 0.86, [50, 90], 0.5, 1.2, 0.55, 0.8);
  }

  // orbiting particles
  const count = mode === "working" ? 5 : 3;

  for (let i = 0; i < count; i++) {

    const angle = t * (0.6 + i * 0.14) + (i * Math.PI * 2) / count;
    const orbit = base * (0.5 + 0.1 * ((i % 2) + Math.sin(t + i) * 0.14));
    const px = c + Math.cos(angle) * orbit;
    const py = c + Math.sin(angle) * orbit * 0.92;

    ctx.fillStyle = rgba(current, 0.9);
    ctx.shadowColor = rgba(current, 1);
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.arc(px, py, 2.1, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
  }

  // speech ripple
  if (mode === "speaking") {

    for (let i = 0; i < 3; i++) {

      const phase = (t * 1.4 + i / 3) % 1;
      const radius = 55 + phase * (w * 0.36);
      const alpha = 0.35 * (1 - phase);

      ctx.strokeStyle = rgba(current, alpha);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(c, c, radius, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  requestAnimationFrame(draw);
}

export function startOrb() {

  canvas = document.getElementById("orb");
  ctx = canvas.getContext("2d");

  subscribe((s, patch) => {

    if (patch.aliceState) target = COLORS[patch.aliceState] || COLORS.idle;
  });

  requestAnimationFrame(draw);
}
