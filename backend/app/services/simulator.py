"""
Simulador del sistema de producción.

Genera logs y métricas falsos pero realistas para que el agente pueda
"investigar" incidentes usando herramientas, sin necesidad de un sistema
real de monitoreo.
"""
import random
from datetime import datetime, timedelta, timezone

SERVICE_LIST = ["api-gateway", "auth-service", "database", "worker", "frontend", "cache"]

# Patrones de falla conocidos por servicio. Se eligen según el `seed` para
# que la evidencia sea estable y reproducible para un mismo incidente.
FAILURE_PATTERNS = {
    "api-gateway": [
        ("ERROR", "upstream_request_timeout upstream=http://backend status=504"),
        ("ERROR", "http_request_timeout request_id=req-{} duration_ms=12000"),
        ("WARN", "rate_limit_exceeded client={} limit=100rps window=60s"),
        ("INFO", "connection_pool_recycled pool_id=gw-{}"),
    ],
    "auth-service": [
        ("ERROR", "jwt_validation_failed token_expired sub=user_{}"),
        ("ERROR", "refresh_token_revoked sub=user_{}"),
        ("WARN", "failed_login_attempts ip=10.0.{}.{} count=12"),
        ("INFO", "token_rotation_ok sub=user_{}"),
    ],
    "database": [
        ("ERROR", "connection_refused host=postgres port=5432"),
        ("ERROR", "connection_pool_exhausted pool_size=20 waiting_connections=45"),
        ("WARN", "slow_query query_id=q_{} duration_ms=2100 table=orders"),
        ("ERROR", "deadlock_detected tx={} retried=3"),
        ("INFO", "checkpoint_started lsn={}"),
    ],
    "worker": [
        ("ERROR", "out_of_memory_killed pod=worker-{} rss_mb=2048 limit_mb=1024"),
        ("WARN", "high_heap_usage heap_mb={} threshold=75%"),
        ("ERROR", "crash_loop_backoff pod=worker-{} restarts=5"),
        ("INFO", "job_completed job_id=j_{} duration_ms=340"),
    ],
    "frontend": [
        ("WARN", "assets_cache_miss path=/static/bundle.js count={}"),
        ("INFO", "websocket_connected session={}"),
        ("ERROR", "s3_signed_url_failed bucket=static-assets"),
    ],
    "cache": [
        ("ERROR", "redis_connection_timeout host=cache port=6379"),
        ("WARN", "eviction_rate_high maxmemory_policy=allkeys-lru"),
        ("INFO", "cluster_slot_migration slot={}"),
    ],
}

# Signaturas que ayudan al agente a cruzar evidencia con el incidente.
SEVERITY_HINTS = {
    "database": "Alta probabilidad de fallo de conexión o saturación del pool de la base de datos.",
    "api-gateway": "Posibles timeouts aguas arriba o saturación del gateway.",
    "auth-service": "Posibles fallos de validación JWT o bloqueo de tokens.",
    "worker": "Posible falta de memoria (OOM) o crash-loop en los workers.",
    "frontend": "Posibles fallos de assets o CDN.",
    "cache": "Posibles fallos de conexión o evicción agresiva del caché.",
}


def _format_log(line: tuple, rng: random.Random, ts: datetime) -> str:
    level, template = line
    placeholders = max(1, template.count("{}"))
    args = [rng.randint(1000, 9999) for _ in range(placeholders)]
    return f"{ts.isoformat()} {level} {template.format(*args)}"


def get_service_logs(service: str, minutes: int = 60, seed: int = 0) -> list[str]:
    """Devuelve logs simulados para un servicio durante los últimos `minutes`."""
    if service not in SERVICE_LIST:
        return [f"Servicio '{service}' no encontrado en el sistema simulado."]

    rng = random.Random(f"{service}:{seed}")
    patterns = FAILURE_PATTERNS[service]
    logs = []
    now = datetime.now(timezone.utc)

    # Entre 3 y 8 eventos en la ventana de tiempo solicitada.
    for i in range(rng.randint(3, 8)):
        ts = now - timedelta(minutes=rng.randint(1, max(1, minutes)))
        logs.append(_format_log(rng.choice(patterns), rng, ts))

    logs.sort()
    return logs


def get_service_metrics(service: str, seed: int = 0) -> dict:
    """Devuelve métricas simuladas para un servicio."""
    if service not in SERVICE_LIST:
        return {"error": f"Servicio '{service}' no encontrado."}

    rng = random.Random(f"metrics:{service}:{seed}")
    healthy = seed == 0

    metrics = {
        "service": service,
        "cpu_usage_percent": rng.randint(10, 95),
        "memory_usage_mb": rng.randint(256, 4096),
        "error_rate_percent": rng.randint(0, 15) if not healthy else rng.randint(0, 2),
        "p95_latency_ms": rng.randint(50, 1500),
        "active_connections": rng.randint(5, 60),
        "restarts_last_hour": rng.randint(0, 6) if not healthy else 0,
    }
    return metrics
