import hashlib
import json
import logging
import os
import re
import secrets
import time
import uuid
from functools import wraps

import jwt
from flask import g, jsonify, request

from shared.redis_store import RedisUnavailable, execute, increment, logger as redis_logger


class InvalidToken(Exception):
    pass


class RevocationStoreUnavailable(Exception):
    pass


class SessionStoreUnavailable(Exception):
    pass


class JWTConfigurationError(Exception):
    pass


REVOKED_KEY = "jwt:revoked:{}"
SESSION_KEY = "session:{}"
REFRESH_KEY = "refresh:{}"
USER_SESSIONS_KEY = "user_sessions:{}"


def jwt_settings():
    secret = os.getenv("JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise JWTConfigurationError(
            "JWT_SECRET debe tener al menos 32 bytes y configurarse por entorno."
        )
    issuer = os.getenv("JWT_ISSUER", "library-login")
    audience = os.getenv("JWT_AUDIENCE", "library-book")
    try:
        expires_in = int(os.getenv("JWT_EXPIRES_IN_SECONDS", "1200"))
        refresh_expires_in = int(os.getenv("REFRESH_TOKEN_TTL_SECONDS", "1800"))
    except ValueError as error:
        raise JWTConfigurationError(
            "JWT_EXPIRES_IN_SECONDS y REFRESH_TOKEN_TTL_SECONDS deben ser enteros positivos."
        ) from error
    if not issuer or not audience or expires_in < 1:
        raise JWTConfigurationError("JWT issuer, audience y duracion deben configurarse.")
    if refresh_expires_in < expires_in:
        raise JWTConfigurationError(
            "REFRESH_TOKEN_TTL_SECONDS no puede ser menor que JWT_EXPIRES_IN_SECONDS."
        )
    return {
        "secret": secret,
        "issuer": issuer,
        "audience": audience,
        "expires_in": expires_in,
        "refresh_expires_in": refresh_expires_in,
    }


def issue_token(user_id, role_id, session_id=None):
    settings = jwt_settings()
    issued_at = int(time.time())
    claims = {
        "sub": str(user_id),
        "user_id": int(user_id),
        "role_id": str(role_id),
        "iat": issued_at,
        "exp": issued_at + settings["expires_in"],
        "iss": settings["issuer"],
        "aud": settings["audience"],
        "jti": str(uuid.uuid4()),
    }
    if session_id:
        claims["sid"] = session_id
    return jwt.encode(claims, settings["secret"], algorithm="HS256"), claims


def _is_revoked(jti):
    try:
        revoked = execute("revocation_read", lambda client: client.exists(REVOKED_KEY.format(jti)))
    except RedisUnavailable as error:
        raise RevocationStoreUnavailable() from error
    increment("revocation_checks")
    return bool(revoked)


def decode_token(token):
    settings = jwt_settings()
    try:
        claims = jwt.decode(
            token,
            settings["secret"],
            algorithms=["HS256"],
            issuer=settings["issuer"],
            audience=settings["audience"],
            options={"require": ["sub", "user_id", "role_id", "iat", "exp", "iss", "aud", "jti"]},
        )
    except (jwt.PyJWTError, TypeError, ValueError) as error:
        raise InvalidToken() from error
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise InvalidToken()
    user_id = claims.get("user_id")
    if isinstance(user_id, bool) or not isinstance(user_id, int) or str(user_id) != claims["sub"]:
        raise InvalidToken()
    if not isinstance(claims.get("role_id"), str) or not claims["role_id"]:
        raise InvalidToken()
    if not isinstance(claims.get("jti"), str) or not claims["jti"]:
        raise InvalidToken()
    if _is_revoked(claims["jti"]):
        increment("jwt_revoked_rejected")
        redis_logger.warning("JWT revocado rechazado jti=%s", claims["jti"])
        raise InvalidToken()
    return claims


def bearer_claims():
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise InvalidToken()
    return decode_token(token.strip())


def revoke_token(claims):
    # La clave solo vive el tiempo restante del JWT; uno ya expirado no necesita revocarse.
    ttl = int(claims["exp"]) - int(time.time())
    if ttl <= 0:
        return
    try:
        execute(
            "revocation_write",
            lambda client: client.set(REVOKED_KEY.format(claims["jti"]), "1", ex=ttl),
        )
    except RedisUnavailable as error:
        raise RevocationStoreUnavailable() from error
    increment("jwt_revoked")
    redis_logger.info("JWT revocado jti=%s ttl=%s", claims["jti"], ttl)


def _refresh_hash(refresh_token):
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def _store_session(client, session_id, user_id, claims, refresh_hash, ttl):
    session_key = SESSION_KEY.format(session_id)
    user_sessions_key = USER_SESSIONS_KEY.format(user_id)
    pipe = client.pipeline(transaction=True)
    pipe.hset(session_key, mapping={
        "user_id": str(user_id),
        "access_jti": claims["jti"],
        "access_exp": str(claims["exp"]),
        "refresh_hash": refresh_hash,
    })
    pipe.expire(session_key, ttl)
    pipe.set(
        REFRESH_KEY.format(refresh_hash),
        json.dumps({"user_id": str(user_id), "sid": session_id}),
        ex=ttl,
    )
    # Indice usuario -> sesiones para cerrar todas al cambiar rol, contraseña o eliminarlo.
    pipe.sadd(user_sessions_key, session_id)
    pipe.expire(user_sessions_key, ttl)
    return pipe.execute()


def create_session(user_id, role_id):
    """Emite access JWT + refresh token y guarda ambos en Redis con TTL."""
    settings = jwt_settings()
    session_id = str(uuid.uuid4())
    refresh_token = secrets.token_urlsafe(48)
    access_token, claims = issue_token(user_id, role_id, session_id)
    ttl = settings["refresh_expires_in"]
    try:
        execute(
            "session_write",
            lambda client: _store_session(
                client, session_id, user_id, claims, _refresh_hash(refresh_token), ttl
            ),
        )
    except RedisUnavailable as error:
        raise SessionStoreUnavailable() from error
    increment("sessions_created")
    redis_logger.info("Sesion creada sid=%s user_id=%s ttl=%s", session_id, user_id, ttl)
    return access_token, claims, refresh_token, ttl


def rotate_refresh_token(refresh_token, resolve_role):
    """Consume el refresh token (uso unico) y emite un nuevo par de tokens.

    resolve_role(user_id) devuelve el rol vigente en PostgreSQL o None si el
    usuario ya no puede iniciar sesion.
    """
    settings = jwt_settings()
    old_hash = _refresh_hash(refresh_token)
    refresh_key = REFRESH_KEY.format(old_hash)

    def take(client):
        pipe = client.pipeline(transaction=True)
        pipe.get(refresh_key)
        pipe.delete(refresh_key)
        return pipe.execute()[0]

    try:
        stored = execute("refresh_read", take)
        if not stored:
            raise InvalidToken()
        data = json.loads(stored)
        session_id, user_id = data["sid"], data["user_id"]
        session = execute(
            "session_read", lambda client: client.hgetall(SESSION_KEY.format(session_id))
        )
        if not session or session.get("refresh_hash") != old_hash:
            raise InvalidToken()
        revoke_token({"jti": session["access_jti"], "exp": session["access_exp"]})
        role_id = resolve_role(int(user_id))
        if not role_id:
            end_session({"sid": session_id, "user_id": user_id})
            raise InvalidToken()
        new_refresh = secrets.token_urlsafe(48)
        access_token, claims = issue_token(user_id, role_id, session_id)
        ttl = settings["refresh_expires_in"]
        execute(
            "session_write",
            lambda client: _store_session(
                client, session_id, user_id, claims, _refresh_hash(new_refresh), ttl
            ),
        )
    except (RedisUnavailable, RevocationStoreUnavailable) as error:
        raise SessionStoreUnavailable() from error
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise InvalidToken() from error
    increment("refresh_rotated")
    redis_logger.info("Refresh token rotado sid=%s user_id=%s", session_id, user_id)
    return access_token, claims, new_refresh, ttl


def session_exists(claims):
    session_id = claims.get("sid")
    if not session_id:
        return True
    try:
        return bool(execute(
            "session_read", lambda client: client.exists(SESSION_KEY.format(session_id))
        ))
    except RedisUnavailable as error:
        raise SessionStoreUnavailable() from error


def end_session(claims):
    """Elimina de Redis la sesion del JWT y su refresh token."""
    session_id = claims.get("sid")
    if not session_id:
        return

    def remove(client):
        session_key = SESSION_KEY.format(session_id)
        refresh_hash = client.hget(session_key, "refresh_hash")
        keys = [session_key]
        if refresh_hash:
            keys.append(REFRESH_KEY.format(refresh_hash))
        if claims.get("user_id") is not None:
            client.srem(USER_SESSIONS_KEY.format(claims["user_id"]), session_id)
        return client.delete(*keys)

    try:
        removed = execute("session_delete", remove)
    except RedisUnavailable as error:
        raise SessionStoreUnavailable() from error
    increment("sessions_deleted")
    redis_logger.info("Sesion eliminada sid=%s claves=%s", session_id, removed)


def revoke_user_sessions(user_id):
    """Revoca los access JWT vigentes del usuario y elimina sus sesiones y refresh tokens."""
    user_sessions_key = USER_SESSIONS_KEY.format(user_id)
    now = int(time.time())

    def remove_all(client):
        removed = 0
        for session_id in client.smembers(user_sessions_key):
            session_key = SESSION_KEY.format(session_id)
            session = client.hgetall(session_key)
            pipe = client.pipeline(transaction=True)
            if session.get("access_jti") and session.get("access_exp", "").isdigit():
                ttl = int(session["access_exp"]) - now
                if ttl > 0:
                    pipe.set(REVOKED_KEY.format(session["access_jti"]), "1", ex=ttl)
            if session.get("refresh_hash"):
                pipe.delete(REFRESH_KEY.format(session["refresh_hash"]))
            pipe.delete(session_key)
            pipe.execute()
            removed += 1
        client.delete(user_sessions_key)
        return removed

    try:
        removed = execute("session_revoke_user", remove_all)
    except RedisUnavailable as error:
        raise SessionStoreUnavailable() from error
    increment("user_sessions_revoked", removed)
    redis_logger.info("Sesiones revocadas user_id=%s total=%s", user_id, removed)
    return removed


_SECRET_KEY_PATTERN = re.compile(
    r"(authorization|cookie|password|token|secret|api[-_]?key|credential)",
    re.IGNORECASE,
)
_JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")


def sanitize(value, key=""):
    if _SECRET_KEY_PATTERN.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {name: sanitize(item, name) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return _JWT_PATTERN.sub("[REDACTED]", value)
    return value


def install_request_logging(app):
    @app.before_request
    def start_request_log():
        g.request_id = request.headers.get("X-Request-ID", "").strip() or str(uuid.uuid4())
        g.request_started = time.perf_counter()

    @app.after_request
    def finish_request_log(response):
        response.headers["X-Request-ID"] = g.get("request_id", str(uuid.uuid4()))
        elapsed_ms = round((time.perf_counter() - g.get("request_started", time.perf_counter())) * 1000, 2)
        body = request.get_json(silent=True)
        response_body = response.get_json(silent=True)
        record = {
            "request_id": response.headers["X-Request-ID"],
            "service": app.name,
            "method": request.method,
            "url": request.base_url,
            "user_id": (g.get("jwt_claims") or {}).get("user_id"),
            "headers": sanitize({
                "content-type": request.headers.get("Content-Type"),
                "accept": request.headers.get("Accept"),
                "authorization": request.headers.get("Authorization"),
                "cookie": request.headers.get("Cookie"),
            }),
            "payload": sanitize(body),
            "status": response.status_code,
            "duration_ms": elapsed_ms,
            "response": sanitize(response_body),
        }
        app.logger.info("request %s", json.dumps(record, ensure_ascii=False, default=str))
        return response


def token_error_response():
    return jsonify(error="Bearer token ausente, invalido, expirado o revocado."), 401


def require_bearer(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            g.jwt_claims = bearer_claims()
        except InvalidToken:
            return token_error_response()
        except RevocationStoreUnavailable:
            logging.getLogger(__name__).exception("No se pudo consultar la revocacion JWT")
            return jsonify(error="No se pudo validar la sesion."), 503
        except JWTConfigurationError:
            logging.getLogger(__name__).exception("La configuracion JWT no es valida")
            return jsonify(error="El servicio no tiene JWT configurado correctamente."), 503
        return function(*args, **kwargs)
    return wrapped


ADMIN_ROLE = "admin"


def is_admin():
    return (g.get("jwt_claims") or {}).get("role_id") == ADMIN_ROLE


def forbidden_response():
    return jsonify(error="No tienes permisos para esta operacion."), 403


def require_role(*roles):
    """JWT valido (401 si no) y rol permitido (403 si no)."""
    def decorator(function):
        @wraps(function)
        def check_role(*args, **kwargs):
            if g.jwt_claims["role_id"] not in roles:
                return forbidden_response()
            return function(*args, **kwargs)
        return require_bearer(check_role)
    return decorator