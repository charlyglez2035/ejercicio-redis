import sys
from pathlib import Path

from flask import jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.jwt_security import ADMIN_ROLE, forbidden_response, is_admin, require_bearer, require_role
from shared.orders import (
    ORDER_STATUSES,
    ORDER_TRANSITIONS,
    approved_amount,
    change_order_status,
    lock_order,
    order_total,
    release_stock,
    reserve_stock,
    restock_order,
)
from shared.service import (
    ApiError,
    create_service,
    current_user_id,
    get_db_connection,
    invalidate_books_cache,
    load_service_env,
    positive_int,
    read_json,
    run_service,
)

load_service_env(__file__)
app = create_service(__name__, "Library Pedidos Service", "PEDIDOS_CORS_ORIGINS")

STOCK_QUERY = "SELECT isbn, title, price, stock FROM book"


def clean_lines(body):
    lines = body.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ApiError("lines debe ser una lista con al menos una linea {isbn, quantity}.", 400)
    merged = {}
    for line in lines:
        if not isinstance(line, dict) or not str(line.get("isbn") or "").strip():
            raise ApiError("Cada linea necesita isbn y quantity.", 400)
        isbn = str(line["isbn"]).strip()
        merged[isbn] = merged.get(isbn, 0) + positive_int(line.get("quantity"), "quantity")
    # Orden fijo por ISBN para bloquear filas de book siempre en el mismo orden.
    return dict(sorted(merged.items()))


def check_owner(order):
    if not is_admin() and order["user_id"] != current_user_id():
        raise ApiError("No tienes permisos para este pedido.", 403)


def require_pending(order):
    if order["status"] != "pending":
        raise ApiError("Solo se pueden modificar lineas de pedidos en estado pending.", 409)


def order_lines(conn, order_id):
    return conn.execute(
        """
        SELECT ol.isbn, b.title, ol.quantity, ol.unit_price,
               ol.quantity * ol.unit_price AS subtotal, b.stock AS current_stock
        FROM order_line ol
        JOIN book b ON b.isbn = ol.isbn
        WHERE ol.order_id = %s
        ORDER BY ol.isbn
        """,
        (order_id,),
    ).fetchall()


def order_detail(conn, order_id):
    order = conn.execute(
        """
        SELECT o.order_id, o.user_id, u.username, o.status, o.created_at, o.updated_at
        FROM customer_order o
        JOIN app_user u ON u.user_id = o.user_id
        WHERE o.order_id = %s
        """,
        (order_id,),
    ).fetchone()
    if order is None:
        raise ApiError("Pedido no encontrado.", 404)
    order["lines"] = order_lines(conn, order_id)
    order["total"] = order_total(conn, order_id)
    order["paid_amount"] = approved_amount(conn, order_id)
    order["allowed_status"] = list(ORDER_TRANSITIONS[order["status"]])
    return order


def add_quantity(conn, order_id, isbn, quantity):
    price = reserve_stock(conn, isbn, quantity)
    conn.execute(
        """
        INSERT INTO order_line (order_id, isbn, quantity, unit_price)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (order_id, isbn) DO UPDATE SET quantity = order_line.quantity + EXCLUDED.quantity
        """,
        (order_id, isbn, quantity, price),
    )


def set_line_quantity(conn, order_id, isbn, quantity):
    """Ajusta la linea al valor indicado moviendo solo la diferencia de stock."""
    line = conn.execute(
        "SELECT quantity FROM order_line WHERE order_id = %s AND isbn = %s FOR UPDATE",
        (order_id, isbn),
    ).fetchone()
    if line is None:
        raise ApiError("La linea no existe en el pedido.", 404)
    delta = quantity - line["quantity"]
    if delta > 0:
        reserve_stock(conn, isbn, delta)
    elif delta < 0:
        release_stock(conn, isbn, -delta)
    conn.execute(
        "UPDATE order_line SET quantity = %s WHERE order_id = %s AND isbn = %s",
        (quantity, order_id, isbn),
    )


def touch(conn, order_id):
    conn.execute(
        "UPDATE customer_order SET updated_at = CURRENT_TIMESTAMP WHERE order_id = %s", (order_id,)
    )


# ==================== CONSULTAS PUBLICAS ====================

@app.get("/pedidos/estados")
def list_statuses():
    return jsonify([
        {"status": status, "next": list(ORDER_TRANSITIONS[status])} for status in ORDER_STATUSES
    ])


@app.get("/stock")
def list_stock():
    with get_db_connection() as conn:
        return jsonify(conn.execute(STOCK_QUERY + " ORDER BY title").fetchall())


@app.get("/stock/<isbn>")
def get_stock(isbn):
    with get_db_connection() as conn:
        book = conn.execute(STOCK_QUERY + " WHERE isbn = %s", (isbn,)).fetchone()
    if book is None:
        raise ApiError("Libro no encontrado.", 404)
    return jsonify(book)


@app.patch("/stock/<isbn>")
@require_role(ADMIN_ROLE)
def update_stock(isbn):
    body = read_json()
    if "stock" in body:
        stock = body["stock"]
        if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
            raise ApiError("stock debe ser un entero mayor o igual a 0.", 400)
        assignment, value = "stock = %s", stock
    elif "delta" in body:
        delta = body["delta"]
        if isinstance(delta, bool) or not isinstance(delta, int) or delta == 0:
            raise ApiError("delta debe ser un entero distinto de 0.", 400)
        assignment, value = "stock = stock + %s", delta
    else:
        raise ApiError("Envia stock o delta.", 400)
    with get_db_connection() as conn:
        book = conn.execute(
            f"UPDATE book SET {assignment} WHERE isbn = %s RETURNING isbn, title, price, stock",
            (value, isbn),
        ).fetchone()
    if book is None:
        raise ApiError("Libro no encontrado.", 404)
    invalidate_books_cache([isbn])
    return jsonify(message="Stock actualizado.", book=book)


# ==================== PEDIDOS ====================

@app.get("/pedidos")
@require_bearer
def list_orders():
    clauses, params = [], []
    if not is_admin():
        clauses.append("o.user_id = %s")
        params.append(current_user_id())
    elif request.args.get("user_id"):
        clauses.append("o.user_id = %s")
        params.append(positive_int(request.args["user_id"], "user_id"))
    status = request.args.get("status", "").strip()
    if status:
        clauses.append("o.status = %s")
        params.append(status)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with get_db_connection() as conn:
        orders = conn.execute(
            f"""
            SELECT o.order_id, o.user_id, u.username, o.status, o.created_at, o.updated_at,
                   COALESCE((SELECT SUM(quantity * unit_price) FROM order_line ol
                             WHERE ol.order_id = o.order_id), 0) AS total
            FROM customer_order o
            JOIN app_user u ON u.user_id = o.user_id
            {where}
            ORDER BY o.order_id DESC
            """,
            params,
        ).fetchall()
    return jsonify(orders)


@app.get("/pedidos/<int:order_id>")
@require_bearer
def get_order(order_id):
    with get_db_connection() as conn:
        order = order_detail(conn, order_id)
    check_owner(order)
    return jsonify(order)


@app.post("/pedidos")
@require_bearer
def create_order():
    body = read_json()
    user_id = current_user_id()
    if "user_id" in body and body["user_id"] != user_id:
        if not is_admin():
            return forbidden_response()
        user_id = positive_int(body["user_id"], "user_id")
    lines = clean_lines(body)
    with get_db_connection() as conn:
        order_id = conn.execute(
            "INSERT INTO customer_order (user_id) VALUES (%s) RETURNING order_id", (user_id,)
        ).fetchone()["order_id"]
        for isbn, quantity in lines.items():
            add_quantity(conn, order_id, isbn, quantity)
        order = order_detail(conn, order_id)
    invalidate_books_cache(lines)
    return jsonify(message="Pedido creado.", order=order), 201


@app.put("/pedidos/<int:order_id>")
@require_bearer
def replace_order(order_id):
    """Sustituye todas las lineas de un pedido pending."""
    body = read_json()
    lines = clean_lines(body)
    with get_db_connection() as conn:
        order = lock_order(conn, order_id)
        check_owner(order)
        require_pending(order)
        touched = set(restock_order(conn, order_id)) | set(lines)
        conn.execute("DELETE FROM order_line WHERE order_id = %s", (order_id,))
        for isbn, quantity in lines.items():
            add_quantity(conn, order_id, isbn, quantity)
        touch(conn, order_id)
        order = order_detail(conn, order_id)
    invalidate_books_cache(touched)
    return jsonify(message="Pedido actualizado.", order=order)


@app.patch("/pedidos/<int:order_id>")
@require_bearer
def patch_order(order_id):
    """Cambia el estado. Un cliente solo puede cancelar su pedido pending."""
    body = read_json()
    new_status = str(body.get("status") or "").strip()
    if not new_status:
        raise ApiError("Campo requerido: status.", 400)
    with get_db_connection() as conn:
        order = lock_order(conn, order_id)
        check_owner(order)
        if not is_admin() and not (order["status"] == "pending" and new_status == "cancelled"):
            raise ApiError("Solo un administrador puede aplicar ese cambio de estado.", 403)
        if new_status == "paid" and approved_amount(conn, order_id) < order_total(conn, order_id):
            raise ApiError("El pedido no tiene pagos aprobados que cubran el total.", 409)
        touched = change_order_status(conn, order, new_status)
        order = order_detail(conn, order_id)
    if touched:
        invalidate_books_cache(touched)
    return jsonify(message="Estado del pedido actualizado.", order=order)


@app.delete("/pedidos/<int:order_id>")
@require_role(ADMIN_ROLE)
def delete_order(order_id):
    with get_db_connection() as conn:
        order = lock_order(conn, order_id)
        if order["status"] not in ("pending", "cancelled"):
            raise ApiError("Solo se eliminan pedidos pending o cancelled; cancela primero.", 409)
        has_payments = conn.execute(
            "SELECT 1 FROM payment WHERE order_id = %s LIMIT 1", (order_id,)
        ).fetchone()
        if has_payments:
            raise ApiError("El pedido tiene pagos registrados; no se puede eliminar.", 409)
        touched = restock_order(conn, order_id) if order["status"] == "pending" else []
        conn.execute("DELETE FROM customer_order WHERE order_id = %s", (order_id,))
    if touched:
        invalidate_books_cache(touched)
    return jsonify(message="Pedido eliminado.")


# ==================== LINEAS ====================

@app.get("/pedidos/<int:order_id>/lineas")
@require_bearer
def list_lines(order_id):
    with get_db_connection() as conn:
        order = order_detail(conn, order_id)
    check_owner(order)
    return jsonify(order["lines"])


@app.post("/pedidos/<int:order_id>/lineas")
@require_bearer
def add_line(order_id):
    body = read_json()
    lines = clean_lines({"lines": [body]})
    with get_db_connection() as conn:
        order = lock_order(conn, order_id)
        check_owner(order)
        require_pending(order)
        for isbn, quantity in lines.items():
            add_quantity(conn, order_id, isbn, quantity)
        touch(conn, order_id)
        order = order_detail(conn, order_id)
    invalidate_books_cache(lines)
    return jsonify(message="Linea agregada.", order=order), 201


@app.put("/pedidos/<int:order_id>/lineas/<isbn>")
@app.patch("/pedidos/<int:order_id>/lineas/<isbn>")
@require_bearer
def update_line(order_id, isbn):
    body = read_json()
    quantity = positive_int(body.get("quantity"), "quantity")
    with get_db_connection() as conn:
        order = lock_order(conn, order_id)
        check_owner(order)
        require_pending(order)
        set_line_quantity(conn, order_id, isbn, quantity)
        touch(conn, order_id)
        order = order_detail(conn, order_id)
    invalidate_books_cache([isbn])
    return jsonify(message="Linea actualizada.", order=order)


@app.delete("/pedidos/<int:order_id>/lineas/<isbn>")
@require_bearer
def delete_line(order_id, isbn):
    with get_db_connection() as conn:
        order = lock_order(conn, order_id)
        check_owner(order)
        require_pending(order)
        line = conn.execute(
            "DELETE FROM order_line WHERE order_id = %s AND isbn = %s RETURNING quantity",
            (order_id, isbn),
        ).fetchone()
        if line is None:
            raise ApiError("La linea no existe en el pedido.", 404)
        release_stock(conn, isbn, line["quantity"])
        touch(conn, order_id)
        order = order_detail(conn, order_id)
    invalidate_books_cache([isbn])
    return jsonify(message="Linea eliminada.", order=order)


if __name__ == "__main__":
    run_service(app, 5004)
