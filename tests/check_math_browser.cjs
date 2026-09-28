// Optional browser gate: NODE_PATH=/path/to/node_modules node tests/check_math_browser.cjs
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const cases = [
  {type:'function', title:'Seno', subtitle:'\\(y=\\sin(x)\\)', data:{expression:'sin(x)',domain:[-6,6]}},
  {type:'function', title:'Parábola variable', data:{expression:'a*x^2',domain:[-3,3],
    parameter:{name:'a',min:-2,max:2,value:1}}},
  {type:'geometry', title:'Vector', data:{elements:[
    {id:'A',kind:'point',at:[1,2]}, {id:'v',kind:'vector',from:[0,0],to:[2,1]},
    {id:'c',kind:'circle',center:[0,0],radius:2}]}},
  {type:'vector_field', title:'Campo rotacional', data:{fx:'-y',fy:'x',grid:7}},
  {type:'circuit', title:'Circuito RC', data:{elements:[
    {kind:'source',direction:'up',label:'V'},
    {kind:'resistor',direction:'right',label:'R'},
    {kind:'capacitor',direction:'down',label:'C'},
    {kind:'line',direction:'left'}]}},
];
const artifacts = cases.map(request => {
  const result = spawnSync(process.env.PYTHON || '.venv/bin/python',
    ['scripts/visual_router.py'], {cwd:root,input:JSON.stringify(request),encoding:'utf8',
      env:{...process.env,MPLCONFIGDIR:path.join(os.tmpdir(),'hermes-mpl')}});
  if (result.status !== 0) throw Error(request.type + ': ' + result.stderr);
  return {request, file:path.join(root,JSON.parse(result.stdout).artifact)};
});

(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    for (const width of [390,768,1366]) {
      const page = await browser.newPage({viewport:{width,height:900}});
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      for (const {request,file} of artifacts) {
        await page.goto(pathToFileURL(file).href);
        await page.waitForTimeout(250);
        const result = await page.evaluate(() => ({
          overflow:document.documentElement.scrollWidth > innerWidth + 2,
          board:!!document.querySelector('#board svg'),
          circuit:!!document.querySelector('.circuit svg'),
          error:document.querySelector('#board')?.textContent.includes('No se pudo mostrar'),
          formula:!!document.querySelector('.katex'),
        }));
        if (errors.length || result.overflow || result.error ||
            (request.type === 'circuit' ? !result.circuit : !result.board) ||
            (request.subtitle && !result.formula))
          throw Error(request.type + ' @ ' + width + 'px: ' + JSON.stringify({result,errors}));
        if (request.subtitle && width === 390) {
          await page.evaluate(() => {
            const formula = document.createElement('p');
            formula.id = 'mathjax-fallback';
            formula.textContent = '\\(x^2\\)';
            document.querySelector('main').append(formula);
            katex.render = () => {throw Error('forced fallback')};
            renderMath();
          });
          await page.locator('#mathjax-fallback mjx-container svg').waitFor();
        }
        if (request.data.parameter) {
          await page.locator('#parameter-slider').evaluate(input => {
            input.value = '40';
            input.dispatchEvent(new Event('input', {bubbles:true}));
          });
          if (await page.locator('#parameter-value').innerText() !== '2.00')
            throw Error('El control de parámetro no actualizó la función.');
        }
        errors.length = 0;
      }
      await page.goto(pathToFileURL(artifacts[0].file).href);
      const widths = [900,390,1366,520,1366];
      const boardWidths = [];
      for (const width of widths) {
        await page.setViewportSize({width,height:900});
        await page.waitForTimeout(100);
        boardWidths.push(await page.locator('#board').evaluate(el => el.getBoundingClientRect().width));
      }
      if (boardWidths.some(width => width < 250) || Math.abs(boardWidths[2]-boardWidths[4]) > 1)
        throw Error('El board matemático se encogió tras redimensionar: ' + JSON.stringify(boardWidths));
      await page.close();
    }
    console.log('Math artifacts: 5 casos × 3 anchos OK');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error);process.exitCode=1});
