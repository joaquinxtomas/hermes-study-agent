// Optional visual gate: PLAYWRIGHT_MODULE and BROWSER_EXECUTABLE may point to existing installs.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const playwright = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const output = path.resolve(process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), 'architecture-browser-')));
fs.mkdirSync(output, {recursive: true});
const fixture = fs.readFileSync(path.join(root, 'tests/fixtures/architecture/study_overview.json'));
const build = spawnSync(process.env.PYTHON || 'python3', ['scripts/visual_router.py'],
  {cwd: root, input: fixture, encoding: 'utf8'});
if (build.status !== 0) throw new Error(build.stderr);
const artifact = path.join(root, JSON.parse(build.stdout).presentation_artifact);

(async () => {
  const browser = await playwright.chromium.launch({headless: true,
    ...(process.env.BROWSER_EXECUTABLE ? {executablePath: process.env.BROWSER_EXECUTABLE} : {})});
  const report = [], errors = [];
  try {
    for (const width of [390, 520, 742, 900, 1366, 1600]) {
      const page = await browser.newPage({viewport: {width, height: 900}});
      page.on('pageerror', error => errors.push(`${width}: ${error.message}`));
      page.on('request', request => {
        if (/^https?:/.test(request.url())) errors.push(`${width}: external request ${request.url()}`);
      });
      await page.goto(pathToFileURL(artifact).href);
      const result = await page.evaluate(() => {
        const visible = [...document.querySelectorAll('.diagram svg')]
          .filter(svg => svg.getBoundingClientRect().width > 0);
        return {scrollWidth: document.documentElement.scrollWidth,
          height: document.documentElement.scrollHeight,
          visibleGraphs: visible.length,
          cards: document.querySelectorAll('.card').length,
          relations: document.querySelectorAll('.relations li').length};
      });
      if (result.scrollWidth > width + 1) errors.push(`${width}: horizontal overflow`);
      if (result.cards !== 8 || result.relations !== 11) errors.push(`${width}: missing semantic content`);
      if (result.visibleGraphs !== (width <= 520 ? 0 : 1)) errors.push(`${width}: wrong responsive view`);
      if (width === 742) {
        await page.locator('.compact .node a').first().click();
        const target = await page.evaluate(() => document.querySelector(':target')?.id);
        if (target !== 'component-0') errors.push(`${width}: node link did not open its details`);
      }
      await page.screenshot({path: path.join(output, `architecture-${width}.png`), fullPage: true});
      report.push({width, ...result});
      await page.close();
    }
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify({report, errors}, null, 2));
  console.log(JSON.stringify({report, errors}, null, 2));
  if (errors.length) process.exitCode = 1;
})().catch(error => {console.error(error); process.exitCode = 1;});
