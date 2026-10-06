# Diagrama entidad-relación

```mermaid
erDiagram
    APP_USER {
        bigint user_id PK
        varchar username UK
        varchar email UK
        text password_hash
        varchar full_name
        varchar role
        timestamptz created_at
    }

    BOOK_FORMAT {
        bigint format_id PK
        varchar name UK
    }

    BOOK_CATEGORY {
        bigint category_id PK
        varchar name UK
        text description
    }

    BOOK {
        varchar isbn PK
        varchar title
        smallint publication_year
        numeric price
        integer stock
        bigint format_id FK
        bigint category_id FK
    }

    AUTHOR {
        bigint author_id PK
        varchar name UK
    }

    BOOK_AUTHOR {
        varchar isbn PK, FK
        bigint author_id PK, FK
        smallint author_order
    }

    GENRE {
        bigint genre_id PK
        varchar name UK
        text description
    }

    BOOK_GENRE {
        varchar isbn PK, FK
        bigint genre_id PK, FK
    }

    CONCEPT {
        bigint concept_id PK
        varchar name UK
    }

    BOOK_CONCEPT {
        varchar isbn PK, FK
        bigint concept_id PK, FK
        text definition
    }

    BOOK_IMAGE {
        bigint image_id PK
        varchar isbn FK
        text image_url
        varchar alt_text
        integer display_order
        boolean is_cover
    }

    BOOK_FORMAT ||--o{ BOOK : "has"
    BOOK_CATEGORY ||--o{ BOOK : "classifies"
    BOOK ||--o{ BOOK_AUTHOR : "has"
    AUTHOR ||--o{ BOOK_AUTHOR : "writes"
    BOOK ||--o{ BOOK_GENRE : "belongs to"
    GENRE ||--o{ BOOK_GENRE : "contains"
    BOOK ||--o{ BOOK_CONCEPT : "defines"
    CONCEPT ||--o{ BOOK_CONCEPT : "appears in"
    BOOK ||--o{ BOOK_IMAGE : "has"
```

## Restricciones principales

- `APP_USER` admite muchos clientes, pero el índice parcial `one_admin_only_idx` permite como máximo un usuario con rol `admin`.
- `BOOK_IMAGE` permite varias imágenes por libro y el índice parcial `one_cover_image_per_book_idx` permite como máximo una portada por libro.
- `BOOK_AUTHOR`, `BOOK_GENRE` y `BOOK_CONCEPT` resuelven las relaciones multivaluadas mediante claves primarias compuestas.
- `BOOK_CONCEPT` conserva una definición específica para cada combinación de libro y concepto.