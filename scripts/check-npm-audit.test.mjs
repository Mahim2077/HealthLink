import assert from "node:assert/strict";
import test from "node:test";
import { evaluateAudit, parseAuditProcess } from "./check-npm-audit.mjs";

const id = "GHSA-vfj7-8cjw-p6xm";
const today = "2026-10-22";
const leaf = () => ({ name: "braces", url: `https://github.com/advisories/${id}` });
const policy = () => ({ version: 1, exceptions: [{ id, package: "braces", version: "3.0.3", expires: "2026-11-21", reason: "Reviewed development-only upstream limitation" }] });
const lock = () => ({ packages: { "node_modules/braces": { dev: true, version: "3.0.3" } } });
const report = () => ({ auditReportVersion: 2, metadata: { vulnerabilities: { total: 2 } }, vulnerabilities: {
  braces: { via: [leaf()], nodes: ["node_modules/braces"] },
  "eslint-config-next": { via: ["braces"], nodes: ["node_modules/eslint-config-next"] },
} });
const evaluate = (r = report(), l = lock(), p = policy(), options = {}) => evaluateAudit(r, l, p, { today, ...options });

test("accepts a clean report without inventing findings", () => {
  const clean = report(); clean.vulnerabilities = {}; clean.metadata.vulnerabilities.total = 0;
  assert.deepEqual(evaluate(clean), { accepted: [], blocked: [], affectedPackages: 0 });
});
test("only the exact dev advisory and its inherited chain are accepted", () => {
  assert.deepEqual(evaluate(), { accepted: [id], blocked: [], affectedPackages: 2 });
});
test("no exceptions apply to the production graph", () => assert.equal(evaluate(undefined, undefined, undefined, { production: true }).blocked.length, 1));
test("a runtime or changed-version package cannot borrow the exception", () => {
  for (const change of [{ dev: false }, { version: "3.0.2" }]) {
    const changed = lock(); Object.assign(changed.packages["node_modules/braces"], change);
    assert.equal(evaluate(undefined, changed).blocked.length, 1);
  }
});
test("new advisories in the same dependency remain blocking", () => {
  const changed = report(); changed.vulnerabilities.braces.via.push({ name: "braces", url: "https://github.com/advisories/GHSA-xxxx-yyyy-zzzz" });
  assert.equal(evaluate(changed).blocked.length, 1);
});
test("expired and duplicate exceptions fail closed", () => {
  const expired = policy(); expired.exceptions[0].expires = "2026-10-21";
  assert.throws(() => evaluate(undefined, undefined, expired), /expired/);
  const duplicate = policy(); duplicate.exceptions.push(duplicate.exceptions[0]);
  assert.throws(() => evaluate(undefined, undefined, duplicate), /duplicate/);
});
test("invalid calendar dates cannot create an unbounded exception", () => {
  for (const date of ["2026-99-99", "2027-02-30", "not-a-date"]) {
    const changed = policy(); changed.exceptions[0].expires = date;
    assert.throws(() => evaluate(undefined, undefined, changed), /Invalid/);
  }
});
test("missing or cyclic advisory chains cannot hide findings", () => {
  const missing = report(); delete missing.vulnerabilities.braces;
  assert.throws(() => evaluate(missing), /Incomplete/);
  const cycle = report(); cycle.vulnerabilities.braces.via = ["eslint-config-next"];
  assert.throws(() => evaluate(cycle), /Incomplete/);
});
test("unknown response formats, missing nodes and inconsistent totals are rejected", () => {
  assert.throws(() => evaluate({ error: { code: "unavailable" } }), /Invalid/);
  const badTotals = report(); badTotals.metadata.vulnerabilities.total = 0;
  assert.throws(() => evaluate(badTotals), /Inconsistent/);
  const noNodes = report(); delete noNodes.vulnerabilities.braces.nodes;
  assert.equal(evaluate(noNodes).blocked.length, 1);
});
test("transport errors, malformed JSON and contradictory exit status fail closed", () => {
  for (const result of [{ status: 2 }, { error: new Error("offline") }, { status: 0, stdout: "not-json" }, { status: 0, stdout: JSON.stringify(report()) }]) {
    assert.throws(() => parseAuditProcess(result), /closed/);
  }
  assert.deepEqual(parseAuditProcess({ status: 1, stdout: JSON.stringify(report()) }), report());
});
