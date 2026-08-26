/* Browser notifications.

ALICE explains *why* she wants notifications before asking for them (a
permission prompt can never be granted silently in a real browser) and only
ever posts them once the user has allowed it. When denied, she stays quiet —
the event feed and the voice cover the same ground.
*/

import { state, set } from "./state.js";

function supported() {
  return "Notification" in window;
}

export function permission() {
  return supported() ? Notification.permission : "unsupported";
}

export function canNotify() {
  return supported() && Notification.permission === "granted";
}

export function setPermissionStatus() {
  set({ permission: { ...state.permission, notifications: canNotify() } });
}

/**
 * Ask the user for notification permission.
 * @param {() => Promise<void>} explain  Show a short in-app reason.
 * @returns {Promise<boolean>} whether permission is granted.
 */
export async function ensurePermission(explain) {
  if (!supported()) return false;

  if (Notification.permission === "granted") {
    setPermissionStatus();
    return true;
  }

  if (Notification.permission === "denied") return false;

  if (explain) {
    try { await explain(); } catch { /* the explain UI must never block */ }
  }

  try {
    const result = await Notification.requestPermission();
    setPermissionStatus();
    return result === "granted";
  } catch {
    return false;
  }
}

export function notify(title, body, opts = {}) {
  if (!canNotify()) return;
  try {
    const n = new Notification(title, {
      body: body || "",
      icon: opts.icon || "/icons/icon-192.png",
      badge: opts.badge || "/icons/icon-192.png",
      tag: opts.tag,
      renotify: opts.renotify,
      dir: "auto",
      silent: false,
    });
    if (opts.onClick && typeof n.onclick === "undefined") {
      n.onclick = () => opts.onClick();
    }
  } catch { /* some browsers disallow constructor directly */ }
}
