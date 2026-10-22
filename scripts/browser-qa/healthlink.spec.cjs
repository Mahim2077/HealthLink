const { test, expect } = require('../../.runtime/browser-qa/node_modules/@playwright/test');
test.describe.configure({ mode: 'serial' });
const fixture = () => JSON.parse(process.env.HEALTHLINK_QA_FIXTURE);
let sessions, failures, unexpected, allowed;
const shared = {};
test.beforeEach(() => { sessions = []; failures = []; unexpected = []; allowed = new Set(); });

async function snapshot(page, info, name) {
  await expect(page.locator('[data-nextjs-dialog]')).toHaveCount(0);
  const file = info.outputPath(name + '.png');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: file, fullPage: true, animations: 'disabled' });
  await info.attach(name, { path: file, contentType: 'image/png' });
}

async function login(page, role) {
  const f = fixture();
  const portal = role === 'doctor' || role === 'lab' ? 'professional' : role === 'other' ? 'citizen' : role;
  await page.goto(`/${portal}/login`);
  if (portal === 'professional') {
    await page.getByLabel('National ID', { exact: true }).fill(f[role + '_nid']);
    await page.getByRole('combobox', { name: 'Professional role', exact: true }).selectOption(role === 'doctor' ? 'DOCTOR' : 'LAB_TECHNICIAN');
  } else {
    await page.getByRole('textbox', { name: /Email address/ }).fill(f[(role === 'other' ? 'other' : role) + '_email']);
  }
  await page.locator('input[type="password"]').fill(f.password);
  await page.getByRole('button', { name: `Sign in to ${portal[0].toUpperCase() + portal.slice(1)} Portal`, exact: true }).click();
  await page.waitForURL(`**/${portal}/dashboard`);
  const heading = role === 'doctor' ? "Today's care overview" : role === 'lab' ? 'Your diagnostic workload' : role === 'admin' ? 'Operational overview' : 'Your care at a glance';
  await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
  await expect(page.getByText('Overview unavailable', { exact: true })).toHaveCount(0);
}

async function actor(browser, role, width = 1366, theme = 'light') {
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:3001', viewport: { width, height: 900 },
    locale: 'en-GB', timezoneId: 'Asia/Dhaka', reducedMotion: 'reduce' });
  if (theme === 'dark') await context.addInitScript(() => {
    localStorage.setItem('healthlink.interface.v1', JSON.stringify({ theme: 'dark' }));
  });
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (['data:', 'blob:'].includes(url.protocol) || (url.hostname === '127.0.0.1' && url.port === '3001')) return route.continue();
    failures.push(role + ': attempted non-local browser request');
    return route.abort();
  });
  const page = await context.newPage();
  sessions.push({ context, page, role });
  page.on('pageerror', error => failures.push(role + ': ' + error.message.slice(0, 200)));
  page.on('console', message => {
    if (message.type() === 'error' && !message.text().startsWith('Failed to load resource')) failures.push(role + ': ' + message.text().slice(0, 200));
  });
  page.on('response', response => {
    const path = new URL(response.url()).pathname;
    if (response.status() < 400 || !path.startsWith('/api/v1/')) return;
    if (path === '/api/v1/auth/refresh' && response.status() === 401) return;
    if (path === '/api/v1/professionals/me' && response.status() === 401 && !response.request().headers()['authorization']) return;
    const key = `${role}:${response.status()}:${path}`;
    if (!allowed.has(key)) unexpected.push(key);
  });
  await login(page, role);
  return page;
}

test.afterEach(async ({}, info) => {
  try {
    if (info.status !== 'passed') for (const item of sessions) {
      await snapshot(item.page, info, 'failure-' + item.role).catch(() => {});
      await info.attach('dom-' + item.role, { body: await item.page.locator('body').innerText(), contentType: 'text/plain' }).catch(() => {});
    }
    if (info.status === 'passed') {
      expect(failures, 'No browser exceptions, console errors or external page requests').toEqual([]);
      expect(unexpected, 'No unexpected API errors').toEqual([]);
    }
  } finally { for (const item of sessions) await item.context.close(); }
});

test('Citizen → Doctor → Lab → Citizen: real local care journey', async ({ browser }, info) => {
  const f = fixture();
  const citizen = await actor(browser, 'citizen', 1366, 'dark');
  await expect(citizen.getByRole('link', { name: /Latest diagnostic result Historical synthetic CBC/ })).toBeVisible();
  await citizen.getByRole('link', { name: /Recent prescription Your latest/ }).click();
  await expect(citizen.getByRole('heading', { name: 'Medicine A', exact: true })).toBeVisible();
  await citizen.getByRole('button', { name: 'Explain with AI', exact: true }).click();
  await expect(citizen.getByRole('heading', { name: 'Plain-language summary' })).toBeVisible();
  await expect(citizen.getByText(/Doctor's recorded instructions \(unchanged\)/)).toContainText('1 tablet');
  await expect(citizen.getByText(/does not record a medicine-specific purpose/)).toBeVisible();
  await snapshot(citizen, info, 'citizen-prescription-explanation');
  const pdfPath = `/api/v1/prescriptions/${f.old_prescription_id}/pdf`;
  const pdfResponse = citizen.waitForResponse(response => new URL(response.url()).pathname === pdfPath && response.request().method() === 'GET');
  await citizen.getByRole('button', { name: 'Generate PDF', exact: true }).click();
  const pdf = await pdfResponse;
  expect(pdf.status()).toBe(200);
  expect(pdf.headers()['cache-control']).toBe('private, no-store');
  await pdf.finished();
  expect(pdf.headers()['content-type']).toContain('application/pdf');
  // Edge can expose an empty CDP response body for inline PDFs. Validate the
  // actual Blob consumed by the UI instead, without downloading/storing a PDF.
  const pdfLink = citizen.getByRole('link', { name: 'Download PDF', exact: true });
  await expect(pdfLink).toBeVisible();
  const pdfBytes = await pdfLink.evaluate(async link => {
    const bytes = new Uint8Array(await (await fetch(link.href)).arrayBuffer());
    return { length: bytes.length, signature: String.fromCharCode(...bytes.subarray(0, 4)) };
  });
  expect(pdfBytes.signature).toBe('%PDF');
  expect(pdfBytes.length).toBeGreaterThan(1000);
  for (const popup of citizen.context().pages()) if (popup !== citizen) await popup.close();

  await citizen.goto('/citizen/doctors/search');
  await citizen.getByRole('textbox', { name: 'Search doctor, specialty, or hospital', exact: true }).fill(f.doctor_name);
  await citizen.getByRole('button', { name: 'Search', exact: true }).click();
  const results = citizen.getByRole('region', { name: 'Doctor search results', exact: true });
  await expect(results).toContainText(f.doctor_name);
  await citizen.getByRole('combobox', { name: 'Sort by', exact: true }).selectOption('NEAREST');
  await expect(citizen.getByRole('dialog')).toBeVisible();
  await citizen.getByRole('button', { name: 'Enter area manually', exact: true }).click();
  await expect(citizen.getByRole('combobox', { name: 'Zila', exact: true }).locator('option')).toHaveCount(65);
  await citizen.getByRole('combobox', { name: 'Zila', exact: true }).selectOption(f.district_code);
  await citizen.getByRole('combobox', { name: 'Upazila', exact: true }).selectOption(f.upazila_code);
  await citizen.getByRole('button', { name: 'Find doctors in this area', exact: true }).click();
  await expect(results).toContainText('Less than 1 km away');
  await expect(citizen.locator('main')).not.toContainText(/latitude|longitude/i);
  await snapshot(citizen, info, 'citizen-nearby-discovery');
  await results.getByRole('link', { name: 'Book appointment', exact: true }).click();
  await citizen.getByTestId('appointment-date-input').fill(f.today);
  await citizen.getByTestId('reason-input').fill('Synthetic browser acceptance visit only');
  const booking = citizen.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/citizens/appointments' && response.request().method() === 'POST');
  await citizen.getByTestId('book-submit').click();
  const booked = await booking;
  expect(booked.status()).toBe(201);
  shared.appointment = await booked.json();
  expect(shared.appointment.serial_number).toBe(1);
  await citizen.waitForURL('**/citizen/appointments?*');
  await expect(citizen.locator('main')).toContainText(f.facility_name);
  await citizen.goto('/citizen/dashboard');
  await expect(citizen.getByRole('link', { name: /Upcoming appointment/ })).toContainText(f.facility_name);
  await snapshot(citizen, info, 'citizen-dashboard');

  await citizen.goto('/citizen/emergency-profile');
  await expect(citizen.getByRole('textbox', { name: 'Allergies', exact: true })).toHaveValue('Synthetic recorded allergy');
  await citizen.getByRole('textbox', { name: 'Special notes', exact: true }).fill('Updated synthetic browser emergency information');
  await citizen.getByRole('button', { name: 'Save emergency profile', exact: true }).click();
  await expect(citizen.getByRole('status')).toContainText(/saved/i);

  const doctor = await actor(browser, 'doctor', 1366, 'dark');
  await doctor.goto('/professional/chamber');
  const facilitySelect = doctor.getByRole('combobox', { name: 'Facility', exact: true });
  if (await facilitySelect.count()) await facilitySelect.selectOption(f.facility_id);
  const starting = doctor.waitForResponse(response => new URL(response.url()).pathname.endsWith('/chamber/sessions/start') && response.request().method() === 'POST');
  await doctor.getByRole('button', { name: "Open today's chamber", exact: true }).click();
  const started = await starting;
  expect(started.ok()).toBe(true);
  // Opening a chamber promotes its first waiting serial automatically.
  expect((await started.json()).current.serial_number).toBe(1);
  const refreshed = doctor.waitForResponse(response => new URL(response.url()).pathname.endsWith('/chamber/sessions/today'));
  // Wait for the refresh view, rather than trusting the optimistic start response.
  await doctor.getByRole('button', { name: 'Refresh queue', exact: true }).click();
  const persisted = await refreshed;
  shared.promotionPersisted = Boolean((await persisted.json()).current);
  expect(shared.promotionPersisted, 'First CURRENT patient persists without a call-next workaround').toBe(true);
  await doctor.getByRole('link', { name: 'Open consultation', exact: true }).click();
  await doctor.getByRole('button', { name: 'Open consultation', exact: true }).click();
  await expect(doctor.getByRole('heading', { name: 'Clinical record and prescription', exact: true })).toBeVisible();
  await expect(doctor.locator('main')).toContainText(f.citizen_name);
  await expect(doctor.locator('main')).toContainText('Updated synthetic browser emergency information');
  const oldLink = doctor.locator(`a[href="/professional/prescriptions/${f.old_prescription_id}"]`);
  await expect(oldLink).toBeVisible();
  await oldLink.click();
  await expect(doctor.getByRole('heading', { name: 'Medicine A', exact: true })).toBeVisible();
  await expect(doctor.getByRole('button', { name: /Update consultation/ })).toHaveCount(0);
  await doctor.goto('/professional/visits');
  await doctor.getByLabel('Chief complaint', { exact: true }).fill('Synthetic browser consultation');
  await doctor.getByRole('textbox', { name: 'Clinical notes', exact: true }).fill('Synthetic local record only');
  await doctor.getByLabel('Medicine name', { exact: true }).fill('Medicine A');
  await doctor.getByLabel('Dosage', { exact: true }).fill('1 tablet');
  await doctor.getByLabel('Frequency', { exact: true }).fill('Daily');
  await doctor.getByLabel('Duration', { exact: true }).fill('5 days');
  await expect(doctor.getByRole('button', { name: 'Finish Appointment', exact: true })).toBeDisabled();
  const createPrescription = doctor.waitForResponse(response => /\/visits\/[^/]+\/prescription$/.test(new URL(response.url()).pathname) && response.request().method() === 'POST');
  await doctor.getByRole('button', { name: 'Save consultation & prescription', exact: true }).click();
  const saved = await createPrescription;
  expect(saved.status()).toBe(201);
  shared.prescription = await saved.json();
  await expect(doctor.getByText('Consultation and prescription saved', { exact: true })).toBeVisible();
  shared.testName = 'Browser synthetic CBC ' + f.run_id.slice(-6);
  await doctor.getByLabel('Test name', { exact: true }).fill(shared.testName);
  await doctor.getByRole('combobox', { name: 'Lab technician', exact: true }).selectOption(f.lab_registration_id);
  const createTest = doctor.waitForResponse(response => response.url().endsWith('/current-patient/diagnostic-tests') && response.request().method() === 'POST');
  await doctor.getByRole('button', { name: 'Request test', exact: true }).click();
  const requested = await createTest;
  expect(requested.status()).toBe(201);
  shared.diagnostic = await requested.json();
  await snapshot(doctor, info, 'doctor-unified-consultation');
  await doctor.setViewportSize({ width: 390, height: 844 });
  await snapshot(doctor, info, 'doctor-unified-consultation-mobile');
  await doctor.setViewportSize({ width: 1366, height: 900 });
  await doctor.getByRole('button', { name: 'Finish Appointment', exact: true }).click();
  await expect(doctor.getByRole('heading', { name: 'No active patient', exact: true })).toBeVisible();
  await doctor.goto('/professional/dashboard');
  await expect(doctor.getByRole('link', { name: /Recent authored prescription/ })).toBeVisible();
  await snapshot(doctor, info, 'doctor-dashboard');
  await doctor.goto(`/professional/prescriptions/${shared.prescription.id}`);
  await doctor.getByRole('textbox', { name: 'Instructions', exact: true }).fill('Synthetic recorded instruction after visit');
  await doctor.getByRole('button', { name: 'Update consultation & prescription', exact: true }).click();
  await expect(doctor.getByText('Consultation and prescription saved', { exact: true })).toBeVisible();

  const lab = await actor(browser, 'lab', 1366, 'dark');
  await expect(lab.getByRole('link', { name: 'Chamber', exact: true })).toHaveCount(0);
  await expect(lab.getByRole('link', { name: 'Consultations', exact: true })).toHaveCount(0);
  await snapshot(lab, info, 'lab-dashboard');
  await lab.goto('/professional/diagnostics');
  const requestCard = lab.locator('article').filter({ has: lab.getByRole('heading', { name: shared.testName, exact: true }) });
  await requestCard.getByRole('button', { name: 'Begin work', exact: true }).click();
  await requestCard.getByRole('link', { name: 'Open lab report', exact: true }).click();
  await lab.getByLabel('Report date', { exact: true }).fill(f.today);
  await lab.getByRole('textbox', { name: 'Summary', exact: true }).fill('Synthetic browser draft');
  await lab.getByLabel('Parameter', { exact: true }).fill('Haemoglobin');
  await lab.getByLabel('Result', { exact: true }).fill('13.5');
  await lab.getByLabel('Numeric result (optional)', { exact: true }).fill('13.5');
  await lab.getByLabel('Unit', { exact: true }).fill('g/dL');
  await lab.getByLabel('Reference range', { exact: true }).fill('12–16');
  await lab.getByLabel('Flag', { exact: true }).fill('NORMAL');
  await expect(lab.getByRole('button', { name: 'Finalize report', exact: true })).toBeDisabled();
  await lab.getByRole('button', { name: 'Save draft', exact: true }).click();
  await expect(lab.getByRole('status')).toContainText('Draft saved');
  await snapshot(lab, info, 'lab-report-draft');
  await lab.setViewportSize({ width: 390, height: 844 });
  await snapshot(lab, info, 'lab-report-draft-mobile');
  await lab.setViewportSize({ width: 1366, height: 900 });
  await lab.getByRole('textbox', { name: 'Summary', exact: true }).fill('Synthetic browser corrected draft');
  await expect(lab.getByRole('button', { name: 'Finalize report', exact: true })).toBeDisabled();
  await lab.getByRole('button', { name: 'Save draft', exact: true }).click();
  await expect(lab.getByRole('status')).toContainText('Draft saved');
  allowed.add(`citizen:404:/api/v1/diagnostic-tests/${shared.diagnostic.id}/lab-report`);
  await citizen.goto(`/citizen/diagnostic-tests/${shared.diagnostic.id}`);
  await expect(citizen.getByRole('heading', { name: 'Report unavailable', exact: true })).toBeVisible();
  lab.once('dialog', dialog => dialog.accept());
  await lab.getByRole('button', { name: 'Finalize report', exact: true }).click();
  await expect(lab.getByRole('status')).toHaveText('Finalized report — read only.');
  await expect(lab.getByRole('button', { name: 'Save draft', exact: true })).toHaveCount(0);
  await snapshot(lab, info, 'lab-finalized-report');
  await citizen.reload();
  await expect(citizen.getByRole('heading', { name: shared.testName, exact: true })).toBeVisible();
  await expect(citizen.getByRole('table')).toContainText('13.500000');
  await citizen.getByRole('button', { name: 'Explain with AI', exact: true }).click();
  await expect(citizen.getByRole('region', { name: 'Understand these results', exact: true }).getByRole('heading', { name: 'Haemoglobin', exact: true })).toBeVisible();
  await snapshot(citizen, info, 'citizen-finalized-result');
  await citizen.goto('/citizen/diagnostic-tests');
  await expect(citizen.getByRole('heading', { name: 'Numeric result trends', exact: true })).toBeVisible();
  await expect(citizen.locator('main')).toContainText('13.5');
  await citizen.goto('/citizen/dashboard');
  await expect(citizen.getByRole('link', { name: /Latest diagnostic result/ })).toContainText(shared.testName);
  await expect(citizen.getByRole('link', { name: /Recent prescription/ })).toHaveAttribute('href', `/citizen/prescriptions/${shared.prescription.id}`);

  const admin = await actor(browser, 'admin', 1366, 'dark');
  await snapshot(admin, info, 'admin-dashboard');
  await admin.goto('/admin/citizen-identities');
  await admin.getByLabel('Email', { exact: true }).fill(f.citizen_email);
  const search = admin.waitForRequest(request => new URL(request.url()).pathname === '/api/v1/admin/citizen-identities/search');
  await admin.getByRole('button', { name: 'Search identities', exact: true }).click();
  const searched = await search;
  expect(searched.method()).toBe('POST');
  expect(new URL(searched.url()).search).toBe('');
  expect(searched.postDataJSON().email).toBe(f.citizen_email);
  await expect(admin.locator('main')).toContainText(f.citizen_name);
  await admin.goto('/admin/facilities');
  await expect(admin.locator('main')).toContainText(f.facility_name);
  await expect(admin.locator('main')).not.toContainText(/latitude|longitude/i);
  await admin.goto('/admin/professional-registrations');
  await expect(admin.locator('main')).toContainText('PendingDoctor');
  await admin.goto('/professional/dashboard');
  await expect(admin.locator('main')).toContainText(/Portal access required|Professional Portal required/i);
  const other = await actor(browser, 'other');
  allowed.add(`other:404:/api/v1/prescriptions/${shared.prescription.id}`);
  await other.goto(`/citizen/prescriptions/${shared.prescription.id}`);
  await expect(other.locator('main')).toContainText(/Prescription unavailable/i);
  await expect(other.locator('main')).not.toContainText('Medicine A');
});

test('Modern AI chat: saved transcript, new conversation, private history and responsive composer', async ({ browser }, info) => {
  const page = await actor(browser, 'citizen', 1487);
  await page.setViewportSize({ width: 1487, height: 1058 });
  const collapse = page.getByRole('button', { name: 'Collapse navigation', exact: true });
  if (await collapse.isVisible()) await collapse.click();
  await page.goto('/citizen/ai-assistant');
  await expect(page.getByRole('heading', { name: 'What would you like to understand?', exact: true })).toBeVisible();
  await snapshot(page, info, 'modern-chat-empty-desktop');
  const question = 'What does a laboratory reference range mean?';
  const input = page.getByRole('textbox', { name: 'Your question', exact: true });
  await input.fill(question);
  await input.press('Enter');
  await expect(page.getByRole('article', { name: 'Question and answer' })).toHaveCount(1);
  await input.fill('What should I ask my doctor?');
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.getByRole('article', { name: 'Question and answer' })).toHaveCount(2);
  await snapshot(page, info, 'modern-chat-transcript-desktop');
  await page.reload();
  const history = page.getByRole('complementary', { name: 'Conversation history', exact: true });
  await history.getByRole('button', { name: /^What does a laboratory reference range mean/ }).click();
  await expect(page.getByRole('article', { name: 'Question and answer' })).toHaveCount(2);
  await page.getByRole('button', { name: 'New conversation', exact: true }).click();
  await expect(page.getByRole('article', { name: 'Question and answer' })).toHaveCount(0);
  await history.getByRole('button', { name: /^What does a laboratory reference range mean/ }).click();
  for (const width of [320, 390, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByRole('button', { name: 'Send message', exact: true })).toBeVisible();
    const dimensions = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.width + 1);
    const composer = await page.getByRole('button', { name: 'Send message', exact: true }).boundingBox();
    expect(composer.y + composer.height).toBeLessThanOrEqual(900);
    if (width < 768) {
      await page.getByRole('button', { name: 'Conversations', exact: true }).click();
      await expect(history.getByRole('button', { name: 'New conversation', exact: true })).toBeVisible();
      await page.getByRole('button', { name: 'Conversations', exact: true }).click();
    }
    await snapshot(page, info, 'modern-chat-responsive-' + width);
  }
  await page.setViewportSize({ width: 1487, height: 1058 });
  await input.fill('Explain the recorded history for education.');
  await page.getByRole('button', { name: 'General · Records off', exact: true }).click();
  await page.getByRole('radio', { name: 'Use my records', exact: true }).check();
  const consent = page.getByRole('checkbox', { name: /I allow HealthLink AI/ });
  await consent.check();
  await input.fill('Explain my recorded history without diagnosing.');
  await expect(consent).not.toBeChecked();
  await expect(page.getByRole('button', { name: 'Send message', exact: true })).toBeDisabled();
  await snapshot(page, info, 'modern-chat-record-consent');
  await consent.check();
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.getByRole('article', { name: 'Question and answer' })).toHaveCount(3);
  await expect(page.getByRole('button', { name: 'General · Records off', exact: true })).toBeVisible();
  await history.getByRole('button', { name: /^Delete conversation:/ }).click();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByRole('article', { name: 'Question and answer' })).toHaveCount(3);
  // Only this test's own newly-created synthetic conversation is deleted.
  await history.getByRole('button', { name: /^Delete conversation:/ }).click();
  await page.getByRole('button', { name: 'Delete permanently', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'What would you like to understand?', exact: true })).toBeVisible();
  await page.reload();
  await expect(history.getByRole('button', { name: /^What does a laboratory reference range mean/ })).toHaveCount(0);
});

test('AI consent, history, saved reminders and privacy remain functional', async ({ browser }, info) => {
  const f = fixture();
  const page = await actor(browser, 'citizen');
  await page.goto('/citizen/ai-assistant');
  await page.getByRole('textbox', { name: 'Your question', exact: true }).fill('What does a medical reference range mean?');
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.getByRole('article', { name: 'Question and answer' })).toHaveCount(1);
  await page.getByRole('textbox', { name: 'Your question', exact: true }).fill('Explain what my recorded results contain.');
  await page.getByRole('button', { name: 'General · Records off', exact: true }).click();
  await page.getByRole('radio', { name: /Use my records/ }).check();
  const consent = page.getByRole('checkbox', { name: /I allow HealthLink AI/ });
  await expect(page.getByRole('button', { name: 'Send message', exact: true })).toBeDisabled();
  await consent.check();
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.getByRole('article', { name: 'Question and answer' })).toHaveCount(2);
  await expect(page.getByRole('button', { name: 'General · Records off', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Symptom guidance', exact: true }).click();
  const symptoms = page.getByRole('textbox');
  await symptoms.fill('I cannot breathe and have severe chest pressure.');
  await page.getByRole('button', { name: /guidance/i }).click();
  await expect(page.locator('main')).toContainText('Urgent or emergency evaluation');
  await snapshot(page, info, 'citizen-ai-emergency-safeguard');
  await page.goto('/citizen/medical-history');
  await expect(page.locator('main')).toContainText('Synthetic browser consultation');
  const summary = page.getByRole('region', { name: 'Summarize my medical history', exact: true });
  await expect(summary.getByRole('button', { name: 'Generate AI summary', exact: true })).toBeDisabled();
  await summary.getByRole('checkbox').check();
  await summary.getByRole('button', { name: 'Generate AI summary', exact: true }).click();
  await expect(summary.getByRole('heading', { name: 'Overview', exact: true })).toBeVisible();
  await expect(summary.getByRole('checkbox')).not.toBeChecked();
  await page.goto('/citizen/reminders');
  await expect(page.getByRole('heading', { name: 'Notifications', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Create reminder', exact: true }).click();
  await page.getByLabel('Medicine', { exact: true }).fill('Synthetic saved reminder');
  await page.getByLabel('Start date', { exact: true }).fill(f.today);
  await page.getByLabel('Time 1', { exact: true }).fill('23:30');
  await page.getByRole('button', { name: 'Save reminder', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Synthetic saved reminder', exact: true })).toBeVisible();
  await page.goto('/citizen/privacy');
  await expect(page.locator('main')).toContainText(/Access history|record access/i);
  await snapshot(page, info, 'citizen-privacy-access');
  await page.goto('/citizen/access-grants');
  const fullNameSearch = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/access-grant-professionals') && new URL(response.url()).searchParams.get('search') === f.doctor_name);
  await page.getByRole('textbox', { name: 'Search verified doctors', exact: true }).fill(f.doctor_name);
  const doctors = await fullNameSearch;
  expect(doctors.ok()).toBe(true);
  shared.fullNameSupported = (await doctors.json()).some(doctor => doctor.id === f.doctor_registration_id);
  expect(shared.fullNameSupported, 'Exact displayed full name finds the verified doctor').toBe(true);
  await page.getByRole('combobox', { name: 'Doctor', exact: true }).selectOption(f.doctor_registration_id);
  await page.getByRole('combobox', { name: 'Records to share', exact: true }).selectOption('PRESCRIPTIONS_ONLY');
  await page.getByRole('button', { name: 'Review sharing', exact: true }).click();
  await page.getByRole('alertdialog').getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Access granted');
  const grant = page.locator('article').filter({ has: page.getByRole('heading', { name: f.doctor_name, exact: true }) });
  await expect(grant).toContainText('Prescriptions only');
  await grant.getByRole('button', { name: 'Revoke access', exact: true }).click();
  await page.getByRole('alertdialog').getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Access revoked');
  await expect(grant).toContainText('Revoked');
  await page.goto('/citizen/lab-reports');
  await page.waitForURL('**/citizen/diagnostic-tests');
  await expect(page.getByRole('heading', { name: 'Diagnostic tests', exact: true })).toBeVisible();
});

for (const [name, width] of [['mobile', 390], ['tablet', 768], ['desktop', 1366], ['wide', 1920]]) {
  test(`Responsive portal matrix: ${name} ${width}px`, async ({ browser }, info) => {
    for (const role of ['citizen', 'doctor', 'lab', 'admin']) {
      const page = await actor(browser, role, width);
      await expect(page.locator('main h1')).toHaveCount(1);
      const skip = page.getByRole('link', { name: 'Skip to content', exact: true });
      await skip.focus();
      await expect(skip).toBeFocused();
      await page.keyboard.press('Enter');
      expect(new URL(page.url()).hash).toBe('#main-content');
      const measure = await page.evaluate(() => ({ visible: document.documentElement.clientWidth, total: document.documentElement.scrollWidth }));
      expect(measure.total, `${role} dashboard horizontal overflow`).toBeLessThanOrEqual(measure.visible + 1);
      await snapshot(page, info, `${name}-${role}-dashboard`);
      const route = role === 'citizen' ? '/citizen/doctors/search' : role === 'doctor' ? '/professional/visits' : role === 'lab' ? '/professional/diagnostics' : '/admin/facilities';
      await page.goto(route);
      await expect(page.locator('main h1')).toHaveCount(1);
      if (role === 'citizen') await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeVisible();
      else if (role === 'doctor') await expect(page.getByRole('heading', { name: 'No active patient', exact: true })).toBeVisible();
      else if (role === 'lab') await expect(page.locator('main')).toContainText(shared.testName);
      else await expect(page.locator('main')).toContainText(fixture().facility_name);
      const size = await page.evaluate(() => ({ visible: document.documentElement.clientWidth, total: document.documentElement.scrollWidth }));
      expect(size.total, `${role} workspace horizontal overflow`).toBeLessThanOrEqual(size.visible + 1);
      await snapshot(page, info, `${name}-${role}-workspace`);
      const detailRoute = role === 'citizen' ? `/citizen/diagnostic-tests/${shared.diagnostic.id}` : role === 'doctor' ? `/professional/prescriptions/${shared.prescription.id}` : '/admin/citizen-identities';
      // Follow actual report links because the professional route contract is
      // owned by the diagnostic queue, not inferred from a citizen URL.
      if (role === 'lab') {
        const reportCard = page.locator('article').filter({ has: page.getByRole('heading', { name: shared.testName, exact: true }) });
        await reportCard.getByRole('link', { name: 'Open lab report', exact: true }).click();
      } else await page.goto(detailRoute);
      if (role === 'citizen' || role === 'lab') await expect(page.getByRole('table')).toContainText('13.500000');
      else if (role === 'doctor') await expect(page.getByRole('button', { name: 'Update consultation & prescription', exact: true })).toBeVisible();
      else await expect(page.getByRole('button', { name: 'Search identities', exact: true })).toBeVisible();
      await expect(page.locator('main h1')).toHaveCount(1);
      const detailSize = await page.evaluate(() => ({ visible: document.documentElement.clientWidth, total: document.documentElement.scrollWidth }));
      expect(detailSize.total, `${role} detail horizontal overflow`).toBeLessThanOrEqual(detailSize.visible + 1);
      await snapshot(page, info, `${name}-${role}-detail`);
    }
  });
}

test('Synthetic operations: schedule edit, facility update and admin verification', async ({ browser }, info) => {
  const f = fixture();
  const doctor = await actor(browser, 'doctor');
  await doctor.getByRole('link', { name: 'Manage practice hours', exact: true }).click();
  await expect(doctor).toHaveURL(/\/professional\/settings\/practice$/);
  await doctor.getByRole('button', { name: 'Edit', exact: true }).click();
  await doctor.getByRole('spinbutton', { name: 'Max patients', exact: true }).fill('21');
  const savingSchedule = doctor.waitForResponse(response => response.request().method() === 'PUT' && new URL(response.url()).pathname.endsWith('/' + f.schedule_id));
  await doctor.getByRole('button', { name: 'Save changes', exact: true }).click();
  expect((await savingSchedule).ok()).toBe(true);
  await doctor.reload();
  await doctor.getByRole('button', { name: 'Edit', exact: true }).click();
  await expect(doctor.getByRole('spinbutton', { name: 'Max patients', exact: true })).toHaveValue('21');
  await doctor.getByRole('button', { name: 'Cancel edit', exact: true }).click();
  const admin = await actor(browser, 'admin');
  await admin.goto('/admin/facilities');
  const facility = admin.locator('article').filter({ has: admin.getByRole('heading', { name: f.facility_name, exact: true }) });
  await facility.getByRole('button', { name: 'Edit', exact: true }).click();
  await admin.getByRole('textbox', { name: 'Phone (optional)', exact: true }).fill('01700000001');
  const savingFacility = admin.waitForResponse(response => response.request().method() === 'PUT' && new URL(response.url()).pathname.endsWith('/facilities/' + f.facility_id));
  await admin.getByRole('button', { name: 'Save changes', exact: true }).click();
  const updated = await savingFacility;
  expect(updated.ok()).toBe(true);
  const data = await updated.json();
  expect(data.location_status).toBe('CONFIRMED');
  expect(data).not.toHaveProperty('latitude');
  expect(data).not.toHaveProperty('longitude');
  await expect(admin.locator('main')).toContainText('Its confirmed location is unchanged');
  await admin.goto('/admin/professional-registrations/' + f.pending_registration_id);
  await expect(admin.getByRole('heading', { name: f.pending_name, exact: true })).toBeVisible();
  await admin.getByRole('combobox', { name: 'Match active facility', exact: true }).selectOption(f.facility_id);
  await admin.getByRole('textbox', { name: 'Verified qualification', exact: true }).fill('Synthetic QA evidence only');
  await admin.getByRole('button', { name: 'Verify and link facility', exact: true }).click();
  await expect(admin.getByRole('heading', { name: 'Decision recorded: VERIFIED', exact: true })).toBeVisible();
  await snapshot(admin, info, 'synthetic-admin-verification');
});

test('Settings matrix: role-aware sections, legacy links, privacy and admin identity detail', async ({ browser }, info) => {
  const f = fixture();
  for (const role of ['citizen', 'doctor', 'lab', 'admin']) {
    const page = await actor(browser, role);
    const portal = role === 'doctor' || role === 'lab' ? 'professional' : role;
    await page.getByRole('link', { name: /: Open settings$/ }).click();
    await expect(page).toHaveURL(new RegExp(`/${portal}/settings$`));
    const nav = page.getByRole('navigation', { name: 'Settings sections', exact: true });
    await expect(nav.getByRole('link', { name: /^Account/ })).toBeVisible();
    await expect(nav.getByRole('link', { name: /^Practice hours/ })).toHaveCount(role === 'doctor' ? 1 : 0);
    await expect(nav.getByRole('link', { name: /^Privacy & sharing/ })).toHaveCount(role === 'citizen' ? 1 : 0);
    await expect(page.getByRole('main')).toHaveCount(1);
    await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1);
    for (const width of [320, 390, 768, 1366]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(nav).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    }
    if (role === 'citizen') {
      await expect(page.getByRole('link', { name: 'Add a professional role', exact: true })).toBeVisible();
      await page.goto('/citizen/profile');
      await expect(page).toHaveURL(/\/citizen\/settings$/);
      // The server redirect changes the URL before session/profile hydration.
      // Do not abort an in-flight refresh with another artificial hard navigation.
      await expect(page.getByRole('heading', { name: 'Profile and identity', exact: true })).toBeVisible();
      await page.goto('/citizen/privacy');
      await expect(page).toHaveURL(/\/citizen\/settings\/privacy$/);
      await expect(page.getByRole('link', { name: 'Manage access grants', exact: true })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Privacy and access history', exact: true })).toBeVisible();
      await expect(page.getByText(/Records stay off unless/)).toBeVisible();
    }
    if (role === 'lab') {
      await page.goto('/professional/settings/practice');
      await expect(page.getByRole('heading', { name: 'Verified doctor access required', exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Publish window', exact: true })).toHaveCount(0);
    }
    if (role === 'admin') {
      await page.goto('/admin/citizen-identities/' + f.citizen_user_id);
      await expect(page.getByRole('heading', { name: f.citizen_name, exact: true })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Record a correction', exact: true })).toBeVisible();
      await snapshot(page, info, 'admin-identity-detail-fixed');
    } else await snapshot(page, info, role + '-settings');
  }
});

test('Display preferences persist without medical data; mobile menu traps and restores focus', async ({ browser }, info) => {
  const page = await actor(browser, 'citizen');
  await page.goto('/citizen/settings/appearance');
  await page.getByRole('combobox', { name: /^Text size/ }).selectOption('large');
  await page.getByRole('combobox', { name: /^Motion/ }).selectOption('reduced');
  await page.getByRole('combobox', { name: /^Desktop sidebar/ }).selectOption('expanded');
  await expect(page.getByRole('status')).toContainText('saved on this device');
  await page.reload();
  await expect(page.getByRole('combobox', { name: /^Text size/ })).toHaveValue('large');
  await expect(page.locator('html')).toHaveAttribute('data-text-size', 'large');
  await expect(page.locator('html')).toHaveAttribute('data-motion', 'reduced');
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('healthlink.interface.v1')))).toEqual({ textSize: 'large', motion: 'reduced', navigation: 'expanded', theme: 'light' });
  for (const width of [320, 390, 768, 1366]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  const opener = page.getByRole('button', { name: 'Open navigation', exact: true });
  await opener.click();
  const dialog = page.getByRole('dialog', { name: 'Citizen portal navigation', exact: true });
  await expect(dialog).toBeVisible();
  expect(await dialog.evaluate(el => el.contains(document.activeElement))).toBe(true);
  expect(await page.evaluate(() => document.body.style.overflow)).toBe('hidden');
  await dialog.getByRole('button', { name: 'Sign out', exact: true }).focus();
  await page.keyboard.press('Tab');
  await expect(dialog.getByRole('link', { name: 'HealthLink', exact: true })).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(dialog.getByRole('button', { name: 'Sign out', exact: true })).toBeFocused();
  await snapshot(page, info, 'settings-mobile-menu-large-text');
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(opener).toBeFocused();
  await snapshot(page, info, 'settings-display-large-mobile');
  for (const path of ['/citizen/doctors/search', '/citizen/medical-history', '/citizen/diagnostic-tests', '/citizen/ai-assistant', '/citizen/emergency-profile']) {
    await page.goto(path);
    await page.waitForLoadState('networkidle');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), path + ' supports larger text').toBe(true);
  }
  await page.goto('/citizen/settings/appearance');
  await page.getByRole('button', { name: 'Reset display preferences', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('data-text-size', 'standard');
});

test('Security Settings confirms all-session revocation and leaves another account signed in', async ({ browser }, info) => {
  const current = await actor(browser, 'citizen');
  const secondSession = await actor(browser, 'citizen');
  const otherAccount = await actor(browser, 'other');
  await current.goto('/citizen/settings/security');
  const revoke = current.getByRole('main').getByRole('button', { name: 'Sign out all sessions', exact: true });
  current.once('dialog', dialog => dialog.dismiss());
  await revoke.click();
  await expect(revoke).toBeEnabled();
  await expect(current).toHaveURL(/\/citizen\/settings\/security$/);
  await snapshot(current, info, 'settings-security');
  current.once('dialog', dialog => dialog.accept());
  const revoking = current.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/logout-all');
  await revoke.click();
  expect((await revoking).status()).toBe(204);
  await expect(current).toHaveURL(/\/citizen\/login$/);
  await secondSession.reload();
  await expect(secondSession.getByRole('heading', { name: 'Sign in to continue', exact: true })).toBeVisible();
  await otherAccount.reload();
  await expect(otherAccount.getByRole('heading', { name: 'Your care at a glance', exact: true })).toBeVisible();
});

test('Light/dark/System themes persist before paint, follow OS changes and synchronize tabs', async ({ browser }, info) => {
  const page = await actor(browser, 'citizen');
  await page.goto('/citizen/settings/appearance');
  const theme = page.getByRole('combobox', { name: /^Color theme/ });
  await expect(theme).toHaveValue('light');
  await theme.selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme)).toBe('dark');
  await page.addInitScript(() => {
    const observer = new MutationObserver(() => {
      if (document.body) {
        window.__themeAtFirstBody = document.documentElement.dataset.theme;
        observer.disconnect();
      }
    });
    observer.observe(document, { childList: true, subtree: true });
  });
  await page.reload();
  await expect(theme).toHaveValue('dark');
  expect(await page.evaluate(() => window.__themeAtFirstBody)).toBe('dark');
  await snapshot(page, info, 'settings-dark-desktop');
  const otherTab = await page.context().newPage();
  await otherTab.goto('/citizen/settings/appearance');
  await expect(otherTab.getByRole('combobox', { name: /^Color theme/ })).toHaveValue('dark');
  await theme.selectOption('light');
  await expect(otherTab.locator('html')).toHaveAttribute('data-theme', 'light');
  await otherTab.close();
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await theme.selectOption('system');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(theme).toHaveValue('system');
  expect(await page.evaluate(() => window.__themeAtFirstBody)).toBe('dark');
  await page.setViewportSize({ width: 390, height: 844 });
  await snapshot(page, info, 'settings-dark-mobile');
  await page.emulateMedia({ media: 'print' });
  await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(248, 251, 250)');
  await page.emulateMedia({ media: 'screen' });
  for (const path of ['/', '/citizen/login', '/professional/register', '/admin/login']) {
    await page.goto(path);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    const expectedBrand = path.startsWith('/admin') ? 'rgb(67, 56, 202)' : path.startsWith('/professional') ? 'rgb(3, 105, 161)' : 'rgb(15, 118, 110)';
    expect(await page.locator('[data-brand-mark]').first().evaluate(el => getComputedStyle(el).color)).toBe(expectedBrand);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    if (path === '/citizen/login') {
      await page.getByRole('button', { name: 'Sign in to Citizen Portal', exact: true }).click();
      const email = page.getByRole('textbox', { name: /Email address/ });
      await expect(email).toHaveAttribute('aria-invalid', 'true');
      await email.focus();
      await expect.poll(() => email.evaluate(el => getComputedStyle(el).borderColor)).toBe('rgb(253, 164, 175)');
    }
    await snapshot(page, info, 'dark-public-' + (path.split('/').filter(Boolean).join('-') || 'home'));
  }
  await page.goto('/citizen/settings/appearance');
  await theme.selectOption('light');
  await snapshot(page, info, 'settings-light-mobile');
});

test('Dark portal matrix: readable settings, dashboards, records, chat and workspaces', async ({ browser }, info) => {
  for (const role of ['citizen', 'doctor', 'lab', 'admin']) {
    const page = await actor(browser, role);
    const portal = role === 'doctor' || role === 'lab' ? 'professional' : role;
    await page.goto(`/${portal}/settings/appearance`);
    await page.getByRole('combobox', { name: /^Color theme/ }).selectOption('dark');
    const routes = role === 'citizen'
      ? ['/citizen/settings', '/citizen/settings/privacy', '/citizen/dashboard', '/citizen/medical-history', '/citizen/diagnostic-tests', '/citizen/doctors/search', '/citizen/ai-assistant']
      : role === 'doctor' ? ['/professional/dashboard', '/professional/chamber', '/professional/visits', '/professional/settings/practice']
      : role === 'lab' ? ['/professional/dashboard', '/professional/diagnostics', '/professional/settings']
      : ['/admin/dashboard', '/admin/facilities', '/admin/professional-registrations', '/admin/settings'];
    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState('networkidle');
      if (route.endsWith('ai-assistant')) {
        await page.getByRole('textbox', { name: 'Your question', exact: true }).fill('What is a laboratory reference range?');
        await page.getByRole('button', { name: 'Send message', exact: true }).click();
        await expect(page.getByRole('article', { name: 'Question and answer' })).toHaveCount(1);
      }
      await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
      const colors = await page.evaluate(() => ({
        body: getComputedStyle(document.body).backgroundColor,
        heading: getComputedStyle(document.querySelector('main h1')).color,
      }));
      expect(colors.body).toBe('rgb(11, 17, 27)');
      expect(colors.heading).toBe('rgb(232, 239, 248)');
      const name = route.split('/').filter(Boolean).join('-');
      await snapshot(page, info, 'dark-' + role + '-' + name);
      await page.setViewportSize({ width: 390, height: 844 });
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), { message: route + ' settles without mobile overflow' }).toBe(true);
      if (route.endsWith('ai-assistant') || route.endsWith('practice') || route.endsWith('facilities')) await snapshot(page, info, 'dark-mobile-' + role + '-' + name);
      await page.setViewportSize({ width: 1366, height: 900 });
    }
  }
});

test('Regression guard: chamber persistence and full-name sharing search', async () => {
  expect.soft(shared.promotionPersisted, 'Start response CURRENT must survive the next HTTP request').toBe(true);
  expect.soft(shared.fullNameSupported, 'Sharing search must find the displayed full doctor name').toBe(true);
});
