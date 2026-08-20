"""
Herramientas que el agente LangGraph puede invocar para recolectar evidencia.

Cada tool registra su resultado para que quede en el historial de decisiones
del incidente (capa de observabilidad de bajo costo sin dependencias extra).
"""
from langchain_core.tools import tool

from app.services.simulator import get_service_logs, get_service_metrics, SERVICE_LIST
from app.services.diagnostics import (
    fetch_deployment_history,
    check_service_health,
    get_alert_history,
    query_database,
)
from app.services.incident import get_embedding_local
from app.db.weaviate_client import get_weaviate_client
from app.db.database import SessionLocal
from app.db import models


@tool
def search_runbook(query: str, limit: int = 3) -> str:
    """Busca runbooks o documentos operativos relevantes en la base de datos vectorial."""
    from weaviate.classes.query import HybridFusion, MetadataQuery

    try:
        client = get_weaviate_client()
        collection = client.collections.get("Runbook")
        query_vector = get_embedding_local(query)
        if not query_vector:
            return "No se pudo generar el vector de búsqueda para los runbooks."

        response = collection.query.hybrid(
            query=query,
            vector=query_vector,
            limit=limit,
            alpha=0.7,
            fusion_type=HybridFusion.RELATIVE_SCORE,
            return_metadata=MetadataQuery(distance=True),
        )

        blocks = []
        for obj in response.objects:
            p = obj.properties
            distance = obj.metadata.distance if obj.metadata else None
            score_info = f" (score: {1 - distance:.2f})" if distance is not None else ""
            blocks.append(
                f"Título: {p.get('title')}{score_info}\n"
                f"Aplica a: {p.get('applies_to')}\n"
                f"Síntomas: {p.get('symptoms')}\n"
                f"Pasos: {p.get('steps')}"
            )
        return "\n\n---\n\n".join(blocks) if blocks else "Sin runbooks relevantes encontrados."
    except Exception as e:
        return f"Error al buscar runbooks: {e}"


@tool
def fetch_service_logs(service: str, minutes: int = 60, seed: int = 0) -> str:
    """Obtiene los últimos logs del servicio indicado en el sistema de producción simulado."""
    logs = get_service_logs(service, minutes=minutes, seed=seed)
    if logs:
        return "\n".join(logs)
    return f"Sin logs registrados para '{service}' en la ventana solicitada."


@tool
def fetch_service_metrics(service: str, seed: int = 0) -> str:
    """Obtiene las métricas actuales de un servicio (CPU, memoria, latencia, errores)."""
    metrics = get_service_metrics(service, seed=seed)
    return "\n".join(f"{k}: {v}" for k, v in metrics.items())


@tool
def search_similar_incidents(query: str, limit: int = 3) -> str:
    """Busca incidentes históricos similares para reutilizar soluciones anteriores."""
    from weaviate.classes.query import HybridFusion, MetadataQuery
    from app.services.incident import get_embedding_local

    try:
        client = get_weaviate_client()
        incidents_collection = client.collections.get("Incident")
        query_vector = get_embedding_local(query)

        if not query_vector:
            return "No se pudo generar el vector para buscar incidentes similares."

        response = incidents_collection.query.hybrid(
            query=query,
            vector=query_vector,
            limit=limit,
            alpha=0.7,
            fusion_type=HybridFusion.RELATIVE_SCORE,
            return_metadata=MetadataQuery(distance=True),
        )

        if not response.objects:
            return "Sin incidentes históricos similares."

        blocks = []
        for obj in response.objects:
            p = obj.properties
            distance = obj.metadata.distance if obj.metadata else None
            score_info = f" (score: {1 - distance:.2f})" if distance is not None else ""
            blocks.append(
                f"Título: {p.get('title', 'Sin título')}{score_info}\n"
                f"Estado: {p.get('status', 'Sin estado')}\n"
                f"Descripción: {p.get('description', 'Sin descripción')}"
            )
        return "\n\n---\n\n".join(blocks)
    except Exception as e:
        return f"Error buscando incidentes similares: {e}"


@tool
def update_incident_status(incident_id: int, new_status: str) -> str:
    """Actualiza el estado del incidente en el sistema (open, investigating, resolved, closed)."""
    if new_status not in {"open", "investigating", "resolved", "closed"}:
        return f"Estado inválido '{new_status}'. Valores permitidos: open, investigating, resolved, closed."

    db = SessionLocal()
    try:
        incident = db.query(models.Incident).filter(models.Incident.id == incident_id).first()
        if not incident:
            return f"No existe un incidente con ID {incident_id}."
        old = incident.status
        incident.status = new_status
        history = models.StatusHistory(
            incident_id=incident.id,
            old_status=old,
            new_status=new_status,
            changed_by="Agent_AI",
        )
        db.add(history)
        db.commit()
        return f"Estado del incidente {incident_id} actualizado: {old} -> {new_status}."
    except Exception as e:
        db.rollback()
        return f"Error actualizando el estado: {e}"
    finally:
        db.close()


@tool
def fetch_deployment_history_tool(service: str, limit: int = 5, seed: int = 0) -> str:
    """Revisa los últimos despliegues del servicio para detectar el cambio que pudo causar el incidente."""
    return fetch_deployment_history(service, limit=limit, seed=seed)


@tool
def check_service_health_tool(service: str, seed: int = 0) -> str:
    """Consulta el estado de salud actual del servicio (healthy, degraded o down)."""
    return check_service_health(service, seed=seed)


@tool
def get_alert_history_tool(service: str, minutes: int = 180, seed: int = 0) -> str:
    """Consulta el historial de alertas recientes de un servicio."""
    return get_alert_history(service, minutes=minutes, seed=seed)


@tool
def query_database_tool(query: str) -> str:
    """Ejecuta una consulta SELECT de solo lectura sobre la base de datos de la aplicación."""
    return query_database(query)


def available_service_hint() -> str:
    """Descripción de los servicios disponibles para el agente."""
    return ", ".join(SERVICE_LIST)
