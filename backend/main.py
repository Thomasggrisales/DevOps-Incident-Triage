from fastapi import FastAPI
from app.api.incidents import router as incidents_router

app = FastAPI(
    title="DevOps Incident Triage API",
    description="API para el sistema de gestión de incidentes",
    version="0.1.0"
)

# Ticket #1: Endpoint explícito de Health Check
@app.get("/health", tags=["System"])
def health_check():
    """
    Verifica si la API está viva y respondiendo.
    """
    return {
        "status": "ok", 
        "message": "¡El servidor base está vivo y respondiendo correctamente!"
    }

# Endpoint raíz informativo
@app.get("/")
def read_root():
    return {
        "message": "Bienvenido a DevOps Incident Triage API. Visita /docs para probar los endpoints."
    }

# Ticket #3: Conectamos las rutas de incidentes al archivo principal
app.include_router(incidents_router)