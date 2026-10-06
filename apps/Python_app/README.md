# Python_app: microservicio de libros

Microservicio Flask para el catálogo de libros. Expone respuestas JSON y XML, Swagger, CORS, PostgreSQL y el ciclo CRUD solicitado.

## Estructura

- `app.py`: API Flask y vistas HTML.
- `requirements.txt`: dependencias Python.
- `.env.example`: variables necesarias sin credenciales reales.
- `scripts/run_cycle.py`: prueba reproducible `POST -> GET -> PATCH -> GET -> DELETE -> GET`.
- `evidencias/`: resultados JSON y capturas del ejercicio.
- `docs/`: bitácora, reflexión y notas de ejecución.

## Instalación local

Desde la raíz del repositorio:

```bash
cd library
python -m venv .venv
source .venv/bin/activate
pip install -r apps/Python_app/requirements.txt
cp apps/Python_app/.env.example apps/Python_app/.env
```

Configura PostgreSQL en `.env` y ejecuta:

```bash
SERVICE_PORT=5101 python apps/Python_app/app.py
```

Endpoints principales:

- `GET /api/health?format=json`
- `GET /books?format=json`
- `POST /books?format=json`
- `PATCH /books/{isbn}?format=json`
- `PUT /books/{isbn}?format=json` (compatibilidad)
- `DELETE /books/{isbn}?format=json`
- `GET /apidocs/`

## Evidencia del ciclo CRUD

Con el servicio local activo en `http://127.0.0.1:5101`:

```bash
python apps/Python_app/scripts/run_cycle.py
```

El script genera `evidencias/cycle_local.json` y `evidencias/cycle_remote.json`. El ISBN usado es temporal y se elimina al final del ciclo.

## Servicio remoto

La URL documentada para la evidencia remota es `http://34.51.65.146:5001`. Durante la captura del 22 de septiembre de 2026, el host no respondió dentro del timeout; ese resultado está documentado en la bitácora y no se presenta como ejecución exitosa.

## Seguridad

No subas `.env`, contraseñas, tokens ni contraseñas de aplicación. Usa `.env.example` como plantilla.
