# Microservicio SOAP para Gestión de Libros

## Descripción
Microservicio Flask para operaciones CRUD de libros con conexión a PostgreSQL, soporte CORS, gestión segura de credenciales mediante variables de entorno y **documentación interactiva con Swagger**.

## Requisitos
- Python 3.8+
- PostgreSQL 12+
- pip

## Instalación

1. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

2. **Configurar variables de entorno:**
   El archivo `.env` ya está configurado con:
   - `DB_HOST`: localhost
   - `DB_PORT`: 5432
   - `DB_NAME`: library
   - `DB_USER`: library_user
   - `DB_PASSWORD`: 2710

3. **Asegurarse de que PostgreSQL está ejecutándose** y que la base de datos `library` existe.

## Ejecución

```bash
python app.py
```

El servicio estará disponible en `http://localhost:5000`

## 📚 Documentación con Swagger

Una vez ejecutado el servicio, puedes acceder a la documentación interactiva de Swagger en:

```
http://localhost:5000/apidocs/
```

Desde la interfaz de Swagger puedes:
- Ver todos los endpoints documentados
- Probar cada endpoint directamente en el navegador
- Ver esquemas de request/response
- Obtener ejemplos de uso

Para más detalles, consulta [SWAGGER.md](SWAGGER.md)

## Endpoints API

### 1. Obtener todos los libros
```
GET /api/books
```

**Respuesta:**
```json
[
  {
    "isbn": "9780307474728",
    "title": "One Hundred Years of Solitude",
    "authors": "Gabriel Garcia Marquez",
    "publication_year": 1967,
    "category": "Literature",
    "format": "Hardcover",
    "price": "299.90",
    "stock": 15
  }
]
```

### 2. Obtener un libro específico
```
GET /api/books/{isbn}
```

**Parámetro:**
- `isbn`: ISBN del libro (ej: 9780307474728)

**Respuesta:**
```json
{
  "isbn": "9780307474728",
  "title": "One Hundred Years of Solitude",
  "authors": "Gabriel Garcia Marquez",
  "publication_year": 1967,
  "category": "Literature",
  "format": "Hardcover",
  "price": "299.90",
  "stock": 15
}
```

### 3. Buscar libros por atributos
```
GET /api/books/search?title=solitude&author=marquez&category=Literature&genre=Novel
```

**Parámetros de consulta (opcionales):**
- `title`: Búsqueda parcial en título
- `author`: Búsqueda parcial en autor
- `category`: Búsqueda en categoría
- `genre`: Búsqueda en género

**Respuesta:** Array de libros que coinciden con los criterios

### 4. Crear un nuevo libro
```
POST /api/books
```

**Body (JSON):**
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

**Respuesta:**
```json
{
  "message": "Libro creado exitosamente",
  "isbn": "9780451524935"
}
```

### 5. Actualizar un libro
```
PUT /api/books/{isbn}
```

**Body (JSON):**
```json
{
  "title": "1984 - Edición Revisada",
  "price": 210.00,
  "stock": 25,
  "authors": ["George Orwell"]
}
```

**Respuesta:**
```json
{
  "message": "Libro actualizado exitosamente"
}
```

### 6. Eliminar un libro
```
DELETE /api/books/{isbn}
```

**Respuesta:**
```json
{
  "message": "Libro eliminado exitosamente"
}
```

### 7. Health Check
```
GET /api/health
```

**Respuesta:**
```json
{
  "status": "ok",
  "message": "Servicio operacional"
}
```

## CORS
El microservicio está configurado para aceptar peticiones CORS desde cualquier origen en los endpoints `/api/*`.

## Estructura de Carpetas
```
soap/
├── .env                 # Variables de entorno
├── requirements.txt     # Dependencias Python
├── app.py              # Aplicación principal
├── README.md           # Este archivo
├── library.xml         # Estructura XML de ejemplo
└── library.xsl         # Estilos XML (si es necesario)
```

## Seguridad
- Las credenciales de base de datos se almacenan en un archivo `.env` que **NO debe ser versionado** en git.
- Todos los parámetros de entrada se parametrizan en consultas SQL para prevenir inyección.
- CORS está configurado para aceptar todas las fuentes, considere limitar esto en producción.

## Notas
- La base de datos debe tener las tablas creadas según el esquema en `../../../db/scheme.sql`
- Los cambios se procesan en transacciones ACID para garantizar la integridad de datos.
- Swagger es completamente interactivo y autogenerado desde el código.
