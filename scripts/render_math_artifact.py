"""Compatibility math backend; authoring routes through study-concept-diagrams."""

import ast
import base64
from html import escape
import json
import math
from pathlib import Path
import re


extension = ".html"
ASSETS = Path(__file__).resolve().parents[1] / "assets" / "math"
FUNCTIONS = {"sin", "cos", "tan", "asin", "acos", "atan", "exp", "log", "sqrt", "Abs"}
ELEMENTS = {"point", "segment", "vector", "circle", "polygon"}
CIRCUIT_ELEMENTS = {"resistor", "capacitor", "inductor", "battery", "source", "ground", "diode", "switch", "line"}
DIRECTIONS = {"right", "left", "up", "down"}


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} debe ser un número finito.")
    return float(value)


def _text(value, name, limit=160):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} debe ser texto de 1 a {limit} caracteres.")
    return value.strip()


def _pair(value, name):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name} debe ser [x, y].")
    return [_number(item, name) for item in value]


def _bounds(value):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError("bounds debe ser [izquierda, arriba, derecha, abajo].")
    left, top, right, bottom = [_number(item, "bounds") for item in value]
    if left >= right or bottom >= top:
        raise ValueError("bounds debe encerrar un área positiva.")
    return [left, top, right, bottom]


def _expression(value, symbols):
    """Convert a small arithmetic grammar to SymPy without evaluating Python input."""
    source = _text(value, "expression", 200).replace("^", "**")
    try:
        import sympy as sp
    except ImportError as error:
        raise RuntimeError("SymPy no está instalado; instalalo para calcular funciones y campos.") from error
    variables = {name: sp.Symbol(name, real=True) for name in symbols}
    names = {**variables, "pi": sp.pi, "E": sp.E}
    functions = {name: getattr(sp, name) for name in FUNCTIONS}

    def convert(node, depth=0):
        if depth > 24:
            raise ValueError("La expresión matemática es demasiado profunda.")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return sp.Float(node.value) if isinstance(node.value, float) else sp.Integer(node.value)
        if isinstance(node, ast.Name) and node.id in names:
            return names[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            result = convert(node.operand, depth + 1)
            return result if isinstance(node.op, ast.UAdd) else -result
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            left, right = convert(node.left, depth + 1), convert(node.right, depth + 1)
            if isinstance(node.op, ast.Pow):
                try:
                    exponent = float(right)
                except (TypeError, ValueError, OverflowError) as error:
                    raise ValueError("El exponente debe ser un número real constante.") from error
                if not right.is_number or not math.isfinite(exponent) or abs(exponent) > 20:
                    raise ValueError("El exponente debe ser constante y de magnitud máxima 20.")
                return left ** right
            return {ast.Add: lambda: left + right, ast.Sub: lambda: left - right,
                    ast.Mult: lambda: left * right, ast.Div: lambda: left / right}[type(node.op)]()
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in functions and len(node.args) == 1 and not node.keywords:
            return functions[node.func.id](convert(node.args[0], depth + 1))
        raise ValueError("Expresión no soportada. Usá x/y, números, + - * / ^ y funciones matemáticas comunes.")

    try:
        result = convert(ast.parse(source, mode="eval").body)
    except (SyntaxError, OverflowError, ZeroDivisionError) as error:
        raise ValueError("Expresión matemática inválida.") from error
    if not result.free_symbols.issubset(set(variables.values())):
        raise ValueError("La expresión contiene variables no admitidas.")
    return result, [variables[name] for name in symbols]


def _sample_function(data):
    if "expression" not in data:
        from render_plot import _series
        class Request:
            type = "function"
            title = "Función"
            def __init__(self, payload):
                self.data = payload
        return [{"label": label or "Serie", "x": x, "y": y} for x, y, label in _series(Request(data))]
    expression, (x,) = _expression(data["expression"], ("x",))
    import sympy as sp
    domain = data.get("domain", [-10, 10])
    lower, upper = _pair(domain, "domain")
    if lower >= upper or upper - lower > 10000:
        raise ValueError("domain debe tener un intervalo creciente de hasta 10000 unidades.")
    f = sp.lambdify(x, expression, modules="math")
    series, segment = [], {"label": str(expression), "x": [], "y": []}
    for index in range(401):
        xv = lower + (upper - lower) * index / 400
        try:
            yv = float(f(xv))
        except (ValueError, ZeroDivisionError, OverflowError, TypeError):
            yv = math.nan
        if math.isfinite(yv) and abs(yv) < 1e8:
            segment["x"].append(xv)
            segment["y"].append(yv)
        elif segment["x"]:
            series.append(segment)
            segment = {"label": str(expression), "x": [], "y": []}
    if segment["x"]:
        series.append(segment)
    if not series:
        raise ValueError("La función no produce valores reales finitos en el dominio indicado.")
    return series


def _parameterized_function(data):
    parameter = data.get("parameter")
    if not isinstance(parameter, dict) or not re.fullmatch(r"[a-z]", str(parameter.get("name", ""))) or parameter["name"] in {"x", "y"}:
        raise ValueError("parameter requiere un nombre de una letra minúscula distinto de x/y.")
    name = parameter["name"]
    lower = _number(parameter.get("min"), "parameter.min")
    upper = _number(parameter.get("max"), "parameter.max")
    initial = _number(parameter.get("value"), "parameter.value")
    if lower >= upper or not lower <= initial <= upper:
        raise ValueError("parameter requiere min < max y value dentro del intervalo.")
    expression, variables = _expression(data.get("expression"), ("x", name))
    domain_left, domain_right = _pair(data.get("domain", [-10, 10]), "domain")
    if domain_left >= domain_right or domain_right-domain_left > 10000:
        raise ValueError("domain debe ser creciente y de hasta 10000 unidades.")
    import sympy as sp
    f = sp.lambdify(variables, expression, modules="math")
    xs = [domain_left+(domain_right-domain_left)*index/200 for index in range(201)]
    values = [lower+(upper-lower)*index/40 for index in range(41)]
    frames = []
    for value in values:
        ys = []
        for x in xs:
            try:
                y = float(f(x, value))
            except (ValueError, ZeroDivisionError, OverflowError, TypeError) as error:
                raise ValueError("La función parametrizada debe ser finita en todo el dominio.") from error
            if not math.isfinite(y) or abs(y) >= 1e8:
                raise ValueError("La función parametrizada debe ser finita en todo el dominio.")
            ys.append(y)
        frames.append(ys)
    selected = min(range(41), key=lambda index: abs(values[index]-initial))
    return {"series": [{"label": str(expression), "x": xs, "y": frames[selected]}],
            "frames": frames, "parameter": {"name": name, "values": values, "selected": selected}}


def _geometry(data):
    items = data.get("elements", [])
    if not isinstance(items, list) or len(items) > 80:
        raise ValueError("elements debe ser una lista de hasta 80 elementos.")
    clean, ids = [], set()
    for item in items:
        if not isinstance(item, dict) or item.get("kind") not in ELEMENTS:
            raise ValueError("Elemento geométrico no soportado.")
        kind = item["kind"]
        item_id = _text(item.get("id"), "element.id", 80)
        if item_id in ids:
            raise ValueError(f"ID geométrico duplicado: {item_id}.")
        ids.add(item_id)
        entry = {"kind": kind, "id": item_id, "label": _text(item.get("label", item_id), "element.label")}
        if kind == "point":
            entry["at"] = _pair(item.get("at"), "point.at")
        elif kind in {"segment", "vector"}:
            entry["from"] = _pair(item.get("from"), f"{kind}.from")
            entry["to"] = _pair(item.get("to"), f"{kind}.to")
        elif kind == "circle":
            entry["center"] = _pair(item.get("center"), "circle.center")
            entry["radius"] = _number(item.get("radius"), "circle.radius")
            if entry["radius"] <= 0:
                raise ValueError("circle.radius debe ser positivo.")
        else:
            points = item.get("points")
            if not isinstance(points, list) or not 3 <= len(points) <= 20:
                raise ValueError("polygon.points requiere de 3 a 20 puntos.")
            entry["points"] = [_pair(point, "polygon.point") for point in points]
        clean.append(entry)
    return {"elements": clean, "bounds": _bounds(data.get("bounds", [-6, 6, 6, -6]))}


def _vector_field(data):
    import sympy as sp
    fx, variables = _expression(data.get("fx"), ("x", "y"))
    fy, _ = _expression(data.get("fy"), ("x", "y"))
    left, top, right, bottom = _bounds(data.get("bounds", [-4, 4, 4, -4]))
    grid = data.get("grid", 9)
    if type(grid) is not int or not 2 <= grid <= 17:
        raise ValueError("grid debe estar entre 2 y 17.")
    f, g = sp.lambdify(variables, fx, modules="math"), sp.lambdify(variables, fy, modules="math")
    vectors = []
    for row in range(grid):
        y = bottom + (top - bottom) * (row + .5) / grid
        for col in range(grid):
            x = left + (right - left) * (col + .5) / grid
            try:
                dx, dy = float(f(x, y)), float(g(x, y))
            except (ValueError, ZeroDivisionError, OverflowError, TypeError):
                continue
            magnitude = math.hypot(dx, dy)
            if math.isfinite(magnitude) and magnitude > 1e-10:
                scale = .36 * min((right-left)/grid, (top-bottom)/grid) / magnitude
                vectors.append({"from": [x, y], "to": [x + dx*scale, y + dy*scale], "magnitude": magnitude})
    return {"bounds": [left, top, right, bottom], "vectors": vectors}


def _circuit_svg(data):
    try:
        import schemdraw
        import schemdraw.elements as elm
    except ImportError as error:
        raise RuntimeError("Schemdraw no está instalado; instalalo para generar circuitos.") from error
    items = data.get("elements")
    if not isinstance(items, list) or not 1 <= len(items) <= 60:
        raise ValueError("Un circuito requiere entre 1 y 60 elementos.")
    classes = {"resistor": elm.Resistor, "capacitor": elm.Capacitor, "inductor": elm.Inductor,
               "battery": elm.Battery, "source": elm.SourceSin, "ground": elm.Ground,
               "diode": elm.Diode, "switch": elm.Switch, "line": elm.Line}
    drawing = schemdraw.Drawing(canvas="svg", show=False)
    for item in items:
        if not isinstance(item, dict) or item.get("kind") not in CIRCUIT_ELEMENTS:
            raise ValueError("Componente de circuito no soportado.")
        element = classes[item["kind"]]()
        direction = item.get("direction", "right")
        if direction not in DIRECTIONS:
            raise ValueError("direction debe ser right, left, up o down.")
        if item["kind"] != "ground":
            element = getattr(element, direction)()
        if "label" in item:
            element = element.label(_text(item["label"], "element.label", 80))
        drawing += element
    return drawing.get_imagedata("svg").decode("utf-8")


def _katex_css():
    css = (ASSETS / "katex" / "katex.min.css").read_text()
    def inline_font(match):
        filename = match.group(1)
        if not re.fullmatch(r"KaTeX_[\w-]+\.woff2", filename):
            return match.group(0)
        font = (ASSETS / "katex" / "fonts" / filename).read_bytes()
        return "url(data:font/woff2;base64," + base64.b64encode(font).decode() + ")"
    css = re.sub(r',url\(fonts/KaTeX_[\w-]+\.(?:woff|ttf)\) format\("(?:woff|truetype)"\)', "", css)
    return re.sub(r"url\(fonts/(KaTeX_[\w-]+\.woff2)\)", inline_font, css)


def _safe_json(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028")


def _has_latex(value):
    if isinstance(value, str):
        return r"\(" in value or "$$" in value
    if isinstance(value, dict):
        return any(_has_latex(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_latex(item) for item in value)
    return False


def _math_scripts():
    return (f'<script>{(ASSETS / "katex" / "katex.min.js").read_text()}</script>'
            f'<script>window.MathJax={{startup:{{typeset:false}},svg:{{fontCache:"local"}}}};</script>'
            f'<script>{(ASSETS / "mathjax" / "tex-svg-v3.js").read_text()}</script>')


def inject_typesetting(path):
    """Add math labels to an existing native HTML artifact only when used."""
    page = path.read_text(encoding="utf-8")
    if '<math' in page or 'katex.min' in page:
        return
    math_js = _JS.split("renderMath();\n", 1)[0] + "renderMath();"
    page = page.replace("default-src 'none'; style-src", "default-src 'none'; script-src 'unsafe-inline'; style-src", 1)
    page = page.replace("</head>", f"<style>{_katex_css()}</style></head>", 1)
    page = page.replace("</body>", _math_scripts() + f"<script>{math_js}</script></body>", 1)
    path.write_text(page, encoding="utf-8")


def render(request, path):
    kind, data = request.type, request.data
    if kind == "function":
        function_data = _parameterized_function(data) if "parameter" in data else {"series": _sample_function(data)}
        series = function_data["series"]
        x_values = [x for item in series for x in item["x"]]
        y_values = sorted(y for frame in function_data.get("frames", [item["y"] for item in series]) for y in frame)
        low = y_values[max(0, int(len(y_values) * .02))]
        high = y_values[min(len(y_values)-1, int(len(y_values) * .98))]
        span = max(high-low, 1.0)
        left, right = min(x_values), max(x_values)
        if left == right:
            left, right = left - 1, right + 1
        default_bounds = [left, high + span*.15, right, low - span*.15]
        payload = {"kind": kind, **function_data, "bounds": _bounds(data.get("bounds", default_bounds))}
    elif kind in {"geometry", "coordinate_system"}:
        payload = {"kind": "geometry", **_geometry(data)}
    elif kind == "vector_field":
        payload = {"kind": kind, **_vector_field(data)}
    elif kind == "circuit":
        payload = {"kind": kind, "svg": _circuit_svg(data)}
    else:
        raise ValueError(f"Tipo matemático no soportado: {kind}.")
    source = request.source
    if source is not None and not isinstance(source, (str, dict)):
        raise ValueError("source debe ser texto u objeto.")
    source_text = source if isinstance(source, str) else " · ".join(str(source[key]) for key in ("title", "chapter", "section", "page") if key in source) if source else ""
    notes = request.notes or []
    needs_latex = _has_latex((request.title, request.subtitle, request.description, notes, source_text, data))
    body = '<div id="board" class="jxgbox" aria-label="Visual matemática interactiva"></div>' if kind != "circuit" else f'<div class="circuit" role="img" aria-label="{escape(request.title)}">{payload["svg"]}</div>'
    if kind == "function" and "parameter" in payload:
        name = payload["parameter"]["name"]
        selected = payload["parameter"]["selected"]
        body += f'<label class="parameter">Parámetro {escape(name)}: <output id="parameter-value">{payload["parameter"]["values"][selected]:.3g}</output><input id="parameter-slider" type="range" min="0" max="40" step="1" value="{selected}" aria-label="Parámetro {escape(name)}"></label>'
    math_js, board_js = _JS.split("renderMath();\n", 1)
    inline_js = (math_js + "renderMath();\n" if needs_latex else "") + (f"const spec={_safe_json(payload)};" + board_js if kind != "circuit" else "")
    page = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(request.title)}</title>
<style>{_CSS}{(ASSETS / "jsxgraph" / "jsxgraph.css").read_text() if kind != "circuit" else ""}{_katex_css() if needs_latex else ""}</style></head><body><main>
<header><span class="eyebrow">Hermes · Visual matemática</span><h1>{escape(request.title)}</h1>{f'<p class="subtitle">{escape(request.subtitle)}</p>' if request.subtitle else ''}{f'<p>{escape(request.description)}</p>' if request.description else ''}</header>
<section class="surface">{body}</section>
{f'<section class="notes"><h2>Qué observar</h2><ul>{"".join(f"<li>{escape(note)}</li>" for note in notes)}</ul></section>' if notes else ''}
{f'<footer>Fuente: {escape(source_text)}</footer>' if source_text else ''}
</main>{f'<script>{(ASSETS / "jsxgraph" / "jsxgraphcore.js").read_text()}</script>' if kind != "circuit" else ""}{_math_scripts() if needs_latex else ""}
{f'<script>{inline_js}</script>' if inline_js else ""}</body></html>'''
    path.write_text(page, encoding="utf-8")


_CSS = """
/* Shared visual guidance: repository DESIGN.md. */
:root{color-scheme:light dark;--bg:#f3f5f8;--paper:#fff;--ink:#18202c;--muted:#586779;--accent:#1d69c9;--border:#dbe2ea}
@media(prefers-color-scheme:dark){:root{--bg:#111923;--paper:#1b2530;--ink:#eef4fb;--muted:#b0c0d1;--accent:#7fb7ff;--border:#344355}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}main{max-width:1120px;margin:0 auto;padding:clamp(16px,4vw,48px)}header{margin-bottom:24px}.eyebrow{font-size:.75rem;letter-spacing:.13em;text-transform:uppercase;color:var(--accent);font-weight:700}h1{font-size:clamp(1.7rem,4vw,2.8rem);line-height:1.16;margin:.4rem 0}h2{font-size:1.1rem}.subtitle{font-size:1.15rem;color:var(--muted)}header p{max-width:70ch}.surface,.notes{background:var(--paper);border:1px solid var(--border);border-radius:18px;padding:clamp(12px,2vw,24px);box-shadow:0 10px 30px #0000000a}.jxgbox{width:100%;height:clamp(340px,62vw,670px);border:0;background:var(--paper);touch-action:none}.parameter{display:block;font-weight:600;margin:12px 6px 0}.parameter input{display:block;width:100%;margin-top:8px;accent-color:var(--accent)}.circuit{background:#fff;border-radius:10px;padding:16px}.circuit svg{display:block;max-width:100%;height:auto;margin:auto}.notes{margin-top:18px}.notes ul{margin-bottom:0}footer{color:var(--muted);margin-top:22px}
"""


_JS = r"""
function renderMath(){
  const walker=document.createTreeWalker(document.querySelector('main'),NodeFilter.SHOW_TEXT);
  const found=[];while(walker.nextNode())if(!walker.currentNode.parentElement.closest('svg,script,style')&&(walker.currentNode.nodeValue.includes('\\(')||walker.currentNode.nodeValue.includes('$$')))found.push(walker.currentNode);
  for(const node of found){const text=node.nodeValue,parts=text.split(/(\\\([^)]*\\\)|\$\$[\s\S]*?\$\$)/g),fragment=document.createDocumentFragment();
    for(const part of parts){if(part.startsWith('\\(')&&part.endsWith('\\)')||part.startsWith('$$')&&part.endsWith('$$')){
      const tex=part.slice(2,-2),span=document.createElement('span');
      try{katex.render(tex,span,{throwOnError:true,output:'htmlAndMathml'});}catch(error){span.textContent=tex;MathJax.startup.promise.then(()=>MathJax.tex2svgPromise(tex,{display:part.startsWith('$$')})).then(svg=>span.replaceChildren(svg)).catch(()=>{});}
      fragment.append(span);
    }else fragment.append(document.createTextNode(part));}node.replaceWith(fragment);}
}
renderMath();
if(spec.kind!=='circuit'){
  try{
    const board=JXG.JSXGraph.initBoard('board',{boundingbox:spec.bounds||[-10,10,10,-10],axis:true,showNavigation:true,showCopyright:false,keepAspectRatio:spec.kind!=='function',resize:{enabled:true,throttle:10}});
    const ink='#1d69c9';
    function point(xy,label,visible=true){return board.create('point',xy,{name:label||'',size:3,visible:visible,fixed:false,strokeColor:ink,fillColor:ink});}
    function segment(a,b,label,arrow=false){board.create('line',[a,b],{name:label||'',straightFirst:false,straightLast:false,lastArrow:arrow,strokeWidth:2.5,strokeColor:ink,fixed:true});}
    if(spec.kind==='function'){
      let curves=spec.series.map(series=>board.create('curve',[series.x,series.y],{name:series.label,strokeColor:ink,strokeWidth:3,fixed:true}));
      if(spec.parameter){
        const slider=document.getElementById('parameter-slider'),value=document.getElementById('parameter-value');
        slider.addEventListener('input',()=>{
          const index=Number(slider.value);
          for(const curve of curves)board.removeObject(curve);
          curves=[board.create('curve',[spec.series[0].x,spec.frames[index]],{name:spec.series[0].label,strokeColor:ink,strokeWidth:3,fixed:true})];
          value.textContent=Number(spec.parameter.values[index]).toPrecision(3);
        });
      }
    }
    if(spec.kind==='vector_field')for(const v of spec.vectors)segment(v.from,v.to,'',true);
    if(spec.kind==='geometry')for(const el of spec.elements){
      if(el.kind==='point')point(el.at,el.label);
      if(el.kind==='segment'||el.kind==='vector')segment(el.from,el.to,el.label,el.kind==='vector');
      if(el.kind==='circle')board.create('circle',[el.center,el.radius],{name:el.label,strokeColor:ink,strokeWidth:2.5,fixed:true});
      if(el.kind==='polygon')board.create('polygon',el.points,{name:el.label,fillColor:ink,fillOpacity:.12,strokeColor:ink,fixed:true});
    }
  }catch(error){document.getElementById('board').textContent='No se pudo mostrar la visual interactiva: '+error.message;}
}
"""
