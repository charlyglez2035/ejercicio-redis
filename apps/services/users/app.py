import sys
from pathlib import Path

import bcrypt
from email_validator import EmailNotValidError, validate_email
from flask import jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.jwt_security import (
    ADMIN_ROLE,
    SessionStoreUnavailable,
    forbidden_response,
    is_admin,
    require_bearer,
    require_role,
    revoke_user_sessions,
)
from shared.service import (
    ApiError,
    create_service,
    current_user_id,
    get_db_connection,
    load_service_env,
    read_json,
    run_service,
)

load_service_env(__file__)
app = create_service(__name__, "Library Users Service", "USERS_CORS_ORIGINS")

# Mismos valores que la restriccion app_user_role_ck de db/scheme.sql.
ROLES = {
    "customer": "Cliente: consulta catalogo y gestiona sus pedidos y pagos.",
    "admin": "Administrador: gestiona usuarios, catalogo, autores, pedidos y pagos.",
}
USER_COLUMNS = "user_id, username, email, full_name, role, email_verified, created_at"


def public_user(user):
    return {
        "id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role_id": user["role"],
        "email_verified": user["email_verified"],
        "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
    }


def clean_fields(body, required):
    """Valida y normaliza los campos editables; nunca devuelve la contraseña en claro."""
    fields = {}
    for name in ("username", "full_name"):
        if name in body:
            value = str(body[name] or "").strip()
            if not value:
                raise ApiError(f"{name} no puede estar vacio.", 400)
            fields[name] = value
    if "email" in body:
        try:
            fields["email"] = validate_email(
                str(body["email"] or "").strip(), check_deliverability=False
            ).normalized.lower()
        except EmailNotValidError:
            raise ApiError("El correo no es valido.", 400) from None
    if "password" in body:
        password = body["password"]
        if not isinstance(password, str) or len(password) < 8:
            raise ApiError("password debe tener al menos 8 caracteres.", 400)
        fields["password_hash"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    if "role_id" in body:
        if body["role_id"] not in ROLES:
            raise ApiError(f"role_id invalido. Usa: {', '.join(ROLES)}.", 400)
        fields["role"] = body["role_id"]
    if "email_verified" in body:
        if not isinstance(body["email_verified"], bool):
            raise ApiError("email_verified debe ser booleano.", 400)
        fields["email_verified"] = body["email_verified"]
    missing = [name for name in required if name not in body]
    if missing:
        raise ApiError(f"Campos requeridos: {', '.join(missing)}.", 400)
    return fields


def can_access(user_id):
    return is_admin() or current_user_id() == user_id


@app.get("/roles")
def list_roles():
    """Catalogo publico de roles existentes."""
    return jsonify([{"role_id": role, "description": text} for role, text in ROLES.items()])


@app.get("/users")
@require_role(ADMIN_ROLE)
def list_users():
    clauses, params = [], []
    role = request.args.get("role_id", "").strip()
    if role:
        clauses.append("role = %s")
        params.append(role)
    query_text = request.args.get("q", "").strip()
    if query_text:
        clauses.append("(username ILIKE %s OR email ILIKE %s OR full_name ILIKE %s)")
        params.extend([f"%{query_text}%"] * 3)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with get_db_connection() as conn:
        users = conn.execute(
            f"SELECT {USER_COLUMNS} FROM app_user{where} ORDER BY user_id", params
        ).fetchall()
    return jsonify([public_user(user) for user in users])


@app.get("/users/<int:user_id>")
@require_bearer
def get_user(user_id):
    if not can_access(user_id):
        return forbidden_response()
    with get_db_connection() as conn:
        user = conn.execute(
            f"SELECT {USER_COLUMNS} FROM app_user WHERE user_id = %s", (user_id,)
        ).fetchone()
    if user is None:
        raise ApiError("Usuario no encontrado.", 404)
    return jsonify(public_user(user))


@app.post("/users")
@require_role(ADMIN_ROLE)
def create_user():
    body = read_json()
    fields = clean_fields(body, required=("username", "email", "full_name", "password"))
    fields.setdefault("role", "customer")
    # Un administrador crea cuentas ya verificadas salvo que indique lo contrario.
    fields.setdefault("email_verified", True)
    columns = ", ".join(fields)
    placeholders = ", ".join(["%s"] * len(fields))
    with get_db_connection() as conn:
        user = conn.execute(
            f"INSERT INTO app_user ({columns}) VALUES ({placeholders}) RETURNING {USER_COLUMNS}",
            list(fields.values()),
        ).fetchone()
    return jsonify(message="Usuario creado.", user=public_user(user)), 201


def update_user(user_id, required):
    if not can_access(user_id):
        return forbidden_response()
    body = read_json()
    fields = clean_fields(body, required)
    if not fields:
        raise ApiError("No hay campos para actualizar.", 400)
    assignments = ", ".join(f"{name} = %s" for name in fields)
    with get_db_connection() as conn:
        current = conn.execute(
            "SELECT role, email, email_verified FROM app_user WHERE user_id = %s FOR UPDATE",
            (user_id,),
        ).fetchone()
        if current is None:
            raise ApiError("Usuario no encontrado.", 404)
        changed = {name for name in ("role", "email", "email_verified")
                   if name in fields and fields[name] != current[name]}
        if not is_admin() and changed & {"role", "email_verified"}:
            raise ApiError("Solo un administrador puede cambiar rol o verificacion.", 403)
        if user_id == current_user_id() and "role" in changed:
            raise ApiError("No puedes cambiar tu propio rol.", 409)
        user = conn.execute(
            f"UPDATE app_user SET {assignments} WHERE user_id = %s RETURNING {USER_COLUMNS}",
            [*fields.values(), user_id],
        ).fetchone()
        # Cambios de credenciales o permisos invalidan los JWT vigentes antes del commit;
        # si Redis falla, la transaccion se revierte.
        if "password_hash" in fields or changed & {"role", "email"}:
            revoke_user_sessions(user_id)
    return jsonify(message="Usuario actualizado.", user=public_user(user))


@app.put("/users/<int:user_id>")
@require_bearer
def replace_user(user_id):
    return update_user(user_id, required=("username", "email", "full_name"))


@app.patch("/users/<int:user_id>")
@require_bearer
def patch_user(user_id):
    return update_user(user_id, required=())


@app.delete("/users/<int:user_id>")
@require_role(ADMIN_ROLE)
def delete_user(user_id):
    if user_id == current_user_id():
        raise ApiError("No puedes eliminar tu propia cuenta de administrador.", 409)
    with get_db_connection() as conn:
        deleted = conn.execute(
            "DELETE FROM app_user WHERE user_id = %s RETURNING user_id", (user_id,)
        ).fetchone()
        if deleted is None:
            raise ApiError("Usuario no encontrado.", 404)
        revoke_user_sessions(user_id)
    return jsonify(message="Usuario eliminado.")


@app.errorhandler(SessionStoreUnavailable)
def session_store_unavailable(_error):
    app.logger.error("No se pudieron revocar las sesiones en Redis")
    return jsonify(error="No se pudo completar la operacion: Redis no disponible."), 503


if __name__ == "__main__":
    run_service(app, 5002)
