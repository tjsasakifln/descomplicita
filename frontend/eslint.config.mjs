import tsParser from "@typescript-eslint/parser";

export default [
  {
    files: ["**/*.{ts,tsx,js,jsx}"],
    languageOptions: {
      parser: tsParser,
    },
    rules: {
      "no-empty": ["error", { allowEmptyCatch: false }],
    },
  },
];
