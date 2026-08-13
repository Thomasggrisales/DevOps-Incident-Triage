"""
Diagnóstico adicional simulado para el agente de triage.

Amplía el "sistema de producción" simulado con señales que un agente de
on-call moderno consulta: historial de despliegues, salud del servicio,
historial de alertas y consultas a la base de datos (solo lectura).

Todas las funciones son deterministas por (servicio, seed) para que la
evidencia sea reproducible para un mismo incidente.
"""
import random
from datetime import datetime, timedelta, timezone

from app.services.simulator import SERVICE_LIST

# Cambio de configuración que suele acompañar al despliegue degradante.
DEPLOY_IMPACT = {
    "api-gateway": "cambios en rate limit y timeout del pool de conexiones",
    "auth-service": "rotación de claves JWT y política de refresh tokens",
    "database": "aumento de max_connections y nuevo índice en la tabla de pedidos",
    "worker": "aumento de concurrencia y reducción del límite de memoria",
    "frontend": "cambio en la configuración de assets y CDN",
    "cache": "política de evicción y tamaños de slots del clúster",
}

ALERT_MESSAGES = {
    "api-gateway": "HighErrorRate api-gateway 5xx > 5%",
    "auth-service": "AuthFailures auth-service intentos fallidos elevados",
    "database": "HighConnections db-primary pool > 80%",
    "worker": "OOMKilled worker crash-loop detectado",
    "frontend": "HighLatency frontend p95 > 2s",
    "cache": "CacheEvictions cache maxmemory casi agotado",
}

ALLOWED_TABLES = {"incidents", "status_history", "users", "agent_sessions"}


def _service_guard(service: str) -> str | None:
    if service not in SERVICE_LIST:
        return f"Servicio '{service}' no encontrado en el sistema simulado."
    return None


def fetch_deployment_history(service: str, limit: int = 5, seed: int = 0) -> str:
    """Devuelve el historial de despliegues recientes de un servicio."""
    guard = _service_guard(service)
    if guard:
        return guard

    rng = random.Random(f"deploy:{service}:{seed}")
    now = datetime.now(timezone.utc)
    lines = [f"Historial de despliegues de '{service}':"]
    for i in range(max(1, min(limit, 10))):
        hours_ago = rng.randint(1, 5) + i * rng.randint(6, 30)
        ts = now - timedelta(hours=hours_ago)
        version = f"v{rng.randint(1, 9)}.{rng.randint(0, 20)}.{rng.randint(0, 50)}"
        if i == 0 and seed != 0:
            status = "degradando el servicio"
            note = f"  <-- candidato: incluye {DEPLOY_IMPACT[service]}"
        else:
            status = "ok"
            note = ""
        lines.append(f"  {ts.isoformat()}  {version}  estado={status}{note}")

    if seed != 0:
        lines.append("  El despliegue más reciente coincide con el inicio del incidente.")
    return "\n".join(lines)


def check_service_health(service: str, seed: int = 0) -> str:
    """Devuelve el estado de salud actual de un servicio (healthy/degraded/down)."""
    guard = _service_guard(service)
    if guard:
        return guard

    rng = random.Random(f"health:{service}:{seed}")
    if seed == 0:
        status, replicas, restarts = "healthy", rng.randint(2, 8), 0
    else:
        status = rng.choice(["degraded", "degraded", "down"])
        replicas = rng.randint(1, 4)
        restarts = rng.randint(1, 8)

    return (
        f"Salud de '{service}': {status} | réplicas: {replicas} | "
        f"reinicios últimas 24h: {restarts} | última sonda liveness: ok"
    )


def get_alert_history(service: str, minutes: int = 180, seed: int = 0) -> str:
    """Devuelve las alertas recientes de un servicio en la ventana solicitada."""
    guard = _service_guard(service)
    if guard:
        return guard

    rng = random.Random(f"alerts:{service}:{seed}")
    now = datetime.now(timezone.utc)
    count = rng.randint(2, 6) if seed != 0 else rng.randint(0, 2)
    lines = [f"Alertas de '{service}' (últimos {minutes} min):"]
    for _ in range(count):
        ts = now - timedelta(minutes=rng.randint(1, max(1, minutes)))
        lines.append(f"  {ts.isoformat()}  {rng.choice(['P1', 'P2', 'P3'])}  {ALERT_MESSAGES[service]}")
    if count == 0:
        lines.append("  Sin alertas en la ventana.")
    return "\n".join(lines)


def query_database(query: str) -> str:
    """Ejecuta una consulta SQL de SOLO LECTURA (SELECT) sobre el esquema de la app."""
    lower = " ".join(query.lower().split())
    if not lower.startswith("select"):
        return "Solo se permiten consultas SELECT de lectura."

    table = next((t for t in ALLOWED_TABLES if f"from {t}" in lower), None)
    if table is None:
        return "Tabla no reconocida. Tablas permitidas: " + ", ".join(sorted(ALLOWED_TABLES))

    rng = random.Random(f"query:{table}")
    if table == "incidents":
        rows = [
            (1, "Alta latencia en payments-api", "critical", "open"),
            (2, "Pool de conexiones agotado en db-primary", "high", "investigating"),
            (3, "504 en api-gateway", "high", "resolved"),
            (4, "JWT validation failures masivos", "medium", "closed"),
        ]
        if "where status" in lower:
            state = lower.split("status")[-1]
            wanted = next((s for s in ("open", "investigating", "resolved", "closed") if s in state), None)
            if wanted:
                rows = [r for r in rows if r[3] == wanted]
        lines = ["id | titulo | severidad | estado"]
        lines += [f"{r[0]} | {r[1]} | {r[2]} | {r[3]}" for r in rows[:10]]
        return "\n".join(lines)

    if table == "status_history":
        lines = ["incident_id | old_status | new_status | changed_by"]
        lines += [f"{i} | {a} | {b} | {c}" for i, a, b, c in [
            (1, "open", "investigating", "Agent_AI"),
            (2, "open", "investigating", "Agent_AI"),
            (1, "investigating", "resolved", "Operator"),
        ]]
        return "\n".join(lines)

    if table == "users":
        return "id | email | role | is_active\n1 | devops@example.com | devops | true"

    return "id | status | title\n0001 | active | sesión de ejemplo"
