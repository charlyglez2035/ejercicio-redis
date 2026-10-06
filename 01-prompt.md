Diseña una base de datos en PostgreSQL, tomando en consideración que más adelante se desarrollará
un sistema web completo que administre
usuarios registrados, implemente CRUD del modelo normalizado (en
todas las tablas), maneje imágenes y conserve definiciones de
conceptos asociadas a cada libro

Partiendo de ISBN, título, autor, año de publicación, género, precio, stock, formato, imágenes y 
conceptos definidos por libro, identifica dependencias funcionales y multivaluadas.
Un libro puede tener varios autores
Un libro puede pertenecer a varios géneros.
Un libro puede definir muchos conceptos y un mismo concepto puede aparecer en distintos 
libros con definiciones diferentes.
Un libro puede tener varias imágenes.
Formato y categoría son catálogos independientes.
Debe existir como máximo un administrador.

crea el diseño de la base de datos en un archivo .sql dentro del directorio library/db y llamalo scheme.sql