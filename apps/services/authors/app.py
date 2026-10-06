import sys
from pathlib import Path

from flask import jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.jwt_security import ADMIN_ROLE, require_role
from shared.service import (
    ApiError,
    create_service,
    get_db_connection,
    invalidate_books_cache,
    load_service_env,
    positive_int,
    read_json,
    run_service,
)

load_service_env(__file__)
app = create_service(__name__, "Library Authors Service", "AUTHORS_CORS_ORIGINS")

AUTHOR_QUERY = """
    SELECT a.author_id, a.name,
           (SELECT COUNT(*) FROM book_author ba WHERE ba.author_id = a.author_id) AS book_count
    FROM author a
"""


def author_books(conn, author_id):
    return conn.execute(
        """
        SELECT b.isbn, b.title, ba.author_order
        FROM book_author ba
        JOIN book b ON b.isbn = ba.isbn
        WHERE ba.author_id = %s
        ORDER BY b.title
        """,
        (author_id,),
    ).fetchall()


def find_author(conn, author_id, lock=False):
    author = conn.execute(
        AUTHOR_QUERY + " WHERE a.author_id = %s" + (" FOR UPDATE OF a" if lock else ""),
        (author_id,),
    ).fetchone()
    if author is None:
        raise ApiError("Autor no encontrado.", 404)
    return author


def clean_name(body, required):
    if "name" not in body:
        if required:
            raise ApiError("Campo requerido: name.", 400)
        return None
    name = str(body["name"] or "").strip()
    if not name:
        raise ApiError("name no puede estar vacio.", 400)
    return name


def clean_isbns(body):
    if "books" not in body:
        return None
    books = body["books"]
    if not isinstance(books, list) or not all(isinstance(isbn, str) and isbn.strip() for isbn in books):
        raise ApiError("books debe ser una lista de ISBN.", 400)
    return list(dict.fromkeys(isbn.strip() for isbn in books))


def replace_books(conn, author_id, isbns):
    """Sustituye las relaciones del autor; devuelve los ISBN cuyo cache debe invalidarse."""
    previous = [row["isbn"] for row in conn.execute(
        "SELECT isbn FROM book_author WHERE author_id = %s", (author_id,)
    ).fetchall()]
    conn.execute("DELETE FROM book_author WHERE author_id = %s", (author_id,))
    for isbn in isbns:
        conn.execute(
            "INSERT INTO book_author (isbn, author_id) VALUES (%s, %s)", (isbn, author_id)
        )
    return set(previous) | set(isbns)


def author_detail(conn, author_id):
    author = find_author(conn, author_id)
    author["books"] = author_books(conn, author_id)
    return author


@app.get("/authors")
def list_authors():
    name = request.args.get("name", "").strip()
    with get_db_connection() as conn:
        if name:
            authors = conn.execute(
                AUTHOR_QUERY + " WHERE a.name ILIKE %s ORDER BY a.name", (f"%{name}%",)
            ).fetchall()
        else:
            authors = conn.execute(AUTHOR_QUERY + " ORDER BY a.name").fetchall()
    return jsonify(authors)


@app.get("/authors/<int:author_id>")
def get_author(author_id):
    with get_db_connection() as conn:
        return jsonify(author_detail(conn, author_id))


@app.get("/authors/<int:author_id>/books")
def get_author_books(author_id):
    with get_db_connection() as conn:
        find_author(conn, author_id)
        return jsonify(author_books(conn, author_id))


@app.post("/authors")
@require_role(ADMIN_ROLE)
def create_author():
    body = read_json()
    name = clean_name(body, required=True)
    isbns = clean_isbns(body)
    with get_db_connection() as conn:
        author_id = conn.execute(
            "INSERT INTO author (name) VALUES (%s) RETURNING author_id", (name,)
        ).fetchone()["author_id"]
        touched = replace_books(conn, author_id, isbns) if isbns else set()
        author = author_detail(conn, author_id)
    if touched:
        invalidate_books_cache(touched)
    return jsonify(message="Autor creado.", author=author), 201


def update_author(author_id, required):
    body = read_json()
    name = clean_name(body, required)
    isbns = clean_isbns(body)
    if name is None and isbns is None:
        raise ApiError("No hay campos para actualizar.", 400)
    with get_db_connection() as conn:
        find_author(conn, author_id, lock=True)
        touched = set()
        if name is not None:
            conn.execute("UPDATE author SET name = %s WHERE author_id = %s", (name, author_id))
            touched |= {row["isbn"] for row in author_books(conn, author_id)}
        if isbns is not None:
            touched |= replace_books(conn, author_id, isbns)
        author = author_detail(conn, author_id)
    invalidate_books_cache(touched)
    return jsonify(message="Autor actualizado.", author=author)


@app.put("/authors/<int:author_id>")
@require_role(ADMIN_ROLE)
def replace_author(author_id):
    return update_author(author_id, required=True)


@app.patch("/authors/<int:author_id>")
@require_role(ADMIN_ROLE)
def patch_author(author_id):
    return update_author(author_id, required=False)


@app.delete("/authors/<int:author_id>")
@require_role(ADMIN_ROLE)
def delete_author(author_id):
    with get_db_connection() as conn:
        author = find_author(conn, author_id, lock=True)
        # book_author usa ON DELETE RESTRICT: se exige quitar antes las relaciones.
        if author["book_count"]:
            raise ApiError("El autor tiene libros asociados; quita primero esas relaciones.", 409)
        conn.execute("DELETE FROM author WHERE author_id = %s", (author_id,))
    return jsonify(message="Autor eliminado.")


@app.post("/authors/<int:author_id>/books")
@require_role(ADMIN_ROLE)
def link_book(author_id):
    body = read_json()
    isbn = str(body.get("isbn") or "").strip()
    if not isbn:
        raise ApiError("Campo requerido: isbn.", 400)
    order = body.get("author_order")
    order = positive_int(order, "author_order") if order is not None else None
    with get_db_connection() as conn:
        find_author(conn, author_id)
        conn.execute(
            "INSERT INTO book_author (isbn, author_id, author_order) VALUES (%s, %s, %s)",
            (isbn, author_id, order),
        )
        books = author_books(conn, author_id)
    invalidate_books_cache([isbn])
    return jsonify(message="Libro relacionado con el autor.", books=books), 201


@app.delete("/authors/<int:author_id>/books/<isbn>")
@require_role(ADMIN_ROLE)
def unlink_book(author_id, isbn):
    with get_db_connection() as conn:
        deleted = conn.execute(
            "DELETE FROM book_author WHERE author_id = %s AND isbn = %s RETURNING isbn",
            (author_id, isbn),
        ).fetchone()
    if deleted is None:
        raise ApiError("La relacion autor-libro no existe.", 404)
    invalidate_books_cache([isbn])
    return jsonify(message="Relacion eliminada.")


if __name__ == "__main__":
    run_service(app, 5003)
