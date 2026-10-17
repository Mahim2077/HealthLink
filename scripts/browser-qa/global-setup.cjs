const { spawnSync } = require('node:child_process');
const path = require('node:path');
module.exports = async () => {
  const root = path.resolve(__dirname, '../..');
  const run = Date.now().toString();
  const result = spawnSync(path.join(root, '.venv/Scripts/python.exe'), [path.join(__dirname, 'seed.py'), run], {
    cwd: root, encoding: 'utf8', env: { ...process.env, APP_ENV: 'test', DEBUG: 'false',
      DATABASE_URL: 'postgresql+psycopg://postgres@127.0.0.1:55433/healthlink_phase27_qa',
      AI_ENABLED: 'false', AI_PROVIDER: 'mock', AI_RECORD_CONTEXT_ENABLED: 'false' },
  });
  if (result.status !== 0) throw new Error('Local synthetic seeding failed: ' + result.stderr);
  const fixture = JSON.parse(result.stdout.trim());
  process.env.HEALTHLINK_QA_FIXTURE = JSON.stringify(fixture);
  console.log('Created new synthetic local browser fixtures; existing accounts untouched.');
};
