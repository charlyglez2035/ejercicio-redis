Actúa como desarrollador backend Python especializado en microservicios, JWT, PostgreSQL y aplicaciones Python Tkinter.

Trabaja SOBRE EL PROYECTO ACTUAL DE "Library" que te proporciono.

IMPORTANTE: esta es una segunda etapa del proyecto. Redis ya fue solicitado/implementado como capa compartida. NO elimines ni reemplaces la integración existente de Redis. Conserva su funcionamiento.

Tu objetivo es dejar el sistema COMPLETO, integrando los microservicios faltantes y modificando la aplicación Python TK para consumirlos.

## REGLAS IMPORTANTES

* Implementa directamente los cambios necesarios en el proyecto.
* NO ejecutes pruebas automatizadas.
* NO ejecutes pytest, unittest, coverage ni linters.
* NO hagas requests de prueba con curl/Postman.
* NO levantes todos los servicios para probarlos.
* NO generes tests nuevos.
* NO gastes tokens en pruebas.
* Puedes inspeccionar código existente para entender contratos, modelos y rutas.
* No rehagas funcionalidades que ya existen.
* Reutiliza código, utilidades, modelos y configuración existentes cuando sea posible.
* Mantén PostgreSQL como fuente principal de datos.
* Mantén Redis y su integración existente.
* No hardcodees secretos.
* No cambies tecnologías existentes salvo que sea estrictamente necesario.
* No rompas endpoints existentes que ya funcionan.
* Si existe una estructura o patrón para microservicios, sigue exactamente ese patrón.
* Si existen migraciones/modelos/configuración de PostgreSQL, reutilízalos y amplíalos en lugar de crear estructuras paralelas innecesarias.

---

# 1. MICROSERVICIO USERS

Desarrolla/completa el microservicio `users`.

Debe administrar:

* usuarios;
* roles;
* correos;
* contraseñas.

Debe permitir las operaciones CRUD necesarias:

* POST
* GET
* PUT
* PATCH
* DELETE

Implementa las rutas siguiendo el patrón que ya utiliza el proyecto.

### Seguridad

Todas las operaciones:

* POST
* PUT
* PATCH
* DELETE

deben exigir:

Authorization: Bearer <JWT>

Las lecturas GET pueden permanecer públicas cuando únicamente consulten información no administrativa.

Las lecturas administrativas deben requerir JWT y el rol correspondiente.

Las contraseñas:

* nunca deben almacenarse en texto plano;
* deben utilizar el mecanismo de hashing existente o uno seguro compatible con el proyecto;
* nunca deben aparecer en logs;
* nunca deben devolverse innecesariamente en respuestas API.

---

# 2. MICROSERVICIO AUTHORS

Desarrolla/completa el microservicio `authors`.

Debe administrar:

* autores;
* relaciones entre autores y libros.

Debe permitir CRUD completo:

* POST
* GET
* PUT
* PATCH
* DELETE

Debe respetar las relaciones existentes con `books`.

Las operaciones de modificación:

* POST
* PUT
* PATCH
* DELETE

requieren:

Authorization: Bearer <JWT>

Las consultas GET pueden ser públicas cuando únicamente consulten información.

Las consultas administrativas deben exigir JWT + permisos/rol.

No dupliques información de libros si la arquitectura existente ya maneja esa relación mediante IDs o referencias.

---

# 3. MICROSERVICIO PEDIDOS

Desarrolla/completa el microservicio `pedidos`.

Debe administrar:

* pedidos;
* líneas de pedido;
* stock;
* estados de pedido.

Debe permitir CRUD completo.

Debe existir una relación coherente entre:

Pedido → Líneas de pedido → Libro/Producto

y debe mantenerse correctamente el stock.

Implementa las operaciones necesarias para:

* crear pedido;
* consultar pedido;
* modificar pedido;
* eliminar/cancelar pedido cuando corresponda;
* administrar líneas;
* actualizar stock;
* actualizar estado.

### Seguridad

POST, PUT, PATCH y DELETE requieren JWT.

Los GET públicos únicamente pueden consultar información permitida.

Las operaciones administrativas requieren JWT + rol autorizado.

Valida el JWT ANTES de modificar datos.

---

# 4. MICROSERVICIO PAGOS

Desarrolla/completa el microservicio `pagos`.

Debe administrar:

* registros de pagos;
* relación del pago con pedidos;
* estado del pago.

Debe permitir CRUD completo.

Debe poder actualizar el estado correspondiente del pedido cuando un pago cambie de estado, respetando la arquitectura existente.

No implementes una pasarela de pago externa si el proyecto no la solicita.

El objetivo aquí es el microservicio de gestión/registro de pagos.

POST, PUT, PATCH y DELETE requieren JWT.

Las operaciones administrativas requieren JWT + rol autorizado.

---

# 5. JWT Y AUTENTICACIÓN

El microservicio `login` debe validar credenciales y emitir JWT.

El JWT debe:

* estar firmado;
* utilizar `JWT_SECRET_KEY`/`SECRET_KEY` mediante variable de entorno;
* utilizar algoritmo HS256;
* expirar en 20 minutos;
* incluir `user_id`;
* incluir `role_id`;
* incluir `jti` si ya está contemplado por la integración Redis.

NO escribas el secreto directamente en el código.

Todos los microservicios deben utilizar la misma variable de entorno:

JWT_SECRET_KEY

o el nombre que ya utilice correctamente el proyecto.

No crees múltiples secretos distintos por microservicio.

---

# 6. VALIDACIÓN JWT EN TODOS LOS MICROSERVICIOS

Users, Authors, Pedidos y Pagos deben validar el JWT antes de cualquier modificación.

La validación debe comprobar:

1. existencia del Authorization header;
2. formato Bearer;
3. firma;
4. algoritmo HS256;
5. expiración;
6. claims necesarios;
7. `user_id`;
8. `role_id`;
9. revocación mediante Redis si ya está implementada.

Si Redis ya proporciona la lista:

jwt:revoked:<jti>

debe conservarse y utilizarse.

NO dupliques la lógica de validación en cada endpoint si el proyecto puede utilizar middleware/decoradores/utilidades compartidas.

---

# 7. RESPUESTAS HTTP DE SEGURIDAD

Utiliza:

### 401 Unauthorized

Cuando:

* no existe JWT;
* el token está mal formado;
* el token es inválido;
* la firma no coincide;
* el token expiró;
* el token fue revocado;
* faltan claims obligatorios.

### 403 Forbidden

Cuando:

* el JWT es válido;
* pero el usuario no tiene el rol/permisos necesarios.

No confundas 401 y 403.

---

# 8. ROLES

El JWT debe contener:

user_id
role_id

Las operaciones administrativas deben comprobar el rol.

No basta con verificar que exista un JWT.

Implementa la autorización siguiendo los roles que YA existan en el proyecto.

Si el proyecto ya tiene una tabla/modelo de roles, reutilízalo.

No inventes un sistema de roles paralelo.

Si existe un rol administrativo, úsalo para proteger las operaciones administrativas.

---

# 9. SECRETOS Y CONFIGURACIÓN

Todos los servicios deben obtener sus secretos mediante variables de entorno.

Como mínimo:

JWT_SECRET_KEY

No escribas secretos directamente en:

* Python;
* `.py`;
* `.json`;
* Dockerfile;
* frontend;
* aplicación TK;
* logs;
* archivos de configuración versionados.

Si existe `.env.example`, agrega únicamente nombres de variables y valores de ejemplo no sensibles.

---

# 10. CORS

Configura CORS correctamente.

En producción:

* permitir únicamente los orígenes de las aplicaciones cliente;
* no utilizar `*` para permitir cualquier origen cuando existan credenciales/autenticación.

Si el proyecto ya tiene una configuración de CORS, modifícala en lugar de crear otra.

Haz que los orígenes permitidos sean configurables mediante variables de entorno cuando sea posible.

---

# 11. HTTPS

Mantén la arquitectura preparada para HTTPS.

No hardcodees URLs HTTP inseguras si el despliegue ya proporciona HTTPS.

Si existe configuración de URLs/base URLs, hazla configurable mediante variables de entorno.

No implementes certificados falsos ni soluciones temporales dentro del código.

---

# 12. LOGS Y DATOS SENSIBLES

Nunca escribas en logs:

* contraseñas;
* JWT completos;
* refresh tokens;
* secretos;
* `JWT_SECRET_KEY`;
* `REDIS_URL` si contiene contraseña.

Los logs pueden indicar:

* endpoint;
* método;
* código HTTP;
* usuario identificado mediante `user_id` si es apropiado;
* resultado general de autenticación;

pero nunca deben exponer tokens completos ni credenciales.

Conserva también la integración de logs existente de Redis.

---

# 13. APLICACIÓN PYTHON TK

Esta parte es OBLIGATORIA.

Modifica la aplicación Python TK existente para consumir TODOS los microservicios desarrollados:

* login
* users
* books
* authors
* pedidos
* pagos

La aplicación debe convertirse en el cliente funcional del sistema.

NO reemplaces la aplicación por una web.

NO conviertas Tkinter en Flask/React/etc.

Debe seguir siendo una aplicación Python TK/Tkinter nativa.

---

# 14. LOGIN EN TK

Implementa/completa el formulario de login.

Debe permitir:

* ingresar correo/usuario;
* ingresar contraseña;
* enviar credenciales al microservicio login;
* recibir JWT;
* conservar el token en memoria de la aplicación;
* utilizar Authorization: Bearer <JWT> en las operaciones protegidas.

No guardes el JWT en archivos de texto plano.

No muestres el JWT al usuario.

Debe existir manejo correcto de:

* credenciales incorrectas;
* 401;
* 403;
* servidor no disponible;
* sesión expirada.

---

# 15. SEMÁFOROS Y NAVEGACIÓN

Utiliza los semáforos/componentes de navegación que YA tenga la aplicación.

La aplicación debe permitir navegar de manera clara entre:

* Login
* Users
* Books
* Authors
* Pedidos
* Pagos

Si por "semáforos" el proyecto se refiere a botones, indicadores, permisos o controles de navegación existentes, respeta exactamente ese concepto y reutiliza la implementación existente.

No inventes una interfaz completamente diferente si ya existe una.

---

# 16. FORMULARIOS TK

Cada microservicio debe tener los formularios necesarios para realizar CRUD.

## Users

Debe poder:

* listar;
* consultar;
* crear;
* editar;
* actualizar;
* eliminar usuarios;

respetando permisos.

## Authors

Debe poder:

* listar;
* consultar;
* crear;
* editar;
* actualizar;
* eliminar autores;
* gestionar su relación con libros.

## Books

Conservar y adaptar la interfaz existente para:

* listar;
* consultar;
* crear;
* editar;
* actualizar;
* eliminar libros.

Debe respetar el cache Redis existente.

## Pedidos

Debe permitir:

* crear pedido;
* consultar pedidos;
* consultar detalle;
* administrar líneas;
* modificar estado cuando corresponda;
* eliminar/cancelar cuando corresponda;
* visualizar stock relacionado.

## Pagos

Debe permitir:

* registrar pago;
* consultar pagos;
* actualizar estado;
* eliminar cuando corresponda;
* relacionar pago con pedido.

---

# 17. AUTORIZACIÓN DESDE TK

La aplicación TK debe enviar:

Authorization: Bearer <JWT>

en todas las operaciones protegidas.

No calcules ni inventes permisos únicamente en la interfaz.

El backend sigue siendo la autoridad para autorización.

La TK puede ocultar/deshabilitar controles según el `role_id` del usuario para mejorar UX, pero el backend DEBE volver a comprobar los permisos.

---

# 18. COMUNICACIÓN ENTRE SERVICIOS

Usa las URLs/configuración existentes.

No hardcodees direcciones si ya existe configuración mediante variables de entorno.

Si es necesario agregar variables, usa nombres claros como:

LOGIN_SERVICE_URL
USERS_SERVICE_URL
BOOKS_SERVICE_URL
AUTHORS_SERVICE_URL
PEDIDOS_SERVICE_URL
PAGOS_SERVICE_URL

pero primero revisa si el proyecto ya tiene nombres equivalentes y reutilízalos.

La aplicación TK debe centralizar la comunicación HTTP si ya existe un cliente/utilidad para ello.

No copies y pegues lógica HTTP en cada formulario si puede reutilizarse.

---

# 19. INTEGRACIÓN CON REDIS

NO elimines ni rompas la integración Redis implementada en la etapa anterior.

Debe continuar funcionando:

* sesiones;
* refresh tokens;
* revocación JWT;
* cache de books;
* TTL;
* invalidación;
* fail-safe.

Los nuevos microservicios deben respetar el mismo mecanismo de autenticación y revocación.

---

# 20. INTEGRIDAD DE DATOS

PostgreSQL continúa siendo la fuente principal.

Respeta:

* claves primarias;
* claves foráneas;
* relaciones;
* restricciones;
* stock;
* estados;
* relaciones entre libros/autores/pedidos/pagos.

No dupliques bases de datos innecesariamente.

Si cada microservicio ya tiene su propia base/esquema, respeta la arquitectura existente.

---

# 21. MANEJO DE ERRORES EN TK

La aplicación debe mostrar mensajes comprensibles para:

* 400;
* 401;
* 403;
* 404;
* 409;
* 500;
* timeout;
* microservicio no disponible.

No muestres tracebacks ni errores internos al usuario final.

---

# 22. IMPLEMENTACIÓN EFICIENTE

Antes de modificar:

1. inspecciona la estructura;
2. identifica cómo funcionan actualmente login y books;
3. identifica cómo funciona la aplicación TK;
4. identifica modelos PostgreSQL existentes;
5. identifica utilidades JWT existentes;
6. identifica integración Redis existente.

Después implementa solamente los cambios necesarios.

Prioridad:

1. backend funcional;
2. autenticación/autorización;
3. relaciones y CRUD;
4. integración TK;
5. manejo de errores;
6. limpieza de código.

No agregues funcionalidades que no fueron solicitadas.

---

# 23. NO EJECUTAR PRUEBAS

ESTO ES MUY IMPORTANTE:

NO ejecutes:

* pytest;
* unittest;
* coverage;
* linters;
* tests de integración;
* Postman;
* curl;
* requests manuales;
* scripts de prueba;
* pruebas automáticas;
* pruebas de UI;
* servidores únicamente para comprobar que funcionan.

Tu tarea es IMPLEMENTAR.

Puedes inspeccionar estáticamente el código para detectar errores obvios de imports, referencias, rutas o configuración, pero NO ejecutes pruebas.

---

# 24. ENTREGA FINAL

Cuando termines, NO me des una explicación larga.

Entrégame únicamente:

## A. Resumen de implementación

Lista breve de:

* Users;
* Authors;
* Pedidos;
* Pagos;
* JWT;
* roles;
* seguridad;
* integración TK;
* Redis conservado.

## B. Archivos modificados

Lista los archivos modificados y una descripción de una línea de cada cambio.

## C. Variables de entorno

Lista las variables nuevas o modificadas que debo configurar.

NO incluyas secretos reales.

## D. PASO A PASO PARA COMPROBAR TODO MANUALMENTE

Esta es la parte MÁS IMPORTANTE de la entrega final.

No ejecutes las comprobaciones tú.

Dame los pasos exactos que YO debo ejecutar para verificar:

1. Levantar Redis.
2. Configurar variables de entorno.
3. Levantar PostgreSQL.
4. Levantar los microservicios.
5. Iniciar la aplicación TK.
6. Hacer login.
7. Comprobar que se obtiene JWT.
8. Comprobar expiración de 20 minutos.
9. Comprobar que el JWT contiene `user_id`, `role_id` y `jti`.
10. Comprobar CRUD de Users.
11. Comprobar CRUD de Authors.
12. Comprobar CRUD de Books.
13. Comprobar CRUD de Pedidos.
14. Comprobar CRUD de Pagos.
15. Comprobar que POST/PUT/PATCH/DELETE sin JWT devuelve 401.
16. Comprobar que un JWT inválido devuelve 401.
17. Comprobar que un JWT expirado devuelve 401.
18. Comprobar que un JWT revocado devuelve 401.
19. Comprobar que un usuario autenticado pero sin permisos recibe 403.
20. Comprobar que un usuario autorizado puede realizar la operación.
21. Comprobar que TK manda `Authorization: Bearer <JWT>`.
22. Comprobar sesiones y refresh tokens en Redis.
23. Comprobar revocación en Redis.
24. Comprobar cache de Books.
25. Comprobar invalidación de cache después de modificaciones.
26. Comprobar manejo de errores de los microservicios.
27. Comprobar que no aparecen contraseñas/JWT/secretos en logs.
28. Comprobar que PostgreSQL continúa siendo la fuente principal.

Para cada paso indica:

* comando o acción exacta;
* resultado esperado;
* qué evidencia puedo tomar para demostrar que funciona.

El procedimiento debe estar pensado para que pueda utilizarlo directamente como guía para las evidencias de mi ejercicio.

NO incluyas tests automatizados.
NO ejecutes ninguna prueba.
