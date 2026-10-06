import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.jwt_security import ADMIN_ROLE, is_admin, require_bearer, require_role
from shared.orders import approved_amount, change_order_status, lock_order, order_total
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
app = create_service(__name__, "Library Pagos Service", "PAGOS_CORS_ORIGINS")

PAYMENT_METHODS = ("card", "cash", "transfer")
PAYMENT_STATUSES = ("pending", "approved", "rejected", "refunded")
PAYMENT_TRANSITIONS = {
    "pending": ("approved", "rejected"),
    "approved": ("refunded",),
    "rejected": (),
    "refunded": (),
}
PAYMENT_QUERY = """
    SELECT p.payment_id, p.order_id, o.user_id, o.status AS order_status,
           p.amount, p.method, p.status, p.reference, p.created_at, p.updated_at
    FROM payment p
    JOIN customer_order o ON o.order_id = p.order_id
"""


def clean_amount(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ApiError("amount debe ser un numero mayor que 0.", 400) from None
    if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal("0.01")):
        raise ApiError("amount debe ser mayor que 0 y tener maximo 2 decimales.", 400)
    return amount


def clean_payment(body, required):
    fields = {}
    if "amount" in body:
        fields["amount"] = clean_amount(body["amount"])
    if "method" in body:
        if body["method"] not in PAYMENT_METHODS:
            raise ApiError(f"method invalido. Usa: {', '.join(PAYMENT_METHODS)}.", 400)
        fields["method"] = body["method"]
    if "reference" in body:
        reference = str(body["reference"] or "").strip()
        if len(reference) > 120:
            raise ApiError("reference admite maximo 120 caracteres.", 400)
        fields["reference"] = reference or None
    missing = [name for name in required if name not in body]
    if missing:
        raise ApiError(f"Campos requeridos: {', '.join(missing)}.", 400)
    return fields


def find_payment(conn, payment_id, lock=False):
    payment = conn.execute(
        PAYMENT_QUERY + " WHERE p.payment_id = %s" + (" FOR UPDATE OF p" if lock else ""),
        (payment_id,),
    ).fetchone()
    if payment is None:
        raise ApiError("Pago no encontrado.", 404)
    return payment


def check_amount(conn, order_id, amount, exclude_payment_id=None):
    """Evita registrar mas dinero del que falta por cubrir en el pedido."""
    pending_sum = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total FROM payment
        WHERE order_id = %s AND status IN ('pending', 'approved')
          AND (%s::bigint IS NULL OR payment_id <> %s::bigint)
        """,
        (order_id, exclude_payment_id, exclude_payment_id),
    ).fetchone()["total"]
    remaining = order_total(conn, order_id) - Decimal(pending_sum)
    if amount > remaining:
        raise ApiError(f"El monto excede lo pendiente del pedido ({max(remaining, 0)}).", 409)


def apply_payment_status(conn, payment, new_status):
    """Cambia el estado del pago y sincroniza el estado del pedido."""
    if new_status not in PAYMENT_STATUSES:
        raise ApiError(f"status invalido. Usa: {', '.join(PAYMENT_STATUSES)}.", 400)
    if new_status == payment["status"]:
        return []
    if new_status not in PAYMENT_TRANSITIONS[payment["status"]]:
        raise ApiError(f"No se puede pasar el pago de {payment['status']} a {new_status}.", 409)
    order = lock_order(conn, payment["order_id"])
    if new_status == "approved" and order["status"] != "pending":
        raise ApiError(f"El pedido esta {order['status']}; no admite pagos.", 409)
    conn.execute(
        "UPDATE payment SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE payment_id = %s",
        (new_status, payment["payment_id"]),
    )
    touched = []
    total = order_total(conn, order["order_id"])
    paid = approved_amount(conn, order["order_id"])
    if new_status == "approved" and paid >= total:
        touched = change_order_status(conn, order, "paid")
    elif new_status == "refunded" and order["status"] == "paid" and paid < total:
        # Reembolso de un pedido aun no enviado: se cancela y se devuelve el stock.
        touched = change_order_status(conn, order, "cancelled")
    return touched


@app.get("/pagos/estados")
def list_statuses():
    return jsonify({
        "methods": list(PAYMENT_METHODS),
        "statuses": [
            {"status": status, "next": list(PAYMENT_TRANSITIONS[status])}
            for status in PAYMENT_STATUSES
        ],
    })


@app.get("/pagos")
@require_bearer
def list_payments():
    clauses, params = [], []
    if not is_admin():
        clauses.append("o.user_id = %s")
        params.append(current_user_id())
    if request.args.get("order_id"):
        clauses.append("p.order_id = %s")
        params.append(positive_int(request.args["order_id"], "order_id"))
    status = request.args.get("status", "").strip()
    if status:
        clauses.append("p.status = %s")
        params.append(status)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with get_db_connection() as conn:
        payments = conn.execute(
            PAYMENT_QUERY + where + " ORDER BY p.payment_id DESC", params
        ).fetchall()
    return jsonify(payments)


@app.get("/pagos/<int:payment_id>")
@require_bearer
def get_payment(payment_id):
    with get_db_connection() as conn:
        payment = find_payment(conn, payment_id)
    if not is_admin() and payment["user_id"] != current_user_id():
        raise ApiError("No tienes permisos para este pago.", 403)
    return jsonify(payment)


@app.post("/pagos")
@require_bearer
def create_payment():
    """Registra un pago pending. Un administrador puede registrarlo ya approved."""
    body = read_json()
    order_id = positive_int(body.get("order_id"), "order_id")
    fields = clean_payment(body, required=("amount", "method"))
    status = body.get("status", "pending")
    if status != "pending" and not is_admin():
        raise ApiError("Solo un administrador puede registrar pagos con otro estado.", 403)
    with get_db_connection() as conn:
        order = lock_order(conn, order_id)
        if not is_admin() and order["user_id"] != current_user_id():
            raise ApiError("No tienes permisos para este pedido.", 403)
        if order["status"] != "pending":
            raise ApiError(f"El pedido esta {order['status']}; no admite pagos.", 409)
        check_amount(conn, order_id, fields["amount"])
        payment_id = conn.execute(
            """
            INSERT INTO payment (order_id, amount, method, reference)
            VALUES (%s, %s, %s, %s) RETURNING payment_id
            """,
            (order_id, fields["amount"], fields["method"], fields.get("reference")),
        ).fetchone()["payment_id"]
        touched = apply_payment_status(conn, find_payment(conn, payment_id, lock=True), status)
        payment = find_payment(conn, payment_id)
    if touched:
        invalidate_books_cache(touched)
    return jsonify(message="Pago registrado.", payment=payment), 201


def update_payment(payment_id, required):
    body = read_json()
    fields = clean_payment(body, required)
    new_status = body.get("status")
    if not fields and new_status is None:
        raise ApiError("No hay campos para actualizar.", 400)
    with get_db_connection() as conn:
        payment = find_payment(conn, payment_id, lock=True)
        if fields:
            if payment["status"] != "pending":
                raise ApiError("Solo se editan monto, metodo o referencia de pagos pending.", 409)
            if "amount" in fields:
                check_amount(conn, payment["order_id"], fields["amount"], payment_id)
            assignments = ", ".join(f"{name} = %s" for name in fields)
            conn.execute(
                f"UPDATE payment SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE payment_id = %s",
                [*fields.values(), payment_id],
            )
        touched = apply_payment_status(conn, payment, new_status) if new_status else []
        payment = find_payment(conn, payment_id)
    if touched:
        invalidate_books_cache(touched)
    return jsonify(message="Pago actualizado.", payment=payment)


@app.put("/pagos/<int:payment_id>")
@require_role(ADMIN_ROLE)
def replace_payment(payment_id):
    return update_payment(payment_id, required=("amount", "method"))


@app.patch("/pagos/<int:payment_id>")
@require_role(ADMIN_ROLE)
def patch_payment(payment_id):
    return update_payment(payment_id, required=())


@app.delete("/pagos/<int:payment_id>")
@require_role(ADMIN_ROLE)
def delete_payment(payment_id):
    with get_db_connection() as conn:
        payment = find_payment(conn, payment_id, lock=True)
        if payment["status"] not in ("pending", "rejected"):
            raise ApiError("Solo se eliminan pagos pending o rejected.", 409)
        conn.execute("DELETE FROM payment WHERE payment_id = %s", (payment_id,))
    return jsonify(message="Pago eliminado.")


if __name__ == "__main__":
    run_service(app, 5005)
