1.- Escribe un microservicio en Flask (no usar blueprints) con una conexión a la BD de Postgress para generar endpoints y realizar las operaciones CRUD de libros. Depositalo en C:\Users\carog\integracion02\library\apps\services\soap

2.- Usa como referencia el esquema de base de datos C:\Users\carog\integracion02\library\db\scheme.sql y el diseño del xml definido en C:\Users\carog\integracion02\library\apps\services\soap\library.xml

3.- El microservicio debe mostrar todos los libros, un libro, buscar por atributos, modificar un libro, borrar un libro y actualizar un libro.

4.- Toma en consideración el problema CORS ya que este servicio será accedido mediante clientes fuera de dominio.

5.- Considera los siguientes dato de Postgres: db: library, usuario: library_user y password: 2710, usa las variables del entorno .env para no exponer las credenciales de servicio.