/* Interface sounds: tiny WebAudio synth, polite and quiet. */

let ctx = null;
let enabled = true;

export function setSoundEnabled(value) {
  enabled = value;
}

function ensure() {

  if (!ctx) {

    const AudioCtx = window.AudioContext || window.webkitAudioContext;

    if (!AudioCtx) return null;

    ctx = new AudioCtx();
  }

  if (ctx.state === "suspended") ctx.resume();

  return ctx;
}

function tone(freq, start, duration, gain = 0.035, type = "sine") {

  const audio = ensure();

  if (!audio) return;

  const osc = audio.createOscillator();
  const amp = audio.createGain();

  osc.type = type;
  osc.frequency.value = freq;

  amp.gain.setValueAtTime(0, audio.currentTime + start);
  amp.gain.linearRampToValueAtTime(gain, audio.currentTime + start + 0.012);
  amp.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + start + duration);

  osc.connect(amp).connect(audio.destination);

  osc.start(audio.currentTime + start);
  osc.stop(audio.currentTime + start + duration + 0.05);
}

export const sfx = {

  message() {
    if (!enabled) return;
    tone(620, 0, 0.09);
    tone(880, 0.07, 0.12);
  },

  send() {
    if (!enabled) return;
    tone(440, 0, 0.06, 0.025);
  },

  step() {
    if (!enabled) return;
    tone(523, 0, 0.05, 0.02, "triangle");
  },

  question() {
    if (!enabled) return;
    tone(740, 0, 0.16, 0.04);
    tone(988, 0.14, 0.22, 0.04);
  },

  complete() {
    if (!enabled) return;
    tone(523, 0.0, 0.14);
    tone(659, 0.12, 0.14);
    tone(784, 0.24, 0.26);
    tone(1047, 0.38, 0.34, 0.03);
  },

  boot() {
    if (!enabled) return;
    tone(330, 0, 0.1, 0.02);
    tone(660, 0.1, 0.2, 0.025);
  },
};
