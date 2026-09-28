"""Standalone editorial roadmap with container-responsive SVG connectors."""

from html import escape
import json
from pathlib import Path

from layout_roadmap import VARIANTS, layout_roadmap
from roadmap_visual_spec import RoadmapVisualSpec

extension = ".html"
IMPORTANCE_LABELS = {"core": "Esencial", "recommended": "Recomendado",
                     "optional": "Opcional", "specialization": "Especialización"}


def _card(node, variant, index, related, main=False):
    node_id = escape(node["id"], quote=True)
    title = escape(node["title"])
    importance = node["importance"]
    related_json = escape(json.dumps(sorted(related[node["id"]]), ensure_ascii=False), quote=True)
    parts = [f'<article class="card {"main-card" if main else "branch-card"} importance-{importance}" '
             f'id="{variant}-node-{index[node["id"]]}" data-id="{node_id}" data-related="{related_json}" tabindex="0">',
             f'<span class="importance">{IMPORTANCE_LABELS[importance]}</span><h3>{title}</h3>']
    if node["subtitle"]:
        parts.append(f'<p class="subtitle">{escape(node["subtitle"])}</p>')
    if node["description"]:
        parts.append(f'<details><summary>Detalles</summary><p>{escape(node["description"])}</p></details>')
    parts.append("</article>")
    return "".join(parts)


def _view(spec, variant, columns, by_id, index, related):
    parts = [f'<div class="roadmap-view {variant}" data-columns="{columns}">']
    plan = layout_roadmap(spec, columns)
    for section_index, item in enumerate(plan):
        section = item["section"]
        used_columns = min(columns, sum(len(row) for row in item["rows"]))
        max_width = used_columns * 260 + (used_columns - 1) * 32 + 60
        parts.append(f'<section class="roadmap-section" style="--section-max:{max_width}px" aria-label="{escape(section["title"], quote=True)}">'
                     f'<div class="section-heading"><span class="section-number">{section_index + 1:02d}</span>'
                     f'<div><h2>{escape(section["title"])}</h2>')
        if section["description"]:
            parts.append(f'<p>{escape(section["description"])}</p>')
        parts.append('</div></div><div class="section-map">'
                     f'<svg class="connectors" aria-hidden="true" data-svg-id="{variant}-{section_index}"></svg>')
        for row_index, row in enumerate(item["rows"]):
            parts.append(f'<div class="row" data-row="{row_index}" style="--columns:{used_columns}">')
            for slot in row:
                node_id = slot["node"]
                parts.append(f'<div class="slot" data-main="{escape(node_id, quote=True)}">')
                parts.append(_card(by_id[node_id], variant, index, related, main=True))
                if slot["branches"]:
                    parts.append('<div class="branch-list">')
                    for branch in slot["branches"]:
                        parts.append(f'<div class="branch-chain" data-kind="{branch["kind"]}" '
                                     f'data-origin="{escape(node_id, quote=True)}" '
                                     f'data-rejoin="{escape(branch["rejoin"] or "", quote=True)}">')
                        if branch["label"] or any(by_id[branch_id]["importance"] != branch["kind"] for branch_id in branch["nodes"]):
                            parts.append(f'<p class="branch-heading">{IMPORTANCE_LABELS[branch["kind"]]}'
                                         + (f' · {escape(branch["label"])}' if branch["label"] else '') + '</p>')
                        for branch_id in branch["nodes"]:
                            parts.append(_card(by_id[branch_id], variant, index, related))
                        if branch["rejoin"]:
                            target = branch["rejoin"]
                            parts.append(f'<a class="rejoin-link" href="#{variant}-node-{index[target]}">'
                                         f'Retoma en {escape(by_id[target]["title"])}</a>')
                        parts.append('</div>')
                    parts.append('</div>')
                parts.append('</div>')
            parts.append('</div>')
        parts.append('</div></section>')
        if section_index < len(plan) - 1:
            previous = by_id[item["rows"][-1][-1]["node"]]["title"]
            following = by_id[plan[section_index + 1]["rows"][0][0]["node"]]["title"]
            parts.append('<div class="section-transition">'
                         f'<span aria-hidden="true">↓</span><small>{escape(previous)} → {escape(following)}</small></div>')
    parts.append('</div>')
    return "".join(parts)


def render(spec, path, output_dir):
    if not isinstance(spec, RoadmapVisualSpec):
        spec = RoadmapVisualSpec.from_dict(spec)
    output_dir, path = Path(output_dir).resolve(), Path(path).resolve()
    if path.parent != output_dir:
        raise ValueError("El artifact debe guardarse dentro del directorio permitido.")
    by_id = {node["id"]: node for node in spec.nodes}
    index = {node["id"]: position for position, node in enumerate(spec.nodes)}
    related = {node_id: set() for node_id in by_id}
    for source, target in zip(spec.main_path, spec.main_path[1:]):
        related[source].add(target)
        related[target].add(source)
    for branch in spec.branches:
        chain = [branch["from"], *branch["nodes"]]
        if branch["rejoin"]:
            chain.append(branch["rejoin"])
        for source, target in zip(chain, chain[1:]):
            related[source].add(target)
            related[target].add(source)
    parts = ["<!doctype html><html lang='es'><head><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width,initial-scale=1'>",
             "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'\">",
             f'<title>{escape(spec.title)}</title><style>{_CSS}</style></head><body><main>',
             f'<header><p class="eyebrow">ROADMAP · {len(spec.sections)} ETAPAS</p><h1>{escape(spec.title)}</h1>']
    if spec.subtitle:
        parts.append(f'<p class="lead">{escape(spec.subtitle)}</p>')
    if spec.description:
        parts.append(f'<p class="description">{escape(spec.description)}</p>')
    parts.append('</header><p class="legend"><strong>Camino principal</strong> · las ramas recomendadas, opcionales y de especialización aparecen junto a su origen.</p>')
    for variant_index, (mode, threshold, columns) in enumerate(VARIANTS):
        parts.append(_view(spec, f'v{variant_index}', columns, by_id, index, related))
    if spec.notes:
        parts.append('<aside class="notes"><h2>Notas</h2><ul>' + ''.join(f'<li>{escape(note)}</li>' for note in spec.notes) + '</ul></aside>')
    if spec.source:
        parts.append('<footer>Fuente · ' + escape(' · '.join(f'{key}: {value}' for key, value in spec.source.items())) + '</footer>')
    parts.append(f'<script>{_JS}</script></main></body></html>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(parts), encoding='utf-8')
    return path


_CSS = """
:root{color-scheme:dark;background:#090f1b;color:#f8fafc;font:15px/1.5 system-ui,sans-serif}*{box-sizing:border-box}body{margin:0}main{container-type:inline-size;max-width:1500px;margin:auto;padding:clamp(16px,3vw,36px)}header{max-width:900px;margin:0 auto 22px}.eyebrow{font-size:.72rem;letter-spacing:.15em;font-weight:750;color:#67e8f9}h1{font-size:clamp(1.8rem,3vw,2.7rem);line-height:1.12;margin:8px 0}.lead{font-size:1.05rem;color:#dbeafe;margin:8px 0}.description,.legend{color:#aebed0}.legend{font-size:.85rem;margin:0 0 24px}.legend strong{color:#f8fafc}.roadmap-view{display:none}.roadmap-view.v0{display:block}.roadmap-section{margin:0}.section-heading{display:flex;gap:16px;align-items:flex-start;margin:0 0 10px}.section-number{color:#67e8f9;font-weight:800;font-size:1.1rem;min-width:32px}.section-heading h2{font-size:1.25rem;line-height:1.2;margin:0}.section-heading p{color:#94a3b8;font-size:.84rem;margin:5px 0 0}.section-map{position:relative;overflow:hidden;background:#111c2b;border:1px solid #334155;border-radius:16px;padding:22px 30px 64px}.row{position:relative;display:grid;grid-template-columns:repeat(var(--columns),minmax(0,1fr));gap:32px;align-items:start}.row:not(:last-child){margin-bottom:64px}.slot{min-width:0;position:relative;z-index:2}.card{position:relative;z-index:2;min-width:0;background:#17263a;border:1px solid #52667d;border-radius:11px;padding:11px 13px;scroll-margin:20px}.main-card{min-height:92px;border-left:5px solid #67e8f9;box-shadow:0 5px 16px #0003}.branch-card{min-height:66px;margin:12px 0 0 28px;background:#162334}.importance{font-size:.63rem;text-transform:uppercase;letter-spacing:.11em;font-weight:800;color:#99e9f2}.card h3{font-size:.98rem;line-height:1.25;margin:4px 0}.card .subtitle{font-size:.78rem;color:#cbd5e1;margin:4px 0 0}.card details{font-size:.77rem;color:#cbd5e1;margin-top:7px}.card details p{margin:6px 0 0}.card summary{cursor:pointer;color:#8be9e0}.branch-list{margin-top:24px}.branch-chain{margin:0 0 16px}.branch-chain:last-child{margin-bottom:0}.branch-heading{font-size:.68rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#aebed0;margin:0 0 4px 28px}.importance-recommended{border-color:#418f97}.importance-optional{border-style:dashed;border-color:#74869b;background:#142033}.importance-optional .importance{color:#b8c3d1}.importance-specialization{border-color:#b884ee;background:#241e3b}.importance-specialization .importance{color:#d6b4fb}.main-card.importance-core{border-left-color:#67e8f9}.main-card.importance-recommended{border-left-color:#38bdf8}.main-card.importance-optional{border-left-color:#94a3b8}.main-card.importance-specialization{border-left-color:#c084fc}.card:focus-visible,.card:target,.rejoin-link:focus-visible{outline:2px solid #fbbf24;outline-offset:3px}.card.muted,.connector.muted{opacity:.25}.rejoin-link{display:block;font-size:.73rem;color:#e0b8ff;margin:7px 0 0 28px}.connectors{position:absolute;inset:0;width:100%;height:100%;z-index:1;pointer-events:none;overflow:visible}.connector{fill:none;stroke:#8ca6b9;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.connector.branch{stroke:#72a9b2;stroke-width:1.7}.connector.rejoin{stroke:#ba9bea;stroke-dasharray:5 4}.section-transition{height:62px;display:flex;align-items:center;justify-content:center;gap:8px;color:#9fb2c5;font-size:.75rem;letter-spacing:.05em;text-transform:uppercase}.section-transition span{font-size:1.6rem;color:#67e8f9}.notes{border:1px solid #334155;border-radius:12px;background:#111c2b;margin-top:24px;padding:16px}.notes h2{font-size:1rem;margin:0}.notes ul{margin:8px 0 0;padding-left:20px}footer{font-size:.78rem;color:#94a3b8;margin:24px 0}
@container(min-width:600px){.roadmap-view.v0{display:none}.roadmap-view.v1{display:block}}
@container(min-width:850px){.roadmap-view.v1{display:none}.roadmap-view.v2{display:block}}
@container(min-width:1100px){.roadmap-view.v2{display:none}.roadmap-view.v3{display:block}}
@container(min-width:1400px){.roadmap-view.v3{display:none}.roadmap-view.v4{display:block}}
@container(min-width:1100px){.roadmap-section{max-width:var(--section-max);margin-inline:auto}}
"""

_JS = r"""
const NS='http://www.w3.org/2000/svg';
function visible(view){return getComputedStyle(view).display!=='none'}
function draw(map){
  const svg=map.querySelector('svg'),box=map.getBoundingClientRect();
  if(!box.width)return;
  const width=box.width,height=box.height,mark='arrow-'+svg.dataset.svgId;
  svg.replaceChildren();svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
  const defs=document.createElementNS(NS,'defs'),marker=document.createElementNS(NS,'marker');
  marker.setAttribute('id',mark);marker.setAttribute('viewBox','0 0 10 10');marker.setAttribute('refX','9');marker.setAttribute('refY','5');marker.setAttribute('markerWidth','6');marker.setAttribute('markerHeight','6');marker.setAttribute('orient','auto-start-reverse');
  const tip=document.createElementNS(NS,'path');tip.setAttribute('d','M 0 0 L 10 5 L 0 10 z');tip.setAttribute('fill','#9bb9c6');marker.append(tip);defs.append(marker);svg.append(defs);
  const rect=element=>{const r=element.getBoundingClientRect();return {l:r.left-box.left,r:r.right-box.left,t:r.top-box.top,b:r.bottom-box.top,cx:(r.left+r.right)/2-box.left,cy:(r.top+r.bottom)/2-box.top}};
  function path(d,kind,from,to,arrow=true){const p=document.createElementNS(NS,'path');p.setAttribute('d',d);p.setAttribute('class','connector '+kind);p.dataset.from=from;p.dataset.to=to;if(arrow)p.setAttribute('marker-end',`url(#${mark})`);svg.append(p)}
  const rows=[...map.querySelectorAll('.row')],mains=[...map.querySelectorAll('.main-card')];
  for(let i=0;i<mains.length-1;i++){
    const a=rect(mains[i]),b=rect(mains[i+1]),same=mains[i].closest('.row')===mains[i+1].closest('.row');
    if(same)path(`M ${a.r} ${a.cy} H ${b.l-5}`,'main',mains[i].dataset.id,mains[i+1].dataset.id);
    else{const row=rect(mains[i].closest('.row')),bus=row.b+20,x=width-12;
      path(`M ${a.r} ${a.cy} H ${x} V ${bus} H ${b.cx} V ${b.t-5}`,'main',mains[i].dataset.id,mains[i+1].dataset.id)}
  }
  const rejoins=[];
  for(const slot of map.querySelectorAll('.slot')){
    const parent=slot.querySelector('.main-card'),chains=[...slot.querySelectorAll('.branch-chain')];if(!chains.length)continue;
    const p=rect(parent),firsts=chains.map(chain=>chain.querySelector('.branch-card'));
    const rail=p.l+12,lowest=Math.max(...firsts.map(card=>rect(card).cy));
    path(`M ${rail} ${p.b} V ${lowest}`,'branch',parent.dataset.id,firsts.at(-1).dataset.id,false);
    for(const chain of chains){
      const cards=[...chain.querySelectorAll('.branch-card')],first=rect(cards[0]);
      path(`M ${rail} ${first.cy} H ${first.l-4}`,'branch',parent.dataset.id,cards[0].dataset.id);
      for(let i=0;i<cards.length-1;i++){const a=rect(cards[i]),b=rect(cards[i+1]);path(`M ${a.cx} ${a.b} V ${b.t-5}`,'branch',cards[i].dataset.id,cards[i+1].dataset.id)}
      if(chain.dataset.rejoin)rejoins.push({source:cards.at(-1),target:chain.dataset.rejoin,row:slot.closest('.row')});
    }
  }
  const groups=new Map();
  for(const item of rejoins){const key=item.row.dataset.row+'|'+item.target;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(item)}
  let channel=0;
  for(const group of groups.values()){
    const row=rect(group[0].row),sources=group.map(item=>rect(item.source)),target=[...map.querySelectorAll('.main-card')].find(card=>card.dataset.id===group[0].target);
    if(!target)continue;
    const t=rect(target),targetRow=rect(target.closest('.row'));
    const shortReturn=group[0].row===target.closest('.row')&&!target.closest('.slot').querySelector('.branch-list')&&sources.every(s=>s.r<t.l);
    const bus=row.b+(shortReturn?20:39)+channel*3,outer=width-18-channel*5;
    const rails=sources.map(s=>s.l-20);
    for(let i=0;i<sources.length;i++)path(`M ${sources[i].l} ${sources[i].cy} H ${rails[i]} V ${bus}`,'rejoin',group[i].source.dataset.id,target.dataset.id,false);
    if(shortReturn)path(`M ${Math.min(...rails)} ${bus} H ${t.cx} V ${t.b+5}`,'rejoin',group[0].source.dataset.id,target.dataset.id);
    else path(`M ${Math.min(...rails)} ${bus} H ${outer} V ${targetRow.t-15} H ${t.cx} V ${t.t-5}`,'rejoin',group[0].source.dataset.id,target.dataset.id);
    channel++;
  }
}
function redraw(){for(const view of document.querySelectorAll('.roadmap-view'))if(visible(view))for(const map of view.querySelectorAll('.section-map'))draw(map)}
let queued=false;function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;redraw()})}
if('ResizeObserver'in window)new ResizeObserver(schedule).observe(document.querySelector('main'));else addEventListener('resize',schedule);
document.fonts?.ready.then(schedule);schedule();
for(const view of document.querySelectorAll('.roadmap-view')){
  function emphasize(card){const related=new Set(JSON.parse(card.dataset.related));related.add(card.dataset.id);
    for(const item of view.querySelectorAll('.card'))item.classList.toggle('muted',!related.has(item.dataset.id));
    for(const edge of view.querySelectorAll('.connector'))edge.classList.toggle('muted',edge.dataset.from!==card.dataset.id&&edge.dataset.to!==card.dataset.id)}
  function clear(){for(const item of view.querySelectorAll('.muted'))item.classList.remove('muted')}
  view.addEventListener('mouseover',event=>{const card=event.target.closest('.card');if(card)emphasize(card)});
  view.addEventListener('mouseout',event=>{if(event.target.closest('.card'))clear()});
  view.addEventListener('focusin',event=>{const card=event.target.closest('.card');if(card)emphasize(card)});
  view.addEventListener('focusout',()=>setTimeout(()=>{if(!view.contains(document.activeElement))clear()},0));
  view.addEventListener('toggle',schedule,true);
}
"""
