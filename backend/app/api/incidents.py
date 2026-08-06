from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from uuid import uuid4
import logging

from app.schemas.incident import IncidentCreate, IncidentResponse
from app.services import incident as incident_service
from app.db.database import get_db
from app.db import models
from app.ai.agent import agent_graph
from app.ai.langfuse_setup import get_langfuse_handler, trace_context

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(incident_in: IncidentCreate, db: Session = Depends(get_db)):
    return incident_service.create_new_incident(db=db, incident_in=incident_in)

@router.get("/", response_model=List[IncidentResponse])
def list_incidents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return incident_service.get_incidents(db=db, skip=skip, limit=limit)

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    db_incident = incident_service.get_incident_by_id(db=db, incident_id=incident_id)
    if not db_incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"El incidente con ID {incident_id} no existe."
        )
    return db_incident

@router.get("/search/")
def search_incidents(q: str = Query(..., description="Tu consulta en lenguaje natural")):
    results = search_incidents_semantic(query=q)
    return {
        "query": q,
        "results": results
    }

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None


def _fresh_state(session: "models.AgentSession", incident: dict, question: str) -> dict:
    """Construye el estado inicial para una ejecución del grafo del agente."""
    messages = (session.conversation or []) + [{"role": "user", "content": question}]
    return {
        "incident": incident,
        "messages": messages,
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
def chat_with_assistant(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chatea con el agente de triage. Sin session_id inicia una nueva sesión
    de incidente; con session_id continúa el triage anterior.
    """
    try:
        session = None
        incident = None

        if request.session_id:
            session = db.query(models.AgentSession).filter(
                models.AgentSession.id == request.session_id
            ).first()
            if not session:
                raise HTTPException(status_code=404, detail="La sesión no existe o fue cerrada.")
            incident = incident_service.get_incident_by_id(db, session.incident_id)
            if not incident:
                raise HTTPException(status_code=404, detail="El incidente asociado ya no existe.")
        else:
            # Nueva sesión: se crea un incidente con el primer mensaje como alerta.
            title = request.question[:80] + ("..." if len(request.question) > 80 else "")
            incident = incident_service.create_new_incident(
                db,
                IncidentCreate(
                    title=title,
                    description=request.question,
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

        incident_dict = {
            "id": incident.id,
            "title": incident.title,
            "description": incident.description,
            "source": incident.source,
            "severity": incident.severity,
            "status": incident.status,
        }

        initial_state = _fresh_state(session, incident_dict, request.question)

        # Trazabilidad con Langfuse (degradación silenciosa si no hay claves).
        langfuse_handler = get_langfuse_handler()
        config = {"configurable": {"thread_id": session.id}}
        if langfuse_handler is not None:
            config["callbacks"] = [langfuse_handler]

        with trace_context(
            langfuse_handler,
            trace_name="incident-triage-agent",
            session_id=session.id,
            metadata={"incident_id": incident.id, "source": incident.source},
            tags=["incident-triage", "langgraph"],
        ):
            result = agent_graph.invoke(initial_state, config=config)

        # Persistir la conversación y actualizar severidad/estado del incidente.
        conversation = initial_state["messages"] + [
            {"role": "agent", "content": result.get("summary", "")}
        ]
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