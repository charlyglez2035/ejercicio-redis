# Arquitectura del proyecto

## Estructura

```text
library/
├── .env                    # Configuracion local, no se versiona
├── .env.example            # Plantilla publica de configuracion
├── .gitignore
├── package.json
├── README.md
├── docs/
│   └── architecture.md
├── db/
│   ├── scheme.sql
│   └── database-diagram.md
└── apps/
    └── web-monolito/
        ├── public/
        ├── src/
        │   ├── db.js
        │   ├── middleware/
        │   ├── routes/
        │   └── server.js
        └── views/
```

## Flujo MVC

El navegador envia formularios HTML a las rutas de `src/routes`. Estas rutas validan el acceso, ejecutan consultas parametrizadas mediante `src/db.js` y renderizan las vistas EJS. No existe una capa API ni intercambio de JSON/XML.

## Persistencia

PostgreSQL contiene el modelo normalizado definido en `db/scheme.sql`. Las relaciones multivaluadas se almacenan en tablas puente y las operaciones relacionadas con un libro se ejecutan dentro de una transaccion.
