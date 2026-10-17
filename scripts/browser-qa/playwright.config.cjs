const { defineConfig } = require('../../.runtime/browser-qa/node_modules/@playwright/test');
const path = require('node:path');
const qaRoot = path.resolve(__dirname, '../../.runtime/browser-qa');
module.exports = defineConfig({
  testDir: __dirname, testMatch: 'healthlink.spec.cjs', globalSetup: require.resolve('./global-setup.cjs'),
  workers: 1, retries: 0, timeout: 240000, expect: { timeout: 15000 },
  outputDir: path.join(qaRoot, 'results'),
  reporter: [['list'], ['html', { outputFolder: path.join(qaRoot, 'report'), open: 'never' }],
    ['json', { outputFile: path.join(qaRoot, 'results.json') }]],
  use: { baseURL: 'http://127.0.0.1:3001', channel: 'msedge', headless: true,
    viewport: { width: 1366, height: 900 }, timezoneId: 'Asia/Dhaka', locale: 'en-GB',
    screenshot: 'only-on-failure', trace: 'off', actionTimeout: 15000, navigationTimeout: 30000 },
});
