# Visual Presentation Layer V1

Lee AGENTS.md, PLAN.md, README.md y la estructura actual del repositorio antes de modificar nada.

## Contexto

El proyecto ya tiene Visual Learning Engine V1 con:

- `visual_router.py`
- Mermaid
- Graphviz
- Matplotlib
- artifacts generados en `diagrams/generated/`
- skill `visual-explain`

Mermaid ya puede renderizar a SVG cuando `mmdc` está disponible.

## Objetivo de esta fase

Implementar una capa de presentación visual moderna, autocontenida y pedagógica para los artifacts generados.

La idea es pasar de:

```text
renderer técnico
→ .svg / .png / .mmd / .dot
```

a:

```text
renderer técnico
→ visual asset
→ artifact presenter
→ HTML autocontenido moderno
```

No reemplazar Mermaid, Graphviz ni Matplotlib. La capa nueva debe reutilizar sus outputs.

## Arquitectura

Mantener separación entre:

1. visual intent
2. visual specification
3. technical renderer
4. artifact presenter

Flujo esperado:

```text
User request
↓
visual-explain
↓
VisualRequest
↓
visual_router.py
↓
Mermaid / Graphviz / Matplotlib
↓
asset técnico
↓
artifact presenter
↓
HTML final
```

No acoplar los renderers técnicos al HTML.

## Archivo principal

Crear, si encaja con la arquitectura actual:

```text
scripts/render_artifact.py
```

Responsabilidad:

- recibir metadata estructurada;
- recibir uno o varios assets visuales;
- generar un HTML standalone;
- guardar el artifact en `diagrams/generated/`;
- devolver metadata del artifact generado.

No implementar servidor web.
No depender de frameworks frontend.

## Formato de entrada

Definir una estructura simple para el artifact.

Puede ser:

- dataclass
- TypedDict
- dict validado
- equivalente simple

Debe soportar como mínimo:

- `title`
- `subtitle` nullable
- `description` nullable
- `visuals`
- `notes`
- `source` nullable
- `subject` nullable
- `topic` nullable
- `created_at`

Cada visual debe soportar:

- `kind`
- `path`
- `caption` nullable
- `alt_text` nullable

Kinds iniciales:

- `svg`
- `png`

No procesar Mermaid ni DOT directamente en esta capa. Debe recibir assets ya renderizados.

## Output

El artifact final debe ser HTML autocontenido.

Ejemplo:

```text
diagrams/generated/
├── source-engine.svg
└── source-engine-artifact.html
```

El HTML debe funcionar abriéndose directamente en navegador local.

No requerir:

- backend
- servidor
- CDN
- internet
- fetch
- npm runtime

## Embedding de assets

### SVG

Preferir inline SVG dentro del HTML.

No usar iframe.

### PNG

Embebido localmente de forma robusta.

Preferencia:

- data URI/base64

o:

- path relativo si la implementación existente lo vuelve más simple y portable.

Priorizar que el HTML pueda moverse junto con el proyecto sin romperse.

## Estilo visual

Crear una interfaz moderna y sobria.

Objetivo visual:

- limpia
- pedagógica
- responsive
- legible
- moderna
- sin aspecto de dashboard empresarial

No copiar una interfaz externa específica.

Usar:

- HTML semántico
- CSS propio
- variables CSS
- `border-radius` moderado
- buen spacing
- tipografía del sistema
- contraste correcto
- dark/light support si es simple

Evitar:

- sombras excesivas
- gradientes decorativos innecesarios
- colores hardcodeados por todos lados
- glassmorphism
- animaciones llamativas
- dependencias externas

## Layout base

El artifact debe poder mostrar:

- título
- subtítulo opcional
- descripción opcional
- visual principal
- caption
- bloque “Qué mirar” o notes
- fuente / contexto

Ejemplo conceptual:

```text
------------------------------------------------
Circuitos R-C

Carga y descarga de un capacitor con resistencia

[ VISUAL ]

Qué mirar
- La corriente cae exponencialmente
- La carga se aproxima asintóticamente

Fuente
Sears & Zemansky · Cap. 26 · Sec. 26.4
------------------------------------------------
```

## Multi-visual

Permitir múltiples visuals.

Ejemplo:

```text
Circuito RC

Visual 1:
esquema del circuito

Visual 2:
curva de carga

Visual 3:
curva de descarga
```

No crear carruseles ni tabs todavía.

Mostrar verticalmente con jerarquía clara.

## Notes / pedagogía

El presenter debe aceptar notes:

```python
[
    "El PDF original permanece en materials/.",
    "SQLite conserva metadata y texto por página."
]
```

Renderizarlas como bloque pedagógico claro.

No inventar notes.

El presenter solo muestra lo que recibe.

## Source context

Soportar metadata de fuente como:

- `title`
- `chapter` nullable
- `section` nullable
- `page` nullable

Ejemplo:

```text
Sears & Zemansky
Capítulo 26
Sección 26.4
Página 896
```

No consultar SQLite desde `render_artifact.py`.

El presenter debe ser puro:

```text
input estructurado → HTML
```

## Integración con Visual Router

No modificar innecesariamente `visual_router.py`.

Agregar integración mínima para que, opcionalmente:

```text
renderer técnico
→ artifact presenter
```

El router debe poder devolver:

- `technical_asset`
- `presentation_artifact`

Ejemplo conceptual:

```json
{
  "renderer": "mermaid",
  "technical_asset": "...source-engine.svg",
  "presentation_artifact": "...source-engine-artifact.html"
}
```

Mantener compatibilidad con el output anterior si es posible.

## Fallbacks

Si solo existe `.mmd` sin SVG:

NO intentar presentar Mermaid source como visual principal.

El presenter debe:

- informar que no existe asset visual renderizado;
- o no generarse.

Si Graphviz solo produjo `.dot`:

misma regla.

Matplotlib:

requiere PNG válido.

No incrustar source code visual como si fuera diagrama.

## Seguridad

El HTML puede contener contenido generado por modelo.

Escapar correctamente:

- title
- subtitle
- descriptions
- captions
- notes
- source metadata

No permitir que texto generado se interprete como HTML arbitrario.

La única excepción puede ser el SVG ya generado por renderers internos.

Antes de incrustar SVG:

- leer archivo local;
- validar que parece SVG;
- no aceptar paths fuera del directorio esperado.

Evitar path traversal.

## Rutas

Mantener artifacts bajo:

```text
diagrams/generated/
```

No escribir fuera de ese directorio salvo que tests usen temp dirs.

Usar filenames seguros.

No sobrescribir artifacts previos salvo que la arquitectura actual ya lo haga explícitamente.

## Tests

Crear tests para la nueva capa.

Sugerencia:

```text
tests/test_render_artifact.py
```

Usar `unittest`.

Testear:

1. genera HTML válido;
2. incluye título escapado;
3. incluye subtitle;
4. incluye notes;
5. inline SVG funciona;
6. PNG queda referenciado/embebido correctamente;
7. múltiples visuals;
8. metadata de source;
9. path traversal rechazado;
10. asset inexistente falla claramente;
11. HTML generado no queda vacío.

Usar `TemporaryDirectory`.

No generar artifacts reales en `diagrams/generated/` durante tests.

## Prueba manual 1

Usar Mermaid ya existente.

Input:

```text
Source Engine SVG
```

Generar:

```text
source-engine-artifact.html
```

Resultado esperado:

- título
- subtítulo
- SVG embebido
- notes
- visual limpio
- responsive

Abrirlo directamente en Firefox.

## Prueba manual 2

Usar un SVG generado por Graphviz.

Crear artifact moderno alrededor del árbol.

Resultado esperado:

- árbol visible
- caption
- notes
- sin HTML roto

## Prueba manual 3

Usar PNG de Matplotlib si está disponible.

Crear artifact con:

- título
- gráfico
- explicación corta
- fuente/contexto opcional

## Integración con visual-explain

Actualizar `skills/visual-explain/SKILL.md` solo si hace falta.

La skill debe entender que:

- technical renderer genera asset;
- presenter genera artifact pedagógico;
- cuando exista artifact HTML, preferir devolverlo al usuario;
- conservar technical asset para portabilidad/debug.

No hacer que la skill genere HTML manualmente.

Debe usar `render_artifact.py`.

## No implementar

No agregar todavía:

- Excalidraw
- Physics schematic engine
- custom SVG drawing engine
- Plotly
- D3
- React
- Vue
- Svelte
- Tailwind
- web server
- artifact editor
- tabs
- carousel
- animation
- zoom/pan custom
- drag-and-drop
- dashboards
- interactive simulations
- NotebookLM
- WhatsApp
- ActivityWatch
- embeddings
- vector database

## Documentación

Actualizar README o docs solamente con lo implementado.

Documentar:

- diferencia entre technical asset y presentation artifact;
- formatos soportados;
- ubicación de artifacts;
- cómo abrirlos;
- limitaciones actuales.

No llamar “interactive” al sistema si no lo es.

## Check environment

No agregar dependencias obligatorias nuevas.

`render_artifact.py` debería depender solo de Python estándar.

Mantener detección existente de:

- Mermaid CLI
- Graphviz
- Matplotlib

## Criterios de aceptación

La fase termina cuando:

1. existe una capa de presentación desacoplada;
2. genera HTML standalone;
3. soporta SVG;
4. soporta PNG;
5. soporta múltiples visuals;
6. soporta notes;
7. soporta source metadata;
8. escapa contenido textual;
9. evita path traversal;
10. tests pasan;
11. Visual Learning existente sigue funcionando;
12. Mermaid/Graphviz/Matplotlib siguen siendo renderers independientes;
13. el artifact final se ve correctamente al abrirlo en navegador;
14. no se implementaron features V2.

## Entrega final

Al terminar:

1. listar archivos creados/modificados;
2. explicar arquitectura final;
3. ejecutar todos los tests;
4. mostrar resultado de tests;
5. mostrar un ejemplo de metadata de artifact;
6. indicar cómo generar uno manualmente;
7. indicar cómo probarlo desde Hermes más adelante;
8. indicar limitaciones;
9. no avanzar a Visual Learning V2.
