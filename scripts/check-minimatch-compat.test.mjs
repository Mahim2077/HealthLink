import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const frontend = fileURLToPath(new URL("../frontend/", import.meta.url));
const require = createRequire(path.join(frontend, "package.json"));
const minimatch = require("minimatch");
const { ESLint } = require("eslint");
const json = filename => JSON.parse(readFileSync(filename, "utf8"));
const consumers = {
  eslint: "9.39.2",
  "@eslint/config-array": "0.21.2",
  "@eslint/eslintrc": "3.3.7",
  "eslint-plugin-import": "2.32.0",
  "eslint-plugin-jsx-a11y": "6.10.2",
  "eslint-plugin-react": "7.37.5",
  "@typescript-eslint/typescript-estree": "8.72.0",
};

test("the adapter uses the genuine patched engine and remains development-only", () => {
  const lock = json(path.join(frontend, "package-lock.json"));
  const adapter = lock.packages["node_modules/minimatch"];
  const engine = lock.packages["node_modules/minimatch-engine"];
  assert.equal(adapter.name, "@healthlink/minimatch-compat");
  assert.equal(adapter.dev, true);
  assert.equal(engine.name, "minimatch");
  assert.equal(engine.version, "11.0.4");
  assert.equal(engine.dev, true);
  assert.equal(engine.resolved, "https://registry.npmjs.org/minimatch/-/minimatch-11.0.4.tgz");
  assert.match(engine.integrity, /^sha512-/);
  assert.equal(require("minimatch-engine/package.json").version, "11.0.4");
  for (const [node, pkg] of Object.entries(lock.packages)) {
    if (pkg.name === "@healthlink/minimatch-compat") {
      assert.equal(node, "node_modules/minimatch", `Unexpected adapter alias: ${node}`);
      assert.equal(pkg.dev, true, `Runtime adapter use: ${node}`);
    }
    if (node !== "node_modules/minimatch" && (node.endsWith("/minimatch") || pkg.name === "minimatch")) {
      assert.equal(node, "node_modules/minimatch-engine", `Unexpected glob implementation: ${node}`);
    }
    if (pkg.dependencies?.minimatch) {
      const name = node.slice(node.lastIndexOf("node_modules/") + "node_modules/".length);
      assert.equal(Object.hasOwn(consumers, name), true, `Review new glob consumer: ${name}`);
      assert.equal(pkg.dev, true, `Runtime glob consumer: ${name}`);
      assert.equal(pkg.version, consumers[name], `Review changed glob consumer: ${name}`);
    }
  }
});

test("every pinned lint consumer resolves the callable and named compatibility API", () => {
  for (const [name, version] of Object.entries(consumers)) {
    const manifest = path.join(frontend, "node_modules", name, "package.json");
    assert.equal(json(manifest).version, version);
    const load = createRequire(manifest);
    assert.equal(load("minimatch"), minimatch, `Different adapter for ${name}`);
    assert.equal(typeof load("minimatch").minimatch, "function");
    assert.equal(load("minimatch")("src/app/page.tsx", "src/**/*.tsx"), true);
  }
});

test("legacy glob behavior covers file traversal, options and platform paths", () => {
  const cases = [
    ["src/app/page.tsx", "src/**/*.tsx", {}, true],
    ["other/page.tsx", "src/**/*.tsx", {}, false],
    [".env", "*", {}, false], [".env", "*", { dot: true }, true],
    ["src/.hidden.ts", "src/**/*.ts", {}, false],
    ["src/.hidden.ts", "src/**/*.ts", { dot: true }, true],
    ["src/lib/a.ts", "src/{app,lib}/**/*.ts", {}, true],
    ["src/app/page.tsx", "!**/*.test.tsx", {}, true],
    ["src/app/page.test.tsx", "!**/*.test.tsx", {}, false],
    ["page.tsx", "*.+(ts|tsx)", {}, true],
    ["src/app/page.tsx", "*.tsx", { matchBase: true }, true],
    ["src/app/page.tsx", "*.tsx", {}, false],
    ["SRC/App/Page.TSX", "src/**/*.tsx", { nocase: true }, true],
    ["!file.ts", "!*.ts", { nonegate: true }, true],
    ["#guide", "#*", { nocomment: true }, true], ["#guide", "#*", {}, false],
    ["src/app/", "src/**", {}, true],
    ["src/app/../lib/file.ts", "src/**/*.ts", {}, false],
    ["src\\app\\page.tsx", "src/**/*.tsx", {}, process.platform === "win32"],
    ["C:\\work\\file.ts", "C:/**/*.ts", {}, process.platform === "win32"],
    ["src/app/page.tsx", "src/*/page.tsx", { noglobstar: true }, true],
    ["src/app/nested/page.tsx", "src/*/page.tsx", { noglobstar: true }, false],
  ];
  for (const [filename, pattern, options, expected] of cases) {
    assert.equal(minimatch(filename, pattern, options), expected, `${filename}: ${pattern}`);
    assert.equal(minimatch.minimatch(filename, pattern, options), expected);
  }
  const matcher = new minimatch.Minimatch("src/**/*.tsx");
  assert.equal(matcher.pattern, "src/**/*.tsx");
  assert.equal(matcher.match("src/app", true), true);
  assert.equal(matcher.match("other", true), false);
});

test("legacy helpers retain default options while avoiding regex backtracking", () => {
  const paths = ["src/a.ts", "src/a.tsx", ".hidden.ts"];
  assert.deepEqual(minimatch.match(paths, "**/*.ts"), ["src/a.ts"]);
  assert.deepEqual(paths.filter(minimatch.filter("**/*.ts")), ["src/a.ts"]);
  assert.deepEqual(minimatch.braceExpand("src/{a,b}.tsx"), ["src/a.tsx", "src/b.tsx"]);
  const withDefaults = minimatch.defaults({ dot: true }).defaults({ nocase: true });
  assert.equal(withDefaults(".HIDDEN.TS", "*.ts"), true);
  assert.equal(new withDefaults.Minimatch("*.ts").match(".HIDDEN.TS"), true);
  const tester = withDefaults.makeRe("*.ts");
  assert.equal(tester instanceof RegExp, false);
  assert.equal(tester.test(".HIDDEN.TS"), true);
  assert.equal(tester.test("image.png"), false);
});

test("ES module consumers receive both default and named exports", () => {
  const result = spawnSync(process.execPath, ["--input-type=module", "-e", `
    import match, { minimatch, Minimatch, makeRe } from "minimatch";
    if (match !== minimatch || !match("src/a.ts", "src/**/*.ts") ||
        !new Minimatch("**/*.ts").match("src/a.ts") || !makeRe("**/*.ts").test("src/a.ts")) process.exit(1);
  `], { cwd: frontend, encoding: "utf8", timeout: 10000 });
  assert.equal(result.error, undefined);
  assert.equal(result.status, 0, result.stderr);
});

test("Next, React Hooks, TypeScript and accessibility rules still flag invalid code", async () => {
  const eslint = new ESLint({ cwd: frontend });
  const [result] = await eslint.lintText(`
    import { useState } from "react";
    export function Guard({ active }: { active: any }) {
      if (active) useState(0);
      return <img src="/photo.png" />;
    }
  `, { filePath: "src/components/lint-guard.tsx" });
  const rules = new Set(result.messages.map(message => message.ruleId));
  for (const rule of ["react-hooks/rules-of-hooks", "@typescript-eslint/no-explicit-any", "@next/next/no-img-element", "jsx-a11y/alt-text"]) {
    assert.equal(rules.has(rule), true, `Missing lint protection: ${rule}`);
  }
});

test("the import plugin's legacy test helper still enforces forbidden paths", async () => {
  const eslint = new ESLint({ cwd: frontend, overrideConfig: {
    rules: { "import/no-internal-modules": ["error", { forbid: ["react/**"] }] },
  } });
  const [blocked] = await eslint.lintText('import value from "react/internal"; export { value };', { filePath: "src/lib/lint-guard.ts" });
  const [allowed] = await eslint.lintText('import value from "react"; export { value };', { filePath: "src/lib/lint-guard.ts" });
  assert.equal(blocked.messages.some(message => message.ruleId === "import/no-internal-modules"), true);
  assert.equal(allowed.messages.some(message => message.ruleId === "import/no-internal-modules"), false);
});
