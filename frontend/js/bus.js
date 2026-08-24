/* Alice's live wire: WebSocket client with auto-reconnect. */

import { set } from "./state.js";

let socket = null;
let backoff = 800;
let wanted = true;

const handlers = new Map();

export function on(type, fn) {

  if (!handlers.has(type)) handlers.set(type, []);

  handlers.get(type).push(fn);
}

function dispatch(event) {

  const fns = handlers.get(event.type) || [];

  for (const fn of fns) {
    try { fn(event); } catch (err) { console.error("[alice] handler", event.type, err); }
  }
}

export function send(payload) {

  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
    return true;
  }

  return false;
}

function connect() {

  if (!wanted) return;

  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const url = `${scheme}://${location.host}/ws`;

  socket = new WebSocket(url);

  socket.onopen = () => {
    backoff = 800;
    set({ link: "online" });
  };

  socket.onmessage = (frame) => {

    try {
      dispatch(JSON.parse(frame.data));
    } catch {
      /* ignore malformed frames */
    }
  };

  socket.onclose = () => {

    set({ link: "offline" });

    if (!wanted) return;

    setTimeout(connect, backoff);
    backoff = Math.min(backoff * 1.7, 8000);
  };

  socket.onerror = () => socket.close();
}

export function start() { connect(); }

export function stop() {
  wanted = false;
  if (socket) socket.close();
}
