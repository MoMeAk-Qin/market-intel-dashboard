module.exports = {
  extends: ["next/core-web-vitals"],
  settings: {
    next: {
      rootDir: ["apps/web/"],
    },
  },
  rules: {
    // App Router 项目无需 pages 目录检查，关闭该规则以避免误报。
    "@next/next/no-html-link-for-pages": "off",
  },
};
