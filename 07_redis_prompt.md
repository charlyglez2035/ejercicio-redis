Actúa como desarrollador backend especializado en microservicios, Redis, JWT y PostgreSQL.

Trabaja SOBRE EL PROYECTO ACTUAL DE "Library" que te proporciono. Primero inspecciona únicamente la estructura y el código necesario para entender cómo están implementados actualmente los microservicios. NO rehagas la arquitectura existente y NO cambies tecnologías que ya funcionan.

## OBJETIVO

Integrar Redis como una capa compartida entre los microservicios, manteniendo PostgreSQL como fuente principal de datos.

Microservicios involucrados:

* login
* books
* users
* autores
* pedidos
* pagos

Redis debe utilizarse para:

1. Sesiones.
2. Refresh tokens.
3. Revocación de JWT.
4. Cache de consultas públicas del catálogo.
5. Coordinación de tareas temporales cuando sea necesario.

## RESTRICCIONES IMPORTANTES

* IMPLEMENTA los cambios directamente en el proyecto.
* NO ejecutes pruebas automatizadas.
* NO ejecutes pytest, unittest, npm test, coverage, linters ni suites de pruebas.
* NO levantes todos los servicios para probarlos.
* NO hagas requests de prueba con curl/Postman.
* NO gastes tokens generando pruebas innecesarias.
* No cambies funcionalidades que no estén relacionadas con Redis.
* No cambies PostgreSQL como fuente principal de datos.
* Conserva la estructura y convenciones existentes del proyecto siempre que sea posible.
* Reutiliza utilidades existentes antes de crear nuevas.
* No agregues dependencias innecesarias.
* Si necesitas modificar configuración, hazlo de forma compatible con el despliegue actual.
* No inventes variables, endpoints o estructuras que contradigan el código existente.
* Si existe `.env.example`, actualízalo sin incluir contraseñas reales.

## 1. REDIS COMPARTIDO

Añade Redis al despliegue existente.

Todos estos microservicios deben poder utilizar la misma instancia Redis:

* login
* books
* users
* autores
* pedidos
* pagos

Configura en todos ellos:

REDIS_URL=redis://:password@host:6379/0

La URL debe obtenerse mediante variable de entorno y NO quedar hardcodeada.

Implementa una configuración/utilidad Redis reutilizable cuando la arquitectura actual lo permita.

Debe contemplar:

* conexión reutilizable/pool;
* timeout de conexión;
* timeout de operaciones;
* autenticación mediante la contraseña de REDIS_URL;
* manejo de desconexión;
* reconexión cuando sea apropiado;
* cierre correcto de conexiones;
* métricas básicas relacionadas con Redis si el proyecto ya dispone de mecanismo de métricas; si no existe, implementa únicamente lo necesario y sencillo.

## 2. LOGIN, SESIONES Y REFRESH TOKENS

En el microservicio login:

* Guarda la sesión en Redis.
* Guarda el refresh token en Redis.
* Ambos deben tener TTL.
* El TTL debe ser coherente con la expiración real de los tokens.
* El JWT de acceso debe conservar una expiración de 20 minutos.
* No almacenes información innecesaria.
* No almacenes contraseñas en Redis.

Al ejecutar:

POST /logout

deben eliminarse de Redis los datos correspondientes a la sesión y al refresh token.

Mantén la funcionalidad existente de autenticación y adapta la implementación actual en lugar de duplicarla.

## 3. REVOCACIÓN DE JWT

Implementa una lista de revocación en Redis.

Cada JWT debe utilizar su `jti` como identificador.

La clave debe seguir exactamente este formato:

jwt:revoked:<jti>

Cuando un JWT sea revocado:

* crear la clave correspondiente en Redis;
* asignarle TTL;
* el TTL debe cubrir como máximo el tiempo restante de vida del JWT.

TODOS los microservicios que acepten JWT deben comprobar la revocación antes de autorizar la petición:

* login, cuando corresponda
* books
* users
* autores
* pedidos
* pagos

La validación debe seguir conceptualmente:

1. validar firma;
2. validar expiración;
3. obtener `jti`;
4. consultar `jwt:revoked:<jti>` en Redis;
5. rechazar el JWT si la clave existe;
6. continuar con autorización únicamente si no está revocado.

No confíes únicamente en el almacenamiento local del servicio.

## 4. CACHE DEL CATÁLOGO

En books implementa cache Redis para las consultas públicas:

GET /books

GET /books/{isbn}

Utiliza claves con este formato:

books:list:<filtros>

books:<isbn>

Los filtros deben formar parte de la clave de forma determinista para evitar colisiones.

Usa un TTL corto y coherente para el catálogo.

Flujo:

GET /books:

1. Construir la clave.
2. Consultar Redis.
3. Si existe cache, devolverla.
4. Si no existe, consultar PostgreSQL.
5. Guardar el resultado en Redis con TTL.
6. Devolver el resultado.

GET /books/{isbn} debe seguir el mismo patrón.

PostgreSQL continúa siendo la fuente principal.

## 5. INVALIDACIÓN DEL CACHE

Después de cualquier operación que pueda modificar libros:

* POST
* PUT
* PATCH
* DELETE

deben invalidarse las claves relacionadas con el catálogo.

Como mínimo:

* books:<isbn>
* books:list:<filtros>

Implementa la estrategia de invalidación que mejor se adapte a la estructura existente.

No dejes cache potencialmente obsoleto después de una modificación.

## 6. FALLA SEGURA

Diferencia claramente entre operaciones donde Redis puede fallar y operaciones donde NO puede fallar.

### Redis opcional:

Para lecturas cacheadas del catálogo:

* si Redis no está disponible, continuar consultando PostgreSQL;
* no convertir una falla de cache en una caída del endpoint público.

### Redis obligatorio:

Para:

* sesiones;
* refresh tokens;
* revocación;
* autorización basada en revocación.

Si Redis no está disponible, la operación debe FALLAR DE FORMA SEGURA.

Nunca aceptes un JWT únicamente porque Redis está caído y no fue posible comprobar si estaba revocado.

La ausencia de Redis no debe convertirse en un bypass de seguridad.

## 7. TIEMPOS DE EXPIRACIÓN

Mantén tiempos coherentes entre JWT y Redis.

Como mínimo:

* Access JWT: 20 minutos.
* Claves de revocación: hasta el tiempo restante del JWT.
* Sesiones: TTL acorde a la sesión existente.
* Refresh token: TTL acorde a su expiración.
* Cache de books: TTL corto.

No inventes tiempos incompatibles con la lógica actual del proyecto. Si ya existen valores configurados, reutilízalos.

Centraliza los valores configurables mediante variables de entorno cuando sea conveniente.

## 8. MANEJO DE ERRORES

Redis no debe provocar errores silenciosos.

Implementa manejo adecuado para:

* timeout;
* conexión rechazada;
* autenticación fallida;
* Redis no disponible;
* errores de lectura;
* errores de escritura;
* desconexión.

Para cache:

Redis falla → continuar con PostgreSQL cuando sea seguro.

Para autenticación/revocación/sesiones:

Redis falla → rechazar la operación de forma segura.

No expongas contraseñas ni credenciales Redis en logs.

## 9. MÉTRICAS / OBSERVABILIDAD

Si el proyecto ya tiene logging o métricas, integra Redis utilizando el mecanismo existente.

Como mínimo debe ser posible identificar:

* conexión exitosa/fallida;
* errores de Redis;
* cache hit;
* cache miss;
* operaciones relevantes de sesión/revocación.

No implementes un sistema de métricas complejo si el proyecto no lo necesita.

## 10. DESPLIEGUE

Integra Redis al despliegue existente de Library.

Revisa los archivos de configuración existentes y modifica únicamente lo necesario para que:

* Redis esté disponible;
* todos los microservicios puedan utilizarlo;
* REDIS_URL sea configurable;
* no se expongan credenciales reales;
* PostgreSQL continúe funcionando como fuente principal.

Si existe Docker Compose, configuración de VM, scripts de despliegue u otro mecanismo existente, intégralo siguiendo esa arquitectura.

## 11. CALIDAD DEL CÓDIGO

Antes de terminar:

* revisa que no haya código duplicado innecesario;
* reutiliza la configuración Redis;
* verifica imports y referencias;
* verifica que las variables de entorno utilizadas existan en los archivos correspondientes;
* verifica que los cambios no rompan rutas existentes;
* revisa especialmente login, middleware/decoradores de JWT y books.

IMPORTANTE: esta revisión debe hacerse mediante inspección del código. NO ejecutes pruebas.

## 12. NO HAGAS ESTO

NO:

* ejecutes tests;
* ejecutes pytest;
* ejecutes unittest;
* ejecutes coverage;
* ejecutes linters;
* hagas requests HTTP de prueba;
* levantes todos los microservicios únicamente para probar;
* generes tests nuevos;
* modifiques funcionalidades ajenas a Redis;
* cambies PostgreSQL;
* cambies la expiración del JWT de acceso de 20 minutos;
* elimines la validación JWT existente;
* hagas que Redis sea obligatorio para GET cacheados;
* permitas autenticación cuando Redis no puede comprobar revocación.

## ENTREGA FINAL

Cuando termines la implementación, NO me des una explicación larga del código.

Entrégame únicamente:

### 1. Cambios realizados

Una lista muy breve de los archivos/componentes modificados y qué se implementó en cada uno.

### 2. Variables de entorno necesarias

Lista exacta de las variables que debo configurar, especialmente REDIS_URL.

No incluyas contraseñas reales.

### 3. Paso a paso para comprobar manualmente la implementación

Quiero un procedimiento práctico y ordenado para verificar yo mismo que todo funciona.

Incluye comprobaciones para:

1. Redis disponible y autenticado.
2. Todos los microservicios usando la misma REDIS_URL.
3. Login creando sesión/refresh token.
4. TTL de sesión y refresh token.
5. JWT con expiración de 20 minutos.
6. Logout eliminando sesión y refresh token.
7. Generación/uso de `jti`.
8. Revocación mediante `jwt:revoked:<jti>`.
9. Rechazo del JWT revocado desde cada microservicio protegido.
10. Cache hit/miss de GET /books.
11. Cache de GET /books/{isbn}.
12. TTL del cache.
13. Invalidación después de POST/PUT/PATCH/DELETE.
14. Funcionamiento de GET /books cuando Redis está caído.
15. Comportamiento seguro de autenticación/revocación cuando Redis está caído.
16. Verificación de logs/métricas.

Para cada comprobación proporciona:

* comando exacto o acción exacta;
* qué resultado espero obtener;
* cómo sé que está correctamente implementado.

NO ejecutes ninguna de estas comprobaciones tú mismo. Solo dame los pasos para que yo los ejecute.

No incluyas pruebas automatizadas ni código de test en la entrega final.
