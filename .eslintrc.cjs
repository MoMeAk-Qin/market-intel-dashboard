module.exports = {
  root: true,
  ignorePatterns: ["node_modules", ".next", "dist"],
  overrides: [
    {
      files: ["apps/api/**/*.{ts,tsx}", "packages/shared/**/*.{ts,tsx}"],
      parser: "@typescript-eslint/parser",
      plugins: ["@typescript-eslint"],
      extends: ["eslint:recommended", "plugin:@typescript-eslint/recommended"],
    },
  ],
};
