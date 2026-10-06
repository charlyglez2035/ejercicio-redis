import os
import hashlib
import secrets
import smtplib
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

import bcrypt
from email_validator import EmailNotValidError, validate_email
import psycopg
from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.jwt_security import (
    InvalidToken,
    JWTConfigurationError,
    RevocationStoreUnavailable,
    SessionStoreUnavailable,
    create_session,
    end_session,
    install_request_logging,
    require_bearer,
    revoke_token,
    rotate_refresh_token,
    session_exists,
    token_error_response,
)
from shared.redis_store import metrics as redis_metrics, ping as redis_ping

load_dotenv(Path(__file__).with_name(".env"))
load_dotenv()

app = Flask(__name__)
app.json.ensure_ascii = False

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "LOGIN_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]
CORS(
    app,
    resources={r"/*": {"origins": allowed_origins}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Accept", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    methods=["GET", "POST", "OPTIONS"],
)
install_request_logging(app)

Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "Library Login Service",
        "version": "1.0.0",
        "description": "Autenticacion de usuarios con respuestas JSON o XML.",
    },
    "basePath": "/",
})

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


def request_format():
    requested = request.args.get("format", "xml").lower()
    if "format" not in request.args and request.accept_mimetypes.best_match(
        ["application/json", "application/xml"]
    ) == "application/json":
        requested = "json"
    return requested


@app.before_request
def validate_format():
    requested = request.args.get("format")
    if requested and requested.lower() not in ("xml", "json"):
        return error("Formato invalido. Usa format=xml o format=json.", 400)


@app.after_request
def preserve_json_xml_format(response):
    if not response.is_json or request_format() == "json":
        return response
    payload = response.get_json(silent=True)
    if not isinstance(payload, dict):
        return response
    return xml_response(add_links(payload), response.status_code)


def add_links(payload):
    links = {
        "self": {"href": request.base_url, "method": request.method},
        "health": {"href": request.url_root.rstrip("/") + "/health", "method": "GET"},
    }
    if request.path == "/register":
        links["login"] = {"href": request.url_root.rstrip("/") + "/login", "method": "POST"}
    elif request.path == "/login":
        links["session"] = {"href": request.url_root.rstrip("/") + "/session", "method": "GET"}
        links["refresh"] = {"href": request.url_root.rstrip("/") + "/refresh", "method": "POST"}
        links["logout"] = {"href": request.url_root.rstrip("/") + "/logout", "method": "POST"}
    elif request.path in ("/session", "/refresh"):
        links["logout"] = {"href": request.url_root.rstrip("/") + "/logout", "method": "POST"}
    payload["_links"] = links
    return payload


def xml_response(payload, status):
    root = ET.Element("response")

    def append(parent, key, value):
        if isinstance(value, dict):
            child = ET.SubElement(parent, key)
            for nested_key, nested_value in value.items():
                append(child, nested_key, nested_value)
        elif isinstance(value, list):
            child = ET.SubElement(parent, key)
            for item in value:
                append(child, "item", item)
        elif value is None:
            child = ET.SubElement(parent, key)
            child.set("null", "true")
        else:
            child = ET.SubElement(parent, key)
            child.text = str(value).lower() if isinstance(value, bool) else str(value)

    for key, value in payload.items():
        append(root, key, value)

    response = app.response_class(
        ET.tostring(root, encoding="utf-8", xml_declaration=True),
        status=status,
        content_type="application/xml; charset=utf-8",
    )
    return response


def respond(payload, status=200):
    payload = add_links(payload)
    if request_format() == "xml":
        return xml_response(payload, status)
    return jsonify(payload), status


def error(message, status):
    return respond({"error": message, "status": status}, status)


def read_json():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return None
    return body


def public_user(user):
    return {
        "id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
    }


def send_verification_email(email, full_name, token):
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        raise RuntimeError("SMTP_HOST no esta configurado.")

    verification_url = (
        os.getenv("LOGIN_PUBLIC_URL", "http://localhost:5000").rstrip("/")
        + "/verify-email?token="
        + token
    )
    message = EmailMessage()
    message["Subject"] = "Verifica tu correo de Library"
    message["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", ""))
    message["To"] = email
    message.set_content(
        f"Hola {full_name},\n\n"
        "Confirma tu correo abriendo este enlace:\n\n"
        f"{verification_url}\n\n"
        "El enlace caduca en 24 horas.\n"
    )

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        smtp.ehlo()
        if use_tls:
            smtp.starttls()
            smtp.ehlo()
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        if smtp_user and smtp_password:
            smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)


@app.post("/register")
def register():
    """Registra un usuario.
    ---
    tags:
      - Authentication
    consumes:
      - application/json
    produces:
      - application/json
      - application/xml
    responses:
      201:
        description: Usuario creado
      400:
        description: Datos invalidos
      409:
        description: Usuario o correo duplicado
      503:
        description: No se pudo enviar el correo de verificacion
    """
    body = read_json()
    if not body:
        return error("El cuerpo debe ser JSON.", 400)

    email = str(body.get("email", "")).strip()
    first_name = str(body.get("nombre", "")).strip()
    paternal_surname = str(body.get("apellido_paterno", "")).strip()
    maternal_surname = str(body.get("apellido_materno", "")).strip()
    full_name = " ".join(
        part for part in (first_name, paternal_surname, maternal_surname) if part
    )
    password = body.get("password")
    if (
        not first_name
        or not paternal_surname
        or not maternal_surname
        or not isinstance(password, str)
        or len(password) < 8
    ):
        return error(
            "username, nombre, apellido_paterno, apellido_materno y una "
            "contraseña de 8 caracteres son obligatorios.",
            400,
        )
    try:
        email = validate_email(email, check_deliverability=True).normalized
    except EmailNotValidError:
        return error("El correo no es valido o su dominio no recibe correo.", 400)

    username = str(body.get("username", "")).strip() or f"user_{secrets.token_hex(8)}"

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    verification_token = secrets.token_urlsafe(32)
    verification_token_hash = hashlib.sha256(verification_token.encode()).hexdigest()
    verification_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    try:
        with get_db_connection() as connection:
            user = connection.execute(
                """
                INSERT INTO app_user (
                    username, email, password_hash, full_name,
                    email_verified, verification_token_hash, verification_expires_at
                )
                VALUES (%s, %s, %s, %s, FALSE, %s, %s)
                RETURNING user_id, username, email, full_name, role
                """,
                (username, email, password_hash, full_name,
                 verification_token_hash, verification_expires_at),
            ).fetchone()
            send_verification_email(email, full_name, verification_token)
        return respond({"message": "Usuario registrado.", "user": public_user(user)}, 201)
    except (RuntimeError, OSError, smtplib.SMTPException):
        app.logger.exception("No se pudo enviar el correo de verificacion")
        return error("No se pudo enviar el correo de verificacion.", 503)
    except psycopg.errors.UniqueViolation:
        return error("El usuario o correo ya existe.", 409)
    except psycopg.Error:
        app.logger.exception("No se pudo registrar el usuario")
        return error("No se pudo completar el registro.", 503)


@app.post("/login")
def login():
    """Autentica un usuario y crea una sesion.
    ---
    tags:
      - Authentication
    consumes:
      - application/json
    produces:
      - application/json
      - application/xml
    responses:
      200:
        description: Sesion iniciada
      400:
        description: Datos invalidos
      401:
        description: Credenciales invalidas
      403:
        description: Debes verificar tu correo antes de iniciar sesion
      503:
        description: Error al consultar la base de datos
    """
    body = read_json()
    identity = str(body.get("identity", "")).strip() if body else ""
    password = body.get("password") if body else None
    if not identity or not isinstance(password, str):
        return error("identity y password son obligatorios.", 400)

    try:
        with get_db_connection() as connection:
            user = connection.execute(
                """
                  SELECT user_id, username, email, password_hash, full_name, role,
                      email_verified
                FROM app_user WHERE username = %s OR email = %s
                """,
                (identity, identity.lower()),
            ).fetchone()
    except psycopg.Error:
        app.logger.exception("No se pudo consultar el usuario")
        return error("No se pudo consultar la base de datos.", 503)

    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return error("Credenciales invalidas.", 401)
    if not user["email_verified"]:
        return error("Debes verificar tu correo antes de iniciar sesion.", 403)

    try:
        access_token, claims, refresh_token, refresh_ttl = create_session(
            user["user_id"], user["role"]
        )
    except JWTConfigurationError:
        app.logger.exception("JWT_SECRET no esta configurado correctamente")
        return error("El servicio de autenticacion no esta configurado.", 503)
    except SessionStoreUnavailable:
        app.logger.error("No se pudo guardar la sesion en Redis")
        return error("No se pudo iniciar la sesion.", 503)
    return respond(token_payload(
        "Sesion iniciada.", access_token, claims, refresh_token, refresh_ttl, public_user(user)
    ), 200)


def token_payload(message, access_token, claims, refresh_token, refresh_ttl, user=None):
    payload = {"message": message}
    if user is not None:
        payload["user"] = user
    payload.update({
        "access_token": access_token,
        "token_type": "Bearer",
        "user_id": claims["user_id"],
        "role_id": claims["role_id"],
        "expires_in": claims["exp"] - claims["iat"],
        "refresh_token": refresh_token,
        "refresh_expires_in": refresh_ttl,
    })
    return payload


def current_role(user_id):
    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT role FROM app_user WHERE user_id = %s AND email_verified",
            (user_id,),
        ).fetchone()
    return user["role"] if user else None


@app.post("/refresh")
def refresh():
    """Renueva el access token con un refresh token de un solo uso.
    ---
    tags:
      - Authentication
    consumes:
      - application/json
    produces:
      - application/json
      - application/xml
    responses:
      200:
        description: Nuevo par de tokens
      400:
        description: Falta refresh_token
      401:
        description: Refresh token invalido, usado o expirado
      503:
        description: Redis no disponible
    """
    body = read_json()
    refresh_token = body.get("refresh_token") if body else None
    if not isinstance(refresh_token, str) or not refresh_token.strip():
        return error("refresh_token es obligatorio.", 400)
    try:
        access_token, claims, new_refresh, refresh_ttl = rotate_refresh_token(
            refresh_token.strip(), current_role
        )
    except psycopg.Error:
        app.logger.exception("No se pudo consultar el rol del usuario")
        return error("No se pudo renovar la sesion.", 503)
    except InvalidToken:
        return error("Refresh token invalido, usado o expirado.", 401)
    except JWTConfigurationError:
        app.logger.exception("La configuracion JWT no es valida")
        return error("El servicio de autenticacion no esta configurado.", 503)
    except SessionStoreUnavailable:
        app.logger.error("No se pudo renovar la sesion en Redis")
        return error("No se pudo renovar la sesion.", 503)
    return respond(token_payload(
        "Sesion renovada.", access_token, claims, new_refresh, refresh_ttl
    ), 200)


@app.get("/verify-email")
def verify_email():
    """Confirma el correo usando el enlace recibido por email."""
    token = request.args.get("token", "")
    token_hash = hashlib.sha256(token.encode()).hexdigest() if token else ""
    try:
        with get_db_connection() as connection:
            user = connection.execute(
                """
                UPDATE app_user
                SET email_verified = TRUE,
                    verification_token_hash = NULL,
                    verification_expires_at = NULL
                WHERE verification_token_hash = %s
                  AND verification_expires_at > CURRENT_TIMESTAMP
                RETURNING email
                """,
                (token_hash,),
            ).fetchone()
        if not user:
            return "Enlace invalido o caducado.", 400
        return "Correo verificado correctamente. Ya puedes iniciar sesion.", 200
    except psycopg.Error:
        app.logger.exception("No se pudo verificar el correo")
        return "No se pudo verificar el correo.", 503


@app.post("/logout")
@require_bearer
def logout():
    """Cierra la sesion actual.
    ---
    tags:
      - Authentication
    produces:
      - application/json
      - application/xml
    responses:
      200:
        description: Sesion cerrada
    """
    try:
        revoke_token(g.jwt_claims)
        end_session(g.jwt_claims)
    except InvalidToken:
        return token_error_response()
    except (RevocationStoreUnavailable, SessionStoreUnavailable):
        app.logger.error("No se pudo revocar el token o eliminar la sesion en Redis")
        return error("No se pudo cerrar la sesion.", 503)
    return respond({"message": "Sesion cerrada."}, 200)


@app.get("/session")
@require_bearer
def current_session():
    """Consulta la sesion autenticada actual.
    ---
    tags:
      - Authentication
    produces:
      - application/json
      - application/xml
    responses:
      200:
        description: Estado de la sesion actual
    """
    claims = g.jwt_claims
    if not claims["sub"].isdigit():
        return token_error_response()
    try:
        if not session_exists(claims):
            return token_error_response()
    except SessionStoreUnavailable:
        app.logger.error("No se pudo consultar la sesion en Redis")
        return error("No se pudo consultar la sesion.", 503)
    try:
        with get_db_connection() as connection:
            user = connection.execute(
                """SELECT user_id, username, email, full_name, role
                   FROM app_user WHERE user_id = %s""",
                (int(claims["sub"]),),
            ).fetchone()
    except psycopg.Error:
        app.logger.exception("No se pudo consultar la sesion")
        return error("No se pudo consultar la sesion.", 503)
    if not user:
        return token_error_response()
    return respond({"authenticated": True, "user": public_user(user)}, 200)


@app.get("/health")
def health():
    """Comprueba el servicio y PostgreSQL.
    ---
    tags:
      - Health
    produces:
      - application/json
      - application/xml
    responses:
      200:
        description: Servicio funcionando correctamente
      503:
        description: Base de datos o Redis no disponible
    """
    try:
        with get_db_connection() as connection:
            connection.execute("SELECT 1")
        database = "ok"
    except psycopg.Error:
        database = "unavailable"
    redis_status = "ok" if redis_ping() else "unavailable"
    healthy = database == "ok" and redis_status == "ok"
    return respond({
        "status": "ok" if healthy else "degraded",
        "database": database,
        "redis": redis_status,
        "redis_metrics": redis_metrics(),
    }, 200 if healthy else 503)


@app.errorhandler(404)
def not_found(_exception):
    return error("Recurso no encontrado.", 404)


@app.errorhandler(405)
def method_not_allowed(_exception):
    return error("Metodo no permitido.", 405)


if __name__ == "__main__":
    app.run(
        host=os.getenv("LOGIN_HOST", "0.0.0.0"),
        port=int(os.getenv("LOGIN_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
