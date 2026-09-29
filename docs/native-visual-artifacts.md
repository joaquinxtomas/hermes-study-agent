# Native Visual Artifact Engine V2

> **Legacy backend reference.** New diagram requests use Hermes
> `concept-diagrams` (`~/.hermes/skills/creative/concept-diagrams`).
> This document records the existing flow/architecture renderer contracts;
> do not add a parallel authoring skill.

Para `flow`, `process` y `pipeline`, el router valida un spec semántico y genera
HTML standalone con cards HTML y conexiones SVG ortogonales. Para
`architecture`, genera un mapa HTML standalone con layout Graphviz.
`roadmap` es una familia editorial separada; ver
[Roadmap Visual Engine V1](roadmap-visual-artifacts.md).
Funciona offline, sin servidor, build ni dependencias de navegador externas.
El mismo documento conserva nodos y relaciones al cambiar su distribución.

## Spec y responsabilidades

El wrapper lleva `type`, `title`, `data` y, opcionalmente, `subtitle`,
`description`, `notes`, `source`, `subject`, `topic`, `output_format`.
`data` contiene `nodes`, `edges`, y opcionalmente `groups` y `annotations`.
`source` nativo admite únicamente `title`, `chapter`, `section`, `page`.
`subject` y `topic` se aceptan en el wrapper pero no se muestran automáticamente
en el HTML nativo; incluir contexto visible en subtitle/notes cuando corresponda.

```json
{
  "type": "flow",
  "title": "Source Engine",
  "output_format": "html",
  "data": {
    "nodes": [
      {"id": "pdf", "title": "PDF original", "role": "source"},
      {"id": "extract", "title": "Extraer páginas", "role": "process"},
      {"id": "store", "title": "SQLite", "role": "storage"}
    ],
    "edges": [{"from": "pdf", "to": "extract"}, {"from": "extract", "to": "store"}],
    "groups": [{"title": "Ingesta", "nodes": ["pdf", "extract", "store"]}]
  },
  "notes": ["Los originales permanecen fuera de SQLite."]
}
```

Roles: `input`, `process`, `storage`, `decision`, `output`, `agent`, `source`,
`tool`. Edges: `normal`, `dashed`, `emphasis`. Descripción y metadata simple
por nodo son opcionales. Todo texto se escapa; la entrada no contiene HTML,
CSS, SVG, coordenadas ni anchors.

- `native_visual_spec.py`: schema y validación; máximo 100 nodos y 200 edges,
  IDs únicos y extremos existentes. Los tres tipos de flow son acíclicos;
  `architecture` admite ciclos.
- `layout_flow.py`: análisis, niveles, orden topológico con preferencia de
  grupo, filas, slots de nodos y lados de los anchors para cada distribución.
- `render_native_artifact.py`: flow/process/pipeline con HTML/CSS, medición
  real, elección de plan, anchors, rutas SVG e interacción.
- `render_architecture_artifact.py`: architecture con Graphviz para el layout,
  SVG embebido en HTML, fichas de componentes y relaciones completas.
- Hermes `concept-diagrams`: punto de entrada activo; este renderer es un backend legacy.
- `visual_presentation.py`: clasificación de complejidad y preferencia inline/expanded;
  no abre herramientas ni altera el HTML.

## Distribución por contenedor

Esta sección describe el renderer de `flow`, `process` y `pipeline`.

`ResizeObserver` observa la composición y el grid, también cuando cambia la
altura por abrir detalles. Los cálculos se agrupan por animation frame. CSS
Container Queries adaptan tipografía; el resize de ventana solo es fallback
para navegadores sin ResizeObserver. No se lee el tamaño del monitor ni el
viewport de la aplicación anfitriona. Contenedores ocultos/desmontados no se
intentan dibujar hasta que vuelven a tener ancho.

Las cards tienen ancho mínimo 208 px, objetivo 248 px y máximo 320 px. En
Narrow se permite un ancho menor si el contenedor es todavía más estrecho.
Se reservan 28 px de margen lateral y 48 px entre columnas. El número de
columnas depende del espacio restante, profundidad y tamaño del grafo; los
planes admiten hasta seis columnas en una composición de máximo 1800 px.

| Modo | Selección sobre el ancho medido de la composición | Distribución |
| --- | --- | --- |
| Narrow | No caben dos cards de ancho mínimo | Una columna; conexiones verticales |
| Compact | Caben dos o más cards, sin cumplir Wide | Cadenas por filas; ramas del mismo nivel juntas cuando caben |
| Wide | Desde 1050 px y espacio para cuatro columnas | Niveles de izquierda a derecha dentro de lanes; bandas adicionales si hace falta |

El cambio Narrow/Compact se deriva del mínimo de card y los espacios: alrededor
de 520 px de composición, no de 1100 px de ventana. Márgenes del documento,
bordes y scrollbars del host se descuentan al medir. Un iframe de 650–900 px
puede utilizar dos o tres columnas. El grafo conserva su topología por encima
del aprovechamiento simétrico de huecos.

Se calculan `node_count`, `edge_count`, `number_of_levels`,
`max_nodes_per_level`, `branching_factor` (máximo de sucesores distintos),
`number_of_groups`, `longest_path` (aristas) y densidad small/medium/large.
La densidad decide si los detalles secundarios aparecen plegados.

Los grupos influyen en el orden y crean lanes visibles. Si las dependencias
obligan a volver a un grupo, se generan segmentos con el mismo título en lugar
de invertir una relación. El primer grupo que contiene un nodo controla su
ubicación. Sin grupos se usan niveles y topología, sin inferir significado
académico. El orden de DOM también sigue el orden semántico para teclado.

## Conectores e interacción

Los anchors `top`, `right`, `bottom`, `left` se asignan según modo y slots.
Las coordenadas finales se obtienen de los rectángulos HTML después del layout.
Las rutas buscan corredores horizontales/verticales libres de cards y títulos
de lanes. Los puertos distribuidos y pequeños offsets distinguen edges
paralelas; se penalizan corredores ya usados. SVG queda sobre los fondos y
cards, y las puntas terminan en los bordes.

El algoritmo es una heurística determinística para estos DAGs pequeños, no un
optimizador global de cruces. Pueden compartirse tramos en casos densos.
Si una conexión no encuentra ruta, se informa en consola y en
`data-routing-errors`; su relación sigue en la lista textual del documento.

Hover/focus atenúa nodos y edges no relacionados directamente. En diagramas
medianos/grandes, `Detalles` permite abrir descripción/metadata con mouse,
teclado o touch; la fila crece y se recalculan conexiones. Las cards de una
fila comparten altura. Los labels que no caben sin colisiones se omiten del
canvas y se conservan completos en `Relaciones del diagrama`. No se trunca el
contenido semántico.

## Uso, exports y límites

```bash
python3 scripts/visual_router.py < docs/source-engine.visual.json
python3 scripts/visual_router.py < tests/fixtures/architecture/study_overview.json
```

Abrir el `presentation_artifact` devuelto. Los archivos viven en
`diagrams/generated/` y reciben sufijos para evitar sobrescrituras.
`output_format: html` es el default y produce solo HTML; `source` agrega `.mmd`;
`svg` intenta además la exportación Mermaid con `mmdc`. Mermaid sigue siendo
export/fallback para los tipos nativos. `sequence` usa Mermaid;
`tree`/`graph`/`dag`, Graphviz; funciones y geometría usan JSXGraph con cálculo
SymPy, circuitos usan Schemdraw, y datos numéricos/métricas usan Matplotlib.
El router no reintenta automáticamente con otro renderer si falla el nativo.
Graphviz `dot` es necesario al generar `architecture`; el HTML generado se
abre offline sin Graphviz.

## Arquitecturas: vista general legible

Una arquitectura muestra normalmente 6–8 componentes y sus relaciones
principales. El renderer impone un máximo de 12 nodos y 18 edges por artifact:
si el spec lo supera, pide un mapa general y vistas separadas por subsistema.
No omite nodos silenciosamente. Un mismo componente conserva una tarjeta;
el schema permite relaciones recíprocas y ciclos. Así, Hermes puede consultar
Source Engine y recibir evidencia sin aparecer duplicado. SQLite puede mostrar
en una sola tarjeta que persiste varios dominios.

Graphviz calcula nodos, flechas y rutas ortogonales. El HTML incluye dos
distribuciones: horizontal para contenedores amplios y vertical para paneles
compactos. En menos de 520 px muestra tarjetas con enlaces a los componentes
relacionados, sin comprimir un SVG hasta hacerlo ilegible. Las etiquetas
completas de las relaciones están en una lista accesible; cada nodo del SVG
enlaza a su ficha HTML. Los `groups` se presentan como resúmenes breves bajo
el mapa y no fuerzan franjas repetidas. No se necesita JavaScript ni red para
abrir el artifact.

El diseño toma como referencia la [skill Architecture Diagram de Hermes](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/skills/bundled/creative/creative-architecture-diagram.md):
colores por función y un documento con mapa y contexto. Su plantilla de
posiciones manuales no se usa como renderer porque requiere ancho fijo.

## Presentación en Hermes Desktop (V2.1)

Además de la ruta HTML, el router devuelve `visual_type`, métricas del grafo,
`complexity`, `preferred_presentation` y `presentation_reason`. La política
usa nodos, edges, niveles, ancho máximo de nivel, ramificación y grupos.
En arquitecturas con ciclos, niveles, camino máximo y ancho por nivel se
reportan como 0 porque no hay orden topológico; la política usa las demás
métricas.
Estos umbrales son independientes de `density`, que el renderer usa para plegar
detalles de cards.

| Complejidad | Criterio inicial (basta uno) | Presentación |
| --- | --- | --- |
| Large | ≥16 nodos, ≥24 edges, ≥12 niveles, ≥6 nodos por nivel, ramificación ≥5 o ≥6 grupos | Expanded |
| Medium | ≥9 nodos, ≥11 edges, ≥8 niveles, ≥4 nodos por nivel, ramificación ≥3 o ≥3 grupos | Inline, salvo densidad alta |
| Small | Ninguno de los anteriores | Inline |

La presentación expandida se reserva para `large` o diagramas medianos muy
densos (≥12 edges y al menos dos edges por nodo). Tener grupos o ramas, por sí
solo, no envía un artifact mediano al panel lateral.

Se ajustan en `scripts/visual_presentation.py`. Una arquitectura mediana con
3 grupos permanece inline; un pipeline lineal de 10 nodos también. En Desktop,
artifacts pequeños y medianos se muestran con el directive nativo
`::preview{file="/absolute/path.html"}`; los expanded abren una vez
`desktop_preview(action=open)` si la herramienta está disponible. La ubicación
de presentación no cambia spec, renderer, layout ni archivo. Si falta el
preview, el HTML se entrega normalmente. CLI y ejecución directa del router no
dependen de Hermes Desktop; Python solo devuelve la preferencia y no abre UI.

La presentación requiere que el agente siga la skill; los casos expanded
requieren la herramienta `desktop_preview` del toolset `desktop_ui`. Una
invocación directa de `visual_router.py` solo genera el artifact y su metadata.
La ruta local `.html` se renderiza en el webview del panel. Para un archivo
remoto que Hermes reciba como HTML aislado, la política del host puede impedir
JavaScript; se conserva el enlace al archivo y el fallback textual de cards y
relaciones. El éxito del tool confirma el envío del evento, no garantiza que
un panel de una sesión fuera de pantalla llegue a mostrarse.

Prueba manual en Hermes Desktop, desde la raíz del repo y con la skill cargada:

1. «Mostrame visualmente Source → Ingest → Index → Search → Answer.»
   Esperado: `small`, `inline`, sin llamada a `desktop_preview`.
2. «Mostrame cómo se conectan Source Engine, Hermes, Knowledge Tracking,
   Study Sessions, SQLite y Study Pack. Agrupalos por función.»
   Esperado: arquitectura mediana inline, sin `desktop_preview`; verificar que
   el artifact integrado muestra nodos y conectores.
3. «Mostrame la arquitectura completa del flujo de estudio de Física,
   incluyendo fuentes, ingesta, retrieval, Hermes, sesiones, dudas, evidencia,
   Knowledge Tracking, persistencia y exportación.»
   Esperado: `large`, un solo open y explicación breve en chat.

Repetir el caso mediano en CLI: debe devolver ruta HTML sin requerir el tool.
La apertura automática por turno requiere una sesión real de Hermes Desktop;
los tests Python cubren política, metadata y generación sin preview, pero no
simulan una llamada del agente al tool del host.

Los ciclos son exclusivos de `architecture`; los flows siguen siendo DAGs.
El renderer de flow no incluye editor, drag-and-drop ni charts. Las visuales
matemáticas y circuitos tienen una familia nativa propia; ver
[Math and Physics Artifacts](math-visual-artifacts.md).
En `flow`, `process` y `pipeline`, JavaScript es necesario para layout y conectores.
Sin scripts quedan cards y
relaciones textuales, con aviso visible. Agregar `?debug` al URL muestra ancho
real, modo, nodos, niveles y densidad. En un iframe `srcdoc`, esa query no se
hereda del host; el inspector puede mostrar el elemento `.debug`.

## Validación reproducible

Fixtures del renderer V2 anterior en `tests/fixtures/native_visual/`. El gate
`check_native_visual_browser.cjs` llama directamente al renderer de flows para
regresión geométrica; los fixtures C y D son casos históricos de arquitectura
y exceden el límite del nuevo routing de `architecture`:

| Fixture | Nodos | Caso |
| --- | --- | --- |
| A | 5 | Pipeline lineal |
| B | 9 | Bifurcación de tres ramas y merge |
| C | 14 | Arquitectura histórica en cuatro grupos |
| D | 19 | Arquitectura histórica del flujo de estudio |
| E | 50 | Stress: 81 edges |

El mapa de arquitectura está en
`tests/fixtures/architecture/study_overview.json`: 8 nodos, 11 relaciones,
un ciclo y tres grupos. El gate de navegador para ese renderer comprueba
390, 520, 742, 900, 1366 y 1600 px, ausencia de scroll horizontal, contenido
semántico completo y navegación desde el mapa a las fichas.

Son datos sintéticos. Los flujos conceptuales de Study Pack/NotebookLM no
certifican que esas integraciones estén implementadas.

```bash
python3 -m unittest discover -s tests -v
# Playwright + navegador instalados únicamente en el entorno de pruebas:
node tests/check_native_visual_browser.cjs diagrams/generated/v2-validation
node tests/check_architecture_browser.cjs diagrams/generated/architecture-validation
# Opcional: usar una instalación existente sin agregar dependencias al proyecto:
# PLAYWRIGHT_MODULE=/ruta/playwright BROWSER_EXECUTABLE=/ruta/chromium node tests/check_native_visual_browser.cjs
```

El gate genera HTML, capturas y `report.json` en 390, 520, 650, 768, 900, 1100,
1366 y 1600 px; comprueba geometría, ancho de cards, colisiones de edges/labels,
scroll horizontal, resize del contenedor, foco, detalles e iframe aislado.
`BROWSER=firefox` permite ejecutar con el Firefox de Playwright instalado.
Las capturas deben revisarse visualmente además de las aserciones geométricas.
La validación del host real y sus límites se documenta por separado en
[Hermes y Native V2](native-visual-hermes-validation.md).
