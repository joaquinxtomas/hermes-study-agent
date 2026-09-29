# Roadmap Visual Engine V1

> **Legacy backend reference.** Roadmap requests use Hermes
> `concept-diagrams`, the single active diagramming skill. Keep this page for
> renderer/schema details.

`roadmap` presenta una ruta de aprendizaje o progreso: etapas ordenadas,
un camino principal y ramas subordinadas. No usa el layout de `architecture` ni
interpreta los conceptos como un grafo arbitrario.

## Spec semántica

El router acepta la estructura dentro de `data`, junto a los campos habituales
del wrapper (`type`, `title`, `subtitle`, `description`, `notes`, `source`). Para
`roadmap` también admite `sections`, `nodes`, `main_path` y `branches` en el
nivel superior, como en el ejemplo del plan.

```json
{
  "type": "roadmap",
  "title": "Fundamentos de programación",
  "data": {
    "sections": [
      {"id": "base", "title": "Bases", "order": 1},
      {"id": "solve", "title": "Resolver problemas", "order": 2}
    ],
    "nodes": [
      {"id": "variables", "title": "Variables", "section": "base", "importance": "core"},
      {"id": "functions", "title": "Funciones", "section": "base", "importance": "core"},
      {"id": "structures", "title": "Estructuras", "section": "solve", "importance": "core"},
      {"id": "algorithms", "title": "Algoritmos", "section": "solve", "importance": "core"},
      {"id": "visualize", "title": "Visualizar pasos", "section": "solve", "importance": "optional"}
    ],
    "main_path": ["variables", "functions", "structures", "algorithms"],
    "branches": [{"from": "algorithms", "nodes": ["visualize"], "kind": "optional"}]
  }
}
```

`importance` admite `core`, `recommended`, `optional` y `specialization`.
`branch.kind` admite los tres últimos. Cada nodo aparece una sola vez, en
`main_path` o en una rama; cada section contiene al menos un nodo del camino
principal. En V1, una rama sale de un nodo del camino principal y permanece
en su section. `rejoin`, si existe, apunta a un nodo posterior de ese mismo
camino y section. Esto evita rutas ambiguas que el layout editorial no puede
expresar bien. El schema admite 1–50 nodos y 1–12 sections; para una ruta más
grande hay que dividirla en overview y etapas, sin omitir contenido en silencio.

`source` admite `title`, `chapter`, `section` y `page` cuando los aportó una
consulta grounded. El renderer no recupera fuentes ni inventa un programa.

## Layout y presentación

`roadmap_visual_spec.py` valida. `layout_roadmap.py` ordena sections y coloca
el camino principal en filas; fija el orden recomendado, opcional,
especialización de las ramas. `render_roadmap_artifact.py` crea HTML standalone
con cinco composiciones predefinidas que cubren tres modos: Narrow (1 columna),
Compact (2–3), Wide (4–5). CSS Container Queries eligen la composición según
el ancho recibido; `ResizeObserver` redibuja los conectores ortogonales al
cambiar el panel o abrir detalles. El main path queda destacado con cards de
mayor peso. Las ramas se anidan bajo su origen. El SVG usa un bus vertical para
fan-out y canales horizontales para retornos y fan-in; los textos permanecen
en HTML. `description` se abre con `<details>`. Hover y foco resaltan el nodo y
sus vecinos inmediatos. Todo abre offline, sin servidor, Graphviz, React ni
fuentes externas.

La política de presentación reutiliza `visual_presentation.py`: pequeño y
mediano → inline; grande o muy denso → expanded. La skill unificada abre
`desktop_preview` una sola vez si está disponible; el router Python solo
devuelve la preferencia y el HTML. CLI entrega el archivo normalmente.

`roadmap` no exporta Mermaid en V1: la gramática de sections y ramas perdería
jerarquía si se degradara automáticamente a edges de un grafo. El único
`output_format` aceptado es `html`.

## Validación

Fixtures en `tests/fixtures/roadmap/`: ruta simple (6 nodos), Electrostática
(11), Data Engineering (22), ramas y rejoin (17), carga (40). Son ejemplos
conceptuales para verificar presentación; no sustituyen el programa de una
materia ni una fuente académica.

```bash
python3 scripts/visual_router.py < tests/fixtures/roadmap/c_data_engineering.json
python3 -m unittest discover -s tests -v
node tests/check_roadmap_browser.cjs /tmp/roadmap-browser
```

El gate de navegador es opcional y requiere Playwright/Chromium de desarrollo.
Mide 390, 520, 650, 768, 900, 1100, 1366 y 1600 px en el fixture principal;
además prueba los otros cuatro fixtures, cambio de ancho sin recarga,
clipping, solapamiento y cruces de conectores con cards. Revisar las capturas
además de las aserciones geométricas.

La apertura automática del panel y su ancho real deben comprobarse en una
sesión de Hermes Desktop con `desktop_preview` disponible. Fuera de esa sesión
no puede verificarse que el host muestre el panel, aunque el HTML y la política
se prueben por separado.
