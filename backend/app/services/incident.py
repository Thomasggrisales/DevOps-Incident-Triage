from sqlalchemy.orm import Session
from app.db.models import Incident, StatusHistory
from app.schemas.incident import IncidentCreate
from app.db.weaviate_client import get_weaviate_client

def get_incidents(db: Session, skip: int = 0, limit: int = 100) -> list[Incident]:
    return db.query(Incident).offset(skip).limit(limit).all()

def get_incident_by_id(db: Session, incident_id: int) -> Incident | None:
    return db.query(Incident).filter(Incident.id == incident_id).first()

def create_new_incident(db: Session, incident_in: IncidentCreate) -> Incident:
    # 1. Guardado en PostgreSQL
    db_incident = Incident(
        title=incident_in.title,
        description=incident_in.description,
        source=incident_in.source,
        severity=incident_in.severity
    )
    db.add(db_incident)
    db.flush() # Obtener el ID asignado por Postgres sin cerrar la transacción

    # 2. Guardado del historial
    db_history = StatusHistory(
        incident_id=db_incident.id,
        old_status=None,
        new_status=db_incident.status,
        changed_by="System_Init"
    )
    db.add(db_history)
    
    # Commit final de ambos (Incidente + Historial)
    db.commit()
    db.refresh(db_incident)

    # 3. Guardado vectorial en Weaviate
    try:
        client = get_weaviate_client()
        incidents_collection = client.collections.get("Incident")
        
        incidents_collection.data.insert({
            "postgres_id": db_incident.id,
            "title": db_incident.title,
            "description": db_incident.description,
            "source": db_incident.source,
            "severity": db_incident.severity,
            "status": str(db_incident.status)
        })
    except Exception as e:
        print(f"Error indexando en Weaviate: {e}")
        # No hacemos raise para que el usuario reciba su incidente creado en Postgres
        
    return db_incident

def update_incident_status(db: Session, incident_id: int, new_status: str) -> Incident | None:
    db_incident = get_incident_by_id(db, incident_id)
    if not db_incident:
        return None
    
    old_status = db_incident.status
    db_incident.status = new_status
    
    db_history = StatusHistory(
        incident_id=incident_id,
        old_status=old_status,
        new_status=new_status,
        changed_by="Operator"
    )
    db.add(db_history)
    
    db.commit()
    db.refresh(db_incident)
    
    return db_incident

def search_incidents_semantic(query: str, limit: int = 3):
    client = get_weaviate_client()
    incidents_collection = client.collections.get("Incident")
    
    # Búsqueda semántica usando el modelo de Hugging Face
    response = incidents_collection.query.near_text(
        query=query,
        limit=limit,
        return_metadata=None # Podemos pedir 'distance' si quieres ver qué tan preciso es
    )
    
    # Formateamos los resultados para devolver algo limpio
    results = []
    for obj in response.objects:
        results.append({
            "postgres_id": obj.properties["postgres_id"],
            "title": obj.properties["title"],
            "description": obj.properties["description"],
            "status": obj.properties["status"]
        })
    
    client.close()
    return results

