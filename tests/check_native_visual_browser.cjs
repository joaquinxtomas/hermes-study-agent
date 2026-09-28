// Optional browser gate: requires Node + Playwright, never a runtime dependency.
// PLAYWRIGHT_MODULE and BROWSER_EXECUTABLE may point at existing installations.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const {pathToFileURL}=require('node:url');
const playwright=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..');
const output=path.resolve(process.argv[2]||fs.mkdtempSync(path.join(os.tmpdir(),'native-visual-v2-')));
fs.mkdirSync(output,{recursive:true});
const build=spawnSync(process.env.PYTHON||'python3',['-c',`
import json, sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from render_native_artifact import render
from native_visual_spec import SemanticVisualSpec
for fixture in sorted(Path('tests/fixtures/native_visual').glob('*.json')):
    request=json.loads(fixture.read_text())
    render(SemanticVisualSpec.from_dict({**request['data'], **{k:v for k,v in request.items() if k not in ('data','output_format')}}), Path(sys.argv[1])/(fixture.stem+'.html'), Path(sys.argv[1]))
`,output],{cwd:root,encoding:'utf8'});
if(build.status!==0)throw new Error(build.stderr);
const widths=[390,520,650,768,900,1100,1366,1600];
function inspect(){
  const host=document.querySelector('.composition'),origin=host.getBoundingClientRect();
  const nodes=[...document.querySelectorAll('.node')].map(n=>{const r=n.getBoundingClientRect();return {id:n.dataset.node,left:r.left-origin.left,right:r.right-origin.left,top:r.top-origin.top,bottom:r.bottom-origin.top,width:r.width,row:n.dataset.row,col:n.dataset.col};});
  const intersects=(a,b)=>a.left<b.right-.5&&a.right>b.left+.5&&a.top<b.bottom-.5&&a.bottom>b.top+.5;
  const problems=[];
  for(let i=0;i<nodes.length;i++){
    if(nodes[i].width<207.5&&host.dataset.mode!=='narrow')problems.push(`narrow card: ${nodes[i].id}`);
    if(nodes[i].left<0||nodes[i].right>host.clientWidth+1)problems.push(`clipped: ${nodes[i].id}`);
    for(let j=i+1;j<nodes.length;j++)if(intersects(nodes[i],nodes[j]))problems.push(`overlap: ${nodes[i].id}/${nodes[j].id}`);
  }
  const paths=[...document.querySelectorAll('.edge')];
  if(paths.length!==EDGES.length)problems.push(`edges: ${paths.length}/${EDGES.length}`);
  for(const p of paths){
    const pts=JSON.parse(p.dataset.points);
    for(let i=1;i<pts.length;i++){
      const a=pts[i-1],b=pts[i];
      if(a[0]!==b[0]&&a[1]!==b[1])problems.push('non-orthogonal');
      for(const r of nodes){
        const hit=a[0]===b[0]?
          a[0]>r.left+.8&&a[0]<r.right-.8&&Math.max(a[1],b[1])>r.top+.8&&Math.min(a[1],b[1])<r.bottom-.8:
          a[1]>r.top+.8&&a[1]<r.bottom-.8&&Math.max(a[0],b[0])>r.left+.8&&Math.min(a[0],b[0])<r.right-.8;
        if(hit)problems.push(`edge ${p.dataset.from}→${p.dataset.to} crosses ${r.id}`);
      }
      if(a[0]<0||a[0]>host.clientWidth||a[1]<0||a[1]>host.clientHeight)problems.push('edge outside host');
    }
  }
  const labels=[...document.querySelectorAll('.edge-label')].map(n=>{const r=n.getBoundingClientRect();return {left:r.left-origin.left,right:r.right-origin.left,top:r.top-origin.top,bottom:r.bottom-origin.top};});
  for(let i=0;i<labels.length;i++){
    if(nodes.some(n=>intersects(n,labels[i])))problems.push('label crosses card');
    if(labels.slice(i+1).some(n=>intersects(n,labels[i])))problems.push('labels overlap');
  }
  if(document.documentElement.scrollWidth>innerWidth+1)problems.push('horizontal scroll');
  if(Number(host.dataset.routingErrors))problems.push('routing errors');
  return {container:host.clientWidth,mode:host.dataset.mode,nodes:nodes.length,edges:paths.length,
    minCardWidth:Math.round(Math.min(...nodes.map(n=>n.width))),columns:new Set(nodes.map(n=>n.col)).size,
    height:document.documentElement.scrollHeight,inlineLabels:labels.length,problems};
}
async function settled(page){await page.waitForFunction(()=>document.querySelector('.composition')?.dataset.ready==='true');await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))));}
(async()=>{
  const browser=await playwright[process.env.BROWSER||'chromium'].launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
  const report=[],errors=[];
  try{
    const page=await browser.newPage({viewport:{width:1600,height:1000}});
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    const fixtures=fs.readdirSync(path.join(root,'tests/fixtures/native_visual')).filter(n=>n.endsWith('.json')).sort();
    for(const fixture of fixtures){
      const name=path.basename(fixture,'.json');
      await page.goto(pathToFileURL(path.join(output,name+'.html')).href+'?debug');
      for(const width of widths){
        await page.setViewportSize({width,height:1000});await settled(page);
        const result=await page.evaluate(inspect);report.push({fixture:name,width,...result});
        if(width>=650&&width<=900&&name==='d_hermes_large'&&result.columns<2)result.problems.push('large diagram collapsed to one column');
        await page.screenshot({path:path.join(output,`${name}-${width}.png`),fullPage:true});
        console.log(`${name} ${width}: ${result.mode}, ${result.columns} cols, ${result.minCardWidth}px cards, ${result.height}px high${result.problems.length?' FAIL '+result.problems.join('; '):' OK'}`);
      }
    }
    // Change only the actual container, holding the browser viewport constant.
    await page.setViewportSize({width:1600,height:1000});
    await page.goto(pathToFileURL(path.join(output,'d_hermes_large.html')).href);
    for(const width of [631,742,480,1300,742]){
      await page.evaluate(w=>document.querySelector('main').style.width=w+'px',width);await settled(page);
      const result=await page.evaluate(inspect);report.push({fixture:'container-resize',width,...result});
      const expected=width===480?'narrow':width===1300?'wide':'compact';
      if(result.mode!==expected)errors.push(`container resize selected ${result.mode}, expected ${expected}`);
    }
    await page.locator('[data-node="hermes"]').focus();
    if(await page.locator('.node.dimmed').count()===0)errors.push('focus failed to highlight relationships');
    await page.locator('[data-node="hermes"] summary').click();await settled(page);
    report.push({fixture:'details-open',width:742,...await page.evaluate(inspect)});
    // Reproduce Hermes artifact sandbox without claiming this is a live-host test.
    const html=fs.readFileSync(path.join(output,'d_hermes_large.html'),'utf8');
    await page.setContent('<iframe sandbox="allow-scripts" style="width:742px;height:700px;border:0"></iframe>');
    await page.locator('iframe').evaluate((el,html)=>el.srcdoc=html,html);
    const frame=await page.locator('iframe').elementHandle().then(el=>el.contentFrame());
    await settled(frame);report.push({fixture:'sandbox-iframe',width:742,...await frame.evaluate(inspect)});
    await page.locator('iframe').evaluate(el=>el.style.width='900px');await settled(frame);
    report.push({fixture:'sandbox-iframe-resize',width:900,...await frame.evaluate(inspect)});
  }finally{await browser.close();}
  fs.writeFileSync(path.join(output,'report.json'),JSON.stringify({report,errors},null,2));
  const failures=report.filter(r=>r.problems.length);
  console.log(`Report: ${output}/report.json; ${report.length} cases, ${failures.length} failures, ${errors.length} browser errors`);
  if(failures.length||errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
