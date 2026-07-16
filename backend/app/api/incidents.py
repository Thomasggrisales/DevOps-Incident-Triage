from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from app.schemas.incident import IncidentCreate, IncidentResponse
from app.services import incident as incident_service
from app.db.database import get_db
from app.services.incident import create_new_incident
from app.ai.rag import ask_devops_assistant

router = APIRouter()

@router.post("/")
def create_incident(incident: IncidentCreate, db: Session = Depends(get_db)):
    # Llamamos al servicio centralizado
    new_incident = create_new_incident(db, incident)
    return {"message": "Registrado con éxito", "id": new_incident.id}

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

# Nuevo endpoint para el Asistente
@router.post("/chat/")
def chat_with_assistant(request: ChatRequest):
    """
    Habla con el Asistente DevOps. 
    Busca contexto en Weaviate y responde usando Hugging Face.
    """
    try:
        respuesta = ask_devops_assistant(request.question)
        return {
            "question": request.question,
            "answer": respuesta
        }
    except Exception as e:
        return {"error": f"Hubo un problema al contactar a la IA: {str(e)}"}