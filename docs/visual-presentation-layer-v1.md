# Visual Presentation Layer V1

Este documento mantiene el plan y el punto de continuidad de la fase. Es la
copia versionable del plan de trabajo recibido en
`visual_presentation_layer_v1_plan.md`; usar este archivo como referencia al
continuar desde otro dispositivo.

## Objetivo y alcance

Agregar una capa desacoplada que reciba assets ya renderizados por Mermaid,
Graphviz o Matplotlib y produzca HTML standalone en `diagrams/generated/`.
Debe funcionar localmente, sin servidor, frontend ni dependencias obligatorias.
El HTML puede incluir varios SVG/PNG, texto pedagógico, notes y metadata de
fuente. El texto se escapa y las rutas de assets se limitan al directorio de
salida. El router conserva los archivos técnicos y expone el HTML cuando existe
un asset de imagen.

Fuera de alcance: Mermaid/DOT como contenido visual directo, frameworks,
servidor, interactividad, animaciones, zoom, dashboards y Visual Learning V2.

## Estado de implementación

- [x] Presenter standalone en `scripts/render_artifact.py`, implementado con
  biblioteca estándar.
- [x] SVG inline; PNG validado y embebido como data URI.
- [x] Layout responsive con soporte claro/oscuro, título, contexto, caption,
  notes y fuente.
- [x] Escape de texto, validación de SVG y rechazo de rutas fuera del directorio
  de assets.
- [x] Integración opcional en `scripts/visual_router.py`; agrega
  `technical_asset` y `presentation_artifact` al JSON solo cuando hay SVG/PNG.
- [x] Graphviz devuelve el PNG cuando se genera para permitir su presentación.
- [x] Skill y README describen la nueva salida y el fallback a source cuando no
  existe imagen renderizada.
- [x] Pruebas de presenter y router: `python -m unittest
  tests.test_render_artifact tests.test_visual_engine -v` — 10 pruebas pasan.
- [ ] Ejecutar de nuevo la suite completa y resolver/verificar sus fallos de
  manejo de bases temporales SQLite. En la última ejecución hubo errores en
  pruebas de `test_database`, `test_source_*` y `test_study_store` al limpiar
  directorios/base de datos temporales en Windows; no se corrigieron como parte
  de esta fase.
- [ ] Hacer revisión visual manual abriendo un HTML generado directamente en
  Firefox o el navegador local.
- [ ] Probar un artifact real de Mermaid y Graphviz si están disponibles
  `mmdc`/`dot`, y uno PNG si Matplotlib está instalado.

## Punto exacto para continuar

La implementación y las pruebas visuales automatizadas están listas. Continuar
con la verificación manual del artifact HTML desde assets reales y registrar el
resultado aquí. Después volver a ejecutar la suite completa para distinguir los
fallos existentes de SQLite de cualquier regresión. No iniciar Visual Learning
V2 hasta cerrar esos checks o anotar explícitamente las limitaciones pendientes.

## Cómo generar un artifact

Desde la raíz, el router lo produce automáticamente cuando un renderer crea
SVG/PNG:

```bash
printf '%s\n' '{"type":"process","title":"Consulta","subtitle":"Recorrido de una pregunta","notes":["Seguir el flujo de izquierda a derecha"],"data":{"nodes":[{"id":"A","label":"Usuario"},{"id":"B","label":"Hermes"}],"edges":[{"from":"A","to":"B"}]},"output_format":"svg"}' \
  | python3 scripts/visual_router.py
```

La respuesta JSON incluye `technical_asset` y `presentation_artifact` cuando el
SVG se renderiza. `mmdc` es opcional. Abrir el path HTML devuelto directamente
en navegador local.

La función también se puede llamar desde Python pasando metadata y paths de
assets ya generados a `render_artifact.render_artifact(...)`; no consulta la
base de datos ni genera Mermaid/DOT.

## Metadata soportada

```json
{
  "title": "Circuito RC",
  "subtitle": "Carga del capacitor",
  "description": "La tensión se aproxima a su valor final.",
  "visuals": [{"kind": "svg", "path": "circuito.svg", "caption": "Esquema", "alt_text": "Circuito RC"}],
  "notes": ["Observar la constante de tiempo"],
  "source": {"title": "Texto de Física", "chapter": "26", "section": "26.4", "page": 896},
  "subject": "Física II",
  "topic": "Circuitos RC"
}
```

## Limitaciones actuales

- El router pasa título, contexto, notes y source presentes en `Visual Request`;
  no consulta SQLite para completar la fuente.
- Solo SVG y PNG renderizados se muestran. Si Mermaid o Graphviz solo guardan
  `.mmd`/`.dot`, no se crea HTML.
- La prueba visual en navegador y los ejemplos con binarios opcionales aún no
  se han realizado.
- No hay zoom, tabs, animación ni controles interactivos.
