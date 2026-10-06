import atexit
import logging
import os
import threading
from urllib.parse import urlsplit, urlunsplit

import redis
from redis.backoff import ExponentialBackoff
from redis.retry import Retry


class RedisUnavailable(Exception):
    pass


logger = logging.getLogger("library.redis")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(getattr(logging, os.getenv("REDIS_LOG_LEVEL", "INFO").upper(), logging.INFO))
    logger.propagate = False

_lock = threading.Lock()
_client = None
_healthy = None
_metrics = {}


def _float_env(name, default):
    try:
        value = float(os.getenv(name, default))
    except ValueError:
        value = float(default)
    return value if value > 0 else float(default)


def redacted_url(url):
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if parts.port:
            host += f":{parts.port}"
        if parts.username or parts.password:
            host = f"[REDACTED]@{host}"
        return urlunsplit((parts.scheme, host, parts.path, "", ""))
    except ValueError:
        return "[REDACTED]"


def increment(name, amount=1):
    with _lock:
        _metrics[name] = _metrics.get(name, 0) + amount


def metrics():
    with _lock:
        snapshot = dict(_metrics)
    snapshot["state"] = {True: "connected", False: "unavailable"}.get(_healthy, "unknown")
    return snapshot


def get_client():
    global _client
    if _client is not None:
        return _client
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        increment("errors.configuration")
        logger.error("REDIS_URL no esta configurada")
        raise RedisUnavailable("REDIS_URL no esta configurada")
    with _lock:
        if _client is None:
            try:
                _client = redis.Redis.from_url(
                    url,
                    decode_responses=True,
                    socket_connect_timeout=_float_env("REDIS_CONNECT_TIMEOUT_SECONDS", "2"),
                    socket_timeout=_float_env("REDIS_SOCKET_TIMEOUT_SECONDS", "2"),
                    health_check_interval=30,
                    retry_on_timeout=True,
                    retry=Retry(ExponentialBackoff(cap=0.5, base=0.05), retries=2),
                    max_connections=int(_float_env("REDIS_MAX_CONNECTIONS", "20")),
                )
            except ValueError as error:
                logger.error("REDIS_URL no es valida")
                raise RedisUnavailable("REDIS_URL no es valida") from error
            logger.info("Cliente Redis configurado para %s", redacted_url(url))
    return _client


def _error_kind(error):
    if isinstance(error, redis.exceptions.AuthenticationError):
        return "authentication"
    if isinstance(error, redis.exceptions.TimeoutError):
        return "timeout"
    if isinstance(error, redis.exceptions.ConnectionError):
        if "refused" in str(error).lower():
            return "connection_refused"
        return "disconnected"
    if isinstance(error, redis.exceptions.ResponseError):
        if "noauth" in str(error).lower() or "wrongpass" in str(error).lower():
            return "authentication"
        return "response"
    return "error"


def execute(operation, command):
    """Ejecuta command(client); cualquier falla de Redis se convierte en RedisUnavailable."""
    global _healthy
    client = get_client()
    try:
        result = command(client)
    except redis.RedisError as error:
        kind = _error_kind(error)
        increment("errors")
        increment(f"errors.{kind}")
        increment(f"errors.{operation}")
        if _healthy is not False:
            logger.error("Redis no disponible (%s) durante %s", kind, operation)
        else:
            logger.warning("Redis sigue sin responder (%s) durante %s", kind, operation)
        _healthy = False
        raise RedisUnavailable(operation) from error
    if _healthy is not True:
        increment("connections_ok")
        logger.info("Conexion Redis %s", "restablecida" if _healthy is False else "establecida")
        _healthy = True
    return result


def ping():
    try:
        return bool(execute("ping", lambda client: client.ping()))
    except RedisUnavailable:
        return False


# Cache opcional: una falla de Redis nunca se propaga al llamador.

def cache_get(key):
    """Devuelve (estado, valor) con estado hit, miss o bypass."""
    try:
        value = execute("cache_read", lambda client: client.get(key))
    except RedisUnavailable:
        increment("cache_bypass")
        logger.warning("cache bypass key=%s", key)
        return "bypass", None
    status = "hit" if value is not None else "miss"
    increment(f"cache_{status}")
    logger.info("cache %s key=%s", status, key)
    return status, value


def cache_set(key, value, ttl_seconds):
    try:
        execute("cache_write", lambda client: client.set(key, value, ex=ttl_seconds))
    except RedisUnavailable:
        return False
    return True


def cache_invalidate(keys=(), pattern=None):
    def remove(client):
        targets = list(keys)
        if pattern:
            targets.extend(client.scan_iter(match=pattern, count=200))
        if targets:
            client.delete(*targets)
        return len(targets)

    try:
        removed = execute("cache_invalidate", remove)
    except RedisUnavailable:
        logger.error("No se pudo invalidar el cache (keys=%s pattern=%s)", list(keys), pattern)
        return False
    increment("cache_invalidations")
    logger.info("cache invalidado claves=%s pattern=%s eliminadas=%s", list(keys), pattern, removed)
    return True


def close():
    global _client
    if _client is not None:
        try:
            _client.close()
            _client.connection_pool.disconnect()
        except redis.RedisError:
            pass
        _client = None


atexit.register(close)
