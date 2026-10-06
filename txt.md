Todos los endpoints deberán soportar:  ?format=xml  y ?format=json, si no se especifica el parámetro format, XML será el formato predeterminado., por ejemplo: POST /login     POST /login?format=xml deberán responder XML, mientras que:  POST /login?format=json deberá responder JSON. El registro deberá solicitar:
nombre
apellido paterno
apellido materno
email
password

El correo deberá validarse antes de registrarse y deberá ser único. La contraseña nunca deberá almacenarse en texto plano. El sistema almacenará únicamente un hash seguro de la contraseña.

La autenticación deberá verificar las credenciales contra PostgreSQL y, cuando sean correctas, crear una sesión del lado de Flask que permita identificar al usuario en solicitudes posteriores.

El correo deberá validarse antes de registrarse y deberá ser único. La contraseña nunca deberá almacenarse en texto plano. El sistema almacenará únicamente un hash seguro de la contraseña.

La autenticación deberá verificar las credenciales contra PostgreSQL y, cuando sean correctas, crear una sesión del lado de Flask que permita identificar al usuario en solicitudes posteriores.

Crea el microservicio en el directorio apps/services/login
Modifica e integra las tablas necesarias a la base de datos library
Despliega el microservicio en el puerto 5000
Utiliza Swagger para documentar los endpoints en XML y JSON
Valida que todos los endpoint funcionen correctamente (anexa evidencia screenshots)
Agrega screenshots de los resultados obtenidos y una pequeña reflexión del porque se tiene que hacer así.
Sube tu proyecto Monorepo compactado en .tar.gz o .zip

Recuerda, no necesitamos almacenar la contraseña dos veces ni crear una tabla exclusivamente para passwords. password_hash pertenece naturalmente a la cuenta de usuario