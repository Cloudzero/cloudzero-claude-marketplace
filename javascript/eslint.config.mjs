/**
 * Copyright (c) CloudZero - ALL RIGHTS RESERVED - PROPRIETARY AND CONFIDENTIAL
 * Unauthorized copying of this file and/or project, via any medium is strictly prohibited.
 * Direct all questions to legal@cloudzero.com
 *
 * CHANGELOG: 2025-11-17 - Initial creation (erik.peterson)
 */

import eslint from "@eslint/js";
import tseslint from "typescript-eslint";
import prettier from "eslint-config-prettier";
import jest from "eslint-plugin-jest";
import globals from "globals";

export default [
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  prettier,
  {
    files: ["**/*.ts"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        project: "./tsconfig.json",
      },
    },
  },
  {
    files: ["**/*.{js,mjs,cjs}"],
    languageOptions: {
      parser: tseslint.parser,
      globals: {
        ...globals.node,
      },
    },
  },
  {
    files: ["**/*.test.ts", "**/*.spec.ts"],
    plugins: {
      jest,
    },
    rules: {
      ...jest.configs.recommended.rules,
    },
    languageOptions: {
      globals: {
        ...jest.environments.globals.globals,
      },
    },
  },
];
