# Latency Audit V1

## Propósito y límites

Esta fase mide antes de optimizar. La instrumentación local registra spans del
CLI, ejecución del programa, procesos hijos y generación de artifacts. Es
opt-in mediante `HERMES_LATENCY=1`; no registra prompts, respuestas, argumentos,
fragmentos de fuentes ni secretos. Los registros van a
`storage/latency_runs.jsonl`, que está excluido de Git.

El repositorio no controla el runtime de Hermes ni recibe su telemetría de
inferencias, carga de skills, despacho de tools, apertura del preview o respuesta
final. Esos campos quedan `null` hasta medirlos desde la sesión/runtime de
Hermes. No se deben inferir a partir del tiempo total de un subprocess.

## Entorno de referencia

- Proyecto: Hermes Study Agent, scripts Python locales y SQLite.
- Reloj de duración: `time.perf_counter()`.
- Persistencia: JSON Lines, una entrada por invocación instrumentada.
- Datos personales: se usa únicamente el nombre del benchmark; nunca el prompt.
- Mediana y p95 se calculan por `benchmark` y `mode` (`cold`/`warm`). El p95
  utiliza interpolación lineal entre observaciones ordenadas.

## Benchmarks fijos

| ID | Prompt de Hermes | Señal de acción útil |
|---|---|---|
| `timer_1m` | “Poneme un timer de 1 minuto para estudiar Física.” | Persistencia efectiva de la sesión / timer |
| `study_session` | “Iniciá una sesión de estudio de Física sobre Ley de Gauss.” | Fila de sesión creada |
| `capture_doubt` | “Guardá esta duda: no entiendo por qué en Gauss el campo puede salir de la integral.” | Duda persistida |
| `source_query` | “Según Sears, explicame cómo se carga y descarga un capacitor en un circuito RC.” | Primera búsqueda de fuente completada |
| `visual_medium` | “Mostrame visualmente cómo se relacionan Source Engine, Hermes, Knowledge Tracking, SQLite y Study Pack.” | HTML generado y preview abierto, si está disponible |
| `roadmap_large` (opcional) | “Mostrame un roadmap completo para aprender Data Engineering separando fundamentos, almacenamiento, pipelines, procesamiento distribuido, orquestación y streaming.” | Artifact roadmap generado y preview abierto |

Ejecutar cada benchmark 5 veces cold y 5 warm (3+3 para una pasada inicial).
Cold significa runtime recién iniciado; warm significa misma sesión de Hermes y
componentes ya cargados. No comparar una llamada CLI aislada con una solicitud
completa de Hermes como si fueran la misma medición.

## Captura local

Las rutas de `study_cli.py`, `source_cli.py` y `visual_router.py` aceptan estos
metadatos opt-in. Los CLI identifican las operaciones comunes (`timer_1m`,
`study_session`, `capture_doubt`, `source_query`, `visual_medium`, `roadmap_large`)
sin guardar argumentos. Un `HERMES_LATENCY_BENCHMARK` explícito prevalece.
La marca `timer_started` se toma después de que la creación de sesión vuelve de
SQLite. `artifact_render_ms` cubre el trabajo del router desde antes de
validar/renderizar hasta que devuelve el artifact. `number_of_process_spawns`
cuenta subprocesses Python iniciados dentro de esa invocación. `python_import_ms`
mide imports del proyecto posteriores al arranque del profiler; no incluye la
creación del proceso del sistema operativo ni el startup del terminal de Hermes.
`process_start_ms` queda null hasta que una medición externa provea ambos
timestamps.

```bash
HERMES_LATENCY=1 \
HERMES_LATENCY_BENCHMARK=timer_1m \
HERMES_LATENCY_MODE=cold \
python3 scripts/study_cli.py session start "Física II" --target-minutes 1 --hard-limit-minutes 2
```

Para probar sin tocar la base personal, ejecutar las pruebas unitarias, que
usan una base temporal. Para una sesión de Hermes, el wrapper que invoca una
tool debe propagar `HERMES_LATENCY_RUN_ID`, `HERMES_LATENCY_BENCHMARK` y
`HERMES_LATENCY_MODE` al subprocess. La instrumentación actual no mide por sí
sola los spans externos de Hermes ni propaga automáticamente el run ID entre
turnos.

## Análisis

```bash
python3 scripts/analyze_latency.py
python3 scripts/analyze_latency.py --input /ruta/a/latency_runs.jsonl
```

El informe agrupa por benchmark y modo, e imprime count, mediana, promedio,
p95, extremos, etapa dominante, porcentaje de esa etapa, y promedios de model
turns, tool calls y procesos. Las celdas sin telemetría permanecen vacías; no
deben completarse con estimaciones.

## Estado de mediciones V1.0 (histórico)

| Benchmark | Modo | N | Mediana total | P95 | Etapa dominante |
|---|---:|---:|---:|---:|---|
| Timer | cold/warm | 0 | pendiente de Hermes | pendiente | pendiente |
| Iniciar sesión | cold/warm | 0 | pendiente de Hermes | pendiente | pendiente |
| Capturar duda | cold/warm | 0 | pendiente de Hermes | pendiente | pendiente |
| Source Engine | cold/warm | 0 | pendiente de Hermes | pendiente | pendiente |
| Artifact visual mediano | cold/warm | 0 | pendiente de Hermes | pendiente | pendiente |
| Roadmap grande (opcional) | cold/warm | 0 | pendiente de Hermes | pendiente | pendiente |

La matriz formal de 5+5 todavía no está ejecutada. Se hizo un piloto real
exploratorio del timer (1 interacción cold); no se usa para calcular medianas ni
p95. La corrida produjo esta observación:

| Observación | Resultado |
|---|---:|
| Hermes `system/init` → primer tool | 84.585 s |
| Hermes `system/init` → persistencia de la sesión | 100.731 s |
| Hermes `system/init` → respuesta final | 106.188 s |
| Invocación terminal que creó la sesión | 174 ms |
| Python imports del proyecto (`study_cli`) | 1.356 ms |
| Ejecución del programa Python/SQLite (`study_cli`) | 17.345 ms |
| Tool calls observadas | 8 |
| Búsquedas de herramienta de cron sin resultado | 2 |

El `system/init` de Hermes se emite antes de inicializar credenciales/agente,
pero después de recibir el prompt; no es T0. Por eso los primeros tres valores
son tiempo observado desde el arranque de sesión del agente, no latencia exacta
request→respuesta. En esta única corrida, la acción local de SQLite fue pequeña
frente al camino previo a la primera tool; todavía no se puede separar modelo,
carga de skills e inicialización de Hermes ni declarar un cuello dominante.
El stream no expone el número exacto de turnos del modelo. No hubo artifact ni
preview en este benchmark. Los registros locales incluyen una fila por cada
CLI invocado durante el timer, no una fila consolidada por interacción Hermes.

La matriz V1.0 de sesión, duda, Source Engine y visual no forma parte de esta
fase de aislamiento.

## Latency Audit V1.1 — Isolation Results

### Metodología y entorno

- Corridas reales el 2026-09-27 con Hermes Agent 0.21.4 y `gpt-6-luna`.
- Los timers usaron `/tmp/latency-audit/direct.db`; no se modificó la base de
  estudio personal. El CLI local se invocó tres veces sobre esa misma base.
- Cold: proceso Hermes nuevo y conversación nueva. Warm de Hermes: se continuó
  el mismo hilo para conservar contexto, pero cada invocación de `hermes chat`
  inició un proceso CLI nuevo. Esto no mide un runtime residente ni cache de
  imports de Hermes. El warm del dispatcher directo sí reutilizó el mismo
  proceso Python después de la primera importación.
- El capturador mide el total desde el lanzamiento del proceso con
  `perf_counter()` y guarda solo tiempos, nombres de tools y contadores. El
  stream de Hermes expone `system/init`, `tool_use`, `tool_result` y `result`,
  pero no un conteo fiable de model turns ni eventos de carga interna de skills.
- `number_of_skill_loads` significa llamadas explícitas a `skill_view`, no la
  carga inicial de instrucciones. Las búsquedas se cuentan por eventos
  `tool_search`. Hermes no marca como error una búsqueda sin coincidencias;
  failed searches queda unavailable.
- `hello_control` verificó que el modelo no invocó tools ni pidió skills. No
  desactivó por configuración todos los schemas de tools/instrucciones, así que
  es un control de no-uso, no una prueba de un runtime despojado de capacidades.
- p95 usa interpolación lineal sobre solo tres muestras: es orientativo, no
  una estimación estable de una distribución.

### Comparación principal

| Benchmark | Modo | Runs | Total median / p95 | Primera decisión/respuesta median / p95 | Acción útil median / p95 | Tools avg | Tool searches avg | Éxito |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `hello_control` | cold | 3 | 4.60 / 4.81 s | 4.04 / 4.17 s | respuesta final: 4.60 / 4.81 s | 0 | 0 | 3/3 |
| `hello_control` | warm, mismo hilo | 3 | 4.74 / 4.79 s | 4.05 / 4.09 s | respuesta final: 4.74 / 4.79 s | 0 | 0 | 3/3 |
| `timer_natural` | cold | 3 | 34.97 / 36.37 s | primer tool: 5.40 / 6.95 s | inicio: ~22.6 / ~30.1 s¹ | 8.0² | 1.5² | 3/3 |
| `timer_natural` | warm, mismo hilo | 3 | 14.49 / 17.54 s | primer tool: 4.41 / 4.83 s | inicio: 10.95 / 11.26 s | 3.33 | 0 | 3/3 |
| `timer_direct_tool` | cold | 3 | 0.83 / 0.85 s | n/a | inicio: 0.83 / 0.85 s | 1 | 0 | 3/3 |
| `timer_direct_tool` | warm, dispatcher importado | 3 | 0.32 / 0.39 s | n/a | inicio: 0.32 / 0.39 s | 1 | 0 | 3/3 |
| `study_cli_direct` | warm, CLI local | 3 | 0.05 / 0.05 s³ | n/a | inicio: 0.020 / 0.021 s | 0 | 0 | 3/3 |

¹ El inicio cold se reconstruyó con el `started_at` de SQLite, el timestamp
`system/init` y el tiempo anterior a ese evento. SQLite guarda segundos enteros,
así que cada valor tiene incertidumbre cercana a ±1 s. Las tres estimaciones
fueron 20.0, 22.6 y 31.0 s; las respuestas finales tardaron 27.4, 35.0 y 36.5 s.

² Tools y búsquedas cold son promedios de las dos corridas cuyo stream se pudo
contar completo: 7 y 9 tools; 1 y 2 búsquedas. No se pudo determinar si esas
búsquedas fallaron, porque la respuesta de `tool_search` no expone un estado
fiable de “sin coincidencias”. En las tres respuestas cold Hermes indicó que
no pudo programar recordatorios; los timers sí quedaron activos. Warm usó 3, 4
y 3 tools y no buscó herramientas.

³ Tres envolturas externas reportaron 0.05 s cada una. El profiler local midió
1.34 ms de imports Python, 20.36 ms de ejecución del programa (incluye SQLite)
y 20.31 ms hasta iniciar/persistir el timer. El costo de SQLite aislado no está
instrumentado.

### Etapas y conteos observados

| Ruta | Medición adicional | Resultado |
|---|---|---|
| Hello cold | Inicio de proceso → `system/init` | mediana 1.63 s |
| Hello warm | Inicio de proceso → `system/init` | mediana 1.55 s |
| Direct tool cold | Import de módulos Hermes | mediana 663 ms |
| Direct tool cold | Dispatcher `handle_function_call` | mediana 164 ms |
| Direct tool warm | Dispatcher `handle_function_call` | mediana 75 ms |
| CLI local warm | Imports del proyecto | mediana 1.34 ms |
| CLI local warm | Programa + SQLite | mediana 20.36 ms |
| Hermes natural | Model turns exactos | unavailable en el stream |
| Hermes natural | Skill loads internos | unavailable; solo se cuenta `skill_view` (1/run) |
| Hermes natural | Failed tool searches | unavailable; no hay señal de no coincidencia fiable |
| Hermes natural | Process spawns | unavailable en el stream |
| Direct tool cold | Process spawns | 2 por llamada según audit hook |
| Direct tool warm | Subprocesses por llamada | unavailable; el hook dio valores acumulativos 3, 4 y 5 |

El timer natural cold usó 7–9 tool calls observadas y tardó ~35 s de mediana.
Warm, con el mismo contexto conversacional, bajó a 14.5 s y 3–4 tool calls.
El primer tool apareció a los 5.4–7.1 s cold y a 4.2–4.9 s warm. El timer no
se inició hasta después de varias vueltas modelo/tools.

El dispatcher directo llamó la terminal real de Hermes sin selección semántica
del modelo y persistió la sesión en SQLite. Frente al timer natural, la acción
directa fue unas 42 veces más rápida cold y 45 veces warm. El dispatcher warm
ocupó ~75 ms; el CLI de estudio ~20 ms. El resto corresponde al arranque/import
del dispatcher y el paso por terminal/subprocess.

### Interpretación y respuestas

1. **¿Python es un cuello de botella relevante?** No. El CLI local completo fue
   ~50 ms; el programa con SQLite fue ~20 ms y los imports del proyecto ~1.4 ms.
   Hermes importa sus módulos por ~663 ms en el primer uso directo, lejos de
   los 15–35 s de la ruta natural.
2. **¿SQLite es un cuello de botella relevante?** No hay evidencia de ello. La
   creación de la sesión está dentro de los ~20 ms del CLI. SQLite no se midió
   por separado, pero la escritura está muy por debajo de la latencia total.
3. **¿El startup de Hermes parece relevante?** Aporta cerca de 1.6 s hasta
   `system/init`, pero hello tarda 4.6–4.7 s total. No es el componente mayor.
4. **¿El tool routing parece relevante?** Sí, junto con el razonamiento y las
   vueltas modelo→tool→modelo. El primer tool aparece varios segundos después
   del lanzamiento y hay esperas de inferencia entre tools. El stream no separa
   inferencia de routing interno.
5. **¿El número de tool calls parece excesivo?** Para iniciar un timer, 7–9
   cold y 3–4 warm parecen altos. Se observaron carga explícita de la skill,
   lecturas/búsquedas y varios pasos de terminal antes de finalizar.
6. **¿El direct tool path mejora materialmente la latencia?** Sí. Cold: 35.0 s
   natural frente a 0.83 s directo. Warm: 14.5 s frente a 0.32 s. Esta ruta
   inicia/persiste el timer, pero no programa recordatorios.
7. **¿Cold y warm presentan una diferencia significativa?** En hello no: 4.60
   frente a 4.74 s. En timer natural sí: 35.0 frente a 14.5 s, junto con menos
   tools. Como el proceso CLI se reinicia, esa diferencia no demuestra que un
   runtime persistente reduzca startup; muestra una diferencia al continuar el
   hilo/contexto.
8. **¿Qué componente conviene investigar primero?** El camino de decisión y
   ejecución del timer: inferencias y tools antes de la escritura útil, además
   del descubrimiento de la capacidad de recordatorios. No se implementó esa
   optimización.

### Incertidumbres restantes

- Hermes no expone model turns, duración individual de inferencias, cargas
  internas de skills ni fallos semánticos de `tool_search`; no se puede separar
  routing de razonamiento con precisión.
- “Warm” reutiliza la conversación, no el proceso. Falta medir dentro de un
  REPL/runtime persistente para aislar startup/cache en sentido estricto.
- El inicio cold se estima desde SQLite con resolución de un segundo; warm se
  marca al recibir el resultado de la tool terminal que creó la sesión.
- Las notificaciones no se midieron como acción útil: Hermes dijo que la
  herramienta de cron/recordatorios no estaba disponible. El timer local siguió
  funcionando.
- No hubo artifacts ni preview en esta fase.

## Fast Path V1 Results

### Implementación y metodología

- Se añadió el plugin local `study-fastpath` con siete herramientas: inicio,
  pausa, reanudación y detención de timer; inicio, cierre y consulta de sesión.
  Las herramientas llaman al Study Core en proceso y no ejecutan terminal,
  subprocesses ni SQL propio.
- Timer y sesión siguen usando la entidad persistente actual de `study_sessions`;
  no se añadió una tabla de timers. Una sesión activa impide iniciar o reanudar
  otra en paralelo.
- El plugin quedó instalado como enlace simbólico en
  `~/.hermes/plugins/study-fastpath`, habilitado, y el toolset `project` se
  habilitó para CLI. Esto evita que las herramientas queden detrás del puente
  `tool_search`. El gateway no estaba en ejecución durante la prueba.
- Corridas naturales ejecutadas el 2026-09-27 con Hermes 0.21.4 y
  `gpt-6-luna`; cada caso usó una SQLite aislada en `/tmp`. El stream de Hermes
  informa uso de tools y timestamps, pero no subprocesses internos; el conteo
  de búsquedas y cargas de skill corresponde a eventos `tool_search` y
  `skill_view` observables.
- Timer natural: tres procesos/conversaciones cold y tres acciones repetidas
  dentro del mismo contexto warm. Como ese contexto acumula historia, las
  muestras warm también miden cómo el modelo maneja acciones repetidas.
  p95 se calcula con interpolación lineal sobre solo tres muestras y es
  orientativo.
- Las corridas usaron el toolset CLI normal con `project` habilitado en la
  configuración local. Cada corrida tuvo una base nueva: timer/session-start
  arrancaron vacíos; status/pause recibieron una sesión activa y resume una
  sesión pausada. El capturador valida `ok: true` en el resultado de la tool,
  además del exit code de Hermes.
- Se descartaron los intentos iniciales donde el capturador sembraba una sesión
  también en los casos de inicio. La tabla usa únicamente las corridas repetidas
  con preparación corregida y acción confirmada.
- La primera prueba del perfil CLI normal tras habilitar `project` tuvo N=1;
  se reporta por separado y no se mezcla con las tres muestras controladas.

### Antes y después

| Benchmark | Modo | Runs | Total median / p95 | Acción útil median / p95 | Tool calls avg | Searches avg | Skill loads avg |
|---|---:|---:|---:|---:|---:|---:|---:|
| Timer natural, antes | cold | 3 | 34.97 / 36.37 s | inicio: ~22.6 / ~30.1 s | 8.0¹ | 1.5¹ | 1 `skill_view`/run² |
| Timer natural, Fast Path | cold | 3 | 8.41 / 10.02 s | inicio: 5.01 / 5.01 s | 1.0 | 0 | 0 |
| Timer natural, antes | warm | 3 | 14.49 / 17.54 s | inicio: 10.95 / 11.26 s | 3.33 | 0 | 1 `skill_view`/run |
| Timer natural, Fast Path | warm | 3 | 7.72 / 10.83 s | inicio: 5.03 / 6.73 s | 1.0 | 0 | 0 |
| Timer directo por terminal, antes | cold / warm | 3 / 3 | 0.83 / 0.85 s; 0.32 / 0.39 s | igual al total | 1.0 | 0 | 0 |
| Timer directo por tool Fast Path | primera / warm | 1 / 2 | 32.2 ms / —; 7.8 ms / — | igual al dispatch | 1.0 | 0 | 0 |

¹ Promedio de las dos corridas anteriores cuyo stream se pudo contar. ² Solo
llamadas explícitas a `skill_view`; la carga interna no es visible en el stream.

En las seis corridas cold/warm el timer inició tras una sola tool; no hubo
`tool_search`, `skill_view` ni uso de `terminal`. La mediana cold del inicio
bajó de ~22.6 s a 5.01 s (78% menos) y el total de 34.97 s a 8.41 s (76%
menos). En warm, el inicio bajó de 10.95 s a 5.03 s (54% menos) y el total de
14.49 s a 7.72 s (47% menos). Una corrida adicional del perfil CLI normal confirmó el mismo routing:
5.29 s hasta la tool, 7.38 s total, una tool call, cero búsquedas y cero cargas
explícitas de skills.

Las acciones naturales adicionales también eligieron una sola herramienta
directa en cada muestra: `session_start` tardó 4.93 s en ejecutarse (9.36 s
total), `session_status` 6.11 s (13.88 s total), pausa 5.26 s (10.06 s total) y
reanudación 8.32 s (10.69 s total). N=1 por acción; no se calcula p95.

El dispatcher directo de Hermes ejecutó la escritura local en 32 ms en su
primera llamada y ~8 ms en las dos siguientes, con cero subprocesses, búsquedas
o cargas de skill. Es una medición posterior a importar Hermes; no incluye su
startup completo. La parte local ya queda en milisegundos y no explica los
segundos que aún preceden a la decisión natural.

### Interpretación Fast Path

- **Routing y tool discovery:** corregidos para estas siete acciones en el
  perfil medido. El schema visible lleva a la tool específica sin búsqueda.
- **Tool calls:** el objetivo de una llamada se cumplió en las seis muestras
  timer y en cada acción natural adicional. No se buscó cron en ninguna de
  estas acciones.
- **Latencia útil:** mejoró de forma material, pero no llega al objetivo
  `<1 s` desde lenguaje natural. En cold la decisión tarda ~4.8–5.0 s antes de
  iniciar; el handler y SQLite tardan decenas de milisegundos o menos.
- **Cold vs warm:** el total mediano fue 8.41 s cold y 7.72 s warm; el inicio,
  5.01 s y 5.03 s respectivamente. El proceso CLI se reinicia en cada corrida,
  por lo que warm significa contexto conversacional reutilizado, no runtime
  residente.
- **Estado y edge cases:** se probaron duración cero, ausencia de timer activo
  al pausar, ausencia de timer pausado al reanudar, inicio duplicado, pausa,
  reanudación, detención/cancelación, inicio/cierre de sesión, status,
  persistencia del tema y bloqueo de sesiones activas concurrentes.
- **Python y SQLite:** siguen sin ser un cuello relevante; el dispatch in
  process directo fue 7 ms warm. No se cambió el esquema ni se añadió una
  dependencia.
- **Siguiente cuello a investigar:** la inferencia inicial. Un fast path previo
  al modelo o un comando explícito podría bajar más el inicio natural; no se
  implementa aquí porque esta fase mantiene la decisión semántica del modelo.

El timer se modela como una sesión de estudio existente: “detener timer” cierra
esa sesión como `cancelled`. No hay timer persistente independiente, ni
notificación proactiva al llegar al objetivo; los recordatorios con fecha o
recurrencia son una intención separada. El plugin no genera artifacts.

## Latency Audit V1.2 — Fast Path Results

### Metodología y alcance

- Medido el 2026-09-27 con Hermes 0.21.4, el perfil CLI `gpt-6-luna`, el plugin
  `study-fastpath` habilitado y SQLite aislada por caso. El comando reproducible
  es `.venv/bin/python scripts/run_fastpath_benchmarks.py --v12 --output /tmp/latency-audit/v12-hermes.jsonl`.
- 33 muestras válidas: timer natural 3 cold + 3 warm; sesión inicial 3 + 3;
  estado de sesión 3 warm; pausa/reanudación 3 secuencias warm (6 acciones);
  control `OK` 3 + 3; tool directa 3 + 3. Cold crea conversación/proceso nuevo;
  warm reutiliza contexto o, para la tool directa, el dispatcher ya importado.
  El CLI reinicia su proceso incluso en las llamadas naturales warm.
- El inicio/acción útil natural se observa al recibir `tool_result` con
  `ok: true`; por eso es una cota superior del instante real de persistencia.
  El handler registra aparte `program_execution_ms` y subprocesses internos.
  El tiempo total llega hasta la salida del proceso y la respuesta final.
- La tool directa cold incluye inicio de Python, imports y dispatch; su instante
  de acción usa una marca de reloj al completar el handler. La muestra warm
  mide el dispatch con el proceso ya cargado. Estos caminos difieren del
  dispatcher por terminal usado en V1.1, así que no se les asigna un porcentaje
  de mejora comparable.
- Mediana y p95 usan tres muestras por grupo; p95 por interpolación lineal es
  orientativo. El JSONL completo quedó en `/tmp/latency-audit/v12-hermes.jsonl`.
  Los conteos de subprocesses naturales son *dentro del handler*, sin incluir
  el proceso de Hermes lanzado por el benchmark.

### Antes y después

| Métrica | V1.1 antes | V1.2 después | Cambio |
|---|---:|---:|---:|
| Timer natural cold, total mediano | ~35.0 s | 6.93 s | 80.2% menos |
| Timer natural warm, total mediano | ~14.5 s | 7.28 s | 49.7% menos |
| Inicio de timer cold, mediana | ~22.6 s | 5.05 s | 77.7% menos |
| Inicio de timer warm, mediana | ~10.95 s | 4.64 s | 57.7% menos |
| Tool calls timer cold | 7–9 observadas (8.0 promedio) | 1.0 | 87.5% menos sobre promedio |
| Tool calls timer warm | 3–4 (3.33 promedio) | 1.0 | 70.0% menos sobre promedio |
| `tool_search` timer cold | 1–2 observadas | 0 | Eliminadas en las muestras |
| `tool_search` timer warm | 0 | 0 | Sin cambio |
| `skill_view` timer | 1 por run observado | 0 | Eliminadas en las muestras |
| Tool directa cold, total mediano | ~0.83 s | 0.91 s | Métodos distintos |
| Tool directa warm, mediana | ~0.32 s | 8.88 ms de dispatch | Métodos distintos |

El baseline V1.1 es histórico y no fue modificado. Su inicio cold fue
reconstruido con el timestamp de SQLite y tiene menos precisión que el stream
V1.2. La diferencia cold de la tool directa (0.83 frente a 0.91 s) está dentro
del costo de arranque/importación y no permite atribuir una regresión al core.

### Matriz V1.2

Todos los tiempos son **mediana / p95 orientativo**. `Primer tool` y `Acción`
se miden desde el envío al proceso de Hermes; `Total` incluye la respuesta.

| Caso | Modo | N | Primer tool | Acción útil | Total | Handler local mediano | Calls / search / skill_view | Éxitos |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Timer natural | cold | 3 | 5.03 / 5.12 s | 5.05 / 5.15 s | 6.93 / 7.57 s | 8.8 ms | 1 / 0 / 0 | 3/3 |
| Timer natural | warm | 3 | 4.62 / 4.89 s | 4.64 / 4.91 s | 7.28 / 8.46 s | 9.0 ms | 1 / 0 / 0 | 3/3 |
| Inicio de sesión | cold | 3 | 4.92 / 6.11 s | 4.95 / 6.14 s | 8.72 / 10.99 s | 13.8 ms | 1 / 0 / 0 | 3/3 |
| Inicio de sesión | warm | 3 | 4.86 / 5.11 s | 4.89 / 5.14 s | 9.40 / 14.66 s | 14.9 ms | 1 / 0 / 0 | 3/3 |
| Estado de sesión | warm | 3 | 4.98 / 5.08 s | 5.00 / 5.10 s | 7.67 / 23.78 s | 1.7 ms | 1 / 0 / 0 | 3/3 |
| Pausa | warm | 3 | 4.96 / 14.68 s | 4.98 / 14.70 s | 11.50 / 19.80 s | 9.6 ms | 1 / 0 / 0 | 3/3 |
| Reanudación | warm | 3 | 7.41 / 11.38 s | 7.43 / 11.40 s | 12.44 / 14.14 s | 9.2 ms | 1 / 0 / 0 | 3/3 |
| Control `OK` | cold | 3 | — | respuesta: 4.81 s | 4.81 / 4.85 s | — | 0 / 0 / 0 | 3/3 |
| Control `OK` | warm | 3 | — | respuesta: 4.95 s | 4.95 / 5.03 s | — | 0 / 0 / 0 | 3/3 |
| Tool directa | cold | 3 | — | 0.76 / 0.78 s | 0.91 / 0.93 s | dispatch: 34.0 ms | 1 / 0 / 0 | 3/3 |
| Tool directa | warm | 3 | — | 8.88 / 8.98 ms | dispatch: 8.88 / 8.98 ms | 8.9 ms | 1 / 0 / 0 | 3/3 |

El estado de sesión tuvo una respuesta total aislada de 25.57 s, aunque la
tool devolvió el estado a los ~5 s y ejecutó ~2 ms de código local. Esto
ensancha el p95 orientativo y muestra que respuesta textual y acción útil son
tiempos distintos. Las tres pausas y reanudaciones conservaron el mismo
`session_id`: cada base terminó con una sola sesión `active`, sin duplicados.
Las seis sesiones iniciadas guardaron un checkpoint del tema “Ley de Gauss”.
Los tests del Study Core comprueban además que la pausa conserva el tiempo
restante y la reanudación continúa desde él. No hubo llamadas a cron/reminders.

Se descartaron intentos del harness que no medían Hermes: un arranque dentro
del sandbox no pudo escribir `~/.hermes`, el script directo usó inicialmente el
Python del proyecto sin dependencias de Hermes y una ruta temporal repetida
provocó una materia duplicada. Se corrigieron únicamente esas condiciones de
medición; ninguna entra en las 33 muestras válidas.

### Conclusiones V1.2

1. **Sí, Fast Path redujo materialmente la latencia:** 78% cold y 58% warm
   hasta iniciar el timer, con el baseline aproximado de V1.1.
2. **Sí, el timer natural usa una sola tool** en 6/6 muestras; inicio de
   sesión, status, pausa y reanudación también en 15/15 muestras.
3. **Sí, `tool_search` desapareció** de las 21 acciones naturales rápidas.
4. **Sí, `skill_view` desapareció** de esas mismas acciones observadas.
5. **No, la acción natural no ocurre en menos de 1 s:** timer 5.05 s cold y
   4.64 s warm de mediana. La herramienta directa sí inicia en 0.76 s cold
   y ~9 ms warm.
6. **Sí, la tool directa sigue rápida:** el handler no crea subprocesses y
   el dispatch warm ronda 9 ms.
7. **Cold y warm naturales difieren poco:** timer útil 5.05 frente a 4.64 s;
   el control `OK` da 4.81 frente a 4.95 s. No hay evidencia de que startup
   explique la mayor parte del tiempo natural.
8. **El cuello dominante está antes de la tool:** ~4.6–5.0 s hasta el primer
   tool de timer, frente a ~9 ms dentro del handler. Después del tool quedan
   ~1.9–2.6 s medianos para la respuesta de timer y hay outliers mayores en
   otras acciones.
9. **Siguiente candidato a evaluar:** un routing de intención previo al loop
   del modelo para acciones locales inequívocas, con medición independiente.
   No se implementó en esta auditoría.

## Interpretación

- `total_ms` solo aparece cuando se marcan tanto la recepción de solicitud como
  la respuesta final en un mismo reloj monotónico.
- `timer_start_latency_ms` requiere `user_request_received` y `timer_started`;
  la medición local de SQLite solo cubre el segundo extremo.
- Los spans ausentes son `null`, no cero.
- La etapa dominante se calcula solo entre etapas instrumentadas. No representa
  el cuello dominante end-to-end si faltan datos de Hermes.
- La medición V1.2 completó ese gate. Después se implementó la separación de
  timers/sesiones y `/study-timer` como comando directo; esa versión todavía no
  se benchmarkeó en una sesión real de Hermes. Los valores históricos de arriba
  corresponden al modelo anterior y no se modificaron.
