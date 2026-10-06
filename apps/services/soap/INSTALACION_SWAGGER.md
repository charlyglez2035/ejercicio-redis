# Instalación y Uso de Swagger

## Instalación

Swagger ya está configurado en el microservicio. Solo necesitas instalar la dependencia:

```bash
pip install -r requirements.txt
```

O si prefieres instalar solo Flasgger:

```bash
pip install flasgger==0.9.7.1
```

## Ejecución del Servicio

1. Asegúrate de que PostgreSQL está ejecutándose
2. Ejecuta el servicio:

```bash
python app.py
```

3. Abre tu navegador y ve a:

```
http://localhost:5000/apidocs/
```

## Interfaz de Swagger

### Pantalla Principal
- **Título**: Library Microservice API
- **Versión**: 1.0.0
- **Descripción**: API RESTful para gestión de libros con CRUD completo
- **Base URL**: http://localhost:5000/api

### Navegación por Endpoints

Los endpoints están organizados en dos secciones (tags):

#### 📚 Books
- GET /books - Obtener todos los libros
- GET /books/{isbn} - Obtener un libro por ISBN
- GET /books/search - Buscar libros por atributos
- POST /books - Crear un nuevo libro
- PUT /books/{isbn} - Actualizar un libro
- DELETE /books/{isbn} - Eliminar un libro

#### 💚 Health
- GET /health - Verificar estado del servicio

## Prueba de Endpoints en Swagger

### Paso 1: Seleccionar un Endpoint
Haz clic en cualquier endpoint para expandir su documentación.

### Paso 2: Ver Detalles
Se mostrará:
- Descripción del endpoint
- Parámetros requeridos/opcionales
- Esquema de request (si aplica)
- Esquema de response (todos los códigos de estado)
- Ejemplos

### Paso 3: Probar (Try it out)
1. Haz clic en el botón "Try it out"
2. Completa los parámetros necesarios
3. Haz clic en "Execute"
4. Visualiza la respuesta en tiempo real

### Ejemplo: Crear un Libro

1. Expande **POST /books**
2. Haz clic en "Try it out"
3. En el campo de body, ingresa:

```json
{
  "isbn": "9780451524935",
  "title": "1984",
  "publication_year": 1949,
  "price": 199.90,
  "stock": 20,
  "format_id": 1,
  "category_id": 1,
  "authors": ["George Orwell"]
}
```

4. Haz clic en "Execute"
5. Verás la respuesta exitosa:

```json
{
  "message": "Libro creado exitosamente",
  "isbn": "9780451524935"
}
```

## Características Destacadas

✅ **Pruebas Interactivas**: No necesitas Postman o curl  
✅ **Documentación Dinámica**: Vinculada al código  
✅ **Esquemas Automáticos**: Basados en docstrings YAML  
✅ **Ejemplos Integrados**: Para cada endpoint  
✅ **Validación Visual**: Tipos de datos y ejemplos  
✅ **Historiales**: Swagger guarda el historial de pruebas  

## Troubleshooting

### No puedo acceder a /apidocs/
- Verifica que el servicio está ejecutándose en `http://localhost:5000`
- Asegúrate de que Flasgger está instalado: `pip install flasgger`

### Los endpoints no se muestran
- Verifica que la sintaxis YAML en los docstrings es correcta
- Recarga la página del navegador
- Revisa la consola de Python para errores

### Error de conexión a BD desde Swagger
- Verifica que PostgreSQL está ejecutándose
- Comprueba las credenciales en `.env`
- Ejecuta `GET /api/health` desde Swagger para verificar la conexión

## Generación de Cliente desde Swagger

Puedes generar clientes automáticamente desde la especificación Swagger. La especificación OpenAPI 2.0 está disponible en:

```
http://localhost:5000/swagger.json
```

Puedes usar herramientas como:
- [Swagger Codegen](https://swagger.io/tools/swagger-codegen/)
- [OpenAPI Generator](https://openapi-generator.tech/)

Para generar clientes en JavaScript, Python, Java, etc.

## Documentación Oficial

Para más información sobre Flasgger, consulta:
- [Documentación oficial de Flasgger](https://github.com/flasgger/flasgger)
- [Documentación de Swagger/OpenAPI](https://swagger.io/docs/)
