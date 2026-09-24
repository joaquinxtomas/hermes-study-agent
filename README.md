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

- `process`, `architecture`, `sequence` → fuente Mermaid `.mmd`;
- `tree`, `graph`, `dag` → fuente Graphviz `.dot`;
- `function`, `numeric_data`, `study_metrics` → imagen PNG con Matplotlib.

Los artifacts se guardan en `diagrams/generated/` y los nombres repetidos
reciben un sufijo, sin sobrescribir los anteriores. Para producir source:

```bash
printf '%s\n' '{"type":"process","title":"Consulta","data":{"nodes":[{"id":"A","label":"Usuario"},{"id":"B","label":"Hermes"}],"edges":[{"from":"A","to":"B"}]}}' \
  | python3 scripts/visual_router.py
```

Mermaid CLI (`mmdc`) intenta generar automáticamente un SVG adicional al `.mmd`
cuando está instalado; si falla, conserva la fuente y muestra una advertencia.
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
