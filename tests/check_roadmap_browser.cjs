// Optional gate: use an existing Playwright/Chromium installation.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const playwright = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const output = path.resolve(process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), 'roadmap-browser-')));
fs.mkdirSync(output, {recursive: true});
const fixtures = ['a_simple', 'b_physics', 'c_data_engineering', 'd_branches', 'e_large'];
const built = fixtures.map(name => {
  const fixture = path.join(root, 'tests/fixtures/roadmap', `${name}.json`);
  const request = JSON.parse(fs.readFileSync(fixture));
  const result = spawnSync(process.env.PYTHON || 'python3', ['scripts/visual_router.py'],
    {cwd: root, input: JSON.stringify(request), encoding: 'utf8'});
  if (result.status !== 0) throw new Error(`${name}: ${result.stderr}`);
  return {name, nodes: request.data.nodes.length,
    artifact: path.join(root, JSON.parse(result.stdout).presentation_artifact)};
});

function inspect() {
  const view = [...document.querySelectorAll('.roadmap-view')].find(item => getComputedStyle(item).display !== 'none');
  const boxes = [...view.querySelectorAll('.card')].map(card => {
    const r = card.getBoundingClientRect();
    return {id: card.dataset.id, l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width};
  });
  const problems = [];
  const intersects = (a, b) => a.l < b.r - 1 && a.r > b.l + 1 && a.t < b.b - 1 && a.b > b.t + 1;
  for (let i = 0; i < boxes.length; i++) {
    if (boxes[i].w < 155) problems.push(`narrow card ${boxes[i].id}`);
    for (let j = i + 1; j < boxes.length; j++) if (intersects(boxes[i], boxes[j])) problems.push(`overlap ${boxes[i].id}/${boxes[j].id}`);
  }
  for (const map of view.querySelectorAll('.section-map')) {
    const origin = map.getBoundingClientRect();
    const cards = [...map.querySelectorAll('.card')].map(card => {
      const r = card.getBoundingClientRect();
      return {id: card.dataset.id, l: r.left-origin.left, r: r.right-origin.left,
        t: r.top-origin.top, b: r.bottom-origin.top};
    });
    for (const card of cards)
      if (card.l < -1 || card.r > origin.width+1 || card.t < -1 || card.b > origin.height+1)
        problems.push(`card clipped ${card.id}`);
    for (const edge of map.querySelectorAll('.connector')) {
      const tokens = edge.getAttribute('d').match(/[MHV]|-?\d+(?:\.\d+)?/g) || [];
      const points = [];
      for (let i = 0, x = 0, y = 0; i < tokens.length;) {
        const command = tokens[i++];
        if (command === 'M') {x = Number(tokens[i++]); y = Number(tokens[i++]);}
        else if (command === 'H') x = Number(tokens[i++]);
        else if (command === 'V') y = Number(tokens[i++]);
        points.push([x,y]);
      }
      for (let i = 1; i < points.length; i++) {
        const [x1,y1] = points[i-1], [x2,y2] = points[i];
        if (x1 < -1 || x2 < -1 || x1 > origin.width+1 || x2 > origin.width+1 ||
            y1 < -1 || y2 < -1 || y1 > origin.height+1 || y2 > origin.height+1)
          problems.push(`connector outside ${edge.dataset.from}`);
        for (const card of cards) {
          if (card.id === edge.dataset.from || card.id === edge.dataset.to) continue;
          const crossing = x1 === x2 ? x1 > card.l+1 && x1 < card.r-1 &&
            Math.max(y1,y2) > card.t+1 && Math.min(y1,y2) < card.b-1 :
            y1 > card.t+1 && y1 < card.b-1 && Math.max(x1,x2) > card.l+1 && Math.min(x1,x2) < card.r-1;
          if (crossing) problems.push(`connector ${edge.dataset.from} crosses ${card.id}`);
        }
      }
    }
  }
  if (document.documentElement.scrollWidth > innerWidth + 1) problems.push('horizontal overflow');
  return {mode: view.className, columns: Number(view.dataset.columns), cards: boxes.length,
    connectors: view.querySelectorAll('.connector').length,
    minCardWidth: Math.round(Math.min(...boxes.map(box => box.w))),
    height: document.documentElement.scrollHeight, problems};
}

(async () => {
  const browser = await playwright.chromium.launch({headless: true,
    ...(process.env.BROWSER_EXECUTABLE ? {executablePath: process.env.BROWSER_EXECUTABLE} : {})});
  const report = [], errors = [];
  try {
    for (const fixture of built) {
      const widths = fixture.name === 'c_data_engineering' ? [390,520,650,768,900,1100,1366,1600] : [390,742,1366];
      for (const width of widths) {
        const page = await browser.newPage({viewport: {width, height: 900}});
        page.on('pageerror', error => errors.push(`${fixture.name} ${width}: ${error.message}`));
        await page.goto(pathToFileURL(fixture.artifact).href);
        await page.waitForFunction(() => document.querySelector('.roadmap-view:not([style]) .connector'));
        const result = await page.evaluate(inspect);
        if (result.cards !== fixture.nodes) result.problems.push(`missing nodes ${result.cards}/${fixture.nodes}`);
        if (result.problems.length) errors.push(`${fixture.name} ${width}: ${result.problems.join('; ')}`);
        if (fixture.name === 'c_data_engineering' ||
            (fixture.name === 'b_physics' && width === 742) ||
            (fixture.name === 'd_branches' && width === 1366))
          await page.screenshot({path: path.join(output, `${fixture.name}-${width}.png`), fullPage: true});
        report.push({fixture: fixture.name, width, ...result});
        await page.close();
      }
    }
    const page = await browser.newPage({viewport: {width: 1600, height: 900}});
    await page.goto(pathToFileURL(built[2].artifact).href);
    await page.waitForFunction(() => document.querySelector('.roadmap-view.v4 .connector'));
    await page.evaluate(() => document.querySelector('main').style.width = '700px');
    await page.waitForFunction(() => document.querySelector('.roadmap-view.v1 .connector'));
    const resized = await page.evaluate(inspect);
    if (resized.columns !== 2) errors.push(`container resize: ${resized.columns} columns`);
    await page.close();
    const focusPage = await browser.newPage({viewport: {width: 742, height: 900}});
    await focusPage.goto(pathToFileURL(built[0].artifact).href);
    await focusPage.waitForFunction(() => document.querySelector('.roadmap-view.v1 .connector'));
    await focusPage.locator('.roadmap-view.v1 .main-card').first().focus();
    const muted = await focusPage.locator('.roadmap-view.v1 .card.muted').count();
    if (!muted) errors.push('keyboard focus did not highlight related nodes');
    await focusPage.locator('.roadmap-view.v1 .card details summary').first().click();
    if (!await focusPage.locator('.roadmap-view.v1 .card details').first().evaluate(item => item.open))
      errors.push('description disclosure did not open');
    await focusPage.close();
  } finally {await browser.close();}
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify({report, errors}, null, 2));
  console.log(JSON.stringify({report, errors}, null, 2));
  if (errors.length) process.exitCode = 1;
})().catch(error => {console.error(error); process.exitCode = 1;});
