# Libreria web y servicios JWT

Aplicacion Node.js MVC con PostgreSQL y microservicios Flask: login (5000), books (`apps/services/soap`, 5001), users (5002), authors (5003), pedidos (5004) y pagos (5005). El catalogo conserva sus formularios; `/jwt-demo` demuestra consultas publicas y escrituras protegidas con JWT en el microservicio book. El cliente Tkinter (`apps/Python_app/tkinter_client.py`) consume los seis servicios.

## Modelo

`db/scheme.sql` normaliza libros, autores, generos, conceptos, imagenes, formatos, categorias y usuarios. Las dependencias multivaluadas se resuelven con `book_author`, `book_genre`, `book_concept` y `book_image`. `book_concept` conserva una definicion distinta por libro y el indice parcial `one_admin_only_idx` limita a un administrador.

## Ejecucion local en WSL

Instala los paquetes del sistema y PostgreSQL si aun no estan disponibles:

```bash
sudo apt update
sudo apt install -y nodejs npm python3 python3-pip python3-venv python3-tk postgresql postgresql-client
```

PostgreSQL local de WSL usa el puerto `5432`; si no esta iniciado, arranca el servicio con `sudo service postgresql start`.

### Redis compartido

Todos los microservicios Flask usan la misma instancia Redis (`REDIS_URL`) para sesiones, refresh tokens, revocacion JWT y cache del catalogo. PostgreSQL sigue siendo la fuente principal de datos.

```bash
sudo apt install -y redis-server
# Define una contraseña propia (no la versiones):
sudo sed -i 's/^#\? *requirepass .*/requirepass TU_PASSWORD_REDIS/' /etc/redis/redis.conf
sudo service redis-server restart
redis-cli -a 'TU_PASSWORD_REDIS' --no-auth-warning ping   # PONG
```

En cada `.env` de servicio usa el mismo valor: `REDIS_URL=redis://:TU_PASSWORD_REDIS@localhost:6379/0`. Si la contraseña tiene caracteres especiales, codificalos en URL.

Desde `library/`, configura las variables locales y una clave JWT aleatoria compartida solo por los dos servicios Flask:

```bash
cp .env.example .env
cp apps/services/login/.env.example apps/services/login/.env
cp apps/services/soap/.env.example apps/services/soap/.env
for s in users authors pedidos pagos; do cp -n apps/services/$s/.env.example apps/services/$s/.env; done
python3 -c 'import secrets; print("JWT_SECRET=" + secrets.token_urlsafe(48)); print("SESSION_SECRET=" + secrets.token_urlsafe(48))'
# Guarda el MISMO JWT_SECRET y REDIS_URL en los seis .env de servicios y SESSION_SECRET en .env raiz.
```

Aplica el esquema inicial si la base aun no existe y luego las migraciones aditivas:

```bash
psql -h localhost -p 5432 -U library_user -d library -f db/scheme.sql
psql -h localhost -p 5432 -U library_user -d library -f db/login-verification.sql
psql -h localhost -p 5432 -U library_user -d library -f db/orders-payments.sql
```

Instala dependencias Python y Node:

```bash
python3 -m venv .venv
source .venv/bin/activate
for s in login soap users authors pedidos pagos; do python3 -m pip install -r apps/services/$s/requirements.txt; done
npm install
```

Inicia cada servicio en su terminal WSL, desde `library/`:

```bash
python3 apps/services/login/app.py     # 5000
python3 apps/services/soap/app.py      # 5001 (books)
python3 apps/services/users/app.py     # 5002
python3 apps/services/authors/app.py   # 5003
python3 apps/services/pedidos/app.py   # 5004
python3 apps/services/pagos/app.py     # 5005
npm start                              # 3000
```

Visita `http://localhost:3000/jwt-demo`. El cliente Tkinter se inicia con `python3 apps/Python_app/tkinter_client.py`; toma las URL `*_SERVICE_URL` del `.env` raiz (o se editan en la pestaña Login). Tkinter consume HTTP, guarda el JWT solo en memoria y no se conecta a PostgreSQL.

### Roles

Se reutiliza la columna `app_user.role` (`customer` o `admin`, un solo admin por `one_admin_only_idx`). El JWT incluye `user_id` y `role_id` (= `role`). Las escrituras de catalogo (books, authors, stock), la gestion de usuarios y la administracion de pagos exigen `admin` (403 si el JWT es valido pero el rol no alcanza). Un `customer` gestiona su perfil, sus pedidos (crear, lineas, cancelar mientras esten `pending`) y registra pagos de sus pedidos.

## Configuracion

`JWT_SECRET` es obligatorio y debe ser una clave aleatoria de al menos 32 bytes, igual en los `.env` de los seis servicios (login, soap, users, authors, pedidos, pagos). Los CORS se configuran con `LOGIN_CORS_ORIGINS`, `BOOKS_CORS_ORIGINS`, `USERS_CORS_ORIGINS`, `AUTHORS_CORS_ORIGINS`, `PEDIDOS_CORS_ORIGINS` y `PAGOS_CORS_ORIGINS` (lista de origenes, sin `*`). Copia los `.env.example` de ambos servicios y pega en ellos el mismo valor generado; Express no necesita ni recibe esa clave. No existe secreto de respaldo. `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_EXPIRES_IN_SECONDS` (1200 = 20 min), `REFRESH_TOKEN_TTL_SECONDS` y `REDIS_URL` deben coincidir. Las variables PostgreSQL viven en el `.env` raíz. Ningun `.env` se versiona.

Redis (`apps/services/shared/redis_store.py`):

- `session:<sid>` (hash) y `refresh:<sha256 del refresh token>` con TTL `REFRESH_TOKEN_TTL_SECONDS` (30 min, igual que la sesion web). No se guardan contraseñas ni tokens en claro.
- `jwt:revoked:<jti>` con TTL igual al tiempo restante del JWT.
- `books:list:<filtros>` y `books:<isbn>` con TTL `BOOKS_CACHE_TTL_SECONDS` (60 s); se invalidan tras POST/PUT/PATCH/DELETE en el servicio book. Las escrituras hechas directamente por el monolito sobre PostgreSQL se reflejan al expirar ese TTL.
- Si Redis falla, las lecturas del catalogo consultan PostgreSQL (`X-Cache: BYPASS`); login, refresh, logout y cualquier peticion con JWT responden 503: nunca se acepta un token sin comprobar su revocacion.
- `GET /health` de login y book muestra el estado de Redis y contadores (hits, misses, errores, revocaciones, sesiones).

`DB_PASSWORD` en el `.env` raíz no puede quedar vacío: debe coincidir con la contraseña PostgreSQL de `DB_USER` (por defecto `library_user`). El monolito y users, authors, pedidos y pagos leen esas variables desde ese archivo; login y book (soap) solo leen su propio `.env`, por lo que ahi deben repetirse las variables `DB_*`.

La revocacion JWT ahora vive en Redis; la tabla `jwt_revocation` (`db/jwt-revocations.sql`) ya no se consulta y puede conservarse sin efecto.

## Endpoints

- Publicos: `POST /register`, `POST /login`, `POST /refresh` (body `{"refresh_token": "..."}`), `GET /health`, `GET /api/books`, `GET /api/books/{isbn}` y equivalentes publicos `/books`.
- Requieren `Authorization: Bearer <token>`: `GET /session`, `POST /logout`, `POST /api/books`, `PUT/PATCH/DELETE /api/books/{isbn}` y sus alias `/books` (las escrituras de libros exigen rol `admin`).
- `OPTIONS` queda publico. `session` y `logout` requieren un token valido; logout revoca el `jti` en Redis hasta su expiracion y elimina la sesion y su refresh token. `refresh` es de un solo uso: emite un nuevo par y revoca el access token anterior.
- La web actua como proxy y conserva el JWT en la sesion de Express; nunca lo entrega al navegador. La consola muestra respuestas reales de los microservicios y redacta credenciales.
- Users (5002): `GET /roles` (publico); `GET /users` (admin); `GET/PUT/PATCH /users/{id}` (admin o el propio usuario; rol y verificacion solo admin); `POST /users` y `DELETE /users/{id}` (admin). Cambiar contraseña, correo o rol, o eliminar al usuario, revoca todas sus sesiones en Redis.
- Authors (5003): `GET /authors`, `GET /authors/{id}`, `GET /authors/{id}/books` (publicos); `POST /authors`, `PUT/PATCH/DELETE /authors/{id}`, `POST /authors/{id}/books`, `DELETE /authors/{id}/books/{isbn}` (admin). Invalida el cache de books.
- Pedidos (5004): `GET /pedidos/estados`, `GET /stock`, `GET /stock/{isbn}` (publicos); `GET/POST /pedidos`, `GET/PUT/PATCH /pedidos/{id}`, `GET/POST /pedidos/{id}/lineas`, `PUT/PATCH/DELETE /pedidos/{id}/lineas/{isbn}` (JWT, dueño o admin); `DELETE /pedidos/{id}` y `PATCH /stock/{isbn}` (admin). El stock se descuenta al crear lineas y se devuelve al quitarlas o cancelar.
- Pagos (5005): `GET /pagos/estados` (publico); `GET/POST /pagos`, `GET /pagos/{id}` (JWT, dueño o admin); `PUT/PATCH/DELETE /pagos/{id}` (admin). Un pago `approved` que cubre el total pasa el pedido a `paid`; un `refunded` de un pedido `paid` lo cancela y devuelve stock.
- Todos aceptan `?format=json` (XML por defecto) y exponen `GET /health` con PostgreSQL y Redis.

Registro sigue usando los campos `nombre`, `apellido_paterno`, `apellido_materno`, `email` y `password`; el inicio de sesion usa `identity` y `password`. El registro exige verificacion de correo segun la configuracion SMTP existente.

## Estructura

- `apps/web-monolito/src/server.js`: composicion del monolito y proxy JWT.
- `apps/web-monolito/src/routes`: controladores HTTP MVC.
- `apps/web-monolito/views`: vistas EJS.
- `apps/web-monolito/public`: estilos y cargas de imagenes.
- `apps/services/shared/jwt_security.py`: emision, validacion, revocacion, roles (`require_role`) y sanitizacion compartidas.
- `apps/services/shared/redis_store.py`: cliente Redis compartido, cache y metricas.
- `apps/services/shared/service.py`: base comun de users, authors, pedidos y pagos (env, CORS, JSON/XML, errores, health).
- `apps/services/shared/orders.py`: reglas de estado y stock compartidas por pedidos y pagos.
- `apps/services/{users,authors,pedidos,pagos}/app.py`: microservicios nuevos.
- `apps/Python_app/tkinter_client.py`: cliente Tkinter de todos los servicios.
- `db/scheme.sql`: esquema PostgreSQL inicial.
- `db/orders-payments.sql`: migracion aditiva de pedidos, lineas y pagos.
- `db/jwt-revocations.sql`: migracion historica de revocacion (sustituida por Redis).

