import os
from pathlib import Path
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from flasgger import Swagger
from werkzeug.exceptions import HTTPException


# ==================== CONFIGURACIÓN ====================

load_dotenv(Path(__file__).with_name(".env"))
load_dotenv()

app = Flask(__name__)
app.json.ensure_ascii = False

CORS(app, resources={
    r"/api/*": {"origins": "*"},
    r"/books*": {"origins": "*"},
    r"/concepts": {"origins": "*"},
})

Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "Library - JSON / XML",
        "version": "2.0.0",
        "description": "XML por defecto. Usa format=json para obtener JSON.",
    },
})

# Para imágenes /uploads/... alojadas en el monolito.
# En la VM configura MONOLITH_PUBLIC_URL en .env con su URL pública.
MONOLITH_PUBLIC_URL = os.getenv(
    "MONOLITH_PUBLIC_URL", "http://localhost:3000"
).rstrip("/") + "/"


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "library"),
        user=os.getenv("DB_USER", "library_user"),
        password=os.getenv("DB_PASSWORD", ""),
        connect_timeout=5,
        row_factory=dict_row,
    )

def attach_public_image_urls(books):
    for book in books:
        for image in book.get("images", []):
            image["image_url"] = urljoin(
                MONOLITH_PUBLIC_URL,
                image["image_url"],
            )
    return books


# ==================== RESPUESTAS JSON / XML ====================

def is_data_route():
    path = request.path
    return (
        path == "/books"
        or path.startswith("/books/")
        or path == "/concepts"
        or path == "/health"
        or path.startswith("/api/")
    )


@app.before_request
def validate_format():
    if is_data_route():
        output_format = request.args.get("format", "xml").lower()

        if output_format not in ("json", "xml"):
            return jsonify(
                error="Formato inválido. Usa format=json o format=xml."
            ), 400


@app.after_request
def format_response(response):
    # Las vistas HTML y Swagger conservan su formato.
    if not response.is_json:
        return response

    if not is_data_route() and response.status_code < 400:
        return response

    output_format = request.args.get("format", "xml").lower()

    if output_format == "json":
        return response

    data = response.get_json()

    if response.status_code >= 400:
        root_name = "error"
    elif request.path in ("/concepts", "/api/cloud", "/api/concepts"):
        root_name = "concepts"
    elif isinstance(data, list):
        root_name = "books"
    else:
        root_name = "response"

    root = ET.Element(root_name)

    singular = {
        "books": "book",
        "concepts": "concept",
        "images": "image",
        "authors": "author",
    }

    def append_xml(parent, value):
        if isinstance(value, dict):
            for key, item in value.items():
                append_xml(ET.SubElement(parent, key), item)

        elif isinstance(value, list):
            tag = singular.get(parent.tag, "item")
            for item in value:
                append_xml(ET.SubElement(parent, tag), item)

        elif value is None:
            parent.set("null", "true")

        elif isinstance(value, bool):
            parent.text = "true" if value else "false"

        else:
            parent.text = str(value)

    append_xml(root, data)

    response.set_data(ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    ))
    response.content_type = "application/xml; charset=utf-8"
    return response


# ==================== CONSULTA BASE ====================

BOOK_QUERY = """
    SELECT
        b.isbn,
        b.title,
        b.publication_year,
        b.price,
        b.stock,
        b.format_id,
        b.category_id,
        bf.name AS format,
        bc.name AS category,
        COALESCE((
            SELECT STRING_AGG(a.name, ', ' ORDER BY a.name)
            FROM book_author ba
            JOIN author a ON a.author_id = ba.author_id
            WHERE ba.isbn = b.isbn
            ), '') AS authors,
            COALESCE((
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'image_id', bi.image_id,
                        'image_url', bi.image_url,
                        'alt_text', bi.alt_text,
                        'is_cover', bi.is_cover,
                        'display_order', bi.display_order
                    )
                    ORDER BY bi.is_cover DESC, bi.display_order, bi.image_id
                )
                FROM book_image bi
                WHERE bi.isbn = b.isbn
            ), '[]'::jsonb) AS images
    FROM book b
    LEFT JOIN book_format bf ON bf.format_id = b.format_id
    LEFT JOIN book_category bc ON bc.category_id = b.category_id
"""


# ==================== LISTADO ====================

@app.get("/books")
@app.get("/api/books")
def get_all_books():
    """
    Obtiene todos los libros.
    ---
    tags:
      - Books
    parameters:
      - name: format
        in: query
        type: string
        enum: [xml, json]
        default: xml
    responses:
      200:
        description: Lista de libros
    """
    with get_db_connection() as conn:
        books = conn.execute(
            BOOK_QUERY + " ORDER BY b.title"
        ).fetchall()

        return jsonify(attach_public_image_urls(books))


# ==================== BÚSQUEDA ====================

@app.get("/books/search")
@app.get("/api/books/search")
def search_books():
    clauses = []
    params = []

    for parameter, column in (
        ("title", "b.title"),
        ("category", "bc.name"),
    ):
        value = request.args.get(parameter, "").strip()
        if value:
            clauses.append(f"{column} ILIKE %s")
            params.append(f"%{value}%")

    author = request.args.get("author", "").strip()
    if author:
        clauses.append("""
            EXISTS (
                SELECT 1
                FROM book_author ba
                JOIN author a ON a.author_id = ba.author_id
                WHERE ba.isbn = b.isbn AND a.name ILIKE %s
            )
        """)
        params.append(f"%{author}%")

    genre = request.args.get("genre", "").strip()
    if genre:
        clauses.append("""
            EXISTS (
                SELECT 1
                FROM book_genre bg
                JOIN genre g ON g.genre_id = bg.genre_id
                WHERE bg.isbn = b.isbn AND g.name ILIKE %s
            )
        """)
        params.append(f"%{genre}%")

    query = BOOK_QUERY
    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY b.title"

    with get_db_connection() as conn:
        books = conn.execute(query, params).fetchall()

    return jsonify(attach_public_image_urls(books))


# ==================== DATOS MÍNIMOS E IMÁGENES ====================

@app.get("/books/cards")
@app.get("/api/books/cards")
def get_book_cards():
    """
    Obtiene datos mínimos e imágenes de los libros.
    ---
    tags:
      - Books
    parameters:
      - name: format
        in: query
        type: string
        enum: [xml, json]
        default: xml
    responses:
      200:
        description: Libros con sus imágenes
    """
    query = """
        SELECT
            b.isbn,
            b.title,
            b.price,
            b.stock,
            COALESCE((
                SELECT STRING_AGG(a.name, ', ' ORDER BY a.name)
                FROM book_author ba
                JOIN author a ON a.author_id = ba.author_id
                WHERE ba.isbn = b.isbn
            ), '') AS authors,
            COALESCE((
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'image_id', bi.image_id,
                        'image_url', bi.image_url,
                        'alt_text', bi.alt_text,
                        'is_cover', bi.is_cover,
                        'display_order', bi.display_order
                    )
                    ORDER BY bi.is_cover DESC, bi.display_order, bi.image_id
                )
                FROM book_image bi
                WHERE bi.isbn = b.isbn
            ), '[]'::jsonb) AS images
        FROM book b
        ORDER BY b.title
    """

    with get_db_connection() as conn:
        books = conn.execute(query).fetchall()

    for book in books:
        for image in book["images"]:
            image["image_url"] = urljoin(
                MONOLITH_PUBLIC_URL,
                image["image_url"],
            )

    return jsonify(books)


# ==================== LIBRO POR ISBN ====================

@app.get("/books/<isbn>")
@app.get("/api/books/<isbn>")
def get_book(isbn):
    """
    Obtiene un libro por ISBN.
    ---
    tags:
      - Books
    parameters:
      - name: isbn
        in: path
        required: true
        type: string
      - name: format
        in: query
        type: string
        enum: [xml, json]
        default: xml
    responses:
      200:
        description: Libro encontrado
      404:
        description: Libro no encontrado
    """
    with get_db_connection() as conn:
        book = conn.execute(
            BOOK_QUERY + " WHERE b.isbn = %s",
            (isbn,),
        ).fetchone()

    if book is None:
        return jsonify(error="Libro no encontrado"), 404

    return jsonify(book)


# ==================== CONCEPTOS CLOUD Y LIBROS ====================

@app.get("/concepts")
@app.get("/api/concepts")
@app.get("/api/cloud")
def get_cloud_concepts():
    """
    Obtiene los modelos cloud y sus libros relacionados.
    ---
    tags:
      - Cloud
    parameters:
      - name: format
        in: query
        type: string
        enum: [xml, json]
        default: xml
    responses:
      200:
        description: Conceptos y libros asociados en PostgreSQL
    """

    # Los modelos generales están definidos aquí.
    # Los libros y las definiciones asociadas salen de PostgreSQL.
    # Si no existen asociaciones, books será una lista vacía.
    query = """
        WITH models(name, title, description, example) AS (
            VALUES
            (
                'IaaS',
                'Infraestructura como servicio',
                'Alquilas infraestructura y administras el sistema operativo y las aplicaciones.',
                'Ejemplo: una máquina virtual de Compute Engine.'
            ),
            (
                'PaaS',
                'Plataforma como servicio',
                'Publicas código en una plataforma que administra la infraestructura y el entorno.',
                'Ejemplo: una aplicación en App Engine.'
            ),
            (
                'SaaS',
                'Software como servicio',
                'Utilizas una aplicación por Internet que mantiene el proveedor.',
                'Ejemplo: Google Docs.'
            ),
            (
                'FaaS',
                'Funciones como servicio',
                'Ejecutas funciones en respuesta a eventos sin administrar servidores.',
                'Ejemplo: procesar un archivo cuando se carga.'
            )
        )
        SELECT
            m.name,
            m.title,
            m.description,
            m.example,
            COALESCE((
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'concept_id', c.concept_id,
                        'definition', bc.definition,
                        'isbn', b.isbn,
                        'title', b.title,
                        'publication_year', b.publication_year,
                        'price', b.price,
                        'stock', b.stock
                    )
                    ORDER BY b.title
                )
                FROM concept c
                JOIN book_concept bc ON bc.concept_id = c.concept_id
                JOIN book b ON b.isbn = bc.isbn
                WHERE LOWER(TRIM(c.name)) = LOWER(m.name)
            ), '[]'::jsonb) AS books
        FROM models m
        ORDER BY m.name
    """

    with get_db_connection() as conn:
        concepts = conn.execute(query).fetchall()

    return jsonify(concepts)


# ==================== AUTORES ====================

def valid_authors(data):
    return (
        "authors" not in data
        or (
            isinstance(data["authors"], list)
            and all(
                isinstance(name, str) and name.strip()
                for name in data["authors"]
            )
        )
    )


def replace_authors(conn, isbn, names):
    conn.execute(
        "DELETE FROM book_author WHERE isbn = %s",
        (isbn,),
    )

    for name in dict.fromkeys(name.strip() for name in names):
        author = conn.execute(
            "SELECT author_id FROM author WHERE name = %s",
            (name,),
        ).fetchone()

        if author is None:
            author = conn.execute(
                """
                INSERT INTO author (name)
                VALUES (%s)
                RETURNING author_id
                """,
                (name,),
            ).fetchone()

        conn.execute(
            """
            INSERT INTO book_author (isbn, author_id)
            VALUES (%s, %s)
            """,
            (isbn, author["author_id"]),
        )


# ==================== CREAR LIBRO ====================

@app.post("/books")
@app.post("/api/books")
def create_book():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Envía un objeto JSON válido"), 400

    for field in ("isbn", "title", "price", "format_id", "category_id"):
        if data.get(field) is None or data.get(field) == "":
            return jsonify(error=f"Campo requerido: {field}"), 400

    if not valid_authors(data):
        return jsonify(error="authors debe ser una lista de nombres"), 400

    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO book (
                isbn, title, publication_year, price,
                stock, format_id, category_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data["isbn"],
            data["title"],
            data.get("publication_year"),
            data["price"],
            data.get("stock", 0),
            data["format_id"],
            data["category_id"],
        ))

        if "authors" in data:
            replace_authors(conn, data["isbn"], data["authors"])

    return jsonify(
        message="Libro creado",
        isbn=data["isbn"],
    ), 201


# ==================== ACTUALIZAR LIBRO ====================

@app.put("/books/<isbn>")
@app.put("/api/books/<isbn>")
@app.patch("/books/<isbn>")
@app.patch("/api/books/<isbn>")
def update_book(isbn):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Envía un objeto JSON válido"), 400

    if not valid_authors(data):
        return jsonify(error="authors debe ser una lista de nombres"), 400

    allowed = (
        "title", "publication_year", "price",
        "stock", "format_id", "category_id",
    )
    fields = [field for field in allowed if field in data]

    if not fields and "authors" not in data:
        return jsonify(error="No hay campos para actualizar"), 400

    with get_db_connection() as conn:
        exists = conn.execute(
            "SELECT isbn FROM book WHERE isbn = %s FOR UPDATE",
            (isbn,),
        ).fetchone()

        if exists is None:
            return jsonify(error="Libro no encontrado"), 404

        if fields:
            assignments = ", ".join(f"{field} = %s" for field in fields)
            params = [data[field] for field in fields] + [isbn]

            conn.execute(
                f"UPDATE book SET {assignments} WHERE isbn = %s",
                params,
            )

        if "authors" in data:
            replace_authors(conn, isbn, data["authors"])

    return jsonify(message="Libro actualizado")


# ==================== ELIMINAR LIBRO ====================

@app.delete("/books/<isbn>")
@app.delete("/api/books/<isbn>")
def delete_book(isbn):
    with get_db_connection() as conn:
        deleted = conn.execute(
            "DELETE FROM book WHERE isbn = %s RETURNING isbn",
            (isbn,),
        ).fetchone()

    if deleted is None:
        return jsonify(error="Libro no encontrado"), 404

    return jsonify(message="Libro eliminado")


# ==================== ESTADO ====================

@app.get("/health")
@app.get("/api/health")
def health_check():
    with get_db_connection() as conn:
        conn.execute("SELECT 1")

    return jsonify(
        status="ok",
        message="Flask y PostgreSQL disponibles",
    )


# ==================== VISTAS HTML ====================

PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    background: #f3f5fa;
    color: #17283f;
    font: 16px/1.6 Arial, sans-serif;
}
header { background: #17283f; padding: 20px; }
nav {
    max-width: 1120px;
    margin: auto;
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
}
nav a { color: white; text-decoration: none; font-weight: bold; }
main { max-width: 1120px; margin: auto; padding: 30px 20px; }
h1 { font-size: 36px; line-height: 1.2; }
h2 { font-size: 22px; line-height: 1.3; }
a { color: #176b59; }
.links { display: flex; gap: 20px; margin: 20px 0; }
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(270px, 100%), 1fr));
    gap: 22px;
}
.card {
    background: white;
    border: 1px solid #dce4ee;
    border-radius: 14px;
    padding: 24px;
    overflow-wrap: anywhere;
}
.card p { color: #526176; }
.badge {
    display: inline-block;
    background: #e0f4eb;
    color: #176b59;
    border-radius: 20px;
    padding: 5px 12px;
    font-weight: bold;
}
.cover {
    width: 100%;
    height: 230px;
    object-fit: contain;
    background: #eef1f6;
    border-radius: 8px;
}
.placeholder {
    height: 230px;
    display: grid;
    place-items: center;
    background: #eef1f6;
    border-radius: 8px;
    color: #526176;
}
.related {
    border-top: 1px solid #e1e7ef;
    margin-top: 15px;
    padding-top: 12px;
}
input {
    width: 100%;
    max-width: 500px;
    padding: 12px;
    border: 1px solid #bac6d5;
    border-radius: 8px;
    font: inherit;
}
button {
    padding: 10px 16px;
    background: #17283f;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
}
</style>
</head>
<body>
<header>
<nav>
    <a href="/cloud">Conceptos cloud</a>
    <a href="/catalogo">Catálogo de libros</a>
</nav>
</header>
<main>
<h1>{{ title }}</h1>
<div class="links">
    <a href="{{ endpoint }}?format=json">Ver JSON</a>
    <a href="{{ endpoint }}?format=xml">Ver XML</a>
</div>

{% if mode == 'books' %}
<label for="search">Buscar por título, autor o ISBN</label><br>
<input id="search" type="search" placeholder="Buscar libros...">
{% endif %}

<p id="status" role="status" aria-live="polite">Cargando...</p>
<button id="retry" hidden>Reintentar</button>
<section id="cards" class="grid"></section>
</main>

<script>
const mode = {{ mode | tojson }};
const endpoint = {{ endpoint | tojson }};
const cards = document.querySelector("#cards");
const status = document.querySelector("#status");
const retry = document.querySelector("#retry");
const search = document.querySelector("#search");
let books = [];

function make(tag, text, className) {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    return el;
}

function addCover(card, book) {
    const image = book.images?.find(img => img.is_cover)
        || book.images?.[0];

    const placeholder = () => make("div", "Sin imagen disponible", "placeholder");

    if (!image?.image_url) {
        card.append(placeholder());
        return;
    }

    let url;
    try {
        url = new URL(image.image_url, location.origin);
        if (!["http:", "https:"].includes(url.protocol)) {
            throw new Error("URL inválida");
        }
    } catch {
        card.append(placeholder());
        return;
    }

    const img = document.createElement("img");
    img.className = "cover";
    img.src = url.href;
    img.alt = image.alt_text || book.title;
    img.loading = "lazy";
    img.addEventListener("error", () => img.replaceWith(placeholder()), {
        once: true
    });
    card.append(img);
}

function render(items) {
    cards.replaceChildren();
    status.textContent = items.length
        ? items.length + " resultados"
        : "No hay resultados.";

    for (const item of items) {
        const card = make("article", "", "card");

        if (mode === "cloud") {
            card.append(
                make("span", item.name, "badge"),
                make("h2", item.title),
                make("p", item.description),
                make("p", item.example)
            );

            const related = make("div", "", "related");
            related.append(make("strong", "Libros relacionados"));

            if (!item.books.length) {
                related.append(make(
                    "p",
                    "Todavía no hay libros asociados a este concepto en la base de datos."
                ));
            }

            for (const book of item.books) {
                related.append(
                    make("h3", book.title),
                    make("p", "ISBN: " + book.isbn),
                    make("p", book.definition)
                );
            }

            card.append(related);
        } else {
            addCover(card, item);
            card.append(
                make("h2", item.title),
                make("p", item.authors || "Autor no registrado"),
                make("p", "ISBN: " + item.isbn),
                make("p", "Precio: " + (item.price ?? "Sin precio")),
                make("p", "Existencias: " + (item.stock ?? 0))
            );
        }

        cards.append(card);
    }
}

function filterBooks() {
    const query = (search?.value || "").toLocaleLowerCase();

    render(books.filter(book =>
        [book.title, book.authors, book.isbn]
            .join(" ")
            .toLocaleLowerCase()
            .includes(query)
    ));
}

function readCloudXml(text) {
    const xml = new DOMParser().parseFromString(text, "application/xml");

    if (xml.querySelector("parsererror")) {
        throw new Error("XML inválido");
    }

    const value = (node, name) =>
        [...node.children].find(child => child.tagName === name)
            ?.textContent || "";

    return [...xml.documentElement.children].map(node => {
        const booksNode = [...node.children].find(
            child => child.tagName === "books"
        );

        return {
            name: value(node, "name"),
            title: value(node, "title"),
            description: value(node, "description"),
            example: value(node, "example"),
            books: [...(booksNode?.children || [])].map(book => ({
                isbn: value(book, "isbn"),
                title: value(book, "title"),
                definition: value(book, "definition")
            }))
        };
    });
}

async function loadData() {
    retry.hidden = true;
    status.textContent = "Cargando...";

    try {
        // Cloud consume XML; las cards consumen JSON.
        const format = mode === "cloud" ? "xml" : "json";
        const response = await fetch(endpoint + "?format=" + format);

        if (!response.ok) {
            throw new Error("HTTP " + response.status);
        }

        if (mode === "cloud") {
            render(readCloudXml(await response.text()));
        } else {
            books = await response.json();

            if (!Array.isArray(books)) {
                throw new Error("Respuesta de catálogo inválida");
            }

            filterBooks();
        }
    } catch (error) {
        cards.replaceChildren();
        status.textContent =
            "No se pudieron cargar los datos. Revisa Flask y PostgreSQL. "
            + error.message;
        retry.hidden = false;
    }
}

search?.addEventListener("input", filterBooks);
retry.addEventListener("click", loadData);
loadData();
</script>
</body>
</html>
"""


@app.get("/")
@app.get("/cloud")
def cloud_page():
    return render_template_string(
        PAGE,
        title="Servicios de Cloud Computing",
        mode="cloud",
        endpoint="/concepts",
    )


@app.get("/catalogo")
def catalog_page():
    return render_template_string(
        PAGE,
        title="Catálogo de libros",
        mode="books",
        endpoint="/books/cards",
    )


# ==================== ERRORES ====================

@app.errorhandler(psycopg.IntegrityError)
def integrity_error(error):
    app.logger.exception("Error de integridad en PostgreSQL")
    return jsonify(
        error="Datos duplicados, referencias inválidas o campos requeridos."
    ), 400


@app.errorhandler(psycopg.DataError)
def data_error(error):
    return jsonify(error="Algún dato tiene un tipo o valor inválido."), 400


@app.errorhandler(psycopg.Error)
def database_error(error):
    app.logger.exception("Error de PostgreSQL")
    return jsonify(
        error="No se pudo consultar PostgreSQL. Revisa la terminal y tu .env."
    ), 500


@app.errorhandler(HTTPException)
def http_error(error):
    response = error.get_response()
    response.set_data(app.json.dumps({
        "error": error.name,
        "message": error.description,
    }))
    response.content_type = "application/json"
    return response


@app.errorhandler(Exception)
def unexpected_error(error):
    app.logger.exception("Error inesperado")
    return jsonify(
        error="Error interno del servidor. Revisa la terminal."
    ), 500


# ==================== ARRANQUE ====================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("SERVICE_PORT", "5001")),
        debug=False,
    )