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
        "Eres un ingeniero DevOps de guardia senior. "
        "Clasifica el incidente según su impacto y asigna el equipo responsable.\n\n"
        "Criterios de severidad:\n"
        "- critical: servicio principal caído, pérdida de datos, breach de seguridad\n"
        "- high: degradación severa, errores >5%, múltiples usuarios afectados\n"
        "- medium: latencia elevada, errores intermitentes, un servicio afectado\n"
        "- low: Cosmético, incidente menor, sin impacto en usuarios\n\n"
        "Responde SOLO con JSON válido:\n"
        '{"severity": "critical|high|medium|low", "owner_team": "<equipo>", '
        '"hypothesis": "<hipótesis inicial basada en la descripción>", '
        '"notes": "<razonamiento breve>"}'
    )
    prompt = (
        f"Incidente:\nTítulo: {incident.get('title')}\n"
        f"Descripción: {incident.get('description')}\nFuente: {incident.get('source')}\n\n"
        f"Contexto de la conversación:\n{_conversation_context(state)}\n\n"
        f"Último mensaje del ingeniero: {user_text}\n\n"
        f"Servicios disponibles: {tools.available_service_hint()}\n\n"
        "Mapeo de nombres comunes:\n"
        "- 'backend' / 'api' / 'servidor' → 'api-gateway' o 'auth-service'\n"
        "- 'bd' / 'base de datos' / 'postgres' → 'database'\n"
        "- 'cache' / 'redis' → 'cache'\n"
        "- 'frontend' / 'ui' → 'frontend'\n"
        "- 'worker' / 'job' / 'tarea' → 'worker'"
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
        "Eres un ingeniero DevOps investigando un incidente. "
        "Tu objetivo es recopilar evidencia de múltiples fuentes para confirmar o descartar la hipótesis.\n\n"
        f"Servicios disponibles: {tools.available_service_hint()}\n\n"
        "Debes buscar:\n"
        "1. Logs y métricas de los servicios sospechosos\n"
        "2. Runbooks que describan síntomas similares (la consulta debe incluir palabras clave del problema)\n"
        "3. Incidentes históricos similares\n\n"
        "Responde SOLO con JSON:\n"
        '{"services": ["<servicios a revisar, máximo 3>"], '
        '"runbook_query": "<consulta con palabras clave del problema para buscar en runbooks>", '
        '"similar_query": "<descripción concisa del problema para buscar incidentes similares>"}'
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
        "Eres un ingeniero DevOps senior analizando evidencia de un incidente.\n\n"
        "REGLAS IMPORTANTES:\n"
        "- Los runbooks son documentación autoritativa. Si un runbook describe los mismos síntomas, "
        "su diagnóstico y solución tienen prioridad sobre cualquier otra evidencia.\n"
        "- Los postmortems son incidentes reales anteriores. Si hay un postmortem similar, "
        "referencia las lecciones aprendidas.\n"
        "- Si la evidencia contradice el runbook, indica la discrepancia.\n\n"
        "Responde SOLO con JSON:\n"
        '{"hypothesis": "<hipótesis refinada con evidencia>", '
        '"runbook_used": "<título del runbook aplicable, o null si ninguno>", '
        '"pending_checks": ["<check 1>", "<check 2>"], '
        '"notes": "<qué evidencia confirma o descarta, y por qué>"}'
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
        "Eres un ingeniero DevOps senior proponiendo una corrección para un incidente.\n\n"
        "REGLAS IMPORTANTES:\n"
        "- Si hay un runbook en la evidencia, SUS PASOS son la base de la corrección. "
        "No inventes pasos que no estén en el runbook.\n"
        "- Si el runbook no cubre exactamente este caso, adáptalo a la situación actual.\n"
        "- Si no hay runbook, usa las mejores prácticas de la industria.\n"
        "- Marca needs_approval=true si la acción es de alto riesgo: "
        "reiniciar producción, escalar infraestructura, modificar configs de seguridad, "
        "o cualquier cambio que no se pueda revertir fácilmente.\n\n"
        "Responde SOLO con JSON:\n"
        '{"fix": "<pasos concretos de la corrección, numerados>", '
        '"fix_risk": "low|medium|high", '
        '"needs_approval": true|false, '
        '"runbook_followed": "<título del runbook seguido, o null>", '
        '"pending_checks": ["<check 1>"]}'
    )
    prompt = (
        f"Incidente: {incident.get('description', '')}\n"
        f"Hipótesis: {state.get('hypothesis')}\n\n"
        f"Evidencia recopilada:\n{evidence_text[:3000]}\n\n"
        f"Contexto conversación:\n{_conversation_context(state)}"
    )
    data = _parse_json(_chat(system, prompt))
    if not data:
        data = _fallback_fix(incident)

    return {
        "fix": data.get("fix", ""),
        "fix_risk": data.get("fix_risk", "medium"),
        "needs_approval": True,
        "pending_checks": data.get("pending_checks", state.get("pending_checks", [])),
    }


def verify(state: IncidentState) -> dict:
    incident = state.get("incident", {})
    system = (
        "Eres un ingeniero DevOps verificando que un fix resolvió un incidente.\n\n"
        "Define pasos concretos de verificación:\n"
        "1. Qué métricas monitorear (latencia, error rate, conexiones, etc.)\n"
        "2. Cuánto tiempo monitorear (mínimo 15 minutos para cambios de config)\n"
        "3. Qué umbral confirma que el fix funcionó\n\n"
        "El veredicto debe ser:\n"
        "- confirmed: la evidencia respalda firmemente que el fix funcionará\n"
        "- uncertain: falta información o la evidencia es ambigua\n"
        "- refuted: la evidencia contradice el fix propuesto\n\n"
        "Responde SOLO con JSON:\n"
        '{"verification": "<pasos concretos de verificación>", '
        '"verdict": "confirmed|uncertain|refuted", '
        '"pending_checks": ["<check 1>"]}'
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

    # Detectar si se usaron runbooks o postmortems.
    runbook_used = any("runbook" in e["tool"].lower() for e in state.get("evidence", []))
    runbook_found = any(
        "título:" in e["result"].lower() and "pasos:" in e["result"].lower()
        for e in state.get("evidence", [])
        if e["tool"] == "search_runbook"
    )

    sources = []
    if runbook_found:
        sources.append("Runbooks de la KB")
    if any(e["tool"] == "search_similar_incidents" and "Título:" in e["result"] for e in state.get("evidence", [])):
        sources.append("Postmortems anteriores")

    summary_parts = [
        f"INCIDENTE: {incident.get('title', 'Sin título')} (id {incident.get('id', 'N/A')})",
        "",
        f"SEVERIDAD: {state.get('severity', 'N/A').upper()} | EQUIPO RESPONSABLE: {state.get('owner_team', 'N/A')}",
        "",
        f"HIPÓTESIS: {state.get('hypothesis', 'N/A')}",
    ]

    if sources:
        summary_parts.extend(["", f"FUENTES CONSULTADAS: {', '.join(sources)}"])

    summary_parts.extend([
        "",
        f"EVIDENCIA:\n" + ("\n".join(evidence_lines) if evidence_lines else "Sin evidencia recopilada."),
        "",
        f"FIX PROPUESTO ({state.get('fix_risk', 'N/A')} riesgo): {state.get('fix', 'N/A')}",
        "",
        f"VERIFICACIÓN: {state.get('verification', 'N/A')}",
        "",
        f"CHECKS PENDIENTES:\n" + ("\n".join(f"- {c}" for c in state.get("pending_checks", [])) or "- Ninguno."),
    ])

    return {"summary": "\n".join(summary_parts)}


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
