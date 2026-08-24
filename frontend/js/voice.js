/* Voice: Alice speaks (speech synthesis) and listens (speech recognition).
   Everything degrades silently on unsupported browsers. */

import { set, state } from "./state.js";
import { plain } from "./md.js";

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

  const utterance = new SpeechSynthesisUtterance(body);

  if (!voicesReady) pickVoice();

  if (voice) utterance.voice = voice;

  utterance.rate = 1.02;
  utterance.pitch = 1.03;

  speechSynthesis.speak(utterance);
}

export function toggleSpeak() {

  const next = !state.speak;

  if (!next && "speechSynthesis" in window) speechSynthesis.cancel();

  set({ speak: next });

  return next;
}

/* ---------------- Listening ---------------- */

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition = null;
let onFinal = null;

export function canListen() {
  return Boolean(Recognition);
}

export function startListening(callback) {

  if (!Recognition) return false;

  stopListening();

  onFinal = callback;

  recognition = new Recognition();
  recognition.lang = "en-US";
  recognition.interimResults = true;
  recognition.continuous = false;

  recognition.onresult = (event) => {

    let interim = "";
    let final = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {

      const text = event.results[i][0].transcript;

      if (event.results[i].isFinal) final += text;
      else interim += text;
    }

    if (onFinal) onFinal(final || interim, Boolean(final));
  };

  recognition.onend = () => set({ aliceState: state.aliceState === "listening" ? "idle" : state.aliceState });

  try {
    recognition.start();
    set({ aliceState: "listening" });
    return true;
  } catch {
    return false;
  }
}

export function stopListening() {

  if (recognition) {
    try { recognition.stop(); } catch { /* already stopped */ }
    recognition = null;
  }
}
