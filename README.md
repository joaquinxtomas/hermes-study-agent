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
Hermes visual-explain skill → scripts/visual_router.py → renderer
                                                   └→ diagrams/generated/
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

## Visual Learning Engine V1

Cuando un diagrama o gráfico mejora la explicación, la skill `visual-explain`
envía una Visual Request JSON al router determinístico. Las skills describen los
datos y no dependen de formatos de renderer:

- `flow`, `process`, `architecture`, `pipeline` → Native Visual Artifact Engine:
  layout DAG determinístico, nodos HTML reales y conectores SVG responsive.
  El spec expresa significado, nunca coordenadas; Mermaid queda como export/fallback.
- `sequence` → fuente Mermaid `.mmd`;
- `tree`, `graph`, `dag` → fuente Graphviz `.dot`;
- `function`, `numeric_data`, `study_metrics` → imagen PNG con Matplotlib.

Los artifacts se guardan en `diagrams/generated/` y los nombres repetidos
reciben un sufijo, sin sobrescribir los anteriores. Para producir source:

```bash
printf '%s\n' '{"type":"flow","title":"Consulta","data":{"nodes":[{"id":"A","title":"Usuario","role":"input"},{"id":"B","title":"Hermes","role":"agent"}],"edges":[{"from":"A","to":"B","label":"pregunta"}]}}' \
  | python3 scripts/visual_router.py
```

Ejemplos completos: `docs/source-engine.visual.json` y
`docs/hermes-architecture.visual.json`. Abrí el `presentation_artifact`
devuelto directamente en Firefox. Mermaid CLI (`mmdc`) puede crear un SVG de
exportación si se solicita; si falla, conserva la fuente. El renderer nativo
funciona offline y usa JavaScript vanilla solo para alinear conectores y
resaltar relaciones enfocadas.
Graphviz (`dot`) permite PNG. Ambos son opcionales y no están incluidos. Los
gráficos requieren Matplotlib; si no
está instalado, el comando informa cómo habilitarlo. No se ejecutan expresiones
de usuario: los plots consumen arrays numéricos `x`/`y` ya calculados.

Desde Hermes Desktop, confía el repositorio con `hermes skills trust "$PWD"`,
abre Hermes desde la raíz y pide una explicación visual. La skill adjunta el
artifact y lo explica; si una herramienta binaria opcional no está disponible,
puede enlazar el source Mermaid/DOT correspondiente.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

El test de PDF genera un documento de dos páginas en una carpeta temporal y se
omite si `pdftotext` no está instalado. Los tests visuales no necesitan
herramientas externas; el caso de PNG verifica el error claro cuando Matplotlib
no está instalado. Los demás tests usan bases SQLite temporales y no dependen de
materiales personales.

El renderer nativo V1 cubre flows, procesos, pipelines y arquitecturas simples
acíclicas; árboles/grafos generales, charts y diagramas físicos quedan fuera de
este alcance. Los demás renderers y el presenter anterior siguen disponibles
para exportación, fallback y compatibilidad. Detalles, schema y prueba manual:
[Native Visual Artifact Engine V1](docs/native-visual-artifacts.md).


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
