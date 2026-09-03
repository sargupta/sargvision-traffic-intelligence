import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/** The command interface had no test runner at all.
 *
 *  Every defect found in it so far — a projection that drew the city 1.5x
 *  wider per kilometre than tall, an action bar below the fold at the size the
 *  control room actually runs, a CORS preflight that would have refused every
 *  write — was found by driving a browser by hand. This exists so the next one
 *  does not have to be.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
