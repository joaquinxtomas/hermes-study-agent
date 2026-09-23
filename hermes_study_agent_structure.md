# Hermes Study Agent — Estructura inicial del proyecto

## Objetivo

Este archivo define únicamente la estructura base del repositorio `hermes-study-agent`.

Debe poder entregarse a un LLM o agente de programación para que cree el scaffolding del proyecto sin implementar lógica todavía.

## Regla principal

Crear solamente directorios y archivos vacíos.

No:

- escribir código funcional;
- instalar dependencias;
- inicializar SQLite;
- configurar Hermes;
- agregar API keys o tokens;
- conectar WhatsApp;
- conectar Codex;
- conectar NotebookLM;
- conectar ActivityWatch;
- crear lógica de routing;
- crear temporizadores.

## Estructura

```text
hermes-study-agent/
├── README.md
├── AGENTS.md
├── .gitignore
│
├── config/
│   └── study.example.yaml
│
├── migrations/
│   └── 001_initial_schema.sql
│
├── skills/
│   ├── capture-doubt/
│   │   └── SKILL.md
│   ├── study-session/
│   │   └── SKILL.md
│   └── session-summary/
│       └── SKILL.md
│
├── scripts/
│   ├── init_db.py
│   └── check_environment.py
│
├── storage/
│   └── .gitkeep
│
├── materials/
│   └── README.md
│
├── exports/
│   └── notebooklm/
│       └── .gitkeep
│
├── diagrams/
│   └── .gitkeep
│
├── docs/
│   └── .gitkeep
│
└── tests/
    └── .gitkeep
```

## Propósito de cada parte

### `README.md`

Documento principal del proyecto.

Más adelante contendrá:

- descripción;
- arquitectura;
- instalación;
- quickstart;
- ejemplos;
- roadmap.

Por ahora debe quedar vacío.

### `AGENTS.md`

Contendrá las reglas que deberán seguir los agentes que trabajen sobre este repositorio.

Más adelante definirá:

- principios arquitectónicos;
- comportamiento pedagógico;
- seguridad;
- reglas para modelos;
- convenciones de código;
- límites entre componentes.

Por ahora debe quedar vacío.

### `config/study.example.yaml`

Plantilla pública de configuración.

Más adelante podrá definir:

- duración de sesiones;
- providers;
- model routing;
- source engine;
- visualizaciones;
- materias;
- features.

La configuración real del usuario será otro archivo y no deberá versionarse.

Por ahora debe quedar vacío.

### `migrations/001_initial_schema.sql`

Primera migración de la base de datos.

Más adelante podrá definir tablas como:

- `subjects`;
- `topics`;
- `doubts`;
- `study_sessions`;
- `misconceptions`;
- `assessments`.

Por ahora debe quedar vacío.

### `skills/`

Contendrá las skills específicas del Study Agent.

#### `capture-doubt/`

Responsabilidad futura:

- capturar una duda;
- clasificarla;
- asociarla a materia y tema;
- guardarla con estado pendiente.

Archivo:

```text
skills/capture-doubt/SKILL.md
```

#### `study-session/`

Responsabilidad futura:

- iniciar sesión;
- pausar;
- reanudar;
- crear checkpoints;
- cerrar;
- restaurar una sesión anterior.

Archivo:

```text
skills/study-session/SKILL.md
```

#### `session-summary/`

Responsabilidad futura:

- resumir lo trabajado;
- registrar dudas;
- registrar errores;
- registrar progreso;
- definir el siguiente paso.

Archivo:

```text
skills/session-summary/SKILL.md
```

Todos los `SKILL.md` deben quedar vacíos por ahora.

### `scripts/`

Contendrá utilidades determinísticas.

#### `init_db.py`

Responsabilidad futura:

- crear `study.db`;
- ejecutar migraciones;
- validar el esquema.

#### `check_environment.py`

Responsabilidad futura:

- comprobar Python;
- comprobar SQLite;
- comprobar Hermes;
- comprobar herramientas opcionales;
- informar dependencias faltantes.

Ambos archivos deben quedar vacíos.

### `storage/`

Contendrá datos generados localmente.

Ejemplos futuros:

- `study.db`;
- índices;
- cache;
- estado local.

Se agrega `.gitkeep` únicamente para conservar el directorio vacío en Git.

### `materials/`

Biblioteca académica local.

Más adelante podrá contener:

```text
materials/
├── fisica/
├── algoritmos/
├── paradigmas/
└── data-engineering/
```

Aquí vivirán:

- libros;
- guías;
- parciales;
- apuntes;
- PDFs.

El `README.md` explicará posteriormente cómo organizar los materiales.

Por ahora debe quedar vacío.

### `exports/notebooklm/`

Contendrá artefactos preparados para NotebookLM.

Ejemplos futuros:

- Study Packs;
- Markdown;
- resúmenes;
- material para Audio Overviews.

Por ahora solo debe existir el directorio con `.gitkeep`.

### `diagrams/`

Contendrá visualizaciones generadas.

Ejemplos futuros:

- Mermaid;
- Graphviz;
- SVG;
- PNG;
- Excalidraw.

Por ahora solo `.gitkeep`.

### `docs/`

Documentación técnica del proyecto.

Más adelante podrá contener:

```text
architecture.md
source-engine.md
model-routing.md
study-sessions.md
security.md
notebooklm.md
```

No crear esos documentos todavía.

### `tests/`

Contendrá tests automatizados.

Más adelante podrá incluir:

- database tests;
- routing tests;
- skill tests;
- source retrieval tests;
- session tests.

Por ahora solo `.gitkeep`.

## Archivos que NO deben existir todavía

No crear todavía:

```text
.env
study.yaml
study.db
requirements.txt
pyproject.toml
Dockerfile
docker-compose.yml
package.json
credentials.json
auth.json
tokens.json
```

Se incorporarán únicamente cuando exista una necesidad concreta.

## Separación conceptual

La estructura debe permitir distinguir claramente:

```text
CORE PUBLICABLE
├── skills/
├── scripts/
├── migrations/
├── config/
└── docs/

DATOS PRIVADOS
├── storage/
├── materials/
└── configuración real del usuario
```

## Datos que nunca deben publicarse

Más adelante deberán mantenerse fuera del repositorio público:

```text
study.db
material académico con copyright
credenciales
tokens
cookies
sesiones de WhatsApp
API keys
logs personales
historial académico
```

## Resultado esperado

Después del scaffolding debe existir exactamente:

```text
hermes-study-agent/
├── README.md
├── AGENTS.md
├── .gitignore
├── config/
│   └── study.example.yaml
├── migrations/
│   └── 001_initial_schema.sql
├── skills/
│   ├── capture-doubt/
│   │   └── SKILL.md
│   ├── study-session/
│   │   └── SKILL.md
│   └── session-summary/
│       └── SKILL.md
├── scripts/
│   ├── init_db.py
│   └── check_environment.py
├── storage/
│   └── .gitkeep
├── materials/
│   └── README.md
├── exports/
│   └── notebooklm/
│       └── .gitkeep
├── diagrams/
│   └── .gitkeep
├── docs/
│   └── .gitkeep
└── tests/
    └── .gitkeep
```

## Prompt recomendado para el LLM

```text
Lee completamente este archivo.

Crea exactamente la estructura de carpetas y archivos indicada.

No escribas implementación dentro de ningún archivo.
No instales dependencias.
No inicialices bases de datos.
No configures Hermes.
No agregues credenciales.
No crees archivos adicionales.

Al finalizar, muestra únicamente el árbol de directorios creado.
```

## Primer commit

Una vez creada la estructura:

```bash
git init
git add .
git commit -m "chore: initial project structure"
```

## Próximo orden de trabajo

Después del scaffolding, avanzar en este orden:

```text
1. AGENTS.md
2. study.example.yaml
3. 001_initial_schema.sql
4. init_db.py
5. capture-doubt
6. study-session
7. session-summary
```

No implementar varias etapas simultáneamente.

La intención es entender con claridad qué responsabilidad agrega cada componente.
