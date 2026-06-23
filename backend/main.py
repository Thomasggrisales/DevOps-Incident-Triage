from fastapi import FastAPI

# Esta es la famosa variable "app" que Uvicorn estaba buscando
app = FastAPI(
    title="DevOps Incident Triage API",
    description="API para el sistema de gestión de incidentes"
)

# Un endpoint de prueba para saber que todo está vivo
@app.get("/")
def read_root():
    return {"status": "ok", "message": "¡La API está funcionando perfectamente!"}