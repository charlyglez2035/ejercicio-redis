-- PostgreSQL schema for the book catalog.
--
-- Functional dependencies:
--   isbn -> title, publication_year, price, stock, format_id, category_id
--   author_id -> author data
--   genre_id -> genre name
--   concept_id -> concept name
--   user_id -> user data
--
-- Multivalued dependencies are represented by separate relations:
--   isbn ->> authors, genres, images, and concept definitions.

BEGIN;

CREATE TABLE app_user (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(160) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer',
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verification_token_hash CHAR(64),
    verification_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT app_user_role_ck CHECK (role IN ('customer', 'admin'))
);

-- The partial unique index permits customers but only one admin.
CREATE UNIQUE INDEX one_admin_only_idx
    ON app_user (role)
    WHERE role = 'admin';

CREATE TABLE book_format (
    format_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE book_category (
    category_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE book (
    isbn VARCHAR(17) PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    publication_year SMALLINT,
    price NUMERIC(12, 2) NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    format_id BIGINT NOT NULL REFERENCES book_format(format_id),
    category_id BIGINT NOT NULL REFERENCES book_category(category_id),
    CONSTRAINT book_isbn_ck CHECK (isbn ~ '^(97[89][- ]?)?[0-9][- 0-9]{8,16}$'),
    CONSTRAINT book_publication_year_ck CHECK (
        publication_year IS NULL OR publication_year BETWEEN 1000 AND 9999
    ),
    CONSTRAINT book_price_ck CHECK (price >= 0),
    CONSTRAINT book_stock_ck CHECK (stock >= 0)
);

CREATE TABLE author (
    author_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(180) NOT NULL,
    CONSTRAINT author_name_uq UNIQUE (name)
);

CREATE TABLE book_author (
    isbn VARCHAR(17) NOT NULL REFERENCES book(isbn) ON DELETE CASCADE,
    author_id BIGINT NOT NULL REFERENCES author(author_id) ON DELETE RESTRICT,
    author_order SMALLINT,
    PRIMARY KEY (isbn, author_id),
    CONSTRAINT book_author_order_ck CHECK (author_order IS NULL OR author_order > 0),
    CONSTRAINT book_author_order_uq UNIQUE (isbn, author_order)
);

CREATE TABLE genre (
    genre_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE book_genre (
    isbn VARCHAR(17) NOT NULL REFERENCES book(isbn) ON DELETE CASCADE,
    genre_id BIGINT NOT NULL REFERENCES genre(genre_id) ON DELETE RESTRICT,
    PRIMARY KEY (isbn, genre_id)
);

CREATE TABLE concept (
    concept_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(180) NOT NULL UNIQUE
);

CREATE TABLE book_concept (
    isbn VARCHAR(17) NOT NULL REFERENCES book(isbn) ON DELETE CASCADE,
    concept_id BIGINT NOT NULL REFERENCES concept(concept_id) ON DELETE RESTRICT,
    definition TEXT NOT NULL,
    PRIMARY KEY (isbn, concept_id)
);

CREATE TABLE book_image (
    image_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn VARCHAR(17) NOT NULL REFERENCES book(isbn) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    alt_text VARCHAR(300),
    display_order INTEGER NOT NULL DEFAULT 1,
    is_cover BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT book_image_order_ck CHECK (display_order > 0),
    CONSTRAINT book_image_order_uq UNIQUE (isbn, display_order),
    CONSTRAINT book_image_url_uq UNIQUE (isbn, image_url)
);

CREATE UNIQUE INDEX one_cover_image_per_book_idx
    ON book_image (isbn)
    WHERE is_cover;

CREATE INDEX book_author_author_idx ON book_author (author_id);
CREATE INDEX book_genre_genre_idx ON book_genre (genre_id);
CREATE INDEX book_concept_concept_idx ON book_concept (concept_id);
CREATE INDEX book_image_isbn_idx ON book_image (isbn);

COMMIT;