# Hermes Study Agent

Núcleo local para guardar materias, dudas, sesiones y checkpoints en SQLite.
Hermes actúa como interfaz mediante skills de proyecto; los datos persistentes
siguen en `storage/study.db`.

## Arquitectura

```text
Hermes skills
    ↓ terminal → scripts/study_cli.py
scripts/study_store.py
    ↓ sqlite3
storage/study.db ← migrations/001_initial_schema.sql
```

Las skills se exponen a Hermes desde `.hermes/skills`, enlazado al directorio
versionado `skills/`. Hermes solo las carga si se confía explícitamente en el
repositorio:

```bash
hermes skills trust "$PWD"
hermes skills list --source local
```

## Base de datos

```bash
python3 scripts/init_db.py
```

El inicializador crea `storage/study.db` y aplica las migraciones. La capa de
datos no crea un esquema por su cuenta: si la base falta, primero hay que
inicializarla.

## Operaciones locales

```bash
python3 scripts/study_cli.py subjects add "Física II" --type problem_solving
python3 scripts/study_cli.py doubts add "Física II" "No entiendo por qué el flujo atraviesa las tapas."
python3 scripts/study_cli.py doubts pending --subject "Física II"
python3 scripts/study_cli.py session start "Física II" --target-minutes 75 --hard-limit-minutes 90
python3 scripts/study_cli.py session checkpoint 1 --current-exercise "8" --current-step "Calculando Q_enc"
python3 scripts/study_cli.py session close 1
python3 scripts/study_cli.py session restore "Física II"
```

Los IDs de sesión se obtienen de la respuesta JSON del comando `session start`.
Para probar sin tocar la base de datos local, se puede indicar otra ruta:

```bash
STUDY_DB_PATH=/tmp/study-test.db python3 scripts/init_db.py
STUDY_DB_PATH=/tmp/study-test.db python3 scripts/study_cli.py subjects list
```

Las duraciones de ejemplo corresponden a `study.default_session` en la
configuración pública; las skills deben leer la configuración antes de iniciar
una sesión.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Los tests de `study_store` usan bases temporales.

## Prueba manual con Hermes

Después de inicializar la base, registrar al menos una materia con el CLI y
confiar en este proyecto con `hermes skills trust "$PWD"`, iniciar una sesión
Hermes desde la raíz del repositorio. Probar:

1. Guardar una duda de una materia existente y confirmar el estado `pending`.
2. Pedir las dudas pendientes de esa materia.
3. Iniciar una sesión, guardar un checkpoint, cerrarla y pedir continuar esa
   materia. La skill debe restaurar el checkpoint desde SQLite.

No están implementados timers, cron ni integraciones externas.
