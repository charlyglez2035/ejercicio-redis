## Ejercicio Microservicio login

1.- El siguiente ejercicio será basado en el proyecto que llevamos trabajando desde un inicio (library), pero será desarrollado en otra carpeta llamada ejercicioguiado04, donde se clonará todo lo que se lleva hasta el momento.

Claro, aquí está el texto de las dos diapositivas, ya limpio para que puedas copiarlo:

## Ejercicio Microservicio login

### Objetivo

Desarrollar un **microservicio independiente de autenticación y gestión básica de usuarios** para la plataforma de librería en línea existente. El servicio deberá desarrollarse con **Python, Flask, Psycopg y PostgreSQL**, utilizar la base de datos actual del proyecto y exponer sus respuestas tanto en **XML como en JSON**.

El propósito del ejercicio es practicar **integración entre aplicaciones, diseño de API, persistencia en PostgreSQL, normalización, autenticación, sesiones, protección de contraseñas y representación de un mismo recurso en diferentes formatos.**

### Requerimientos funcionales

El microservicio deberá implementar las siguientes operaciones:

| Método | Endpoint    | Función                                            |
| ------ | ----------- | -------------------------------------------------- |
| POST   | `/register` | Registrar un nuevo usuario                         |
| POST   | `/login`    | Autenticar al usuario e iniciar sesión             |
| POST   | `/logout`   | Cerrar la sesión                                   |
| GET    | `/session`  | Consultar si existe una sesión autenticada         |
| GET    | `/health`   | Verificar el estado del microservicio y PostgreSQL |

---

## Ejercicio Microservicio login — continuación

El **correo deberá validarse antes de registrarse y deberá ser único**. La contraseña **nunca deberá almacenarse en texto plano**. El sistema almacenará únicamente un **hash seguro de la contraseña**.

La autenticación deberá verificar las credenciales contra **PostgreSQL** y, cuando sean correctas, crear una **sesión del lado de Flask** que permita identificar al usuario en solicitudes posteriores.

1. Crea el microservicio en el directorio `apps/services/login`.
2. Modifica e integra las tablas necesarias a la base de datos `library`.
3. Despliega el microservicio en el **puerto 5000**.
4. Utiliza **Swagger** para documentar los endpoints en **XML y JSON**.
5. Valida que todos los endpoints funcionen correctamente.

**Recuerda:** no necesitamos almacenar la contraseña dos veces ni crear una tabla exclusivamente para passwords. `password_hash` pertenece naturalmente a la cuenta de usuario.
