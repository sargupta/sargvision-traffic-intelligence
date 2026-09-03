import { afterEach, describe, expect, it, vi } from "vitest";
import { clearToken, getToken, onTokenChange, setToken } from "./auth";

afterEach(() => clearToken());

describe("the officer token store", () => {
  it("keeps a token across a reload of the same browser", () => {
    setToken("abc123");
    expect(window.localStorage.getItem("sargvision.officer_token")).toBe("abc123");
    expect(getToken()).toBe("abc123");
  });

  it("trims what was pasted, because a copied token carries whitespace", () => {
    setToken("  abc123\n");
    expect(getToken()).toBe("abc123");
  });

  it("locking the console removes the token rather than storing an empty one", () => {
    setToken("abc123");
    clearToken();
    expect(getToken()).toBe("");
    expect(window.localStorage.getItem("sargvision.officer_token")).toBeNull();
  });

  it("notifies listeners, so the header cannot show a stale lock state", () => {
    const seen = vi.fn();
    const stop = onTokenChange(seen);
    setToken("abc123");
    expect(seen).toHaveBeenCalled();
    stop();
    setToken("def456");
    expect(seen).toHaveBeenCalledTimes(1);
  });

  it("follows a change made in another tab in the same room", () => {
    const seen = vi.fn();
    const stop = onTokenChange(seen);
    window.dispatchEvent(new Event("storage"));
    expect(seen).toHaveBeenCalled();
    stop();
  });

  it("keeps working when the browser refuses storage", () => {
    // A private window, or site data blocked. Recording must degrade to this
    // session rather than throwing on a control room console.
    const setItem = vi
      .spyOn(window.localStorage, "setItem")
      .mockImplementation(() => {
        throw new Error("denied");
      });
    const getItem = vi
      .spyOn(window.localStorage, "getItem")
      .mockImplementation(() => {
        throw new Error("denied");
      });

    expect(() => setToken("abc123")).not.toThrow();
    expect(getToken()).toBe("abc123"); // held in memory for this session

    setItem.mockRestore();
    getItem.mockRestore();
  });
});
