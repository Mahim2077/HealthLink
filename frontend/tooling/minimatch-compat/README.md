# ESLint glob compatibility

This private development adapter keeps the existing ESLint 9 / Next.js 16 lint
stack while replacing its minimatch 3/10 implementations with the official,
hash-locked `minimatch@11.0.4` engine under the explicit `minimatch-engine` alias.
No matching implementation or security fix is copied into this package.

The callable CommonJS/default export and named helpers support the pinned lint
consumers. Legacy `makeRe()` callers in eslint-plugin-import only need `.test()`;
the adapter returns a tester backed by the engine's non-regex matcher. It does
not return a RegExp or promise general-purpose minimatch 3 compatibility.

The override applies to the seven current lint consumers. Security tests must
reject runtime use or a changed consumer set/version; review the adapter when
updating lint packages. `install-links=true` packs this local package during both
`npm install` and `npm ci`, so clean installations do not rely on symlink state.
Application runtime dependencies must never resolve this development adapter.

Run `npm run test:security`, `npm run audit:security`, lint, typecheck, frontend
tests and the optimized build after changing this package. Remove the adapter
and its overrides once the lint stack natively supports the patched engine.
