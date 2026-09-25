# PLAN.md — Hermes Study Agent / Foundation Phase

## Objetivo

Construir únicamente la base local y determinística del proyecto.

No integrar todavía:
- Hermes
- Codex OAuth
- otros LLMs
- WhatsApp
- NotebookLM
- ActivityWatch
- Tailscale
- RAG / embeddings
- vector databases
- dashboards

La meta de esta etapa es dejar funcionando:
- configuración base;
- SQLite;
- migraciones;
- inicialización de base;
- estructura de sesiones;
- dudas;
- checkpoints;
- tests mínimos.

## Contexto obligatorio

Antes de modificar archivos:
1. Leer `AGENTS.md`.
2. Leer `config/study.example.yaml`.
3. Leer `hermes_study_agent_structure.md`.
4. Inspeccionar la estructura actual del repositorio.
5. No crear nuevas carpetas salvo que sean estrictamente necesarias.
6. No agregar dependencias externas sin necesidad.

# Fase 1 — Base de datos

Archivo: `migrations/001_initial_schema.sql`

Crear únicamente estas tablas:

## subjects
Campos:
- `id`
- `name`
- `type`
- `active`
- `created_at`

Restricciones:
- `name` obligatorio.
- `name` único.
- `active` por defecto verdadero.

## doubts
Campos:
- `id`
- `subject_id`
- `text`
- `status`
- `created_at`
- `resolved_at`

Estados previstos:
- `pending`
- `studying`
- `resolved`
- `review`

Crear foreign key hacia `subjects`.

## study_sessions
Campos:
- `id`
- `subject_id`
- `started_at`
- `ended_at`
- `target_minutes`
- `hard_limit_minutes`
- `status`

Estados iniciales:
- `active`
- `paused`
- `completed`
- `cancelled`

Crear foreign key hacia `subjects`.

## checkpoints
Campos:
- `id`
- `session_id`
- `current_topic`
- `current_source`
- `current_exercise`
- `current_step`
- `next_action`
- `created_at`

Crear foreign key hacia `study_sessions`.

## Reglas SQL

Usar SQLite.

Activar:

```sql
PRAGMA foreign_keys = ON;
```

Usar `INTEGER PRIMARY KEY AUTOINCREMENT` para identificadores.

No crear todavía:
- topics
- misconceptions
- assessments
- sources
- embeddings
- model_usage
- activity_events

# Fase 2 — Inicialización de la base

Archivo: `scripts/init_db.py`

Responsabilidades:
1. localizar la raíz del proyecto;
2. localizar `migrations/`;
3. crear `storage/` si no existe;
4. crear `storage/study.db`;
5. descubrir archivos `.sql`;
6. ordenarlos por nombre;
7. ejecutar las migraciones;
8. activar foreign keys;
9. mostrar mensajes claros.

No usar dependencias externas.

Usar únicamente:
- `sqlite3`
- `pathlib`

# Fase 3 — Verificación de entorno

Archivo: `scripts/check_environment.py`

Verificar:
- versión de Python;
- existencia de `sqlite3` de Python;
- existencia de carpetas importantes;
- existencia de `study.example.yaml`;
- existencia de migraciones;
- existencia opcional del comando `hermes`.

Hermes NO debe ser obligatorio todavía.

Resultado esperado:

```text
[OK] Python
[OK] SQLite
[OK] config
[OK] migrations
[INFO] Hermes not installed
```

No instalar nada automáticamente.

# Fase 4 — Configuración

Revisar `config/study.example.yaml`.

Validar únicamente que sea coherente con el esquema implementado.

No agregar proveedores LLM.
No agregar secretos.
No crear todavía `study.yaml`.

# Fase 5 — Skill capture-doubt

Archivo: `skills/capture-doubt/SKILL.md`

Definir la especificación de la skill.

No implementar integración real con Hermes todavía.

Input de ejemplo:

```text
No entiendo por qué el flujo atraviesa las tapas.
```

Output conceptual:

```json
{
  "subject": "Física II",
  "text": "No entiendo por qué el flujo atraviesa las tapas.",
  "status": "pending"
}
```

Responsabilidad:
- identificar materia cuando sea posible;
- guardar duda;
- establecer estado inicial;
- confirmar almacenamiento.

No iniciar automáticamente una sesión de tutoría.

# Fase 6 — Skill study-session

Archivo: `skills/study-session/SKILL.md`

Documentar:
- start;
- pause;
- resume;
- checkpoint;
- close;
- restore.

Definir:
- `target_minutes`
- `hard_limit_minutes`

El timer debe ser determinístico.

No implementar todavía Hermes cron.

# Fase 7 — Skill session-summary

Archivo: `skills/session-summary/SKILL.md`

Documentar qué debe producir al cerrar una sesión:
- materia;
- duración;
- contenido trabajado;
- dudas;
- checkpoint;
- próximo paso.

No utilizar todavía un LLM real.

# Fase 8 — Tests

Crear tests mínimos para:

## Database
Verificar que existen:
- `subjects`
- `doubts`
- `study_sessions`
- `checkpoints`

## Foreign keys
Verificar relaciones.

## init_db
Verificar que:
- crea la base;
- aplica la migración;
- produce el esquema esperado.

Usar `unittest` de la standard library inicialmente.

No agregar `pytest` todavía.

Los tests no deben modificar la base real del usuario.
Utilizar una base temporal.

# Fase 9 — .gitignore

Asegurar que no se versionen:

```text
storage/study.db
config/study.yaml
.env
auth.json
credentials.json
tokens.json
__pycache__/
*.pyc
```

No ignorar:
- `study.example.yaml`
- `migrations/`
- `skills/`
- `tests/`

# Fase 10 — README

Actualizar `README.md` únicamente con información de esta fase:
- qué es el proyecto;
- estado actual;
- cómo crear la base;
- cómo ejecutar comprobación de entorno;
- cómo ejecutar tests.

No documentar todavía integraciones no implementadas como si ya funcionaran.

# Criterios de aceptación

Debe funcionar:

```bash
python3 scripts/check_environment.py
```

También:

```bash
python3 scripts/init_db.py
```

debe crear:

```text
storage/study.db
```

Deben existir las tablas:
- `subjects`
- `doubts`
- `study_sessions`
- `checkpoints`

Los tests deben finalizar correctamente.

# Restricciones

No:
- instalar frameworks;
- implementar servidor web;
- implementar API;
- configurar Hermes;
- conectar modelos;
- crear embeddings;
- usar Docker;
- agregar PostgreSQL;
- agregar frontend;
- implementar NotebookLM;
- implementar WhatsApp;
- implementar ActivityWatch;
- implementar Tailscale;
- crear multiagentes.

Mantener esta etapa pequeña y completamente local.

# Entrega final de Codex

Después de implementar:
1. listar los archivos modificados;
2. explicar brevemente cada cambio;
3. ejecutar los tests;
4. mostrar resultados;
5. señalar cualquier decisión no prevista;
6. no continuar con la siguiente fase sin nueva instrucción.

# Instrucción sugerida para Codex

```text
Lee primero AGENTS.md y PLAN.md completos.

Implementa únicamente la foundation phase descrita en PLAN.md.

No avances a integraciones futuras.

Ejecuta las verificaciones y tests al terminar.

Si alguna decisión no está definida, elige la opción más simple y consistente con AGENTS.md.
```
