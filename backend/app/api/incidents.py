from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from uuid import uuid4
from datetime import datetime
import logging

from app.schemas.incident import IncidentCreate, IncidentResponse
from app.services import incident as incident_service
from app.services.incident import search_incidents_semantic
from app.db.database import get_db
from app.db import models
from app.core.deps import get_current_user
from app.ai.agent import agent_graph
from app.ai.langfuse_setup import get_langfuse_handler, trace_context

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident_in: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return incident_service.create_new_incident(db=db, incident_in=incident_in)

@router.get("/", response_model=List[IncidentResponse])
def list_incidents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return incident_service.get_incidents(db=db, skip=skip, limit=limit)


@router.get("/stats/")
def incident_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Resumen de métricas del dashboard (totales, severidad, estado, MTTR)."""
    incidents = db.query(models.Incident).all()

    by_status: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for inc in incidents:
        by_status[inc.status or "open"] = by_status.get(inc.status or "open", 0) + 1
        by_severity[inc.severity or "pending"] = by_severity.get(inc.severity or "pending", 0) + 1

    total = len(incidents)
    active = by_status.get("open", 0) + by_status.get("investigating", 0)
    resolved = by_status.get("resolved", 0)
    resolution_rate = round(resolved / total * 100, 1) if total else 0.0
    critical_active = sum(
        1 for inc in incidents
        if inc.severity == "critical" and inc.status not in ("resolved", "closed")
    )

    # MTTR: promedio de horas entre created_at y el primer cambio a "resolved".
    mttr_seconds = []
    for inc in incidents:
        history = db.query(models.StatusHistory).filter(
            models.StatusHistory.incident_id == inc.id,
            models.StatusHistory.new_status == "resolved",
        ).order_by(models.StatusHistory.changed_at.asc()).first()
        if history and history.changed_at and inc.created_at:
            delta = (history.changed_at - inc.created_at).total_seconds()
            if delta >= 0:
                mttr_seconds.append(delta)
    mttr_hours = round(sum(mttr_seconds) / len(mttr_seconds) / 3600, 2) if mttr_seconds else None

    recent = [
        {
            "id": i.id,
            "title": i.title,
            "severity": i.severity,
            "status": i.status,
            "source": i.source,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in sorted(incidents, key=lambda x: x.created_at or datetime.min, reverse=True)[:6]
    ]

    return {
        "total": total,
        "active": active,
        "resolved": resolved,
        "critical_active": critical_active,
        "resolution_rate": resolution_rate,
        "mttr_hours": mttr_hours,
        "by_status": by_status,
        "by_severity": by_severity,
        "recent": recent,
    }

@router.get("/search/")
def search_incidents(
    q: str = Query(..., description="Tu consulta en lenguaje natural"),
    current_user: models.User = Depends(get_current_user),
):
    results = search_incidents_semantic(query=q)
    return {
        "query": q,
        "results": results
    }

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_incident = incident_service.get_incident_by_id(db=db, incident_id=incident_id)
    if not db_incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"El incidente con ID {incident_id} no existe."
        )
    return db_incident


@router.get("/{incident_id}/session")
def get_or_create_session(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Busca o crea una sesión de agente para un incidente dado."""
    incident = incident_service.get_incident_by_id(db=db, incident_id=incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="El incidente no existe.")

    session = (
        db.query(models.AgentSession)
        .filter(models.AgentSession.incident_id == incident_id)
        .order_by(models.AgentSession.created_at.desc())
        .first()
    )

    if not session:
        title = incident.title[:80]
        session = models.AgentSession(
            id=str(uuid4()),
            incident_id=incident.id,
            title=title,
            status="active",
            conversation=[],
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    conversation = session.conversation or []
    history_msgs: list[ChatMessage] = []
    for msg in conversation:
        role = msg.get("role", "agent")
        content = msg.get("content", "")
        if not content:
            continue
        history_msgs.append(ChatMessage(
            role=role,
            text=content,
            sessionId=session.id,
            needsApproval=msg.get("needs_approval"),
            fix=msg.get("fix"),
            fixRisk=msg.get("fix_risk"),
        ))

    return {
        "session_id": session.id,
        "incident": {
            "id": incident.id,
            "title": incident.title,
            "severity": incident.severity,
            "status": incident.status,
            "source": incident.source,
            "created_at": incident.created_at.isoformat() if incident.created_at else None,
        },
        "messages": history_msgs,
    }


class ChatMessage(BaseModel):
    role: str
    text: str
    sessionId: str | None = None
    needsApproval: bool | None = None
    fix: str | None = None
    fixRisk: str | None = None

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None
    incident_id: int | None = None


class ApprovalRequest(BaseModel):
    session_id: str
    decision: str  # "approved" | "rejected"
    comment: str | None = None


# ---------------------------------------------------------------------------
# Detección de un nuevo incidente dentro de una conversación existente.
# Una sesión = un incidente: si el usuario describe otro incidente, se inicia
# una sesión nueva para no contaminar el contexto con el incidente anterior.
# ---------------------------------------------------------------------------

_INCIDENT_SERVICE_KEYWORDS = [
    "api-gateway", "apigateway", "gateway", "auth-service", "auth", "database",
    "postgres", "redis", "worker", "frontend", "backend", "cache", "script",
    "cron", "api", "microservicio", "servicio",
]
_INCIDENT_FAILURE_KEYWORDS = [
    "error", "fail", "timeout", "caída", "caida", "caído", "caido", "down",
    "outage", "lent", "crash", "pérdida", "perdida", "502", "503", "504",
    "500", "falla", "no funciona", "no responde", "no arranca", "se cae",
    "explota", "detenid",
]
_FOLLOWUP_HINTS = [
    "aprueba", "rechaza", "aprobar", "rechazar", "qué evidencia", "que evidencia",
    "qué hace", "que hace", "continúa", "continua", "sigue", "verifica",
    "más info", "mas info", "detalle", "explica", "resumen", "por qué", "por que",
]


def _looks_like_new_incident(text: str) -> bool:
    """Devuelve True si el mensaje parece la descripción de un incidente nuevo."""
    t = text.lower()
    if any(hint in t for hint in _FOLLOWUP_HINTS):
        return False
    mentions_service = any(k in t for k in _INCIDENT_SERVICE_KEYWORDS)
    mentions_failure = any(k in t for k in _INCIDENT_FAILURE_KEYWORDS)
    return (mentions_service or mentions_failure) and len(t.strip()) > 20


def _start_new_session(db: Session, question: str):
    """Crea un incidente y una sesión de agente para un nuevo triage."""
    title = question[:80] + ("..." if len(question) > 80 else "")
    incident = incident_service.create_new_incident(
        db,
        IncidentCreate(
            title=title,
            description=question,
            source="chat",
            severity="pending",
        ),
    )
    session = models.AgentSession(
        id=str(uuid4()),
        incident_id=incident.id,
        title=title,
        status="active",
        conversation=[],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, incident


def _conversation_messages(session: "models.AgentSession", question: str) -> list[dict]:
    """Mensajes de la sesión + el nuevo mensaje del usuario."""
    return (session.conversation or []) + [{"role": "user", "content": question}]


def _fresh_state(session: "models.AgentSession", incident: dict, question: str) -> dict:
    """Construye el estado inicial para una ejecución del grafo del agente."""
    return {
        "incident": incident,
        "messages": _conversation_messages(session, question),
        "hypothesis": "",
        "severity": "pending",
        "owner_team": "",
        "actions_taken": [],
        "pending_checks": [],
        "evidence": [],
        "plan": [],
        "fix": "",
        "fix_risk": "",
        "needs_approval": False,
        "verification": "",
        "verdict": "",
        "summary": "",
        "error": "",
        "error_count": 0,
    }


# Endpoint para el Asistente con agente LangGraph y sesiones persistentes
@router.post("/chat/")
def chat_with_assistant(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Chatea con el agente de triage. Sin session_id inicia una nueva sesión
    de incidente; con session_id continúa el triage anterior.
    """
    try:
        session = None
        incident = None
        new_session = False

        if request.session_id:
            session = db.query(models.AgentSession).filter(
                models.AgentSession.id == request.session_id
            ).first()
            if not session:
                raise HTTPException(status_code=404, detail="La sesión no existe o fue cerrada.")
            if not request.incident_id and _looks_like_new_incident(request.question):
                # El usuario describió otro incidente: nueva sesión, sin contexto previo.
                session, incident = _start_new_session(db, request.question)
                new_session = True
            else:
                incident = incident_service.get_incident_by_id(db, session.incident_id)
                if not incident:
                    raise HTTPException(status_code=404, detail="El incidente asociado ya no existe.")
        else:
            # Nueva sesión: se crea un incidente con el primer mensaje como alerta.
            session, incident = _start_new_session(db, request.question)

        incident_dict = {
            "id": incident.id,
            "title": incident.title,
            "description": incident.description,
            "source": incident.source,
            "severity": incident.severity,
            "status": incident.status,
        }

        # Trazabilidad con Langfuse (degradación silenciosa si no hay claves).
        langfuse_handler = get_langfuse_handler()
        config = {"configurable": {"thread_id": session.id}}
        if langfuse_handler is not None:
            config["callbacks"] = [langfuse_handler]

        # Si la sesión ya tiene un checkpoint en Postgres, se reanuda el estado
        # persistido (hipótesis, evidencia, checks, etc.) pasando solo los mensajes.
        has_checkpoint = False
        if not new_session and request.session_id:
            try:
                has_checkpoint = agent_graph.checkpointer.get_tuple(config) is not None
            except Exception:
                has_checkpoint = False

        if has_checkpoint:
            initial_state = {"messages": _conversation_messages(session, request.question)}
        else:
            initial_state = _fresh_state(session, incident_dict, request.question)

        with trace_context(
            langfuse_handler,
            trace_name="incident-triage-agent",
            session_id=session.id,
            metadata={"incident_id": incident.id, "source": incident.source},
            tags=["incident-triage", "langgraph"],
        ):
            result = agent_graph.invoke(initial_state, config=config)

        # Persistir la conversación y actualizar severidad/estado del incidente.
        agent_msg = {
            "role": "agent",
            "content": result.get("summary", ""),
            "needs_approval": result.get("needs_approval", False),
            "fix": result.get("fix", ""),
            "fix_risk": result.get("fix_risk", ""),
        }
        conversation = initial_state["messages"] + [agent_msg]
        session.conversation = conversation
        db.add(session)

        if incident.severity == "pending" and result.get("severity") not in ("", None, "pending"):
            incident.severity = result["severity"]
        if result.get("needs_approval"):
            incident.status = "investigating"
            db.add(incident)
        db.commit()

        return {
            "session_id": session.id,
            "answer": result.get("summary", "Sin respuesta del agente."),
            "new_session": new_session,
            "state": {
                "severity": result.get("severity"),
                "owner_team": result.get("owner_team"),
                "hypothesis": result.get("hypothesis"),
                "plan": result.get("plan"),
                "actions_taken": result.get("actions_taken"),
                "pending_checks": result.get("pending_checks"),
                "evidence": result.get("evidence"),
                "fix": result.get("fix"),
                "fix_risk": result.get("fix_risk"),
                "needs_approval": result.get("needs_approval"),
                "verification": result.get("verification"),
                "verdict": result.get("verdict"),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error en el chat del agente.")
        return {"error": f"Hubo un problema al contactar al agente: {str(e)}"}


@router.post("/approval/")
def submit_approval(
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Registra la decisión humana sobre el fix propuesto por el agente."""
    if request.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decisión inválida. Use 'approved' o 'rejected'.")

    session = db.query(models.AgentSession).filter(
        models.AgentSession.id == request.session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="La sesión no existe o fue cerrada.")
    incident = incident_service.get_incident_by_id(db, session.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="El incidente asociado ya no existe.")

    old_status = incident.status
    new_status = "resolved" if request.decision == "approved" else "open"
    incident.status = new_status

    history = models.StatusHistory(
        incident_id=incident.id,
        old_status=old_status,
        new_status=new_status,
        changed_by="human_operator",
    )
    db.add(history)

    decision_line = (
        f"[DECISIÓN HUMANA] El operador {'APROBÓ' if request.decision == 'approved' else 'RECHAZÓ'} "
        f"el fix propuesto (estado del incidente: {new_status})."
    )
    if request.comment:
        decision_line += f" Comentario: {request.comment}"
    session.conversation = (session.conversation or []) + [
        {"role": "agent", "content": decision_line}
    ]
    db.add(session)
    db.commit()

    return {
        "decision": request.decision,
        "incident_id": incident.id,
        "status": incident.status,
    } 


# --- Auto-scrape endpoints ---

@router.get("/scrape/status")
def get_scrape_status():
    """Devuelve el estado de la configuración de auto-scrape."""
    from app.services.auto_scrape import get_auto_scrape_config
    return get_auto_scrape_config()


@router.post("/scrape/run")
def run_scrape(
    force: bool = Query(False, description="Forzar re-indexación completa"),
    current_user: models.User = Depends(get_current_user),
):
    """Ejecuta un scrape manual de todas las fuentes configuradas."""
    from app.services.auto_scrape import run_auto_scrape, is_auto_scrape_running
    
    if is_auto_scrape_running():
        raise HTTPException(
            status_code=409,
            detail="Ya hay un scrape en ejecución. Espera a que termine."
        )
    
    # Ejecutar en background para no bloquear la respuesta
    import threading
    thread = threading.Thread(
        target=run_auto_scrape,
        args=(force,),
        daemon=True,
    )
    thread.start()
    
    return {
        "status": "started",
        "force": force,
        "message": "Scrape iniciado en background. Consulta /scrape/status para ver el progreso.",
    }