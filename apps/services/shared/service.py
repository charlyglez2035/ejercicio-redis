"""Piezas comunes de los microservicios Flask (users, authors, pedidos, pagos).

Sigue el patron de login/book: .env propio del servicio, PostgreSQL con psycopg,
respuestas XML por defecto o JSON con ?format=json, logging sanitizado y JWT
compartido mediante shared.jwt_security.
"""
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from psycopg.rows import dict_row
from werkzeug.exceptions import HTTPException

from shared.jwt_security import install_request_logging
from shared.redis_store import cache_invalidate, metrics as redis_metrics, ping as redis_ping

LIBRARY_ROOT = Path(__file__).resolve().parents[3]


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def load_service_env(service_file):
    # Primero el .env del servicio; el .env raiz aporta las variables PostgreSQL compartidas.
    load_dotenv(Path(service_file).with_name(".env"))
    load_dotenv(LIBRARY_ROOT / ".env")


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


def read_json():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError("Envia un objeto JSON valido.", 400)
    return body


def current_user_id():
    return g.jwt_claims["user_id"]


def positive_int(value, field):
    if isinstance(value, bool):
        raise ApiError(f"{field} debe ser un entero positivo.", 400)
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{field} debe ser un entero positivo.", 400) from None
    if number < 1 or str(number) != str(value).strip():
        raise ApiError(f"{field} debe ser un entero positivo.", 400)
    return number


def invalidate_books_cache(isbns=()):
    """Mantiene coherente el cache Redis del catalogo tras cambios en stock o autores."""
    cache_invalidate([f"books:{isbn}" for isbn in isbns], pattern="books:list:*")


def _cors_origins(env_name):
    return [
        origin.strip()
        for origin in os.getenv(env_name, "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    ]


def create_service(name, title, cors_env):
    app = Flask(name)
    app.json.ensure_ascii = False
    app.logger.setLevel(os.getenv("SERVICE_LOG_LEVEL", "INFO").upper())
    CORS(
        app,
        resources={r"/*": {"origins": _cors_origins(cors_env)}},
        allow_headers=["Content-Type", "Accept", "Authorization", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    install_request_logging(app)
    Swagger(app, template={
        "swagger": "2.0",
        "info": {"title": title, "version": "1.0.0",
                 "description": "XML por defecto. Usa format=json para obtener JSON."},
    })
    _install_formats(app)
    _install_error_handlers(app)

    @app.get("/health")
    def health():
        try:
            with get_db_connection() as conn:
                conn.execute("SELECT 1")
            database = "ok"
        except psycopg.Error:
            database = "unavailable"
        redis_status = "ok" if redis_ping() else "unavailable"
        healthy = database == "ok" and redis_status == "ok"
        return jsonify(
            status="ok" if healthy else "degraded",
            database=database,
            redis=redis_status,
            redis_metrics=redis_metrics(),
        ), 200 if healthy else 503

    return app


def run_service(app, default_port):
    app.run(
        host=os.getenv("SERVICE_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVICE_PORT", str(default_port))),
        debug=False,
    )


def _install_formats(app):
    @app.before_request
    def validate_format():
        output_format = request.args.get("format", "xml").lower()
        if output_format not in ("json", "xml"):
            return jsonify(error="Formato invalido. Usa format=json o format=xml."), 400

    @app.after_request
    def format_response(response):
        if not response.is_json or request.args.get("format", "xml").lower() == "json":
            return response
        if request.path.startswith(("/apispec", "/apidocs", "/flasgger")):
            return response
        data = response.get_json(silent=True)
        if response.status_code >= 400:
            root_name = "error"
        elif isinstance(data, list):
            root_name = "items"
        else:
            root_name = "response"
        root = ET.Element(root_name)

        def append_xml(parent, value):
            if isinstance(value, dict):
                for key, item in value.items():
                    append_xml(ET.SubElement(parent, str(key)), item)
            elif isinstance(value, list):
                for item in value:
                    append_xml(ET.SubElement(parent, "item"), item)
            elif value is None:
                parent.set("null", "true")
            elif isinstance(value, bool):
                parent.text = "true" if value else "false"
            else:
                parent.text = str(value)

        append_xml(root, data)
        response.set_data(ET.tostring(root, encoding="utf-8", xml_declaration=True))
        response.content_type = "application/xml; charset=utf-8"
        return response


def _install_error_handlers(app):
    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify(error=error.message), error.status

    @app.errorhandler(psycopg.errors.UniqueViolation)
    def unique_violation(_error):
        return jsonify(error="El registro ya existe o viola una restriccion unica."), 409

    @app.errorhandler(psycopg.errors.ForeignKeyViolation)
    def foreign_key_violation(_error):
        return jsonify(error="El registro esta relacionado con otros datos o la referencia no existe."), 409

    @app.errorhandler(psycopg.IntegrityError)
    def integrity_error(_error):
        return jsonify(error="Datos invalidos o campos requeridos ausentes."), 400

    @app.errorhandler(psycopg.DataError)
    def data_error(_error):
        return jsonify(error="Algun dato tiene un tipo o valor invalido."), 400

    @app.errorhandler(psycopg.OperationalError)
    def database_unavailable(_error):
        app.logger.exception("PostgreSQL no disponible")
        return jsonify(error="La base de datos no esta disponible."), 503

    @app.errorhandler(psycopg.Error)
    def database_error(_error):
        app.logger.exception("Error de PostgreSQL")
        return jsonify(error="No se pudo completar la operacion en la base de datos."), 500

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.name, message=error.description), error.code

    @app.errorhandler(Exception)
    def unexpected_error(_error):
        app.logger.exception("Error inesperado")
        return jsonify(error="Error interno del servidor."), 500
