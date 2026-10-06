# Bitácora de pruebas

**Fecha:** 22 de septiembre de 2026  
**Proyecto:** `apps/Python_app`  
**Entorno local:** Ubuntu dentro de WSL, Python 3.14, Flask, PostgreSQL 18.

## Pruebas realizadas

| Prueba | Resultado | Evidencia |
|---|---:|---|
| Compilación de `app.py` | OK | `python -m py_compile` sin salida de error |
| `GET /api/health?format=json` local | 200 | `cycle_local.json` |
| `POST /books?format=json` local | 201 | `cycle_local.json` |
| `GET /books/{isbn}` después de POST | 200 | `cycle_local.json` |
| `PATCH /books/{isbn}` local | 200 | `cycle_local.json` |
| `GET /books/{isbn}` después de PATCH | 200 | `cycle_local.json` |
| `DELETE /books/{isbn}` local | 200 | `cycle_local.json` |
| `GET /books/{isbn}` después de DELETE | 404 esperado | `cycle_local.json` |
| Servicio remoto `34.51.65.146:5001` | No disponible | timeout documentado |

## Criterio de limpieza

El ISBN de prueba se genera temporalmente, se crea durante el ciclo y se elimina al finalizar. La consulta final devuelve `404`, lo que confirma que no quedó basura de prueba en la base local.

## Observación remota

Se intentó `GET /health?format=json` y el endpoint remoto no respondió dentro del tiempo de espera. También se intentó el ciclo remoto con timeout controlado. Esta evidencia se conserva como resultado de disponibilidad, no como una prueba CRUD exitosa.
