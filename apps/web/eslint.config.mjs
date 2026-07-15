import coreWebVitals from "eslint-config-next/core-web-vitals";
import typescript from "eslint-config-next/typescript";

/** Flat config for ESLint 9 + eslint-config-next 16 (Next.js 16 removed `next lint`). */
const eslintConfig = [...coreWebVitals, ...typescript];

export default eslintConfig;
