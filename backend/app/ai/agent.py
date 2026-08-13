"""
Agente LangGraph para el triage de incidentes DevOps.

Pipeline planificado: clasificar -> investigar -> proponer fix -> verificar.

El estado se conserva entre turnos de la conversación usando el checkpointer
(MemorySaver), por lo que la hipótesis, las acciones tomadas y los checks
pendientes sobreviven a lo largo de toda la sesión del incidente.
"""
import json
import logging
import os
import re
from typing import TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.ai import tools
from app.services import diagnostics as _diagnostics

# Cliente MCP opcional: si no está instalado, el agente degrada a las
# implementaciones locales (las mismas que expone el MCP server).
try:
    from app.mcp.client import mcp_invoke
except Exception:  # pragma: no cover - entorno sin MCP instalado
    mcp_invoke = None

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://host.docker.internal:11434"
OLLAMA_MODEL = "mistral"

LLM = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.0,
    num_predict=600,
)


class IncidentState(TypedDict, total=False):
    incident: dict
    messages: list[dict]
    hypothesis: str
    severity: str
    owner_team: str
    actions_taken: list[str]
    pending_checks: list[str]
    evidence: list[dict]
    plan: list[str]
    fix: str
    fix_risk: str
    needs_approval: bool
    verification: str
    verdict: str
    summary: str
    error: str
    error_count: int


def _chat(system: str, user: str) -> str:
    """Invoca el LLM local. Devuelve cadena vacía si falla (para fallback)."""
    try:
        response = LLM.invoke(f"<s>{system}\n\n{user}</s>")
        content = response.content
        return content.strip() if isinstance(content, str) else str(content).strip()
    except Exception as e:
        logger.error("Fallo al contactar el LLM: %s", e)
        return ""


def _parse_json(text: str) -> dict | None:
    """Extrae un objeto JSON de la respuesta del LLM (robusto ante markdown)."""
    if not text:
        return None
    text = text.strip()
    # Quita bloques de código markdown si el LLM los agregó.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _get_last_user_message(state: IncidentState) -> str:
    msgs = state.get("messages", [])
    for msg in reversed(msgs):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return state.get("incident", {}).get("description", "")


def _invoke_diag(name: str, **kwargs) -> str:
    """Invoca una tool de diagnóstico vía MCP; cae a la implementación local si falla."""
    if mcp_invoke is not None:
        result = mcp_invoke(name, **kwargs)
        if result is not None:
            return result
    return getattr(_diagnostics, name)(**kwargs)


def _conversation_context(state: IncidentState) -> str:
    msgs = state.get("messages", [])
    if len(msgs) <= 1:
        return "Sin contexto adicional. Es la primera interacción."
    lines = [
        f"- {m.get('role')}: {m.get('content')}"
        for m in msgs[-4:]
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fallbacks (se usan cuando el LLM no está disponible para no romper el flujo)
# ---------------------------------------------------------------------------

def _fallback_classify(state: IncidentState) -> dict:
    text = (state.get("incident", {}).get("description", "") + " " +
            state.get("incident", {}).get("title", "")).lower()
    if any(k in text for k in ["critical", "down", "caida", "caída", "outage", "pérdida", "perdida", "secur", "breach"]):
        severity = "critical"
    elif any(k in text for k in ["high", "error", "failed", "timeout", "pool", "crash"]):
        severity = "high"
    elif any(k in text for k in ["medium", "warn", "slow", "latency"]):
        severity = "medium"
    else:
        severity = "low"

    teams = {"database": "DBA", "api-gateway": "Plataforma", "auth-service": "Seguridad",
             "worker": "Backend", "frontend": "Frontend", "cache": "Infraestructura"}
    team = "DevOps"
    for key, value in teams.items():
        if key in text:
            team = value
            break
    return {
        "severity": severity,
        "owner_team": team,
        "hypothesis": "Fallo no determinado (LLM no disponible); se usó clasificación heurística.",
        "plan": ["1. Clasificar el incidente", "2. Investigar con logs y métricas",
                 "3. Proponer fix", "4. Verificar la solución"],
        "actions_taken": [f"Incidente clasificado como {severity} (equipo: {team}) por heurística."],
    }


def _fallback_synthesis(evidence_text: str) -> dict:
    return {
        "hypothesis": "No se pudo sintetizar evidencia con el LLM. Revisar los logs y métricas recopilados.",
        "pending_checks": ["Validar manualmente la evidencia recopilada.",
                           "Revisar la última ventana de despliegue o cambio."],
    }


def _fallback_fix(incident: dict) -> dict:
    return {
        "fix": "Acción conservadora sugerida por fallback: reiniciar el servicio afectado y monitorear por 15 minutos.",
        "fix_risk": "medium",
        "needs_approval": True,
        "pending_checks": ["Verificar que el servicio recupere su estado tras el reinicio.",
                           "Revisar métricas de error durante la ventana de verificación."],
    }


# ---------------------------------------------------------------------------
# Nodos del grafo
# ---------------------------------------------------------------------------

def classify(state: IncidentState) -> dict:
    incident = state.get("incident", {})
    user_text = _get_last_user_message(state)
    system = (
        "Eres un ingeniero DevOps de guardia senior. Clasifica el incidente y plantea una hipótesis inicial. "
        "Responde SOLO con JSON válido y sin texto adicional: "
        '{"severity": "critical|high|medium|low", "owner_team": "<equipo>", '
        '"hypothesis": "<hipótesis inicial>", "notes": "<razonamiento breve>"}'
    )
    prompt = (
        f"Incidente:\nTítulo: {incident.get('title')}\n"
        f"Descripción: {incident.get('description')}\nFuente: {incident.get('source')}\n\n"
        f"Contexto de la conversación:\n{_conversation_context(state)}\n\n"
        f"Último mensaje del ingeniero: {user_text}\n\n"
        f"Servicios disponibles en el sistema: {tools.available_service_hint()}"
    )

    data = _parse_json(_chat(system, prompt))
    if not data:
        logger.warning("LLM no respondió JSON en classify, usando fallback.")
        fallback = _fallback_classify(state)
        fallback["error"] = "LLM no disponible; clasificación heurística."
        return fallback

    return {
        "severity": data.get("severity", "medium"),
        "owner_team": data.get("owner_team", "DevOps"),
        "hypothesis": data.get("hypothesis", ""),
        "plan": ["1. Clasificar el incidente", "2. Investigar con logs y métricas",
                 "3. Proponer fix", "4. Verificar la solución"],
        "actions_taken": [f"Incidente clasificado como {data.get('severity')} "
                          f"(equipo: {data.get('owner_team')}). Hipótesis: {data.get('hypothesis')}"],
        "error": "",
    }


def investigate(state: IncidentState) -> dict:
    incident = state.get("incident", {})
    incident_id = incident.get("id", 0)
    seed = incident_id or 0

    # 1) El LLM decide qué servicios y búsquedas ejecutar.
    system = (
        "Eres un ingeniero DevOps investigando un incidente. Decide qué herramientas usar. "
        f"Servicios disponibles: {tools.available_service_hint()}. "
        "Responde SOLO con JSON: "
        '{"services": ["<servicios a revisar>"], "runbook_query": "<consulta para runbooks>", '
        '"similar_query": "<consulta para incidentes similares>"}'
    )
    plan_data = _parse_json(_chat(system, f"Incidente:\n{incident.get('description', '')}\n\n"
                                          f"Hipótesis actual: {state.get('hypothesis')}"))
    services = plan_data.get("services", []) if plan_data else []
    runbook_query = plan_data.get("runbook_query", incident.get("description", "")) if plan_data else incident.get("description", "")
    similar_query = plan_data.get("similar_query", incident.get("title", "")) if plan_data else incident.get("title", "")

    if not services:
        # Fallback: derivar el servicio desde la hipótesis/texto.
        text = (incident.get("description", "") + " " + state.get("hypothesis", "")).lower()
        for srv in tools.available_service_hint().split(", "):
            if srv.split("-")[0] in text or srv in text:
                services = [srv]
                break
        if not services:
            services = ["database"]

    evidence: list[dict] = []
    actions: list[str] = []

    for service in services[:3]:
        logs_result = tools.fetch_service_logs.invoke({"service": service, "minutes": 60, "seed": seed})
        evidence.append({"tool": "fetch_service_logs", "query": service, "result": logs_result})
        actions.append(f"Se revisaron los logs de '{service}'.")

        metrics_result = tools.fetch_service_metrics.invoke({"service": service, "seed": seed})
        evidence.append({"tool": "fetch_service_metrics", "query": service, "result": metrics_result})
        actions.append(f"Se revisaron las métricas de '{service}'.")

    runbook_result = tools.search_runbook.invoke({"query": runbook_query})
    evidence.append({"tool": "search_runbook", "query": runbook_query, "result": runbook_result})
    actions.append("Se buscaron runbooks/KB relevantes.")

    similar_result = tools.search_similar_incidents.invoke({"query": similar_query})
    evidence.append({"tool": "search_similar_incidents", "query": similar_query, "result": similar_result})
    actions.append("Se buscaron incidentes históricos similares.")

    # 1b) Diagnóstico adicional (despliegues, salud, alertas, BD) vía MCP.
    #     El agente consulta el servidor MCP estándar y cae a la implementación
    #     local solo si el server no está disponible.
    primary = services[0] if services else "database"
    diagnostics_specs = [
        ("fetch_deployment_history", {"service": primary, "limit": 5, "seed": seed}),
        ("check_service_health", {"service": primary, "seed": seed}),
        ("get_alert_history", {"service": primary, "minutes": 180, "seed": seed}),
    ]
    for tool_name, kwargs in diagnostics_specs:
        result = _invoke_diag(tool_name, **kwargs)
        evidence.append({"tool": tool_name, "query": primary, "result": result})
        actions.append(f"Se revisó {tool_name} de '{primary}'.")

    db_query = "SELECT id, titulo, severidad, estado FROM incidents WHERE status = 'open'"
    db_result = _invoke_diag("query_database", query=db_query)
    evidence.append({"tool": "query_database", "query": "incidentes abiertos", "result": db_result})
    actions.append("Se consultó la base de datos (incidentes abiertos).")

    # 2) El LLM sintetiza la hipótesis con la evidencia.
    evidence_text = "\n\n".join(
        f"[{item['tool']} <- {item['query']}]\n{item['result']}" for item in evidence
    )
    system = (
        "Sintetiza la hipótesis del incidente usando la evidencia. "
        "Responde SOLO con JSON: "
        '{"hypothesis": "<hipótesis refinada>", "pending_checks": ["<check 1>", "<check 2>"], '
        '"notes": "<qué evidencia confirma o descarta>"}'
    )
    syn = _parse_json(_chat(system, f"Incidente: {incident.get('description', '')}\n\nEvidencia:\n{evidence_text[:3500]}"))
    if not syn:
        syn = _fallback_synthesis(evidence_text)

    return {
        "evidence": evidence,
        "actions_taken": actions,
        "hypothesis": syn.get("hypothesis", state.get("hypothesis", "")),
        "pending_checks": syn.get("pending_checks", []),
    }


def propose_fix(state: IncidentState) -> dict:
    incident = state.get("incident", {})
    evidence_text = "\n\n".join(f"[{e['tool']}]\n{e['result']}" for e in state.get("evidence", []))
    system = (
        "Eres un ingeniero DevOps senior. Propón un plan de corrección claro para el incidente. "
        "Si la acción es de alto riesgo (reiniciar producción, escalar, cambiar config crítica), "
        "marca needs_approval como true. Responde SOLO con JSON: "
        '{"fix": "<pasos de la corrección>", "fix_risk": "low|medium|high", '
        '"needs_approval": true|false, "pending_checks": ["<check 1>"]}'
    )
    prompt = (
        f"Incidente: {incident.get('description', '')}\n"
        f"Hipótesis: {state.get('hypothesis')}\n\nEvidencia:\n{evidence_text[:3000]}\n\n"
        f"Runbooks relevantes encontrados.\nContexto conversación:\n{_conversation_context(state)}"
    )
    data = _parse_json(_chat(system, prompt))
    if not data:
        data = _fallback_fix(incident)

    return {
        "fix": data.get("fix", ""),
        "fix_risk": data.get("fix_risk", "medium"),
        "needs_approval": bool(data.get("needs_approval", True)),
        "pending_checks": data.get("pending_checks", state.get("pending_checks", [])),
    }


def verify(state: IncidentState) -> dict:
    incident = state.get("incident", {})
    system = (
        "Define cómo verificar que el fix propuesto resuelve el incidente y emite un veredicto. "
        "Responde SOLO con JSON: "
        '{"verification": "<pasos concretos de verificación>", '
        '"verdict": "confirmed|uncertain|refuted", "pending_checks": ["<check 1>"]}'
    )
    prompt = (
        f"Incidente: {incident.get('description', '')}\n"
        f"Hipótesis: {state.get('hypothesis')}\nFix propuesto: {state.get('fix')}\n\n"
        f"Evidencia:\n" + "\n".join(f"- {e['tool']}: {e['result'][:120]}" for e in state.get("evidence", []))
    )
    data = _parse_json(_chat(system, prompt))
    if not data:
        data = {
            "verification": "Monitorear métricas de error/latencia durante 15 minutos tras aplicar el fix "
                            "y confirmar que el servicio vuelve a estado normal.",
            "verdict": "uncertain",
            "pending_checks": ["Confirmar recuperación del servicio tras aplicar el fix."],
        }

    return {
        "verification": data.get("verification", ""),
        "verdict": data.get("verdict", "uncertain"),
        "pending_checks": data.get("pending_checks", state.get("pending_checks", [])),
    }


def finish(state: IncidentState) -> dict:
    incident = state.get("incident", {})
    evidence_lines = []
    for e in state.get("evidence", []):
        result = e["result"]
        if len(result) > 180:
            result = result[:180] + "..."
        evidence_lines.append(f"- [{e['tool']}] {result}")

    summary = "\n".join([
        f"INCIDENTE: {incident.get('title', 'Sin título')} (id {incident.get('id', 'N/A')})",
        "",
        f"SEVERIDAD: {state.get('severity', 'N/A').upper()} | EQUIPO RESPONSABLE: {state.get('owner_team', 'N/A')}",
        "",
        f"HIPÓTESIS: {state.get('hypothesis', 'N/A')}",
        "",
        f"EVIDENCIA:\n" + ("\n".join(evidence_lines) if evidence_lines else "Sin evidencia recopilada."),
        "",
        f"FIX PROPUESTO ({state.get('fix_risk', 'N/A')} riesgo): {state.get('fix', 'N/A')}",
        "",
        f"VERIFICACIÓN: {state.get('verification', 'N/A')}",
        "",
        f"CHECKS PENDIENTES:\n" + ("\n".join(f"- {c}" for c in state.get("pending_checks", [])) or "- Ninguno."),
    ])
    return {"summary": summary}


def handle_error(state: IncidentState) -> dict:
    """Nodo de degradación: si algo falla, responde con la info recopilada hasta ahora."""
    err = state.get("error", "")
    base = finish(state)
    base["summary"] = (
        f"Se presentó un problema durante el triage ({err}). "
        "El agente continuó usando información parcial. Detalles:\n\n" + base["summary"]
    )
    return base


# ---------------------------------------------------------------------------
# Checkpointer: persiste el estado del grafo en Postgres (sobrevive reinicios).
# Si la BD no está disponible, degrada a memoria sin romper el flujo.
# ---------------------------------------------------------------------------

def _create_checkpointer():
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres_user:postgres_password123@db:5432/devops_incident_db",
    )
    try:
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver

        conn = psycopg.connect(database_url, autocommit=True, prepare_threshold=0)
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()
        logger.info("Checkpointer de Postgres inicializado.")
        return checkpointer
    except Exception as e:
        logger.warning("Postgres checkpointer no disponible, usando MemorySaver: %s", e)
        return MemorySaver()


# ---------------------------------------------------------------------------
# Construcción del grafo
# ---------------------------------------------------------------------------

def _build_graph():
    workflow = StateGraph(IncidentState)

    workflow.add_node("classify", classify)
    workflow.add_node("investigate", investigate)
    workflow.add_node("propose_fix", propose_fix)
    workflow.add_node("verify", verify)
    workflow.add_node("finish", finish)
    workflow.add_node("handle_error", handle_error)

    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", "investigate")
    workflow.add_edge("investigate", "propose_fix")
    workflow.add_edge("propose_fix", "verify")
    workflow.add_edge("verify", "finish")

    # Si el LLM falló de forma crítica, el flujo continúa con fallback igualmente.
    def has_critical_error(state: IncidentState) -> str:
        return "finish" if state.get("error") else "handle_error"

    workflow.add_conditional_edges("finish", has_critical_error, {"finish": END, "handle_error": "handle_error"})
    workflow.add_edge("handle_error", END)

    checkpointer = _create_checkpointer()
    return workflow.compile(checkpointer=checkpointer)


agent_graph = _build_graph()
