Implementa JWT en este proyecto local de librería. Trabaja únicamente en el workspace abierto de VS Code: no clones repositorios, no consultes GitHub y no hagas commits ni push.

AHORRO DE TOKENS
- Inspecciona una sola vez los archivos relevantes e identifica la versión activa. Evita leer dependencias, archivos generados y copias antiguas.
- Implementa los cambios completos antes de ejecutar pruebas. Durante la implementación no ejecutes suites, pruebas exploratorias ni validaciones repetidas.
- Reutiliza código y dependencias existentes; agrega únicamente lo necesario. No refactorices componentes ajenos al objetivo.
- No generes planes extensos, explicaciones por archivo ni código completo en el chat. Modifica los archivos directamente.
- Al final realiza una validación breve y acotada. Si falla, corrige y repite únicamente el caso afectado.

OBJETIVO
Proteger las escrituras del microservicio book con JWT emitidos por login, adaptar el cliente web y Python Tkinter, y mostrar las peticiones en una consola dentro de la web.

LOCALIZACIÓN
Ubica los servicios activos login/book, el cliente web, el esquema PostgreSQL y el cliente Tkinter. Como referencia podrían estar en:
- library/apps/services/login/app.py
- library/apps/services/soap/app.py
- library/apps/web-monolito/
- library/db/scheme.sql
No asumas que Python_app/app.py es Tkinter: verifica sus imports. Si no existe un cliente Tkinter, crea uno sencillo.

IMPLEMENTACIÓN
1. Login:
- Mantén register, login y health públicos.
- Login valida las credenciales existentes y devuelve access_token, token_type y expires_in.
- Usa HS256 mediante una biblioteca compatible. Secreto fuerte compartido solo entre servidores, configurado por entorno, sin secreto de respaldo.
- Incluye sub string, iat, exp, iss, aud y jti; valida algoritmo, firma, expiración, issuer y audience.
- Session exige Bearer válido.
- Logout revoca el jti hasta su expiración. Login y book deben consultar la misma revocación persistente en PostgreSQL; agrega una migración aditiva si hace falta.

2. Book:
- GET /api/books y GET /api/books/{isbn} siguen públicos.
- POST /api/books y PUT, PATCH, DELETE /api/books/{isbn} requieren Authorization: Bearer <token>.
- Aplica la misma protección a los alias /books si existen.
- Usa un decorador/middleware común y valida antes de modificar la base.
- Token ausente, inválido, expirado o revocado: 401. No impongas roles nuevos.
- Conserva PostgreSQL, datos, validaciones, imágenes y comportamiento JSON/XML existente.
- Permite Authorization y X-Request-ID en CORS cuando corresponda; OPTIONS permanece público.

3. Web:
- Integra login, session y logout; adjunta Bearer en las escrituras.
- Si Express llama a los servicios, guarda el JWT en su sesión de servidor; si el navegador llama directamente, guárdalo en memoria.
- Permite consultar sin login y demostrar POST, PUT, PATCH y DELETE, incluyendo una escritura sin token.
- Agrega un panel visible “Consola de peticiones” con fecha, X-Request-ID, servicio, método, URL, headers, payload enviado, estado HTTP, duración y respuesta/error.
- Registra también rechazos. Si Express actúa como proxy, muestra el resultado real del microservicio.
- Usa un wrapper común, limita entradas e incluye limpiar y copiar/exportar.
- Redacta contraseñas, JWT, Authorization, cookies y otros secretos en solicitudes y respuestas. Renderiza como texto seguro.
- Los servicios también deben registrar peticiones sanitizadas en terminal. No expongas logs globales en un endpoint público.

4. Tkinter:
- Adapta el cliente existente o crea uno mínimo con URLs configurables, registro/login/session/logout, consulta pública y CRUD con JWT.
- Guarda el token en memoria; consume los servicios, sin conectarse directamente a PostgreSQL.
- Incluye panel de peticiones sanitizadas, timeout y manejo de 401.
- Evita bloquear la interfaz; actualiza widgets desde el hilo principal.

5. Configuración:
- Actualiza dependencias, .env.example y un README breve con comandos WSL, variables, migración y endpoints públicos/protegidos.
- No incluyas secretos, .env, node_modules ni entornos virtuales en Git.

VALIDACIÓN FINAL: ÚNICA Y LIMITADA
No construyas una suite extensa ni instales herramientas de pruebas adicionales. Una vez terminada toda la implementación, ejecuta una sola demostración integrada con un usuario y un libro temporal:
1. GET público: 200.
2. POST, PUT, PATCH y DELETE sin token: 401, sin cambios en la base.
3. Login y session válidos.
4. POST → PUT → PATCH → DELETE con JWT válido; confirma los cambios del libro temporal.
5. Una escritura con token manipulado: 401.
6. Logout y reutilización del token: 401 en session y book.
7. Verifica visualmente el log web y el funcionamiento básico de Tkinter.
No borres ni modifiques libros existentes. Reutiliza este mismo recorrido para las evidencias.

EVIDENCIAS
Si tienes herramientas de captura, toma screenshots reales durante esa validación, sin repetir operaciones solo para capturarlas:
- GET público y escritura rechazada, con log visible.
- Login y CRUD autorizado, con payloads y respuestas legibles.
- Token inválido y rechazo después del logout.
- Tkinter con su panel.
Guárdalas en evidencias/jwt/. Nunca muestres secretos ni fabriques capturas. Si no puedes capturar o ejecutar algún componente, indica el pendiente y los pasos mínimos para verificarlo.

ENTREGA
Termina con un resumen corto: cambios, resultados realmente comprobados, capturas y bloqueos. No afirmes que algo fue probado si no lo ejecutaste.