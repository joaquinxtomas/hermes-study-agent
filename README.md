# Hermes Study Agent

Núcleo local para materias, dudas, sesiones y materiales de estudio. Hermes
coordina las skills; SQLite y los originales locales conservan los datos.

## Arquitectura

```text
Hermes source-query skill
    ↓ terminal → scripts/source_cli.py
scripts/source_ingest.py / scripts/source_search.py
    ↓                         ↓
materials/             scripts/source_store.py
                              ↓ sqlite3
             storage/study.db (metadata + texto por página)
```

El motor visual local agrega esta ruta independiente:

```text
Hermes concept-diagrams skill → standalone HTML preview in chat
Project visual_router.py      → compatibility renderers → diagrams/generated/
```

Las skills de este repositorio se exponen mediante `.hermes/skills`, enlazado a
`skills/`. En Hermes, confía en el repositorio una vez:

```bash
hermes skills trust "$PWD"
hermes skills list --source local
```

## Base de datos

```bash
python3 scripts/init_db.py
```

El inicializador aplica las migraciones pendientes en orden. Usa el
`PRAGMA user_version` nativo de SQLite para recordar la versión; las migraciones
se aplican dentro de una transacción y se pueden volver a ejecutar sin repetir
cambios ya aplicados.

## Materiales y fuentes

Organiza los originales bajo `materials/`; la estructura sugerida está en
[materials/README.md](materials/README.md). Los originales son inmutables. La
base guarda metadatos y texto extraído por página, no copia los archivos.

1. Coloca el archivo en `materials/`.
2. Registra la materia y, opcionalmente, el topic si aún no existen:

   ```bash
   python3 scripts/study_cli.py subjects list
   python3 scripts/source_cli.py add-topic --subject "Física II" --name "Flujo eléctrico"
   ```

3. Registra la fuente con su path relativo al repositorio y el ID de topic si
   corresponde:

   ```bash
   python3 scripts/source_cli.py register-source \
     --subject "Física II" --topic-id 1 \
     --title "Guía Unidad 2" --type guide \
     --path materials/fisica/guides/unidad-2.pdf
   ```

4. Ingiere el PDF usando el ID devuelto al registrarlo:

   ```bash
   python3 scripts/source_cli.py ingest-source 1
   ```

5. Busca lexicalmente; los resultados incluyen título, página, fragmento y
   relevancia:

   ```bash
   python3 scripts/source_cli.py search-source "ejercicio 8" --source-id 1
   ```

También se puede listar y filtrar fuentes con `list-sources`. Los archivos
registrados deben vivir dentro de `materials/`; se rechazan paths que salgan de
ese directorio. Reingestar reemplaza las páginas anteriores de esa fuente en
una transacción.

### Requisito para PDFs

No se agregaron dependencias Python. La extracción usa `pdftotext`, incluido en
Poppler; comprueba su disponibilidad con `command -v pdftotext`. La extracción
conserva el número de página. PDFs escaneados requieren OCR, que no está
implementado.

## Sesiones con temporizador

Una sesión puede contener varios bloques de timer secuenciales. Pausar o detener
un bloque no cierra la sesión; iniciar otra sesión guarda un checkpoint y cierra
la anterior. Inicializa o actualiza la base después de instalar el cambio con
`python3 scripts/init_db.py`. En Hermes, `study-fastpath` ejecuta acciones en el
Study Core y ofrece `/study-timer 25`, `/study-timer pausa`,
`/study-timer reanudar`, `/study-timer detener` y `/study-timer estado`, sin una
vuelta por el modelo.

En Hermes Desktop, habilita también la parte **Study Timer** en
Capabilities → Plugins. El panel se abre al iniciar un timer, permanece en el
workspace y muestra la cuenta regresiva en el status bar. Sus acciones se
guardan en SQLite; la actualización por segundo es visual. La notificación de
fin solo se muestra mientras Desktop está abierto. Un timer local no programa
cron; los recordatorios con fecha u hora son una acción separada.
Fuera de Hermes, el CLI conserva las operaciones locales:

```bash
python3 scripts/study_cli.py session start "Física II" --target-minutes 75 --hard-limit-minutes 90
python3 scripts/study_cli.py session timer status SESSION_ID
python3 scripts/study_cli.py session pause SESSION_ID
python3 scripts/study_cli.py session resume SESSION_ID
```

Para habilitar el fast path en otra instalación local de Hermes, coloca o
enlaza `hermes_plugins/study_fastpath` en `~/.hermes/plugins/study-fastpath`,
ejecuta `hermes plugins enable study-fastpath` y
`hermes tools enable project --platform cli`, y abre una sesión nueva. Habilita
la parte Desktop desde Capabilities → Plugins y vuelve a escanear plugins si no
aparece. El toolset `project` expone las acciones sin pasar por `tool_search`.

Cuando se procesa el límite máximo, Study Core pausa la sesión y guarda un
checkpoint basado en el último contexto persistido. Actualiza ese checkpoint
desde Hermes cuando cambie el tema, fuente o ejercicio; un callback no puede ver
la conversación activa. El tiempo de estudio nunca crea evidencia de
aprendizaje; el tracking solo registra respuestas, ejercicios y revisiones
observables vinculados con `--session-id`.

## Consultar desde Hermes

Desde Hermes Desktop, abre una sesión con el directorio de trabajo en la raíz
del repositorio y pregunta, por ejemplo:

> Buscá en la guía Unidad 2 dónde aparece el ejercicio 8.

La skill `source-query` localiza la fuente registrada, busca en sus páginas y
responde con citas de título y página. Para una consulta “usando únicamente
esta guía”, la skill limita la búsqueda a esa fuente y reconoce cuando los
fragmentos no alcanzan para responder. El texto que no provenga de la fuente se
separa como contexto general.

La búsqueda actual recorre las páginas locales, normaliza mayúsculas y tildes y
ordena por cobertura/frecuencia de términos, con una bonificación por frase
exacta. Es lexical; no usa embeddings, OCR ni proveedores externos.

## Visual diagrams

La única skill activa para diagramas y explicaciones visuales es Hermes
`concept-diagrams` (`~/.hermes/skills/creative/concept-diagrams`). Sus
artifacts pequeños y medianos se previsualizan inline; los grandes o densos
pueden abrirse en el panel expandido. `DESIGN.md` guía los renderers del
proyecto. Los renderers especializados siguen como backends de compatibilidad:

- `flow`, `process`, `pipeline` → Native Visual Artifact Engine:
  layout DAG por contenedor (Wide/Compact/Narrow), tarjetas HTML y conectores SVG ortogonales.
- `architecture` → mapa HTML con layout Graphviz, una vista general de hasta 12
  componentes y detalles accesibles debajo. Admite relaciones recíprocas.
  El spec expresa significado, nunca coordenadas; Mermaid queda como export/fallback.
- `roadmap` → ruta de aprendizaje HTML con sections, main path y ramas;
  presentación editorial responsive, hasta 50 conceptos. No requiere Graphviz.
- `sequence` → fuente Mermaid `.mmd`;
- `tree`, `graph`, `dag` → fuente Graphviz `.dot`;
- `function`, `geometry`, `coordinate_system`, `vector_field` → HTML nativo interactivo con JSXGraph; SymPy calcula funciones y campos.
- `circuit` → esquema SVG de Schemdraw dentro de HTML nativo.
- `numeric_data`, `study_metrics` → imagen PNG con Matplotlib y wrapper HTML.

Los artifacts se guardan en `diagrams/generated/` y los nombres repetidos
reciben un sufijo, sin sobrescribir los anteriores. Para generar un HTML nativo:

```bash
printf '%s\n' '{"type":"flow","title":"Consulta","data":{"nodes":[{"id":"A","title":"Usuario","role":"input"},{"id":"B","title":"Hermes","role":"agent"}],"edges":[{"from":"A","to":"B","label":"pregunta"}]}}' \
  | python3 scripts/visual_router.py
```

Ejemplos completos: `docs/source-engine.visual.json` y
`docs/hermes-architecture.visual.json`. Abrí el `presentation_artifact`
devuelto directamente en Firefox. Mermaid CLI (`mmdc`) puede crear un SVG de
exportación si se solicita; si falla, conserva la fuente. El renderer de flows
funciona offline y usa JavaScript vanilla para medir el contenedor, elegir la distribución y
trazar conectores; foco y hover resaltan las relaciones directas.
Graphviz (`dot`) distribuye arquitecturas y permite PNG en el renderer de
grafos. Mermaid CLI es opcional; `dot` se necesita para generar arquitecturas.
Los gráficos numéricos previos requieren Matplotlib. Las visuales matemáticas
requieren SymPy y los circuitos Schemdraw al generar el artifact. JSXGraph,
KaTeX y MathJax se incorporan al HTML cuando hacen falta; se abre offline.
Las expresiones pasan por una gramática matemática restringida.

## Auditoría de latencia

La instrumentación opt-in del CLI y el renderer, junto con el estado de las
mediciones end-to-end pendientes de Hermes, está documentada en
[docs/latency-audit-v1.md](docs/latency-audit-v1.md). Para analizar registros
locales: `python3 scripts/analyze_latency.py`.

Desde Hermes Desktop, confía el repositorio con `hermes skills trust "$PWD"`,
abre Hermes desde la raíz y pide una explicación visual. Artifacts pequeños y
medianos se muestran inline; solo los grandes o muy densos prefieren el panel
lateral. En CLI o si `desktop_preview` no está disponible, se devuelve la ruta
del HTML. `study-concept-diagrams`, `visual-explain` y
`native-visual-artifacts` se conservan como punteros legacy, no como rutas
alternativas.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

El test de PDF genera un documento de dos páginas en una carpeta temporal y se
omite si `pdftotext` no está instalado. Los tests de arquitectura que necesitan
Graphviz se omiten si `dot` no está instalado; el caso de PNG verifica el error claro cuando Matplotlib
no está instalado. Los demás tests usan bases SQLite temporales y no dependen de
materiales personales.

Los backends especializados cubren flows, procesos, pipelines, arquitecturas,
roadmaps y visuales matemáticas. Las
arquitecturas usan Graphviz y admiten ciclos. Roadmap V1 cubre rutas de
aprendizaje con camino principal, etapas y ramas. Árboles y grafos generales
usan Graphviz. Los demás renderers siguen disponibles
para exportación, fallback y compatibilidad. Detalles, schema y prueba manual:
[Native Visual Artifact Engine V2](docs/native-visual-artifacts.md) y
[Roadmap Visual Engine V1](docs/roadmap-visual-artifacts.md),
[Math and Physics Artifacts](docs/math-visual-artifacts.md).


## Knowledge Tracking V1

Knowledge Tracking registra evidencia por topic y dimension. Los estados admitidos son `not_seen`, `introduced`, `understood`, `practicing`, `independent` y `needs_review`; las dimensiones son `conceptual`, `procedural`, `independent_problem_solving` y `retention`. No usa porcentajes ni scores: cada estado representa una inferencia deterministica basada unicamente en evidencia guardada en SQLite, no una medida absoluta de capacidad.

Tipos de evidencia: `explanation`, `guided_exercise`, `independent_exercise`, `exam_question`, `doubt`, `review` y `self_assessment`. Resultados: `correct`, `partially_correct`, `incorrect`, `completed` y `observed`. Una explicacion correcta mejora lo conceptual; un ejercicio guiado puede llevar lo procedural a `practicing`, sin demostrar independencia; un ejercicio independiente correcto puede llevar la dimension correspondiente a `independent`; un error independiente o de examen lleva a `needs_review` (desde `independent`, baja a `practicing` conservadoramente). Un repaso correcto puede mejorar retencion. Registrar una duda no degrada estados.

Los errores observables recurrentes se guardan como misconceptions. Una descripcion identica por topic incrementa ocurrencias; V1 no hace deduplicacion semantica.

Ejemplos desde la raiz:

```bash
python3 scripts/study_cli.py knowledge topics list --subject "Fisica II"
python3 scripts/study_cli.py knowledge evidence add 4 procedural guided_exercise correct "Resolvio el ejercicio con una pista" --session-id 12
python3 scripts/study_cli.py knowledge status show 4
python3 scripts/study_cli.py knowledge status list independent_problem_solving needs_review
python3 scripts/study_cli.py knowledge misconceptions add 4 "Confunde flujo electrico con campo electrico al aplicar Gauss"
```

La evidencia acepta `--session-id`, `--doubt-id` y `--source-id`. Al crear una duda asociada con `--topic-id`, se registra como `doubt/observed`; el cierre de sesion por si solo no crea evidencia ni cambia estados. Hermes puede consultar y registrar con la skill local `knowledge-tracking`, que explica estados usando registros concretos. V1 no incluye planificacion automatica, repeticion espaciada ni dashboards.
