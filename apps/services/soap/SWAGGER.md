# Documentación Swagger - Library Microservice API

## Acceso a la Documentación Swagger

Una vez que el microservicio esté ejecutándose, puedes acceder a la documentación interactiva de Swagger en:

```
http://localhost:5000/apidocs/
```

## Características de Swagger

### 📋 Interfaz Interactiva
- **Visualización completa de endpoints**: Todos los métodos HTTP disponibles están documentados
- **Esquemas de request/response**: Especificaciones claras de qué se envía y qué se recibe
- **Try it out**: Prueba los endpoints directamente desde el navegador sin necesario usar curl o Postman

### 🏷️ Etiquetas (Tags)
Los endpoints están organizados por etiquetas:
- **Books**: Operaciones CRUD sobre libros
- **Health**: Verificación del estado del servicio

## Endpoints Documentados

### GET /api/books
**Obtiene todos los libros**
- Parámetros: Ninguno
- Respuesta: Array de libros con información completa

### GET /api/books/{isbn}
**Obtiene un libro específico por ISBN**
- Parámetro: `isbn` (string, requerido)
- Respuesta: Objeto con detalles del libro
- Códigos de estado: 200, 404, 500

### GET /api/books/search
**Busca libros por atributos**
- Parámetros de consulta (opcionales):
  - `title`: Búsqueda parcial en título
  - `author`: Búsqueda parcial en autor
  - `category`: Búsqueda en categoría
  - `genre`: Búsqueda en género
- Respuesta: Array de libros que coinciden

### POST /api/books
**Crea un nuevo libro**
- Body JSON (requerido):
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
- Respuesta: Confirmación con ISBN creado
- Códigos de estado: 201, 400, 500

### PUT /api/books/{isbn}
**Actualiza un libro existente**
- Parámetro: `isbn` (string, requerido)
- Body JSON (parcial, opcionales todos los campos):
  ```json
  {
    "title": "1984 - Edición Especial",
    "price": 210.00,
    "stock": 25,
    "authors": ["George Orwell"]
  }
  ```
- Respuesta: Mensaje de confirmación
- Códigos de estado: 200, 404, 500

### DELETE /api/books/{isbn}
**Elimina un libro**
- Parámetro: `isbn` (string, requerido)
- Respuesta: Mensaje de confirmación
- Códigos de estado: 200, 404, 500

### GET /api/health
**Verifica el estado del servicio**
- Parámetros: Ninguno
- Respuesta: Estado del servicio (ok/error) y mensaje
- Códigos de estado: 200, 500

## Ventajas de Usar Swagger

✅ **Documentación siempre actualizada**: Vinculada directamente al código  
✅ **Pruebas interactivas**: No necesitas herramientas externas  
✅ **Especificación clara**: Tipos de datos, ejemplos, validaciones  
✅ **Generación automática**: Se genera desde decoradores en el código  
✅ **Compatible con OpenAPI**: Estándar industria de documentación API  

## Notas Técnicas

- Swagger se configura automáticamente con Flasgger
- La documentación se genera desde docstrings YAML en los decoradores de rutas
- Los esquemas incluyen información de respuesta para todos los códigos de estado
- Los parámetros están marcados como requeridos cuando es necesario

## Instalación de Dependencias

Para que Swagger funcione, asegúrate de tener instalado:
```bash
pip install flasgger
```

Ya está incluido en `requirements.txt`.
