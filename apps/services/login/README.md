# Microservicio de login

Servicio Flask independiente para autenticacion contra la tabla `app_user` de la base de datos `library`. Reutiliza `password_hash` y `full_name` del esquema existente, por lo que no duplica contrasenas ni crea una tabla adicional.

## Instalacion y ejecucion

Desde `library/`:

```powershell
python -m pip install -r apps/services/login/requirements.txt
python apps/services/login/app.py
```

El servicio escucha en `http://localhost:5000`. Swagger queda disponible en `http://localhost:5000/apidocs/`.

Copia `.env.example` a `.env` y ajusta las credenciales de PostgreSQL. `LOGIN_CORS_ORIGINS` acepta una lista separada por comas. Las cookies de sesion solo se permiten desde esos origenes y se envian con credenciales.

Aplica la migracion de verificacion antes de iniciar el servicio:

```bash
psql -h localhost -p 5432 -U library_user -d library -f db/login-verification.sql
```

Configura `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USER` y `SMTP_PASSWORD` en `.env`. Para Gmail se necesita una contrasena de aplicacion, no la contrasena normal de la cuenta. `LOGIN_PUBLIC_URL` debe ser la URL que el usuario pueda abrir; en local es `http://localhost:5000`.

## Formatos

Todos los endpoints aceptan `?format=xml` y `?format=json`. El formato predeterminado es XML, como solicita el ejercicio. Tambien se reconoce `Accept: application/json` cuando no se envia `format`.

Ejemplo de registro:

```json
{
  "nombre": "Ana",
  "apellido_paterno": "Martinez",
  "apellido_materno": "Lopez",
  "email": "ana@example.com",
  "password": "una-clave-segura"
}
```

Los nombres se combinan en `full_name` para conservar compatibilidad con el monolito actual. Las respuestas incluyen `_links` con las operaciones relacionadas (HATEOAS), y nunca incluyen `password` ni `password_hash`.

## Endpoints

- `POST /register`: valida el formato y los registros MX del dominio, crea la cuenta no verificada y envia el enlace por correo.
- `GET /verify-email?token=...`: confirma el correo y activa la cuenta durante 24 horas.
- `POST /login`: comprueba las credenciales bcrypt y crea la sesion Flask solo si el correo esta verificado.
- `POST /logout`: destruye la sesion.
- `GET /session`: indica si existe una sesion autenticada.
- `GET /health`: comprueba el servicio y PostgreSQL.

Cada endpoint responde errores con el mismo formato solicitado. Las pruebas manuales deben conservar la cookie de sesion, por ejemplo usando `curl -c cookies.txt` y `curl -b cookies.txt`.

La comprobacion MX filtra dominios inexistentes, mientras que el enlace SMTP confirma que el usuario controla el buzon. CAPTCHA es opcional y sirve para frenar bots, no para validar la existencia del correo.
