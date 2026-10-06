Trabaja sobre el proyecto actual de Library después de haber terminado las dos etapas anteriores:

1. Integración de Redis.
2. Desarrollo de Users, Authors, Pedidos, Pagos e integración con la aplicación Python TK.

Ahora NO quiero que desarrolles nuevas funcionalidades.

Quiero preparar este proyecto para desplegarlo correctamente en mi VM y crear un repositorio NUEVO en GitHub llamado:

ejercicio-redis

## OBJETIVO

Dejar el proyecto listo para:

PC/WSL
↓
GitHub
↓
Repositorio `ejercicio-redis`
↓
VM
↓
Microservicios + Redis + PostgreSQL

La aplicación Python TK seguirá ejecutándose en mi PC/WSL y consumirá los microservicios desplegados en la VM.

---

# REGLAS IMPORTANTES

* NO modifiques la funcionalidad de los microservicios.
* NO cambies la arquitectura.
* NO elimines Redis.
* NO cambies PostgreSQL.
* NO ejecutes pruebas automatizadas.
* NO ejecutes pytest.
* NO ejecutes unittest.
* NO ejecutes coverage.
* NO ejecutes linters.
* NO hagas requests de prueba.
* NO levantes todos los servicios para probar.
* NO gastes tokens en pruebas.
* Solo prepara el proyecto para GitHub y despliegue.
* Puedes inspeccionar archivos y configuración.
* No incluyas secretos reales en GitHub.
* No subas `.env`.
* No subas contraseñas.
* No subas JWT_SECRET_KEY real.
* No subas REDIS_URL con contraseña real.

---

# 1. INSPECCIONA EL PROYECTO

Primero identifica:

* estructura principal;
* microservicio login;
* microservicio books;
* microservicio users;
* microservicio authors/autores;
* microservicio pedidos;
* microservicio pagos;
* aplicación Python TK;
* Redis;
* PostgreSQL;
* archivos de configuración;
* requirements;
* Docker/Compose si existe;
* scripts de inicio;
* archivos `.env`;
* archivos `.env.example`.

NO MODIFIQUES NADA todavía.

Dime qué estructura detectaste.

---

# 2. PREPARAR GIT

Verifica si el proyecto ya es un repositorio Git.

Identifica:

* branch actual;
* remote actual;
* archivos modificados;
* archivos que NO deberían subirse.

El objetivo es crear un repositorio NUEVO:

ejercicio-redis

No quiero utilizar el repositorio anterior como destino.

---

# 3. .GITIGNORE

Revisa o crea `.gitignore` apropiadamente.

Debe evitar subir como mínimo:

.env
*.env
**pycache**/
*.pyc
venv/
.venv/
env/
*.log

y cualquier archivo que contenga:

* contraseñas;
* JWT_SECRET_KEY;
* REDIS_URL real;
* credenciales PostgreSQL;
* credenciales de servicios.

NO elimines archivos importantes del proyecto.

---

# 4. .ENV.EXAMPLE

Asegúrate de tener un `.env.example` que documente las variables necesarias SIN secretos reales.

Debe incluir las variables que realmente utiliza el proyecto.

Como mínimo identifica si existen:

JWT_SECRET_KEY
REDIS_URL
DATABASE_URL

y las URLs/puertos de los microservicios.

NO inventes variables si el proyecto ya utiliza otros nombres.

Si ya existen variables equivalentes, utiliza los nombres existentes.

Los valores deben ser ejemplos seguros.

---

# 5. CONFIGURACIÓN PARA LA VM

El proyecto debe poder clonarse desde GitHub y ejecutarse en la VM sin depender de archivos locales que no estén en GitHub.

Identifica qué cosas deben configurarse MANUALMENTE en la VM después del clone.

Por ejemplo:

* `.env`;
* credenciales;
* IP/host;
* puertos;
* PostgreSQL;
* Redis;
* servicios.

Distingue claramente:

### SE SUBE A GITHUB

Código y configuración no sensible.

### NO SE SUBE A GITHUB

Secretos y credenciales.

---

# 6. ESTRUCTURA DE DESPLIEGUE

Determina cómo deben ejecutarse los microservicios en la VM.

Si el proyecto ya utiliza:

* systemd;
* Docker;
* Docker Compose;
* scripts;
* uvicorn;
* gunicorn;
* Flask;
* FastAPI;

respeta el mecanismo existente.

NO cambies el método de despliegue solamente para facilitar el ejercicio.

Si actualmente cada microservicio se inicia de una forma determinada, documenta exactamente esa forma.

---

# 7. CREAR REPOSITORIO GITHUB

Quiero crear un repositorio NUEVO:

ejercicio-redis

Dame los comandos exactos para hacerlo desde mi PC/WSL.

El procedimiento debe contemplar:

```bash
git init
```

si es necesario.

Después:

```bash
git add .
git commit -m "Initial implementation of Library with Redis"
```

y la configuración del remote.

IMPORTANTE:

NO inventes mi nombre de usuario de GitHub.

Utiliza un placeholder como:

GITHUB_USER

y explícame dónde debo sustituirlo.

El repositorio debe quedar como:

https://github.com/GITHUB_USER/ejercicio-redis

No asumas que el repositorio ya existe.

Explícame también cómo crearlo en GitHub desde el navegador si es necesario.

---

# 8. SUBIR A GITHUB

Dame los comandos exactos, en orden, para:

1. comprobar estado;
2. agregar archivos;
3. hacer commit;
4. configurar branch principal;
5. agregar remote;
6. hacer push.

Incluye una comprobación previa para asegurar que `.env` NO será enviado.

No ejecutes estos comandos.

Solo dame los comandos.

---

# 9. CLONAR EN LA VM

Después de subir el repositorio, quiero descargarlo en la VM.

Dame los comandos exactos para conectarme a mi VM mediante SSH y:

1. elegir la carpeta correcta;
2. clonar `ejercicio-redis`;
3. entrar al proyecto;
4. verificar que los archivos estén presentes.

Usa:

```bash
git clone
```

con el repositorio:

```text
ejercicio-redis
```

No inventes mi usuario de GitHub.

Usa:

```text
https://github.com/GITHUB_USER/ejercicio-redis.git
```

como ejemplo.

---

# 10. CONFIGURAR LA VM

Después del clone, dime exactamente qué debo configurar MANUALMENTE en la VM.

Especialmente:

* `.env`;
* JWT_SECRET_KEY;
* REDIS_URL;
* DATABASE_URL;
* URLs internas/externas de los microservicios;
* puertos.

IMPORTANTE:

No me des una contraseña real.

Utiliza placeholders.

Ejemplo:

```env
JWT_SECRET_KEY=<SECRET>
REDIS_URL=redis://:<REDIS_PASSWORD>@<REDIS_HOST>:6379/0
```

pero adapta los nombres a los que realmente utiliza el proyecto.

---

# 11. REDIS EN LA VM

Mi Redis ya está instalado/configurado en la VM.

No quiero que reinstales Redis.

Dame únicamente los pasos para:

* verificar que Redis esté disponible;
* configurar la aplicación para utilizarlo;
* comprobar que REDIS_URL apunta a la instancia correcta.

NO ejecutes estos pasos.

Solo indícamelos.

---

# 12. POSTGRESQL EN LA VM

PostgreSQL también debe continuar siendo la fuente principal de datos.

Dime qué configuración necesita el proyecto para conectarse a PostgreSQL.

No borres bases de datos.

No ejecutes migraciones destructivas.

Si existen migraciones, indícame el comando que YO debería ejecutar, pero NO lo ejecutes.

---

# 13. DEPENDENCIAS

Identifica cómo instala dependencias el proyecto.

Si existe:

requirements.txt

dime:

```bash
pip install -r requirements.txt
```

Si existe un entorno virtual, indica cómo crearlo/activarlo.

Si existen requirements separados por microservicio, documenta el procedimiento correcto.

No instales nada tú.

---

# 14. LEVANTAR LOS MICROSERVICIOS

Quiero que me indiques cómo iniciar cada microservicio en la VM.

Para cada uno:

### login

Comando:

...

Puerto:

...

### books

Comando:

...

Puerto:

...

### users

Comando:

...

Puerto:

...

### authors

Comando:

...

Puerto:

...

### pedidos

Comando:

...

Puerto:

...

### pagos

Comando:

...

Puerto:

...

NO inventes comandos ni puertos.

Obtén la información del código/configuración existente.

Si utilizan un script común, utiliza ese mecanismo.

---

# 15. PROCESOS EN LA VM

Indícame cómo comprobar manualmente que los microservicios están ejecutándose.

Quiero comandos de consulta como:

```bash
ps
ss
systemctl status
```

solo si corresponden a la arquitectura real.

NO ejecutes los comandos.

Dime qué debería aparecer.

---

# 16. CONECTIVIDAD DESDE MI PC/WSL

La aplicación TK está en mi PC/WSL.

Los microservicios están en la VM.

Dime cómo debo configurar las URLs para que TK pueda conectarse a la VM.

Identifica dónde se configuran actualmente esas URLs.

No hardcodees una IP inventada.

Utiliza:

```text
<VM_IP>
```

si la IP real no está disponible.

Dime exactamente qué debo sustituir.

---

# 17. FIREWALL / PUERTOS

Identifica qué puertos de la VM necesitan ser accesibles desde mi PC para que TK pueda consumir los microservicios.

No abras puertos automáticamente.

Dime:

* qué puerto;
* qué servicio;
* si necesita acceso externo;
* qué regla de firewall tendría que revisar.

No ejecutes cambios de firewall.

---

# 18. HTTPS

Determina cómo está planteado HTTPS en el proyecto.

Si existe:

* reverse proxy;
* Nginx;
* certificado;
* HTTPS;
* dominio;

documenta cómo debe funcionar.

Si HTTPS todavía depende del despliegue, indícalo como configuración pendiente.

NO inventes certificados.

---

# 19. ACTUALIZAR EL PROYECTO

Si para que el proyecto sea clonable desde GitHub hace falta algún archivo de configuración NO sensible, créalo/modifícalo.

Pero:

NO modifiques lógica de negocio.

NO cambies endpoints.

NO cambies JWT.

NO cambies Redis.

NO cambies PostgreSQL.

NO cambies la aplicación TK.

Solo realiza cambios estrictamente necesarios para que el repositorio sea desplegable.

---

# 20. VERIFICACIÓN ESTÁTICA

Antes de terminar, revisa estáticamente:

* imports;
* rutas;
* archivos necesarios;
* `.gitignore`;
* `.env.example`;
* requirements;
* scripts;
* configuración.

NO ejecutes pruebas.

NO levantes servicios.

NO hagas requests.

---

# 21. ENTREGA FINAL

Tu respuesta final debe tener EXACTAMENTE estas secciones:

## 1. Estructura del proyecto

Explica brevemente qué contiene el repositorio.

## 2. Archivos modificados

Lista únicamente los archivos que modificaste y por qué.

## 3. Variables de entorno

Lista las variables necesarias para la VM.

Sin secretos reales.

## 4. Crear repositorio GitHub

Dame los comandos exactos desde PC/WSL.

Utiliza:

GITHUB_USER

como placeholder.

## 5. Subir proyecto a GitHub

Dame los comandos exactos.

## 6. Conectarme a la VM

Dame el comando SSH correspondiente como plantilla.

## 7. Descargar el repositorio en la VM

Dame los comandos exactos:

```bash
git clone ...
cd ejercicio-redis
```

## 8. Configurar `.env` en la VM

Dime exactamente qué debo configurar.

## 9. Preparar dependencias

Dame los comandos exactos.

## 10. Configurar Redis

Dime qué debo revisar.

## 11. Configurar PostgreSQL

Dime qué debo revisar.

## 12. Iniciar los microservicios

Para cada servicio:

* comando;
* puerto;
* ubicación;
* logs.

## 13. Verificar servicios

Dame comandos de lectura para verificar procesos y puertos.

## 14. Configurar TK

Dime qué URLs debo configurar para apuntar a la VM.

## 15. Firewall

Dime qué puertos debo revisar.

## 16. Checklist de despliegue

```text
[ ] Repositorio creado
[ ] Proyecto subido a GitHub
[ ] .env NO subido
[ ] Proyecto clonado en VM
[ ] Dependencias instaladas
[ ] Redis configurado
[ ] PostgreSQL configurado
[ ] Login configurado
[ ] Books configurado
[ ] Users configurado
[ ] Authors configurado
[ ] Pedidos configurado
[ ] Pagos configurado
[ ] Puertos revisados
[ ] TK apunta a la VM
```

## MUY IMPORTANTE

NO ejecutes ninguno de los comandos.

NO hagas pruebas.

NO hagas requests.

NO levantes servicios.

Solo inspecciona el proyecto, prepara los archivos necesarios y dame la guía exacta para que YO haga el despliegue.
