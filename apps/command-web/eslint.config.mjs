import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

/** The interface had no linter. `next lint` wanted an interactive setup, so it
 *  had never been configured and nothing in CI looked at this code beyond
 *  `tsc --noEmit` and a successful build.
 *
 *  core-web-vitals is the useful half: it catches the accessibility and
 *  correctness mistakes that matter on a console someone stares at for a whole
 *  shift, rather than arguing about formatting. Warnings are errors, because a
 *  warning nobody fails on is a warning nobody reads.
 */
export default [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  { ignores: [".next/**", "out/**", "node_modules/**"] },
];
