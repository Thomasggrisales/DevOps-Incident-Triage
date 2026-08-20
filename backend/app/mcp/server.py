"""
Servidor MCP del agente de triage DevOps.

Expone las capacidades del agente (logs, métricas, runbooks, incidentes
similares, diagnóstico y base de datos de solo lectura) como tools MCP.

Se puede ejecutar como server independiente sobre stdio:

    python -m app.mcp.server

El agente LangGraph lo consume como cliente (ver app.mcp.client).
"""
from mcp.server.fastmcp import FastMCP

from app.services import simulator, diagnostics
from app.ai import tools as agent_tools

mcp = FastMCP("devops-triage")


@mcp.tool()
def fetch_service_logs(service: str, minutes: int = 60, seed: int = 0) -> str:
    """Obtiene los últimos logs de un servicio en la ventana solicitada."""
    logs = simulator.get_service_logs(service, minutes=minutes, seed=seed)
    return "\n".join(logs) if logs else f"Sin logs registrados para '{service}'."


@mcp.tool()
def fetch_service_metrics(service: str, seed: int = 0) -> str:
    """Obtiene las métricas actuales de un servicio (CPU, memoria, latencia, errores)."""
    metrics = simulator.get_service_metrics(service, seed=seed)
    return "\n".join(f"{k}: {v}" for k, v in metrics.items())


@mcp.tool()
def search_runbook(query: str, limit: int = 3) -> str:
    """Busca runbooks o documentos operativos relevantes en la base de datos vectorial."""
    return agent_tools.search_runbook.invoke({"query": query, "limit": limit})


@mcp.tool()
def search_similar_incidents(query: str, limit: int = 3) -> str:
    """Busca incidentes históricos similares para reutilizar soluciones anteriores."""
    return agent_tools.search_similar_incidents.invoke({"query": query, "limit": limit})


@mcp.tool()
def update_incident_status(incident_id: int, new_status: str) -> str:
    """Actualiza el estado de un incidente (open, investigating, resolved)."""
    return agent_tools.update_incident_status.invoke(
        {"incident_id": incident_id, "new_status": new_status}
    )


@mcp.tool()
def fetch_deployment_history(service: str, limit: int = 5, seed: int = 0) -> str:
    """Revisa los últimos despliegues del servicio para detectar el cambio que pudo causar el incidente."""
    return diagnostics.fetch_deployment_history(service, limit=limit, seed=seed)


@mcp.tool()
def check_service_health(service: str, seed: int = 0) -> str:
    """Consulta el estado de salud actual del servicio (healthy, degraded o down)."""
    return diagnostics.check_service_health(service, seed=seed)


@mcp.tool()
def get_alert_history(service: str, minutes: int = 180, seed: int = 0) -> str:
    """Consulta el historial de alertas recientes de un servicio."""
    return diagnostics.get_alert_history(service, minutes=minutes, seed=seed)


@mcp.tool()
def query_database(query: str) -> str:
    """Ejecuta una consulta SELECT de solo lectura sobre la base de datos de la aplicación."""
    return diagnostics.query_database(query)


if __name__ == "__main__":
    mcp.run(transport="stdio")
