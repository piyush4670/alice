/* The Voice Engine.

ALICE speaks (speech synthesis), listens (speech recognition), and — the
main event — stays hands-free: she hears the wake word “Hey Alice”, stops
talking instantly, and takes the next instruction without missing a beat.

Everything degrades silently on browsers that lack the APIs. The live mic
level is written to `level.js` so the visualiser can react in real time.
*/

import { set, state, aliceState } from "./state.js";
import { plain } from "./md.js";
import { level } from "./level.js";

/* ---------------- Speech synthesis (ALICE talking) ---------------- */

let voice = null;
let voicesReady = false;

const PREFERRED = [
  "Google UK English Female",
  "Google US English",
  "Microsoft Aria Online (Natural) - English (United States)",
  "Microsoft Zira - English (United States)",
  "Samantha",
  "Karen",
  "Serena",
];

function pickVoice() {
  const voices = speechSynthesis.getVoices();
  if (!voices.length) return;
  voicesReady = true;
  for (const name of PREFERRED) {
    const found = voices.find((v) => v.name.includes(name));
    if (found) { voice = found; return; }
  }
  voice = voices.find((v) => v.lang.startsWith("en")) || voices[0];
}

export function initVoice() {
  if (!("speechSynthesis" in window)) return;
  pickVoice();
  speechSynthesis.onvoiceschanged = pickVoice;
}

export function speak(text) {
  if (!state.speak || !("speechSynthesis" in window)) return;

  const body = plain(text).slice(0, 600);
  if (!body) return;

  cancelSpeech();

  const utterance = new SpeechSynthesisUtterance(body);
  if (!voicesReady) pickVoice();
  if (voice) utterance.voice = voice;

  utterance.rate = 1.02;
  utterance.pitch = 1.03;

  utterance.onstart = () => set({ speaking: true });
  utterance.onend = () => set({ speaking: false });
  utterance.onerror = () => set({ speaking: false });

  speechSynthesis.speak(utterance);
}

export function cancelSpeech() {
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  set({ speaking: false });
}

export function isSpeaking() {
  return "speechSynthesis" in window && speechSynthesis.speaking;
}

export function toggleSpeak() {
  const next = !state.speak;
  if (!next) cancelSpeech();
  set({ speak: next });
  return next;
}

/* ---------------- Live mic level meter ---------------- */

let stream = null;
let analyser = null;
let audioCtx = null;
let levelRaf = null;
let levelData = null;

function startLevelMeter() {
  if (!("mediaDevices" in navigator) || !navigator.mediaDevices.getUserMedia) return false;

  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return false;

  return navigator.mediaDevices
    .getUserMedia({ audio: true })
    .then((s) => {
      stream = s;
      audioCtx = new AudioCtx();
      const source = audioCtx.createMediaStreamSource(s);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.75;
      source.connect(analyser);
      levelData = new Uint8Array(analyser.frequencyBinCount);
      level.source = "mic";
      tickLevel();
      return true;
    })
    .catch(() => false);
}

function tickLevel() {
  if (!analyser || !levelData) return;
  analyser.getByteFrequencyData(levelData);

  let sum = 0;
  for (let i = 0; i < levelData.length; i++) sum += levelData[i];
  const avg = sum / levelData.length;
  level.value = Math.min(1, avg / 255);

  levelRaf = requestAnimationFrame(tickLevel);
}

function stopLevelMeter() {
  if (levelRaf) cancelAnimationFrame(levelRaf);
  levelRaf = null;
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  if (audioCtx) { try { audioCtx.close(); } catch { /* noop */ } }
  audioCtx = null;
  analyser = null;
  levelData = null;
  level.source = state.speaking ? "speak" : "idle";
}

/* ---------------- Speech recognition / wake word ---------------- */

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

// Ordered; the first that appears wins as the wake phrase anchor.
const WAKE_PHRASES = [
  "hey alice",
  "ok alice",
  "okay alice",
  "hi alice",
  "hello alice",
  "good morning alice",
  "alice",
];

const WATCH_LANG = "en-US";

let recognition = null;   // the continuous hands-free session
let wakeActive = false;   // recognition is running for wake word
let mode = "wake";        // "wake" | "command"
let commandOffset = 0;
let commandBuffer = "";
let commandTimer = null;

let onWakeHandler = null;
let onCommandHandler = null;
let onInterimHandler = null;
let onPermissionDenied = null;

export function setWakeHandlers({ onWake, onCommand, onInterim, onPermissionDenied: onDeny }) {
  onWakeHandler = onWake || null;
  onCommandHandler = onCommand || null;
  onInterimHandler = onInterim || null;
  onPermissionDenied = onDeny || null;
}

function lastWakeIndex(lower) {
  let best = -1;
  for (const phrase of WAKE_PHRASES) {
    const idx = lower.lastIndexOf(phrase);
    if (idx > best) best = idx;
  }
  return best;
}

function wakePhraseAt(lower, idx) {
  for (const phrase of WAKE_PHRASES) {
    const start = lower.lastIndexOf(phrase);
    if (start === idx) return phrase;
  }
  return WAKE_PHRASES[WAKE_PHRASES.length - 1]; // "alice"
}

function armCommandTimer() {
  clearCommandTimer();
  commandTimer = setTimeout(() => {
    // The user said “hey Alice” but no instruction followed.
    if (mode === "command") {
      mode = "wake";
      commandOffset = 0;
      commandBuffer = "";
      set({ wake: false, listening: false });
      if (onInterimHandler) onInterimHandler("");
    }
  }, 8000);
}

function clearCommandTimer() {
  if (commandTimer) { clearTimeout(commandTimer); commandTimer = null; }
}

function cleanCommand(text) {
  return text
    .replace(/^(hey|ok|okay|hi|hello|good morning)\s*alice[,.\s]+/i, "")
    .replace(/^[,.\s]+/, "")
    .replace(/[?.!]+$/, "")
    .trim();
}

function onWakeResult(event) {
  let full = "";
  let hasFinal = false;

  for (let i = 0; i < event.results.length; i++) {
    const res = event.results[i];
    full += res[0].transcript;
    if (res.isFinal) hasFinal = true;
  }

  const lower = full.toLowerCase();

  if (mode === "command") {
    let cmd = cleanCommand(full.slice(commandOffset));
    commandBuffer = cmd;
    if (onInterimHandler) onInterimHandler(cmd);

    if (hasFinal) {
      if (cmd) {
        dispatchCommand(cmd);
      } else {
        // Just the wake word, no instruction — go back to listening.
        clearCommandTimer();
        set({ wake: false, listening: false });
        resetSession();
      }
    }
  } else {
    const idx = lastWakeIndex(lower);
    if (idx >= 0) {
      const phrase = wakePhraseAt(lower, idx);
      commandOffset = idx + phrase.length;
      mode = "command";
      commandBuffer = cleanCommand(full.slice(commandOffset));

      // Interrupt: stop talking the instant we hear the wake word.
      cancelSpeech();
      set({ wake: true, listening: true });
      aliceState("listening");
      if (onWakeHandler) onWakeHandler();

      if (onInterimHandler) onInterimHandler(commandBuffer);
      armCommandTimer();
    }
  }
}

function dispatchCommand(text) {
  clearCommandTimer();
  mode = "wake";
  commandOffset = 0;
  commandBuffer = "";
  set({ wake: false, listening: false });
  if (onInterimHandler) onInterimHandler("");
  resetSession();
  if (onCommandHandler && text) onCommandHandler(text);
}

function onWakeEnd() {
  if (!wakeActive) return; // intentionally stopped

  if (mode === "command") {
    const cmd = cleanCommand(commandBuffer);
    if (cmd) {
      dispatchCommand(cmd);
      return;
    }
    // Nothing captured; fall back to wake mode.
    clearCommandTimer();
    mode = "wake";
    commandOffset = 0;
  }

  // Browsers drop a continuous session after silence; seamlessly resume.
  try { recognition.start(); } catch { /* already starting */ }
}

function onWakeError(event) {
  const err = event && event.error;

  if (err === "not-allowed" || err === "service-not-allowed") {
    disableWakeWord();
    if (onPermissionDenied) onPermissionDenied();
    return;
  }

  // "no-speech", "aborted", "network" etc. — keep the session alive.
  if (mode === "command") onWakeEnd();
}

function resetSession() {
  try {
    if (recognition) recognition.abort();
  } catch { /* noop */ }
  try { recognition.start(); } catch { /* noop */ }
}

export function startWakeWord() {
  if (!Recognition || wakeActive) return false;

  try {
    recognition = new Recognition();
    recognition.lang = WATCH_LANG;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = onWakeResult;
    recognition.onend = onWakeEnd;
    recognition.onerror = onWakeError;

    recognition.start();
    wakeActive = true;
    mode = "wake";
    commandOffset = 0;
    return true;
  } catch {
    wakeActive = false;
    recognition = null;
    return false;
  }
}

export function stopWakeWord() {
  wakeActive = false;
  mode = "wake";
  commandOffset = 0;
  clearCommandTimer();
  if (recognition) {
    try { recognition.abort(); } catch { /* noop */ }
    recognition = null;
  }
  set({ wake: false, listening: false });
  if (state.aliceState === "listening") aliceState("idle");
}

export function isWakeEnabled() {
  return wakeActive;
}

export async function enableWakeWord() {
  if (!Recognition) return false;
  if (wakeActive) return true;

  // First grab the mic for the live level meter; this is what prompts the
  // browser for permission and lets the visualiser react in real time.
  await startLevelMeter();

  const ok = startWakeWord();
  set({ handsFree: ok, listening: false, permission: { ...state.permission, mic: ok } });
  return ok;
}

export function disableWakeWord() {
  stopWakeWord();
  stopLevelMeter();
  set({ handsFree: false, listening: false, permission: { ...state.permission, mic: false } });
}

/* ---------------- One-shot dictation (mic button) ---------------- */

let dictation = null;
let dictationActive = false;

export function canListen() {
  return Boolean(Recognition);
}

export function startListening(callback) {
  if (!Recognition) return false;

  // The wake session and a one-shot dictation can't share the recogniser.
  // Pause the wake loop, run the dictation, then resume it.
  if (wakeActive) stopWakeWord();

  stopListening();

  dictationActive = true;

  dictation = new Recognition();
  dictation.lang = WATCH_LANG;
  dictation.interimResults = true;
  dictation.continuous = false;

  dictation.onresult = (event) => {
    let interim = "";
    let final = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const text = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += text;
      else interim += text;
    }
    if (callback) callback(final || interim, Boolean(final));
  };

  dictation.onend = () => {
    dictationActive = false;
    dictation = null;
    set({ listening: false });
    aliceState(state.aliceState === "listening" ? "idle" : state.aliceState);
    if (wakeActive === false && state.handsFree) startWakeWord();
  };

  try {
    dictation.start();
    set({ listening: true });
    return true;
  } catch {
    dictationActive = false;
    dictation = null;
    return false;
  }
}

export function stopListening() {
  if (dictation) {
    try { dictation.abort(); } catch { /* already stopped */ }
    dictation = null;
  }
  dictationActive = false;
  set({ listening: false });
}

/* ---------------- helpers used by the UI ---------------- */

export function micPermission() {
  return state.permission.mic;
}
