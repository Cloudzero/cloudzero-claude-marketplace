/**
 * Copyright (c) CloudZero - ALL RIGHTS RESERVED - PROPRIETARY AND CONFIDENTIAL
 * Unauthorized copying of this file and/or project, via any medium is strictly prohibited.
 * Direct all questions to legal@cloudzero.com
 *
 * CHANGELOG: 2025-11-17 - Initial creation (erik.peterson)
 */

import { greet, VERSION } from "../src/index";

describe("Template Tests", () => {
  it("should pass example test", () => {
    expect(true).toBe(true);
  });

  it("should have version defined", () => {
    expect(VERSION).toBeDefined();
    expect(typeof VERSION).toBe("string");
  });

  it("should greet correctly", () => {
    expect(greet("World")).toBe("Hello, World!");
  });
});
