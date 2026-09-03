import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

/** A real Storage for the tests.
 *
 *  Under this runner `window.localStorage` arrives as a bare object with no
 *  getItem — Node's own experimental localStorage shadows jsdom's. Left alone,
 *  every storage call throws, `lib/auth` catches it by design, and the tests
 *  that think they are exercising persistence quietly exercise the fallback
 *  instead. So install a working one and let the storage-refused case be
 *  something a test opts into deliberately.
 */
function memoryStorage(): Storage {
  let map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    key: (i: number) => [...map.keys()][i] ?? null,
    getItem: (k: string) => (map.has(k) ? map.get(k)! : null),
    setItem: (k: string, v: string) => void map.set(k, String(v)),
    removeItem: (k: string) => void map.delete(k),
    clear: () => void (map = new Map()),
  } as Storage;
}

for (const name of ["localStorage", "sessionStorage"] as const) {
  Object.defineProperty(window, name, {
    value: memoryStorage(),
    configurable: true,
    writable: true,
  });
}

afterEach(() => {
  cleanup();
  // The token store is module-level as well as persisted, so a test that
  // unlocks recording would otherwise leave the next one already unlocked.
  window.localStorage.clear();
});
