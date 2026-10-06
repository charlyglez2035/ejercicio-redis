Actúa como auditor técnico del proyecto "Library".

Los DOS trabajos anteriores ya fueron implementados:

1. Integración de Redis:

   * sesiones;
   * refresh tokens;
   * revocación JWT;
   * cache de Books;
   * TTL;
   * invalidación;
   * manejo seguro cuando Redis no está disponible;
   * REDIS_URL compartida.

2. Desarrollo/integración de:

   * login;
   * users;
   * authors;
   * books;
   * pedidos;
   * pagos;
   * JWT;
   * roles;
   * autorización;
   * aplicación Python TK;
   * formularios y CRUD.

## ARQUITECTURA REAL DEL PROYECTO

IMPORTANTE:

Los microservicios de Library están desplegados y ejecutándose en una VM.

La aplicación Python TK es el cliente que se ejecuta fuera de la VM y consume los microservicios mediante sus URLs/IP correspondientes.

Por lo tanto, NO trates el proyecto como si todos los servicios estuvieran ejecutándose localmente.

La auditoría debe distinguir claramente entre:

### VM

Aquí se encuentran:

* microservicio login;
* microservicio books;
* microservicio users;
* microservicio authors/autores;
* microservicio pedidos;
* microservicio pagos;
* Redis;
* PostgreSQL;
* logs de los microservicios;
* configuración de variables de entorno.

### PC/WSL

Aquí se encuentra:

* aplicación Python TK;
* código cliente;
* herramientas como SSH/curl/Redis CLI si las utilizo desde la máquina local.

Si alguna herramienta debe ejecutarse dentro de la VM, indícalo explícitamente.

---

# REGLAS ABSOLUTAS

NO MODIFIQUES NINGÚN ARCHIVO.

NO hagas commits.

NO instales dependencias.

NO ejecutes pruebas automatizadas.

NO ejecutes:

* pytest;
* unittest;
* coverage;
* linters;
* tests de integración.

NO levantes ni reinicies servicios automáticamente.

NO hagas requests automáticamente para probar el sistema.

NO ejecutes comandos destructivos.

Puedes inspeccionar código y configuración.

Puedes utilizar comandos de lectura/consulta para identificar:

* archivos;
* rutas;
* configuración;
* variables de entorno;
* procesos;
* servicios;
* logs;
* estructura;
* endpoints.

Si necesito ejecutar una comprobación real, indícame el comando exacto para que YO lo ejecute.

Tu trabajo es AUDITAR y PREPARAR LA GUÍA DE EVIDENCIAS.

---

# 1. AUDITORÍA DE LA ARQUITECTURA

Primero identifica:

* cómo están desplegados los microservicios en la VM;
* qué puertos utiliza cada uno;
* qué URLs utiliza la aplicación TK;
* dónde está Redis;
* dónde está PostgreSQL;
* cómo se levantan actualmente los servicios;
* cómo se configuran las variables de entorno.

NO asumas nombres de servicios o puertos.

Obtén los nombres reales inspeccionando el proyecto.

Dime algo equivalente a:

| Componente | Ubicación | Puerto/URL | Evidencia |
| ---------- | --------- | ---------- | --------- |
| Login      | VM        | ...        | ...       |
| Books      | VM        | ...        | ...       |
| Users      | VM        | ...        | ...       |
| Authors    | VM        | ...        | ...       |
| Pedidos    | VM        | ...        | ...       |
| Pagos      | VM        | ...        | ...       |
| Redis      | VM        | 6379       | ...       |
| PostgreSQL | VM        | ...        | ...       |
| TK         | PC/WSL    | local      | ...       |

---

# 2. AUDITORÍA DE REDIS EN LA VM

Verifica específicamente la instalación/configuración de Redis en la VM.

Determina:

* servicio/proceso utilizado;
* puerto;
* autenticación;
* REDIS_URL;
* host;
* DB utilizada;
* timeout;
* conexión desde cada microservicio.

Verifica que:

login, books, users, authors, pedidos y pagos

utilicen la misma instancia Redis compartida.

No expongas contraseñas reales en tu respuesta.

---

# 3. SESIONES Y REFRESH TOKENS

Inspecciona el código del microservicio login.

Determina:

* cómo se crea la sesión;
* cómo se almacena en Redis;
* qué clave utiliza;
* TTL;
* cómo se almacena el refresh token;
* TTL;
* cómo se elimina durante logout.

Después dame los comandos que YO debo ejecutar EN LA VM para comprobarlo.

Por ejemplo, si corresponde:

redis-cli ...

pero NO ejecutes esos comandos tú.

Indica:

**Comando:** ...

**Ejecutar en:** VM

**Qué debe aparecer:** ...

**Captura:** Sí/No

**Qué requisito demuestra:** ...

---

# 4. JWT

Audita:

* HS256;
* JWT_SECRET_KEY;
* expiración de 20 minutos;
* user_id;
* role_id;
* jti;
* firma.

Indica exactamente:

* archivo;
* función/clase;
* configuración.

Después dime cómo puedo verificar manualmente el JWT.

IMPORTANTE:

No me pidas exponer mi SECRET_KEY.

---

# 5. REVOCACIÓN JWT

Comprueba que Redis utilice:

jwt:revoked:<jti>

y que todos los servicios protegidos consulten esa clave.

Verifica:

* login;
* books;
* users;
* authors;
* pedidos;
* pagos.

Después proporciona el procedimiento para demostrarlo.

Las comprobaciones Redis deben estar orientadas a ejecutarse EN LA VM.

---

# 6. CACHE DE BOOKS

Audita:

GET /books

GET /books/{isbn}

Comprueba:

books:list:<filtros>

books:<isbn>

TTL.

Invalidación después de:

* POST;
* PUT;
* PATCH;
* DELETE.

Después dame los comandos exactos para inspeccionar Redis EN LA VM.

NO los ejecutes.

---

# 7. FAIL-SAFE DE REDIS

Audita el código para comprobar:

### Cache

Redis caído → GET /books puede utilizar PostgreSQL.

### Seguridad

Redis caído → no se debe aceptar un JWT cuando no se puede comprobar revocación.

No modifiques nada.

Si esto solamente puede comprobarse ejecutando una prueba manual, marca:

🔎 VERIFICACIÓN MANUAL NECESARIA

y dime exactamente cómo debo hacerla.

---

# 8. AUDITORÍA DE MICROSERVICIOS

Audita individualmente:

1. Login
2. Users
3. Authors
4. Books
5. Pedidos
6. Pagos

Para cada uno:

* ubicación en la VM;
* puerto;
* endpoints;
* métodos;
* autenticación;
* roles;
* PostgreSQL;
* Redis cuando corresponda.

---

# 9. CRUD

Verifica:

### Users

POST / GET / PUT / PATCH / DELETE

### Authors

POST / GET / PUT / PATCH / DELETE

### Books

POST / GET / PUT / PATCH / DELETE

### Pedidos

POST / GET / PUT / PATCH / DELETE

### Pagos

POST / GET / PUT / PATCH / DELETE

Si algún CRUD no existe o está incompleto, indícalo.

---

# 10. JWT Y AUTORIZACIÓN

Verifica:

POST → JWT

PUT → JWT

PATCH → JWT

DELETE → JWT

Comprueba:

* firma;
* algoritmo;
* expiración;
* user_id;
* role_id;
* jti;
* revocación Redis;
* permisos.

---

# 11. 401 Y 403

Determina cómo están implementados:

### 401

* JWT ausente;
* JWT inválido;
* JWT expirado;
* JWT revocado.

### 403

* JWT válido;
* rol insuficiente.

Después dame las peticiones manuales que YO debo hacer desde mi PC/WSL contra la IP/URL REAL de la VM.

NO ejecutes las peticiones.

NO inventes IPs ni puertos.

Utiliza los valores encontrados en el proyecto.

---

# 12. ROLES

Determina:

* roles existentes;
* role_id;
* operaciones permitidas;
* endpoints administrativos.

Dime exactamente qué usuario/rol necesito utilizar para demostrar:

* operación autorizada;
* operación rechazada por permisos.

---

# 13. TK

Audita la aplicación Python TK en mi PC/WSL.

Comprueba que consuma los microservicios que están en la VM.

Identifica:

* URL de login;
* URL de users;
* URL de books;
* URL de authors;
* URL de pedidos;
* URL de pagos.

Comprueba que no esté apuntando accidentalmente a:

localhost

cuando debería utilizar la VM.

Verifica que TK:

* haga login;
* reciba JWT;
* conserve el JWT;
* envíe Authorization: Bearer <JWT>;
* maneje 401;
* maneje 403;
* permita CRUD.

---

# 14. CAPTURAS DE LA VM

Quiero que me indiques exactamente qué capturas debo tomar DESDE LA VM.

Prioriza:

### Redis

1. Redis funcionando.
2. REDIS_URL/configuración sin revelar contraseña.
3. Sesión almacenada.
4. Refresh token.
5. TTL.
6. Logout/eliminación.
7. jwt:revoked:<jti>.
8. Cache books.
9. TTL cache.
10. Invalidación.

### Microservicios

11. Servicios/procesos levantados.
12. Logs de login.
13. Logs de Books.
14. Logs de Users.
15. Logs de Authors.
16. Logs de Pedidos.
17. Logs de Pagos.

No quiero capturas redundantes.

Si varios requisitos pueden demostrarse con una sola pantalla, indícalo.

---

# 15. CAPTURAS DE CÓDIGO

Indica exactamente qué archivos y bloques de código debo capturar.

Prioridad:

1. REDIS_URL.
2. conexión Redis.
3. sesión.
4. refresh token.
5. logout.
6. JWT HS256.
7. expiración 20 minutos.
8. claims.
9. revocación.
10. middleware JWT.
11. roles.
12. cache Books.
13. invalidación.
14. CRUD.
15. hashing.
16. CORS.
17. TK HTTP client.

Para cada captura:

**Archivo:**

**Buscar:**

**Bloque que debe verse:**

**Requisito demostrado:**

---

# 16. CAPTURAS DESDE PC/WSL

Indica qué debo ejecutar desde mi PC/WSL para demostrar que puedo llegar a los microservicios de la VM.

Por ejemplo:

* curl;
* SSH;
* comandos de red;
* requests manuales.

Pero NO los ejecutes.

Dime exactamente:

**Ejecutar en:** PC/WSL

**Comando:** ...

**Resultado esperado:** ...

**Captura:** Sí

**Nombre:** ...

---

# 17. CAPTURAS DE LA APLICACIÓN TK

Indica exactamente qué pantallas debo capturar:

1. Login.
2. Menú principal.
3. Users.
4. Authors.
5. Books.
6. Pedidos.
7. Pagos.
8. CRUD.
9. permisos.
10. errores 401/403.

Optimiza las capturas.

No quiero una captura por cada botón.

---

# 18. EVIDENCIAS DE CRUD

Diseña una secuencia eficiente para cada microservicio:

Crear → consultar/listar → modificar → eliminar.

Indica qué operaciones realmente necesito demostrar y cuáles pueden quedar cubiertas por una misma evidencia.

---

# 19. EVIDENCIAS DE SEGURIDAD

Diseña capturas para demostrar:

### 401

* sin JWT;
* JWT inválido;
* JWT expirado;
* JWT revocado.

### 403

* JWT válido;
* rol insuficiente.

Las peticiones se harán desde PC/WSL hacia la VM.

NO las ejecutes.

---

# 20. LOGS

Dime exactamente qué logs debo capturar EN LA VM para demostrar:

* login;
* autenticación;
* autorización;
* rechazo;
* Redis;
* cache hit;
* cache miss;
* logout.

Comprueba mediante inspección que los logs no expongan:

* contraseña;
* JWT completo;
* refresh token;
* JWT_SECRET_KEY;
* contraseña Redis.

Si exponen alguno:

❌ NO CUMPLE

Indica el archivo/línea responsable.

NO modifiques nada.

---

# 21. MATRIZ FINAL

Genera:

| # | Requisito | Implementado | Dónde | Cómo comprobar | Captura |
| - | --------- | ------------ | ----- | -------------- | ------- |

Incluye TODOS los requisitos de las dos etapas.

Estados:

✅ CUMPLE

⚠️ PARCIAL

❌ NO CUMPLE

🔎 VERIFICAR MANUALMENTE

---

# 22. PLAN FINAL DE CAPTURAS

Quiero el número MÍNIMO de capturas necesarias para demostrar el proyecto completo.

Para cada captura:

## CAPTURA XX — Nombre

**Dónde:**
VM / PC-WSL / TK / VS Code

**Qué abrir:**

**Qué ejecutar:**

**Qué debe verse:**

**Qué requisito demuestra:**

**Nombre del archivo:**

No me des recomendaciones genéricas.

Quiero instrucciones concretas.

---

# 23. ORDEN DE DEMOSTRACIÓN

Finalmente crea una guía paso a paso que yo pueda seguir:

### FASE 1 — VM

1. Verificar Redis.
2. Verificar PostgreSQL.
3. Verificar microservicios.
4. Verificar configuración.
5. Tomar capturas.

### FASE 2 — Redis

6. Login.
7. Sesión.
8. Refresh token.
9. TTL.
10. Logout.
11. Revocación.
12. Cache.
13. Invalidación.
14. Tomar capturas.

### FASE 3 — API

15. Login.
16. CRUD.
17. 401.
18. 403.
19. Roles.
20. Tomar capturas.

### FASE 4 — TK

21. Login.
22. Users.
23. Authors.
24. Books.
25. Pedidos.
26. Pagos.
27. CRUD.
28. Tomar capturas.

### FASE 5 — SEGURIDAD

29. Logs.
30. HTTPS/CORS.
31. Tokens.
32. Tomar capturas.

Adapta el orden si la arquitectura real del proyecto lo requiere.

---

# RESULTADO FINAL

Termina con:

## A. Lo que sí está implementado

## B. Lo que está parcialmente implementado

## C. Lo que falta

## D. Lo que requiere comprobación manual

## E. Lista definitiva de capturas

## F. Procedimiento definitivo para tomar las capturas

IMPORTANTE:

NO MODIFIQUES EL PROYECTO.

NO EJECUTES PRUEBAS.

NO EJECUTES PETICIONES DE PRUEBA.

NO LEVANTES SERVICIOS.

NO HAGAS CAMBIOS.

SOLO AUDITA Y DAME LA GUÍA EXACTA.

Recuerda siempre:

**Microservicios + Redis + PostgreSQL = VM**

**Aplicación TK = PC/WSL**

Las comprobaciones que involucren Redis, PostgreSQL, procesos o logs de microservicios deben indicar explícitamente que se realizan EN LA VM.
