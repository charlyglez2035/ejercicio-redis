"""Reglas de pedidos compartidas por los microservicios pedidos y pagos.

Ambos usan la misma base PostgreSQL; las funciones reciben una conexion abierta
para ejecutarse dentro de la transaccion del endpoint que las llama.
"""
from decimal import Decimal

from shared.service import ApiError

ORDER_STATUSES = ("pending", "paid", "shipped", "delivered", "cancelled")
ORDER_TRANSITIONS = {
    "pending": ("paid", "cancelled"),
    "paid": ("shipped", "cancelled"),
    "shipped": ("delivered",),
    "delivered": (),
    "cancelled": (),
}


def lock_order(conn, order_id):
    order = conn.execute(
        "SELECT * FROM customer_order WHERE order_id = %s FOR UPDATE",
        (order_id,),
    ).fetchone()
    if order is None:
        raise ApiError("Pedido no encontrado.", 404)
    return order


def order_total(conn, order_id):
    row = conn.execute(
        "SELECT COALESCE(SUM(quantity * unit_price), 0) AS total FROM order_line WHERE order_id = %s",
        (order_id,),
    ).fetchone()
    return Decimal(row["total"])


def approved_amount(conn, order_id):
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS paid FROM payment WHERE order_id = %s AND status = 'approved'",
        (order_id,),
    ).fetchone()
    return Decimal(row["paid"])


def reserve_stock(conn, isbn, quantity):
    """Descuenta stock con bloqueo de fila; devuelve el precio vigente del libro."""
    book = conn.execute(
        "SELECT isbn, price, stock FROM book WHERE isbn = %s FOR UPDATE",
        (isbn,),
    ).fetchone()
    if book is None:
        raise ApiError(f"El libro {isbn} no existe.", 404)
    if book["stock"] < quantity:
        raise ApiError(f"Stock insuficiente para {isbn}: disponible {book['stock']}.", 409)
    conn.execute("UPDATE book SET stock = stock - %s WHERE isbn = %s", (quantity, isbn))
    return book["price"]


def release_stock(conn, isbn, quantity):
    conn.execute("UPDATE book SET stock = stock + %s WHERE isbn = %s", (quantity, isbn))


def restock_order(conn, order_id):
    lines = conn.execute(
        "SELECT isbn, quantity FROM order_line WHERE order_id = %s ORDER BY isbn",
        (order_id,),
    ).fetchall()
    for line in lines:
        release_stock(conn, line["isbn"], line["quantity"])
    return [line["isbn"] for line in lines]


def change_order_status(conn, order, new_status):
    """Aplica una transicion valida; cancelar devuelve el stock. Devuelve ISBN afectados."""
    if new_status not in ORDER_STATUSES:
        raise ApiError(f"Estado invalido. Usa: {', '.join(ORDER_STATUSES)}.", 400)
    if new_status == order["status"]:
        return []
    if new_status not in ORDER_TRANSITIONS[order["status"]]:
        raise ApiError(
            f"No se puede pasar de {order['status']} a {new_status}.", 409
        )
    touched = restock_order(conn, order["order_id"]) if new_status == "cancelled" else []
    conn.execute(
        "UPDATE customer_order SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
        (new_status, order["order_id"]),
    )
    order["status"] = new_status
    return touched
