"use client";

/** The officer token that authorises recording an action.
 *
 *  Reads are open — the board renders for anyone who can reach it — so this
 *  gates only the verbs. The token is issued to the control room out of band
 *  and pasted in once; it lives in this browser and is never sent anywhere
 *  except as a Bearer header to our own API.
 *
 *  Deliberately not a login. There is no user directory behind this yet, so a
 *  shared room token is what it honestly is: proof that the person at the
 *  console belongs in the room. `by` still records which seat acted, and the
 *  audit trail is only as good as that — which is why the next step is real
 *  per-officer identity, not a longer token.
 */

const KEY = "sargvision.officer_token";
const EVENT = "sargvision:token";

/** localStorage throws in some privacy modes; recording must degrade, not crash. */
function safeGet(): string {
  try {
    return window.localStorage.getItem(KEY) ?? "";
  } catch {
    return "";
  }
}

let memory = "";

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return memory || safeGet();
}

export function setToken(token: string): void {
  memory = token.trim();
  try {
    if (memory) window.localStorage.setItem(KEY, memory);
    else window.localStorage.removeItem(KEY);
  } catch {
    /* held in memory for this session only */
  }
  window.dispatchEvent(new Event(EVENT));
}

export function clearToken(): void {
  setToken("");
}

/** Notify on change, so the header's lock state cannot drift from reality. */
export function onTokenChange(fn: () => void): () => void {
  window.addEventListener(EVENT, fn);
  window.addEventListener("storage", fn); // another tab in the same room
  return () => {
    window.removeEventListener(EVENT, fn);
    window.removeEventListener("storage", fn);
  };
}
