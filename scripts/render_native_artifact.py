"""Render semantic flows as a standalone HTML composition of cards and SVG links."""

from html import escape
from pathlib import Path
import json

from layout_flow import flow_layout
from native_visual_spec import SemanticVisualSpec

extension = ".html"


def render(spec, path, output_dir):
    if not isinstance(spec, SemanticVisualSpec):
        spec = SemanticVisualSpec.from_dict(spec)
    output_dir, path = Path(output_dir).resolve(), Path(path).resolve()
    if path.parent != output_dir:
        raise ValueError("El artifact debe guardarse dentro del directorio permitido.")
    levels = flow_layout(spec)
    nodes = {node["id"]: node for node in spec.nodes}
    parts = ["<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
             "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'\">",
             f"<title>{escape(spec.title)}</title><style>{_CSS}</style></head><body><main><header>"]
    parts.append(f"<p class='eyebrow'>MAPA DEL SISTEMA <span>{len(nodes)} ETAPAS</span></p><h1>{escape(spec.title)}</h1>")
    if spec.subtitle:
        parts.append(f"<p class='subtitle'>{escape(spec.subtitle)}</p>")
    if spec.description:
        parts.append(f"<p class='description'>{escape(spec.description)}</p>")
    parts.append("</header><section class='composition' aria-label='Diagrama de flujo'><svg class='links' aria-hidden='true'></svg><div class='flow'>")
    for level, group in enumerate(levels):
        parts.append(f"<div class='level' data-level='{level}'>")
        for node in group:
            role = node["role"]
            parts.append(f"<article class='node role-{role}' data-node='{escape(node['id'], quote=True)}' tabindex='0'><span class='role'>{escape(role.upper())}</span><h2>{escape(node['title'])}</h2>")
            if node["subtitle"]:
                parts.append(f"<p class='node-subtitle'>{escape(node['subtitle'])}</p>")
            if node["description"]:
                parts.append(f"<p class='node-description'>{escape(node['description'])}</p>")
            if node["metadata"]:
                parts.append("<dl>" + "".join(f"<div><dt>{escape(str(k))}</dt><dd>{escape(str(v))}</dd></div>" for k, v in node["metadata"].items()) + "</dl>")
            parts.append("</article>")
        parts.append("</div>")
    parts.append("</div></section>")
    if spec.groups:
        parts.append("<section class='groups' aria-label='Grupos'><h2>Áreas</h2><div>" + "".join(
            f"<p><strong>{escape(group['title'])}</strong> · {escape(', '.join(nodes[i]['title'] for i in group['nodes']))}</p>" for group in spec.groups) + "</div></section>")
    if spec.annotations:
        parts.append("<aside class='annotations'>" + "".join(f"<p>{escape(note)}</p>" for note in spec.annotations) + "</aside>")
    if spec.notes:
        parts.append("<section class='notes'><h2>Cómo leerlo</h2><ul>" + "".join(f"<li>{escape(note)}</li>" for note in spec.notes) + "</ul></section>")
    if spec.source:
        parts.append("<footer>Fuente · " + escape(" · ".join(f"{k}: {v}" for k, v in spec.source.items())) + "</footer>")
    parts.append(f"</main><script>const EDGES={_js_json(spec.edges)};{_JS}</script></body></html>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts), encoding="utf-8")
    return path


def _js_json(value):
    return json.dumps(value, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


_JS = r"""
const host=document.querySelector('.composition'),svg=host.querySelector('.links');
function draw(){const r=host.getBoundingClientRect(),w=r.width,h=r.height;svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.replaceChildren();const defs=document.createElementNS('http://www.w3.org/2000/svg','defs'),marker=document.createElementNS('http://www.w3.org/2000/svg','marker');marker.id='arrow';marker.setAttribute('viewBox','0 0 10 10');marker.setAttribute('refX','8');marker.setAttribute('refY','5');marker.setAttribute('markerWidth','6');marker.setAttribute('markerHeight','6');marker.setAttribute('orient','auto-start-reverse');const tip=document.createElementNS('http://www.w3.org/2000/svg','path');tip.setAttribute('d','M 0 0 L 10 5 L 0 10 z');tip.setAttribute('fill','context-stroke');marker.append(tip);defs.append(marker);svg.append(defs);
for(const e of EDGES){const a=host.querySelector(`[data-node="${CSS.escape(e.from)}"]`),b=host.querySelector(`[data-node="${CSS.escape(e.to)}"]`);if(!a||!b)continue;
const x=a.getBoundingClientRect(),y=b.getBoundingClientRect(),horizontal=Math.abs(y.left-x.right)<Math.abs(y.top-x.bottom),sx=(horizontal?x.right:x.left+x.width/2)-r.left,sy=(horizontal?x.top+x.height/2:x.bottom)-r.top,tx=(horizontal?y.left:y.left+y.width/2)-r.left,ty=(horizontal?y.top+y.height/2:y.top)-r.top;
const d=horizontal?`M ${sx} ${sy} C ${sx+36} ${sy}, ${tx-36} ${ty}, ${tx} ${ty}`:`M ${sx} ${sy} C ${sx} ${sy+32}, ${tx} ${ty-32}, ${tx} ${ty}`;
const p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('d',d);p.setAttribute('class',`edge ${e.style||'normal'}`);p.dataset.from=e.from;p.dataset.to=e.to;svg.append(p);
if(e.label){const t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',(sx+tx)/2);t.setAttribute('y',(sy+ty)/2-7);t.textContent=e.label;t.setAttribute('class','edge-label');svg.append(t)}}}
function highlight(id){for(const n of host.querySelectorAll('.node'))n.classList.toggle('dimmed',id&&n.dataset.node!==id&&!EDGES.some(e=>(e.from===id&&e.to===n.dataset.node)||(e.to===id&&e.from===n.dataset.node)));for(const p of svg.querySelectorAll('.edge'))p.classList.toggle('dimmed',id&&p.dataset.from!==id&&p.dataset.to!==id)}
host.querySelectorAll('.node').forEach(n=>{n.addEventListener('focus',()=>highlight(n.dataset.node));n.addEventListener('mouseenter',()=>highlight(n.dataset.node));n.addEventListener('blur',()=>highlight(null));n.addEventListener('mouseleave',()=>highlight(null))});
new ResizeObserver(draw).observe(host);window.addEventListener('load',draw);draw();
"""


_CSS = """
:root{color-scheme:light dark;--bg:#f3f5f6;--paper:#fff;--ink:#1d292e;--muted:#617178;--line:#d5dfe1;--accent:#20756d;--tint:#e6f2ef}
@media(prefers-color-scheme:dark){:root{--bg:#151b1d;--paper:#20292c;--ink:#edf3f2;--muted:#a7b7b8;--line:#3c4c4e;--accent:#8ec9bd;--tint:#293d3b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif}main{max-width:1440px;margin:auto;padding:clamp(24px,5vw,68px)}header{max-width:780px;margin:0 auto 34px}.eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.13em;color:var(--accent)}.eyebrow span{margin-left:12px;color:var(--muted)}h1{font-size:clamp(2rem,4vw,3.5rem);line-height:1.08;letter-spacing:-.04em;margin:.3em 0}.subtitle{font-size:1.2rem;color:var(--muted);margin:.5em 0}.description{color:var(--muted)}
.composition{position:relative;border:1px solid var(--line);border-radius:22px;background:var(--paper);padding:clamp(22px,4vw,48px);overflow:hidden}.flow{position:relative;z-index:1;display:flex;align-items:stretch;gap:clamp(38px,5vw,76px);min-height:230px}.level{flex:1;display:flex;flex-direction:column;justify-content:center;gap:20px;min-width:0}.node{position:relative;min-width:150px;padding:20px 20px 18px;border:1px solid var(--line);border-top:3px solid var(--accent);border-radius:13px;background:var(--paper);transition:opacity .15s,border-color .15s;outline:none}.node:focus-visible{box-shadow:0 0 0 3px color-mix(in srgb,var(--accent),transparent 70%)}.role{font-size:.67rem;font-weight:750;letter-spacing:.12em;color:var(--accent)}.node h2{font-size:1.12rem;line-height:1.25;margin:8px 0 5px}.node-subtitle{font-family:ui-monospace,monospace;font-size:.78rem;color:var(--accent);margin:0 0 7px;overflow-wrap:anywhere}.node-description{font-size:.87rem;color:var(--muted);margin:0}.node dl{margin:13px 0 0;border-top:1px solid var(--line);padding-top:9px}.node dl div{display:flex;gap:8px;font-size:.75rem}.node dt{color:var(--muted)}.node dd{margin:0;overflow-wrap:anywhere}.role-input,.role-source{border-top-color:#597b58}.role-storage{border-top-color:#7274a3}.role-output{border-top-color:#a56e43}.role-agent{border-top-color:#9a638a}.links{position:absolute;inset:0;width:100%;height:100%;overflow:visible;z-index:0;pointer-events:none}.edge{fill:none;stroke:#91aaa7;stroke-width:2;marker-end:url(#arrow)}.edge.dashed{stroke-dasharray:6 5}.edge.emphasis{stroke:var(--accent);stroke-width:3}.edge-label{font:12px system-ui,sans-serif;fill:var(--muted);text-anchor:middle;paint-order:stroke;stroke:var(--paper);stroke-width:5px;stroke-linejoin:round}.dimmed{opacity:.24}
.notes,.groups{margin:28px auto 0;max-width:1000px;padding:20px 24px;border-left:3px solid var(--accent);background:var(--tint);border-radius:0 12px 12px 0}.notes h2,.groups h2{font-size:.9rem;margin:0 0 7px}.notes ul{margin:0;padding-left:20px}.groups>div{display:flex;gap:18px;flex-wrap:wrap}.groups p{margin:0;font-size:.85rem}.annotations{display:flex;gap:12px;flex-wrap:wrap;max-width:1000px;margin:18px auto}.annotations p{margin:0;padding:8px 12px;background:var(--tint);border-radius:999px;font-size:.8rem}footer{max-width:1000px;margin:24px auto;color:var(--muted);font-size:.8rem}
@media(max-width:1100px){main{padding:24px 14px}.composition{padding:24px 18px}.flow{flex-direction:column;gap:30px}.level{gap:14px}.node{min-width:0}.edge-label{font-size:11px}}
"""
