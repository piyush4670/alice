/* The Voice Engine.

ALICE speaks and listens on every device — especially Android, where the
built-in Web Speech APIs are flaky.

Speaking (TTS), in order of preference:
  1. Server TTS  →  /api/voice/speak  (Groq PlayAI)  — reliable MP3
  2. Browser speechSynthesis with Android unlock hacks

Listening (STT), in order of preference:
  1. MediaRecorder + /api/voice/transcribe (Whisper)  — works on Android
  2. webkitSpeechRecognition one-shot (desktop Chrome fallback)

Wake-word “Hey Alice” still uses the browser recogniser when available
(continuous mode). On Android the mic button is the reliable path.
*/

import { set, state, aliceState } from "./state.js";
import { plain } from "./md.js";
import { level } from "./level.js";

/* ---------------- Speech synthesis (ALICE talking) ---------------- */

let voice = null;
let voicesReady = false;
let currentAudio = null;       // HTMLAudioElement for server TTS
let speakToken = 0;            // cancels in-flight speak() calls
let browserUnlocked = false;   // Android needs a gesture-primed synth

const PREFERRED = [
  "Google UK English Female",
  "Google US English",
  "Microsoft Aria Online (Natural) - English (United States)",
  "Microsoft Zira - English (United States)",
  "Samantha",
  "Karen",
  "Serena",
  "English United Kingdom",
  "en-GB",
  "en-US",
];

function pickVoice() {
  if (!("speechSynthesis" in window)) return;
  const voices = speechSynthesis.getVoices() || [];
  if (!voices.length) return;
  voicesReady = true;
  for (const name of PREFERRED) {
    const found = voices.find((v) => v.name.includes(name) || v.lang === name);
    if (found) { voice = found; return; }
  }
  voice = voices.find((v) => (v.lang || "").toLowerCase().startsWith("en")) || voices[0];
}

/** Android Chrome often never fires voiceschanged — poll briefly. */
function warmVoices() {
  if (!("speechSynthesis" in window)) return;
  pickVoice();
  speechSynthesis.onvoiceschanged = pickVoice;
  let tries = 0;
  const tick = () => {
    if (voicesReady || tries++ > 20) return;
    pickVoice();
    if (!voicesReady) setTimeout(tick, 250);
  };
  setTimeout(tick, 100);
}

/**
 * Prime the speech engine inside a user gesture. Required on Android
 * Chrome — without this, later speak() calls silently produce no audio.
 */
export function unlockAudio() {
  if (browserUnlocked) return;
  browserUnlocked = true;

  // Resume any suspended AudioContext used by the level meter later.
  try {
    if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
  } catch { /* noop */ }

  if (!("speechSynthesis" in window)) return;

  try {
    // A near-silent utterance unlocks the synth for the session.
    const u = new SpeechSynthesisUtterance(" ");
    u.volume = 0;
    u.rate = 2;
    speechSynthesis.speak(u);
    speechSynthesis.cancel();
    pickVoice();
  } catch { /* noop */ }
}

export function initVoice() {
  warmVoices();
  // Restore speak preference so Alice keeps talking across reloads.
  // Default is ON (she speaks). Only an explicit "0" mutes her.
  try {
    const saved = localStorage.getItem("alice.speak");
    if (saved === "0") set({ speak: false });
    else set({ speak: true });
  } catch { /* private mode — keep default on */ }
}

function markSpeaking(on) {
  set({ speaking: on });
  if (on) {
    aliceState("speaking");
    level.source = "speak";
  } else if (state.aliceState === "speaking") {
    aliceState(state.listening || state.wake ? "listening" : "idle");
    level.source = state.listening ? "mic" : "idle";
  }
}

function finishSpeak(token) {
  if (token !== speakToken) return;
  markSpeaking(false);
}

/** Browser speechSynthesis path with Android keep-alive hacks. */
function speakBrowser(body, token) {
  if (!("speechSynthesis" in window)) {
    finishSpeak(token);
    return false;
  }

  try {
    speechSynthesis.cancel();
  } catch { /* noop */ }

  if (!voicesReady) pickVoice();

  const utterance = new SpeechSynthesisUtterance(body);
  if (voice) utterance.voice = voice;
  utterance.lang = (voice && voice.lang) || "en-US";
  utterance.rate = 1.02;
  utterance.pitch = 1.03;
  utterance.volume = 1;

  let settled = false;
  const settle = () => {
    if (settled) return;
    settled = true;
    clearInterval(keepAlive);
    clearTimeout(watchdog);
    finishSpeak(token);
  };

  utterance.onstart = () => {
    if (token !== speakToken) return;
    markSpeaking(true);
  };
  utterance.onend = settle;
  utterance.onerror = settle;

  // Chrome pauses speechSynthesis after ~15s of continuous speak.
  const keepAlive = setInterval(() => {
    if (token !== speakToken) { clearInterval(keepAlive); return; }
    try {
      if (speechSynthesis.speaking) {
        speechSynthesis.pause();
        speechSynthesis.resume();
      }
    } catch { /* noop */ }
  }, 8000);

  // Hard stop if the engine swallows the utterance (common on Android).
  const watchdog = setTimeout(() => {
    if (token !== speakToken) return;
    if (!speechSynthesis.speaking && !speechSynthesis.pending) settle();
  }, Math.max(8000, body.length * 80));

  try {
    markSpeaking(true);
    speechSynthesis.speak(utterance);
    // Some Android builds need an explicit resume right after speak().
    try { speechSynthesis.resume(); } catch { /* noop */ }
    return true;
  } catch {
    settle();
    return false;
  }
}

/** Server TTS → play an MP3. Most reliable path on phones. */
async function speakServer(body, token) {
  const res = await fetch("/api/voice/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: body }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(detail || `speak ${res.status}`);
  }

  const blob = await res.blob();
  if (token !== speakToken) return;

  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.preload = "auto";
  currentAudio = audio;

  await new Promise((resolve, reject) => {
    const done = () => {
      URL.revokeObjectURL(url);
      if (currentAudio === audio) currentAudio = null;
      resolve();
    };
    audio.onended = done;
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      if (currentAudio === audio) currentAudio = null;
      reject(new Error("audio playback failed"));
    };
    markSpeaking(true);
    const play = audio.play();
    if (play && typeof play.then === "function") {
      play.catch(reject);
    }
  });

  finishSpeak(token);
}

export function speak(text) {
  if (!state.speak) return;

  const body = plain(text).slice(0, 900);
  if (!body) return;

  // Fresh token cancels any in-flight speak.
  const token = ++speakToken;
  cancelSpeechPlayback();

  // Prefer server TTS; fall back to browser synth.
  speakServer(body, token).catch(() => {
    if (token !== speakToken) return;
    speakBrowser(body, token);
  });
}

function cancelSpeechPlayback() {
  if (currentAudio) {
    try {
      currentAudio.pause();
      currentAudio.src = "";
    } catch { /* noop */ }
    currentAudio = null;
  }
  if ("speechSynthesis" in window) {
    try { speechSynthesis.cancel(); } catch { /* noop */ }
  }
}

export function cancelSpeech() {
  speakToken += 1;
  cancelSpeechPlayback();
  markSpeaking(false);
}

export function isSpeaking() {
  if (currentAudio && !currentAudio.paused) return true;
  return "speechSynthesis" in window && speechSynthesis.speaking;
}

export function toggleSpeak() {
  unlockAudio();
  const next = !state.speak;
  if (!next) cancelSpeech();
  set({ speak: next });
  try { localStorage.setItem("alice.speak", next ? "1" : "0"); } catch { /* noop */ }
  return next;
}

/* ---------------- Live mic level meter ---------------- */

let stream = null;
let analyser = null;
let audioCtx = null;
let levelRaf = null;
let levelData = null;

function startLevelMeter(existingStream) {
  if (!("mediaDevices" in navigator) || !navigator.mediaDevices.getUserMedia) return Promise.resolve(false);

  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return Promise.resolve(false);

  const attach = (s) => {
    stream = s;
    try {
      audioCtx = audioCtx || new AudioCtx();
      if (audioCtx.state === "suspended") audioCtx.resume();
      const source = audioCtx.createMediaStreamSource(s);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.75;
      source.connect(analyser);
      levelData = new Uint8Array(analyser.frequencyBinCount);
      level.source = "mic";
      tickLevel();
      return true;
    } catch {
      return false;
    }
  };

  if (existingStream) return Promise.resolve(attach(existingStream));

  return navigator.mediaDevices
    .getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    })
    .then(attach)
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

let recognition = null;
let wakeActive = false;
let mode = "wake";
let commandOffset = 0;
let commandBuffer = "";
let commandTimer = null;

let onWakeHandler = null;
let onCommandHandler = null;
let onInterimHandler = null;
let onPermissionDenied = null;
let onListenError = null;

export function setWakeHandlers({ onWake, onCommand, onInterim, onPermissionDenied: onDeny, onError }) {
  onWakeHandler = onWake || null;
  onCommandHandler = onCommand || null;
  onInterimHandler = onInterim || null;
  onPermissionDenied = onDeny || null;
  onListenError = onError || null;
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
  return WAKE_PHRASES[WAKE_PHRASES.length - 1];
}

function armCommandTimer() {
  clearCommandTimer();
  commandTimer = setTimeout(() => {
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
  if (!wakeActive) return;

  if (mode === "command") {
    const cmd = cleanCommand(commandBuffer);
    if (cmd) {
      dispatchCommand(cmd);
      return;
    }
    clearCommandTimer();
    mode = "wake";
    commandOffset = 0;
  }

  try { recognition.start(); } catch { /* already starting */ }
}

function onWakeError(event) {
  const err = event && event.error;

  if (err === "not-allowed" || err === "service-not-allowed") {
    disableWakeWord();
    if (onPermissionDenied) onPermissionDenied();
    return;
  }

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
  unlockAudio();
  if (!Recognition) return false;
  if (wakeActive) return true;

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

/* ---------------- Mic button: MediaRecorder + Whisper (Android-first) ---------------- */

let dictation = null;
let dictationActive = false;
let recorder = null;
let recordChunks = [];
let recordStream = null;
let recordTimer = null;
let recordCallback = null;
let recordMode = null; // "media" | "webkit"

const MAX_RECORD_MS = 20000;

function pickMimeType() {
  if (typeof MediaRecorder === "undefined") return "";
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
    "audio/aac",
  ];
  for (const type of candidates) {
    try {
      if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(type)) return type;
    } catch { /* noop */ }
  }
  return "";
}

/** True when we can listen somehow. */
export function canListen() {
  return Boolean(
    (typeof MediaRecorder !== "undefined" && navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
    || Recognition
  );
}

/**
 * Preferred path on Android: hold-to-talk via MediaRecorder, then
 * POST the clip to /api/voice/transcribe (Whisper).
 */
async function startMediaDictation(callback) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error("no media devices");
  }
  if (typeof MediaRecorder === "undefined") {
    throw new Error("no MediaRecorder");
  }

  unlockAudio();

  // Pause wake loop so it doesn't fight for the mic.
  const wasWake = wakeActive;
  if (wasWake) stopWakeWord();

  const mime = pickMimeType();
  const constraints = {
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      channelCount: 1,
    },
  };

  const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
  recordStream = mediaStream;
  await startLevelMeter(mediaStream);

  recordChunks = [];
  recordCallback = callback;
  recordMode = "media";

  const options = mime ? { mimeType: mime } : undefined;
  let rec;
  try {
    rec = options ? new MediaRecorder(mediaStream, options) : new MediaRecorder(mediaStream);
  } catch {
    rec = new MediaRecorder(mediaStream);
  }
  recorder = rec;

  rec.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) recordChunks.push(e.data);
  };

  rec.onerror = () => {
    finishMediaDictation(new Error("recorder error"));
  };

  rec.onstop = () => {
    const chunks = recordChunks.slice();
    const type = rec.mimeType || mime || "audio/webm";
    cleanupRecorder();
    processRecording(chunks, type, callback, wasWake);
  };

  try {
    rec.start(250);
  } catch (err) {
    cleanupRecorder();
    if (wasWake && state.handsFree) startWakeWord();
    throw err;
  }

  dictationActive = true;
  set({ listening: true, permission: { ...state.permission, mic: true } });
  aliceState("listening");

  // Auto-stop so a forgotten tap doesn't record forever.
  clearTimeout(recordTimer);
  recordTimer = setTimeout(() => {
    if (dictationActive && recordMode === "media") stopListening();
  }, MAX_RECORD_MS);

  return true;
}

function cleanupRecorder() {
  clearTimeout(recordTimer);
  recordTimer = null;
  if (recorder && recorder.state !== "inactive") {
    try { recorder.stop(); } catch { /* noop */ }
  }
  recorder = null;
  if (recordStream) {
    // Level meter owns the tracks when attached; only stop if meter isn't using them.
    try {
      if (stream !== recordStream) {
        recordStream.getTracks().forEach((t) => t.stop());
      }
    } catch { /* noop */ }
    recordStream = null;
  }
  recordChunks = [];
}

async function processRecording(chunks, type, callback, resumeWake) {
  dictationActive = false;
  set({ listening: false });
  if (state.aliceState === "listening") aliceState("idle");

  // Stop the level meter now that recording is done.
  stopLevelMeter();

  if (resumeWake && state.handsFree) {
    try { startWakeWord(); } catch { /* noop */ }
  }

  if (!chunks.length) {
    if (callback) callback("", true);
    if (onListenError) onListenError("I didn't catch any audio — try again.");
    return;
  }

  const blob = new Blob(chunks, { type: type || "audio/webm" });
  if (blob.size < 256) {
    if (callback) callback("", true);
    if (onListenError) onListenError("That was too short — hold the mic and speak.");
    return;
  }

  try {
    const form = new FormData();
    const ext = (type || "").includes("mp4") ? "mp4"
      : (type || "").includes("ogg") ? "ogg"
      : "webm";
    form.append("audio", blob, `alice.${ext}`);
    form.append("language", "en");

    const res = await fetch("/api/voice/transcribe", {
      method: "POST",
      body: form,
    });

    if (!res.ok) {
      let detail = "Speech recognition failed.";
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch { /* noop */ }
      if (onListenError) onListenError(typeof detail === "string" ? detail : "Speech recognition failed.");
      if (callback) callback("", true);
      return;
    }

    const data = await res.json();
    const text = (data.text || "").trim();
    if (callback) callback(text, true);
    if (!text && onListenError) onListenError("I couldn't catch that — try again.");
  } catch (err) {
    if (onListenError) onListenError("Couldn't reach the speech service.");
    if (callback) callback("", true);
  }
}

function finishMediaDictation() {
  if (recorder && recorder.state === "recording") {
    try { recorder.stop(); } catch { /* onstop handles cleanup */ }
  } else {
    cleanupRecorder();
    dictationActive = false;
    set({ listening: false });
  }
}

/** Desktop fallback: one-shot Web Speech API. */
function startWebkitDictation(callback) {
  if (!Recognition) return false;

  if (wakeActive) stopWakeWord();
  stopListening();

  dictationActive = true;
  recordMode = "webkit";
  recordCallback = callback;

  dictation = new Recognition();
  dictation.lang = WATCH_LANG;
  dictation.interimResults = true;
  dictation.continuous = false;
  dictation.maxAlternatives = 3;

  dictation.onresult = (event) => {
    let interim = "";
    let final = "";
    let best = 0;
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const alt = event.results[i][0];
      const text = alt.transcript;
      const conf = alt.confidence || 0;
      if (event.results[i].isFinal) {
        if (conf >= best) { final = text; best = conf; }
        else final += text;
      } else {
        interim += text;
      }
    }
    if (callback) callback((final || interim).trim(), Boolean(final));
  };

  dictation.onerror = (event) => {
    const err = event && event.error;
    if (err === "not-allowed" || err === "service-not-allowed") {
      if (onPermissionDenied) onPermissionDenied();
    } else if (err && err !== "aborted" && err !== "no-speech") {
      if (onListenError) onListenError("Mic error — try holding the button and speaking clearly.");
    }
  };

  dictation.onend = () => {
    dictationActive = false;
    dictation = null;
    recordMode = null;
    set({ listening: false });
    if (state.aliceState === "listening") aliceState("idle");
    if (wakeActive === false && state.handsFree) startWakeWord();
  };

  try {
    dictation.start();
    set({ listening: true });
    aliceState("listening");
    return true;
  } catch {
    dictationActive = false;
    dictation = null;
    recordMode = null;
    return false;
  }
}

/**
 * Start listening. Prefers MediaRecorder+Whisper (reliable on Android).
 * Falls back to webkitSpeechRecognition on desktop if MediaRecorder fails.
 *
 * Tap once to start, tap again (or wait for auto-stop) to finish.
 */
export function startListening(callback) {
  unlockAudio();

  // Already recording? Treat as stop.
  if (dictationActive) {
    stopListening();
    return false;
  }

  // Prefer MediaRecorder on every platform that has it — it's the path
  // that works on Android Chrome, Samsung Internet, Firefox, etc.
  if (typeof MediaRecorder !== "undefined" && navigator.mediaDevices) {
    startMediaDictation(callback).catch((err) => {
      console.warn("[alice] media dictation failed, trying webkit", err);
      const ok = startWebkitDictation(callback);
      if (!ok && onListenError) {
        onListenError("Microphone unavailable on this device.");
      }
    });
    return true;
  }

  return startWebkitDictation(callback);
}

export function stopListening() {
  clearTimeout(recordTimer);
  recordTimer = null;

  if (recordMode === "media" && recorder) {
    finishMediaDictation();
    return;
  }

  if (dictation) {
    try { dictation.stop(); } catch {
      try { dictation.abort(); } catch { /* already stopped */ }
    }
    dictation = null;
  }
  dictationActive = false;
  recordMode = null;
  set({ listening: false });
}

export function isListening() {
  return dictationActive;
}

/* ---------------- helpers used by the UI ---------------- */

export function micPermission() {
  return state.permission.mic;
}
