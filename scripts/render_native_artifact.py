"""Compatibility backend for flows; authoring routes through study-concept-diagrams."""

from html import escape
from pathlib import Path
import json

from layout_flow import responsive_layouts
from native_visual_spec import SemanticVisualSpec

extension = ".html"


def render(spec, path, output_dir):
    if not isinstance(spec, SemanticVisualSpec):
        spec = SemanticVisualSpec.from_dict(spec)
    output_dir, path = Path(output_dir).resolve(), Path(path).resolve()
    if path.parent != output_dir:
        raise ValueError("El artifact debe guardarse dentro del directorio permitido.")
    layout = responsive_layouts(spec)
    collapsed = layout["analysis"]["density"] != "small"
    nodes = {node["id"]: node for node in spec.nodes}
    parts = ["<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
             "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'\">",
             f"<title>{escape(spec.title)}</title><style>{_CSS}</style></head><body><main><header>",
             f"<p class='eyebrow'>MAPA DEL SISTEMA <span>{len(nodes)} ETAPAS</span></p><h1>{escape(spec.title)}</h1>"]
    for key in ("subtitle", "description"):
        if getattr(spec, key):
            parts.append(f"<p class='{key}'>{escape(getattr(spec, key))}</p>")
    parts.append("</header><output class='debug' hidden></output><section class='composition' aria-label='Diagrama de flujo'><svg class='links' aria-hidden='true'></svg><div class='edge-labels' aria-hidden='true'></div><div class='flow'>")
    # Initial HTML follows the same semantic reading order as all responsive plans.
    for lane in layout["plans"]["narrow-1"]["lanes"]:
        for node_id in lane["nodes"]:
            node = nodes[node_id]
            parts.append(f"<article class='node role-{node['role']}' data-node='{escape(node_id, quote=True)}' tabindex='0'><span class='role'>{escape(node['role'].upper())}</span><h2>{escape(node['title'])}</h2>")
            if node["subtitle"]:
                parts.append(f"<p class='node-subtitle'>{escape(node['subtitle'])}</p>")
            if collapsed and (node["description"] or node["metadata"]):
                parts.append("<details><summary>Detalles</summary>")
            if node["description"]:
                parts.append(f"<p class='node-description'>{escape(node['description'])}</p>")
            if node["metadata"]:
                parts.append("<dl>" + "".join(f"<div><dt>{escape(str(k))}</dt><dd>{escape(str(v))}</dd></div>" for k, v in node["metadata"].items()) + "</dl>")
            if collapsed and (node["description"] or node["metadata"]):
                parts.append("</details>")
            parts.append("</article>")
    parts.append("</div></section><noscript>Activá JavaScript para distribuir el diagrama y ver sus conectores. Las tarjetas y relaciones siguen disponibles.</noscript>")
    if spec.edges:
        parts.append("<details class='relations'><summary>Relaciones del diagrama</summary><ul>" + "".join(
            f"<li>{escape(nodes[e['from']]['title'])} → {escape(nodes[e['to']]['title'])}" +
            (f": {escape(e['label'])}" if e["label"] else "") + "</li>" for e in spec.edges) + "</ul></details>")
    if spec.annotations:
        parts.append("<aside class='annotations'>" + "".join(f"<p>{escape(note)}</p>" for note in spec.annotations) + "</aside>")
    if spec.notes:
        parts.append("<section class='notes'><h2>Cómo leerlo</h2><ul>" + "".join(f"<li>{escape(note)}</li>" for note in spec.notes) + "</ul></section>")
    if spec.source:
        parts.append("<footer>Fuente · " + escape(" · ".join(f"{k}: {v}" for k, v in spec.source.items())) + "</footer>")
    parts.append(f"</main><script>const EDGES={_js_json(spec.edges)},LAYOUT={_js_json(layout)};{_JS}</script></body></html>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts), encoding="utf-8")
    return path


def _js_json(value):
    return json.dumps(value, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


_JS = r"""
const host=document.querySelector('.composition'),flow=host.querySelector('.flow');
const svg=host.querySelector('.links'),labels=host.querySelector('.edge-labels');
const cards=new Map([...flow.querySelectorAll('.node')].map(n=>[n.dataset.node,n]));
const debug=document.querySelector('.debug'),S=LAYOUT.sizing;
let active=null,hovered=null,plan=null,layoutKey='',scheduled=false;
debug.hidden=!new URLSearchParams(location.search).has('debug');
function element(tag,attrs={}){
  const el=document.createElementNS('http://www.w3.org/2000/svg',tag);
  for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);
  return el;
}
function relative(el){const a=el.getBoundingClientRect(),b=host.getBoundingClientRect();
  return {left:a.left-b.left,right:a.right-b.left,top:a.top-b.top,bottom:a.bottom-b.top,width:a.width,height:a.height};}
function arrange(){
  const width=host.clientWidth,available=Math.max(1,width-2*S.gutter);
  const fits=Math.max(1,Math.min(6,Math.floor((available+S.gap)/(S.min+S.gap))));
  const preferred=Math.max(1,Math.min(6,Math.floor((available+S.gap)/(S.preferred+S.gap))));
  const capacity=LAYOUT.analysis.density==='small'&&preferred>=2&&Math.max(LAYOUT.analysis.number_of_levels,LAYOUT.analysis.max_nodes_per_level)<=preferred?preferred:fits;
  const mode=capacity<2?'narrow':width>=1050&&capacity>=4?'wide':'compact';
  let columns=mode==='narrow'?1:capacity;
  const key=`${mode}-${columns}`;
  plan=LAYOUT.plans[key];
  columns=Math.min(columns,Math.max(...Object.values(plan.positions).map(p=>p.col))+1);
  const cardWidth=Math.min(S.max,(available-(columns-1)*S.gap)/columns);
  flow.style.gridTemplateColumns=`repeat(${columns}, minmax(0, ${cardWidth}px))`;
  host.dataset.mode=mode;
  if(layoutKey!==key){
    layoutKey=key;
    flow.querySelectorAll('.lane-band,.lane-title').forEach(n=>n.remove());
    for(const [id,pos] of Object.entries(plan.positions)){
      const node=cards.get(id);node.style.gridRow=pos.row+1;node.style.gridColumn=pos.col+1;
      node.dataset.row=pos.row;node.dataset.col=pos.col;
    }
    for(const lane of plan.lanes){
      if(lane.title===null)continue;
      const band=document.createElement('div');band.className='lane-band';band.setAttribute('aria-hidden','true');
      band.style.gridArea=`${lane.start+1} / 1 / ${lane.end+1} / -1`;flow.append(band);
      const title=document.createElement('h3');title.className='lane-title';title.textContent=lane.title;
      title.style.gridArea=`${lane.start+1} / 1 / auto / -1`;
      flow.insertBefore(title,cards.get(lane.nodes[0]));
    }
  }
  const a=LAYOUT.analysis;
  debug.value=`container: ${Math.round(width)}px · mode: ${mode} · nodes: ${a.node_count} · levels: ${a.number_of_levels} · ${a.density}`;
}
function point(box,side,fraction){
  if(side==='left'||side==='right')return [box[side],box.top+box.height*fraction];
  return [box.left+box.width*fraction,box[side]];
}
function stub(p,side){const [dx,dy]={top:[0,-12],right:[12,0],bottom:[0,12],left:[-12,0]}[side];return [p[0]+dx,p[1]+dy];}
function crosses(a,b,r,pad=5){
  if(a[0]===b[0])return a[0]>r.left-pad&&a[0]<r.right+pad&&Math.max(a[1],b[1])>r.top-pad&&Math.min(a[1],b[1])<r.bottom+pad;
  return a[1]>r.top-pad&&a[1]<r.bottom+pad&&Math.max(a[0],b[0])>r.left-pad&&Math.min(a[0],b[0])<r.right+pad;
}
function simplify(points){
  const out=[];
  for(const p of points){
    if(out.length&&out.at(-1)[0]===p[0]&&out.at(-1)[1]===p[1])continue;
    while(out.length>1){const a=out.at(-2),b=out.at(-1);
      if((a[0]===b[0]&&b[0]===p[0]&&(b[1]-a[1])*(p[1]-b[1])>=0)||
         (a[1]===b[1]&&b[1]===p[1]&&(b[0]-a[0])*(p[0]-b[0])>=0))out.pop();else break;}
    out.push(p);
  }
  return out;
}
function route(s,t,sa,ta,obstacles,xs,ys,used,index,source,target){
  const a=stub(s,sa),b=stub(t,ta),candidates=[];
  candidates.push([s,a,[b[0],a[1]],b,t],[s,a,[a[0],b[1]],b,t]);
  const offset=((index%5)-2)*3;
  for(const x of xs)candidates.push([s,a,[x+offset,a[1]],[x+offset,b[1]],b,t]);
  for(const y of ys)candidates.push([s,a,[a[0],y+offset],[b[0],y+offset],b,t]);
  let best=null,bestScore=Infinity;
  for(const candidate of candidates){
    const points=simplify(candidate);let length=0,valid=true;
    for(let i=1;i<points.length;i++){
      const u=points[i-1],v=points[i];
      if(obstacles.some(r=>crosses(u,v,r,r===source||r===target?0:5))){valid=false;break;}
      length+=Math.abs(u[0]-v[0])+Math.abs(u[1]-v[1]);
    }
    if(!valid)continue;
    let score=length+points.length*12;
    // Prefer free corridors; shared portions remain possible in dense DAGs.
    for(let i=1;i<points.length;i++)for(const [u,v] of used){
      const a=points[i-1],b=points[i];
      if(a[0]===b[0]&&u[0]===v[0]&&Math.abs(a[0]-u[0])<2)
        score+=Math.max(0,Math.min(Math.max(a[1],b[1]),Math.max(u[1],v[1]))-Math.max(Math.min(a[1],b[1]),Math.min(u[1],v[1])))*2;
      if(a[1]===b[1]&&u[1]===v[1]&&Math.abs(a[1]-u[1])<2)
        score+=Math.max(0,Math.min(Math.max(a[0],b[0]),Math.max(u[0],v[0]))-Math.max(Math.min(a[0],b[0]),Math.min(u[0],v[0])))*2;
    }
    if(score<bestScore){best=points;bestScore=score;}
  }
  return best;
}
function intersects(a,b,pad=0){return a.left<b.right+pad&&a.right>b.left-pad&&a.top<b.bottom+pad&&a.bottom>b.top-pad;}
function draw(){
  svg.replaceChildren();labels.replaceChildren();
  svg.setAttribute('viewBox',`0 0 ${host.clientWidth} ${host.clientHeight}`);
  const defs=element('defs'),marker=element('marker',{id:'arrow',viewBox:'0 0 10 10',refX:10,refY:5,markerWidth:9,markerHeight:9,markerUnits:'userSpaceOnUse',orient:'auto'});
  marker.append(element('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'context-stroke'}));defs.append(marker);svg.append(defs);
  const boxes=new Map([...cards].map(([id,n])=>[id,relative(n)]));
  const obstacles=[...boxes.values(),...flow.querySelectorAll('.lane-title')].map(r=>r instanceof Element?relative(r):r);
  const rows=new Map(),cols=new Map();
  for(const [id,b] of boxes){const p=plan.positions[id];
    const row=rows.get(p.row)||{top:b.top,bottom:b.bottom};row.top=Math.min(row.top,b.top);row.bottom=Math.max(row.bottom,b.bottom);rows.set(p.row,row);
    const col=cols.get(p.col)||{left:b.left,right:b.right};col.left=Math.min(col.left,b.left);col.right=Math.max(col.right,b.right);cols.set(p.col,col);}
  const colList=[...cols].sort((a,b)=>a[0]-b[0]).map(v=>v[1]),rowList=[...rows].sort((a,b)=>a[0]-b[0]).map(v=>v[1]);
  const xs=[14,host.clientWidth-14,...colList.slice(1).map((c,i)=>(colList[i].right+c.left)/2)];
  const ys=[14,host.clientHeight-14,...rowList.flatMap(r=>[r.top-24,r.bottom+24])];
  const ports=new Map(),ranks=[];
  EDGES.forEach((e,i)=>{ranks[i]=[];[e.from,e.to].forEach((id,end)=>{const key=JSON.stringify([id,plan.anchors[i][end]]);
    if(!ports.has(key))ports.set(key,[]);ranks[i][end]=[key,ports.get(key).length];ports.get(key).push(i);});});
  const used=[],placedLabels=[];let failures=0;
  EDGES.forEach((e,i)=>{
    const [sa,ta]=plan.anchors[i],a=boxes.get(e.from),b=boxes.get(e.to);
    const fractions=ranks[i].map(([key,index])=>.2+.6*(index+1)/(ports.get(key).length+1));
    const s=point(a,sa,fractions[0]),t=point(b,ta,fractions[1]);
    const points=route(s,t,sa,ta,obstacles,xs,ys,used,i,a,b);
    if(!points){failures++;return;}
    for(let k=1;k<points.length;k++)used.push([points[k-1],points[k]]);
    const edge=element('path',{d:points.map((p,k)=>`${k?'L':'M'} ${p[0]} ${p[1]}`).join(' '),class:`edge ${e.style}`});
    edge.dataset.from=e.from;edge.dataset.to=e.to;edge.dataset.points=JSON.stringify(points);
    edge.dataset.fromAnchor=sa;edge.dataset.toAnchor=ta;
    const title=element('title');title.textContent=e.label||`${e.from} → ${e.to}`;edge.append(title);svg.append(edge);
    if(!e.label)return;
    const label=document.createElement('span');label.className='edge-label';label.textContent=e.label;
    label.dataset.from=e.from;label.dataset.to=e.to;labels.append(label);
    const w=label.offsetWidth,h=label.offsetHeight;
    let placed=false;
    const segments=points.slice(1).map((v,j)=>[points[j],v]).sort((u,v)=>Math.abs(v[0][0]-v[1][0])-Math.abs(u[0][0]-u[1][0]));
    for(const [u,v] of segments){
      const x=(u[0]+v[0])/2,y=(u[1]+v[1])/2;
      const box={left:x-w/2,right:x+w/2,top:y-h/2,bottom:y+h/2};
      if(box.left<4||box.right>host.clientWidth-4||box.top<0||box.bottom>host.clientHeight)continue;
      if(obstacles.some(r=>intersects(box,r,7))||placedLabels.some(r=>intersects(box,r,4)))continue;
      label.style.left=`${box.left}px`;label.style.top=`${box.top}px`;placedLabels.push(box);placed=true;break;
    }
    if(!placed)label.remove(); // Full labels remain in the accessible relations list.
  });
  host.dataset.routingErrors=failures;
  if(failures)console.error(`No se pudieron trazar ${failures} conexiones; consultar Relaciones del diagrama.`);
  highlight();host.dataset.ready='true';
}
function highlight(){const id=active||hovered;
  for(const [key,n] of cards)n.classList.toggle('dimmed',!!id&&key!==id&&!EDGES.some(e=>(e.from===id&&e.to===key)||(e.to===id&&e.from===key)));
  for(const p of host.querySelectorAll('.edge,.edge-label'))p.classList.toggle('dimmed',!!id&&p.dataset.from!==id&&p.dataset.to!==id);
}
function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;if(!host.isConnected||host.clientWidth===0)return;arrange();draw();});}
for(const [id,node] of cards){
  node.addEventListener('focusin',()=>{active=id;highlight();});
  node.addEventListener('focusout',e=>{if(!node.contains(e.relatedTarget)){active=null;highlight();}});
  node.addEventListener('mouseenter',()=>{hovered=id;highlight();});
  node.addEventListener('mouseleave',()=>{hovered=null;highlight();});
}
if(typeof ResizeObserver!=='undefined'){
  const observer=new ResizeObserver(schedule);observer.observe(host);observer.observe(flow);
}else window.addEventListener('resize',schedule);
window.addEventListener('load',schedule);document.fonts?.ready.then(schedule);schedule();
"""

_CSS = """
/* Shared visual guidance: repository DESIGN.md. */
:root{color-scheme:light dark;--bg:#f3f5f6;--paper:#fff;--ink:#1d292e;--muted:#596b73;--line:#cbd7da;--accent:#20756d;--tint:#e6f2ef;--edge:#507f79}
@media(prefers-color-scheme:dark){:root{--bg:#151b1d;--paper:#20292c;--ink:#edf3f2;--muted:#b4c3c5;--line:#45575b;--accent:#8ed5c5;--tint:#293d3b;--edge:#a0beb8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
main{padding:24px 16px;max-width:1800px;margin:auto;container-type:inline-size}header{max-width:900px;margin:0 auto 28px}
.eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.13em;color:var(--accent)}.eyebrow span{margin-left:12px;color:var(--muted)}
h1{font-size:2.6rem;line-height:1.1;letter-spacing:-.035em;margin:.3em 0;overflow-wrap:anywhere}.subtitle{font-size:1.15rem;color:var(--muted)}.description{color:var(--muted)}
.composition{position:relative;border:1px solid var(--line);border-radius:18px;background:var(--paper);padding:28px;isolation:isolate}
.flow{display:grid;grid-template-columns:minmax(0,320px);justify-content:center;gap:64px 48px;position:relative}
.node{position:relative;z-index:2;min-width:0;padding:16px;border:1px solid var(--line);border-top:3px solid var(--accent);border-radius:12px;background:var(--paper);overflow-wrap:anywhere}
.node:focus-visible{outline:3px solid var(--accent);outline-offset:3px}.role{font-size:.65rem;font-weight:700;letter-spacing:.11em;color:var(--accent)}
.node h2{font-size:1.08rem;line-height:1.3;margin:7px 0}.node-subtitle{font-size:.8rem;color:var(--accent);margin:0}.node-description{font-size:.85rem;color:var(--muted);margin:10px 0 0}
.node dl{margin:10px 0 0;border-top:1px solid var(--line);padding-top:8px;font-size:.76rem}.node dl div{display:flex;gap:8px;flex-wrap:wrap}.node dt{color:var(--muted)}.node dd{margin:0;min-width:0}
summary{cursor:pointer;color:var(--accent)}.node summary{font-size:.76rem;margin-top:10px}.node details[open] summary{margin-bottom:8px}
.role-input,.role-source{border-top-color:#597b58}.role-storage{border-top-color:#7274a3}.role-output{border-top-color:#a56e43}.role-agent{border-top-color:#9a638a}
.lane-band{z-index:0;background:var(--tint);border-radius:12px;margin:-12px;opacity:.5;pointer-events:none}.lane-title{z-index:2;align-self:start;justify-self:start;max-width:100%;margin:0;font-size:.75rem;line-height:1.35;text-transform:uppercase;letter-spacing:.1em;overflow-wrap:anywhere;color:var(--accent)}
.links,.edge-labels{position:absolute;inset:0;width:100%;height:100%;z-index:3;pointer-events:none;overflow:visible}.edge{fill:none;stroke:var(--edge);stroke-width:2;stroke-linejoin:round;marker-end:url(#arrow)}.edge.dashed{stroke-dasharray:6 5}.edge.emphasis{stroke:var(--accent);stroke-width:2.8}
.edge-label{position:absolute;max-width:140px;padding:2px 5px;font-size:11px;line-height:1.25;background:var(--paper);color:var(--ink);border-radius:4px;text-align:center;overflow-wrap:anywhere}.dimmed{opacity:.22}
.notes,.relations{margin:24px auto 0;max-width:1000px;padding:16px 20px;background:var(--tint);border-radius:10px}.notes h2{font-size:.95rem;margin:0 0 8px}.notes ul{margin:0;padding-left:20px}
.annotations{display:flex;gap:12px;flex-wrap:wrap;max-width:1000px;margin:18px auto}.annotations p{margin:0;padding:8px 12px;background:var(--tint);border-radius:8px}.notes,.annotations,.relations,footer{overflow-wrap:anywhere}footer{max-width:1000px;margin:24px auto;color:var(--muted);font-size:.8rem}
.debug{display:block;padding:8px;font:12px ui-monospace,monospace;overflow-wrap:anywhere}.debug[hidden]{display:none}
@container(max-width:599px){h1{font-size:1.8rem}.subtitle{font-size:1rem}.node h2{font-size:1rem}.node{padding:14px}}
"""
