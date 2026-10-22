// Fail closed on every advisory except reviewed, exact-version, dev-only cases.
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const object = value => value !== null && typeof value === "object" && !Array.isArray(value);

export function evaluateAudit(report, lock, policy, { production = false, today = new Date().toISOString().slice(0, 10) } = {}) {
  if (!object(report) || report.error || report.auditReportVersion !== 2 ||
      !object(report.vulnerabilities) || !object(report.metadata?.vulnerabilities) ||
      !object(lock?.packages) || policy?.version !== 1 || !Array.isArray(policy.exceptions)) {
    throw new Error("Invalid or unavailable dependency audit; security gate closed.");
  }
  const exceptions = new Map();
  for (const item of policy.exceptions) {
    const expiry = Date.parse(`${item?.expires}T00:00:00Z`);
    const validDate = Number.isFinite(expiry) && new Date(expiry).toISOString().slice(0, 10) === item.expires;
    if (!/^GHSA-[a-z0-9-]+$/.test(item.id ?? "") || !item.package || !item.version || !item.reason ||
        !validDate || !/^\d{4}-\d{2}-\d{2}$/.test(item.expires ?? "") || item.expires < today || exceptions.has(item.id)) {
      throw new Error("Invalid, duplicate or expired audit exception; review the security policy.");
    }
    exceptions.set(item.id, item);
  }
  const accepted = new Set();
  const blocked = new Set();
  function visit(name, ancestors = new Set()) {
    const entry = report.vulnerabilities[name];
    if (ancestors.has(name) || !object(entry) || !Array.isArray(entry.via) || entry.via.length === 0) {
      throw new Error("Incomplete dependency advisory chain; security gate closed.");
    }
    const next = new Set([...ancestors, name]);
    for (const cause of entry.via) {
      if (typeof cause === "string") { visit(cause, next); continue; }
      if (!object(cause) || typeof cause.url !== "string" || cause.name !== name) {
        throw new Error("Unrecognized dependency advisory; security gate closed.");
      }
      const id = /^https:\/\/github\.com\/advisories\/(GHSA-[a-z0-9-]+)$/.exec(cause.url)?.[1];
      const exception = exceptions.get(id);
      const exactDevOnly = Array.isArray(entry.nodes) && entry.nodes.length > 0 && entry.nodes.every(node => {
        const installed = lock.packages[node];
        const matchesName = typeof node === "string" &&
          (node === `node_modules/${name}` || node.endsWith(`/node_modules/${name}`));
        return matchesName && object(installed) && installed.dev === true && installed.version === exception?.version;
      });
      if (!production && exception?.package === name && exactDevOnly) accepted.add(id);
      else blocked.add(`${name}: ${id ?? cause.url}`);
    }
  }
  for (const name of Object.keys(report.vulnerabilities)) visit(name);
  const count = Object.keys(report.vulnerabilities).length;
  if (!Number.isInteger(report.metadata.vulnerabilities.total) || report.metadata.vulnerabilities.total !== count) {
    throw new Error("Inconsistent dependency audit totals; security gate closed.");
  }
  return { accepted: [...accepted].sort(), blocked: [...blocked].sort(), affectedPackages: count };
}

export function parseAuditProcess(result) {
  if (result.error || ![0, 1].includes(result.status)) throw new Error("npm audit transport failed; security gate closed.");
  let report;
  try { report = JSON.parse(result.stdout); }
  catch { throw new Error("npm audit returned invalid JSON; security gate closed."); }
  if ((result.status === 0) !== (report.metadata?.vulnerabilities?.total === 0)) {
    throw new Error("npm audit status disagrees with its report; security gate closed.");
  }
  return report;
}

function main() {
  const npm = process.env.npm_execpath;
  if (!npm) throw new Error("Run this gate with npm run audit:security.");
  const lock = JSON.parse(readFileSync(path.join(root, "frontend/package-lock.json"), "utf8"));
  const policy = JSON.parse(readFileSync(path.join(root, "security/npm-audit-policy.json"), "utf8"));
  for (const production of [true, false]) {
    const args = [npm, "audit", "--json", "--audit-level=low", "--ignore-scripts", ...(production ? ["--omit=dev"] : [])];
    const result = spawnSync(process.execPath, args, { cwd: path.join(root, "frontend"), encoding: "utf8", timeout: 120000, maxBuffer: 5_000_000 });
    const outcome = evaluateAudit(parseAuditProcess(result), lock, policy, { production });
    if (outcome.blocked.length) throw new Error(`Unaccepted ${production ? "production" : "development"} advisories:\n${outcome.blocked.join("\n")}`);
    console.log(`${production ? "Production" : "Full"} dependency gate passed; ${outcome.affectedPackages} flagged package entries, ${outcome.accepted.length} reviewed dev-only exceptions.`);
    for (const id of outcome.accepted) console.log(`EXCEPTION ${id}, expires ${policy.exceptions.find(item => item.id === id).expires}; see security/npm-audit-policy.json.`);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
