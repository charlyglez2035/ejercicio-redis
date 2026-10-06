# Ejemplos de uso del API con curl

## 1. Health Check
curl http://localhost:5000/api/health

## 2. Obtener todos los libros
curl http://localhost:5000/api/books

## 3. Obtener un libro específico
curl http://localhost:5000/api/books/9780307474728

## 4. Buscar libros por título
curl "http://localhost:5000/api/books/search?title=solitude"

## 5. Buscar libros por autor
curl "http://localhost:5000/api/books/search?author=marquez"

## 6. Buscar libros por categoría
curl "http://localhost:5000/api/books/search?category=Literature"

## 7. Buscar con múltiples criterios
curl "http://localhost:5000/api/books/search?title=1984&author=orwell"

## 8. Crear un nuevo libro
curl -X POST http://localhost:5000/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "isbn": "9780451524935",
    "title": "1984",
    "publication_year": 1949,
    "price": 199.90,
    "stock": 20,
    "format_id": 1,
    "category_id": 1,
    "authors": ["George Orwell"]
  }'

## 9. Actualizar un libro
curl -X PUT http://localhost:5000/api/books/9780451524935 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984 - Edición Revisada",
    "price": 210.00,
    "stock": 25
  }'

## 10. Eliminar un libro
curl -X DELETE http://localhost:5000/api/books/9780451524935

## Notas:
# - Reemplaza localhost:5000 con la URL correcta si el servicio está en otro servidor
# - Asegúrate de que el servicio Flask está ejecutándose antes de hacer las peticiones
# - Los parámetros JSON deben tener los tipos correctos (números sin comillas, strings con comillas)
