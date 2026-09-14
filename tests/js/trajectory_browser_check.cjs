// Run against the served dashboard using Chromium, including the refresh that
// previously destroyed the open panel. PLAYWRIGHT_MODULE and CHROMIUM_BINARY
// allow reuse of an installed browser without adding a project dependency.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({headless: true,
    executablePath: process.env.CHROMIUM_BINARY, args: ['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1100}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(process.env.DASHBOARD_URL || 'http://127.0.0.1:8100/loop');
    await page.waitForSelector('#trajectory-model');
    assert.equal(await page.locator('#champ, #tiles, #champ-badge').count(), 0,
      'Retired champion/progress summaries must not remain above the plot');
    const payload = await page.evaluate(async () => (await fetch('/api/loop')).json());
    const trajectory = payload.knowledge.improvement_trajectory;
    const counts = trajectory.keep_history.per_model_counts;
    const checkedModels = {};
    for (const curve of trajectory.production_headline.curves) {
      await page.locator('#trajectory-model').selectOption(curve.id);
      const expected = counts[curve.model] || 0;
      assert.equal(await page.locator('.trajectory-event').count(), expected,
        `${curve.model}: every attributed keep must be rendered`);
      checkedModels[curve.model] = expected;
    }
    const model = process.env.TRAJECTORY_MODEL || 'GLM-5.3-Flash';
    await page.locator('#trajectory-model').selectOption({label: await page.locator('#trajectory-model option')
      .evaluateAll((options, name) => options.find(o => o.textContent.startsWith(name)).textContent, model)});
    const dots = page.locator('.trajectory-event');
    assert.ok(await dots.count() > 3, 'Complete keep history must exceed checkpoint-only dots');
    assert.equal(await page.locator('.trajectory-event:not([data-disposition="kept"])').count(), 0);
    assert.equal(await page.locator('.keep-timeline .axis').count(), 0,
      'Keeps without cumulative evidence must not appear against a percent axis');
    const dot = dots.last();
    await dot.hover();
    const hover = page.locator('#trajectory-keep-tooltip');
    await hover.waitFor({state: 'visible'});
    assert.match(await hover.textContent(), /Marginal:.*cumulative:/);
    await dot.click();
    const drawer = page.locator('#trajectory-event-drawer');
    await drawer.waitFor({state: 'visible'});
    const initial = await page.locator('#trajectory-event-detail').textContent();
    assert.match(initial, /hypothesis/);
    // Trigger the exact normal refresh, then allow a full natural poll too.
    await page.evaluate(() => tick());
    await page.waitForTimeout(21000);
    assert.equal(await drawer.isVisible(), true, 'Polling must preserve the panel');
    assert.equal(await page.locator('#trajectory-event-detail').textContent(), initial);
    await page.locator('#trajectory-event-close').press('Escape');
    assert.equal(await drawer.isVisible(), false);
    await page.keyboard.press('Enter');
    await drawer.waitFor({state: 'visible'});
    assert.deepEqual(errors, []);
    if (process.env.SCREENSHOT_PATH) await page.screenshot({path: process.env.SCREENSHOT_PATH});
    console.log(JSON.stringify({model, keeps: await dots.count(), hover: true,
      click: true, survivesRefresh: true, keyboard: true, checkedModels, errors}));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
