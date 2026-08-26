/* Offline sanity harness: import every frontend ES module with browser shims
   so we catch missing exports / circular imports / import-time crashes
   without needing a browser. main.js is excluded (it boots the app).

       node scripts/check_frontend.mjs
*/

import { pathToFileURL } from "node:url";
import path from "node:path";

const root = path.resolve(new URL("..", import.meta.url).pathname);

/* ---- minimal browser shims ---- */
const noop = () => {};
const define = (key, value) => {
  try { Object.defineProperty(globalThis, key, { value, configurable: true, writable: true }); }
  catch { /* read-only global; leave it */ }
};
define("window", globalThis);
define("document", {
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  createElement: () => ({}),
  addEventListener: noop,
  body: { innerText: "" },
});
define("navigator", { mediaDevices: { getUserMedia: () => Promise.reject(new Error("no")) } });
define("localStorage", { getItem: () => null, setItem: noop, removeItem: noop });
define("requestAnimationFrame", noop);
define("cancelAnimationFrame", noop);
define("speechSynthesis", { getVoices: () => [], speak: noop, cancel: noop });
define("SpeechSynthesisUtterance", class {});
define("SpeechRecognition", undefined);
define("webkitSpeechRecognition", undefined);
define("WebSocket", class {});
define("AudioContext", undefined);
define("location", { protocol: "http:", host: "localhost", search: "" });

const excludes = new Set(["main.js", "check_frontend.mjs"]);
const files = ["state.js", "level.js", "md.js", "sound.js", "audio.js", "voice.js", "bus.js", "chat.js", "mission.js", "panels.js", "startup.js", "webdock.js", "notify.js"];
const dir = path.join(root, "frontend", "js");

let failed = 0;
for (const file of files) {
  const url = pathToFileURL(path.join(dir, file)).href;
  try {
    await import(url);
    console.log("OK  " + file);
  } catch (err) {
    failed++;
    console.log("ERR " + file + " :: " + err.message);
  }
}

process.exit(failed ? 1 : 0);
