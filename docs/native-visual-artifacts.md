# Native Visual Artifact Engine V1

Para `flow`, `process`, `pipeline` y `architecture`, el router valida una
especificación semántica, calcula niveles de un DAG acíclico y genera un HTML
standalone. Los nodos son tarjetas HTML; un SVG inline dibuja conectores y
labels según la posición medida de cada tarjeta. No hay posiciones absolutas en
la entrada ni dependencias externas. JavaScript del proyecto solo alinea las
conexiones en resize y resalta nodos/conexiones al enfocar una tarjeta.

El wrapper de Hermes lleva `type`, `title` y `data`; dentro de `data` se pasan
`nodes`, `edges` y, opcionalmente, `groups`, `annotations`, `notes` y `source`:

```json
{
  "type": "flow",
  "title": "Source Engine",
  "data": {
    "nodes": [
      {"id": "pdf", "title": "PDF original", "subtitle": "materials/", "role": "input"},
      {"id": "store", "title": "SQLite", "subtitle": "sources + source_pages", "role": "storage"}
    ],
    "edges": [{"from": "pdf", "to": "store", "label": "ingestar", "style": "normal"}]
  },
  "source": {"title": "Guía", "chapter": "2", "section": "2.1", "page": 8},
  "notes": ["Los originales no se copian a SQLite."]
}
```

Roles: `input`, `process`, `storage`, `decision`, `output`, `agent`, `source`,
`tool`. Estilos de conexión: `normal`, `dashed`, `emphasis`. Los labels y
metadatos son texto escapado, nunca HTML. Los ejemplos completos son
[`source-engine.visual.json`](source-engine.visual.json) y
[`hermes-architecture.visual.json`](hermes-architecture.visual.json).

Desde la raíz del repositorio:

```bash
python3 scripts/visual_router.py < docs/source-engine.visual.json
```

Abrí el `presentation_artifact` de la respuesta en Firefox. También podés abrir
el archivo HTML directamente, sin servidor, internet o build step. Desde Hermes
Desktop, confía el repositorio con `hermes skills trust "$PWD"`, abre una sesión
desde esa raíz y pide: “Mostrame visualmente cómo funciona nuestro Source
Engine”. La skill `visual-explain` describe la salida y conserva el artifact.

Mermaid se guarda como `.mmd` export técnico por defecto; con
`"output_format":"svg"` también intenta crear un SVG vía `mmdc`. El HTML nativo
sigue siendo el artifact principal. Tree/graph/DAG continúan con Graphviz;
function/numeric data/study metrics continúan con Matplotlib. No se removieron
el presenter previo ni esos renderers.

V1 admite flows dirigidos acíclicos de hasta 100 nodos. En pantallas anchas el
flujo es horizontal; hasta 1100 px se apila verticalmente. No implementa ciclos,
charts, física, edición, zoom ni simulaciones. No hay dependencias nuevas.
