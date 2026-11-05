"use strict";

// eslint-disable-next-line @typescript-eslint/no-require-imports -- Legacy lint consumers load CommonJS.
const engine = require("minimatch-engine");

function adapt(api) {
  const match = typeof api === "function" ? api : api.minimatch;
  function minimatch(path, pattern, options) {
    return match(path, pattern, options);
  }
  Object.assign(minimatch, api);
  minimatch.minimatch = minimatch;
  // Existing import-plugin callers only use .test(); keep matching non-regex.
  minimatch.makeRe = (pattern, options) => {
    const matcher = new api.Minimatch(pattern, options);
    return { test: (path) => matcher.match(path) };
  };
  minimatch.defaults = (options) => adapt(api.defaults(options));
  return minimatch;
}

module.exports = adapt(engine);
