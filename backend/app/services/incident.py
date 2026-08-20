import requests
from sqlalchemy.orm import Session
from app.db.models import Incident, StatusHistory
from app.schemas.incident import IncidentCreate
from app.db.weaviate_client import get_weaviate_client

def get_embedding_local(text: str) -> list:
    """Genera embeddings usando Ollama localmente (sin internet)"""
    # host.docker.internal apunta a tu máquina física (localhost)
    OLLAMA_URL = "http://host.docker.internal:11434/api/embeddings"
    
    payload = {
        "model": "all-minilm", # El mismo modelo ligero que usaba Hugging Face
        "prompt": text
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()["embedding"]
        else:
            print(f"Error en Ollama Embeddings: {response.text}")
            return []
    except Exception as e:
        print(f"Error de conexión con Ollama Embeddings: {e}")
        return []

def get_incidents(db: Session, skip: int = 0, limit: int = 100) -> list[Incident]:
    return db.query(Incident).order_by(Incident.id.desc()).offset(skip).limit(limit).all()

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

    # 3. Guardado vectorial en Weaviate (Manual con Ollama)
    client = None
    try:
        client = get_weaviate_client()
        incidents_collection = client.collections.get("Incident")
        
        # Generamos el vector combinando título y descripción
        texto_a_vectorizar = f"{db_incident.title}. {db_incident.description}"
        vector = get_embedding_local(texto_a_vectorizar)
        
        if vector:
            incidents_collection.data.insert(
                properties={
                    "postgres_id": db_incident.id,
                    "title": db_incident.title,
                    "description": db_incident.description,
                    "source": db_incident.source,
                    "severity": db_incident.severity,
                    "status": str(db_incident.status)
                },
                vector=vector # Inyectamos el vector manualmente aquí
            )
        else:
            print("Advertencia: No se generó el vector en Ollama. El incidente no se indexó en Weaviate.")
            
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
    client = None
    try:
        client = get_weaviate_client()
        incidents_collection = client.collections.get("Incident")
        
        # 1. Vectorizamos la pregunta usando Ollama localmente
        query_vector = get_embedding_local(query)
        
        if not query_vector:
            print("No se pudo generar el vector, abortando búsqueda en Weaviate.")
            return []
        
        # 2. Búsqueda semántica usando los números (near_vector)
        response = incidents_collection.query.near_vector(
            near_vector=query_vector,
            limit=limit,
            return_metadata=None
        )
        
        # 3. Formateamos los resultados para devolver algo limpio
        results = []
        for obj in response.objects:
            results.append({
                "postgres_id": obj.properties.get("postgres_id"),
                "title": obj.properties.get("title", "Sin título"),
                "description": obj.properties.get("description", "Sin descripción"),
                "status": obj.properties.get("status", "Sin estado")
            })
            
        return results
        
    except Exception as e:
        print(f"Error en la búsqueda semántica: {e}")
        return []