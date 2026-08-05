import weaviate
import os
import requests
from weaviate.classes.config import Property, DataType, Configure

WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "weaviate")
HUGGINGFACE_APIKEY = os.getenv("HUGGINGFACE_APIKEY")

def get_weaviate_client():
    """Conecta a Weaviate localmente de forma limpia."""
    return weaviate.connect_to_custom(
        http_host=WEAVIATE_HOST,
        http_port=8080,
        http_secure=False,
        grpc_host=WEAVIATE_HOST,
        grpc_port=50051,
        grpc_secure=False
    )

def init_weaviate_schema():
    """Crea las colecciones indicando que nosotros daremos los vectores manualmente."""
    client = get_weaviate_client()
    try:
        if not client.collections.exists("Incident"):
            client.collections.create(
                name="Incident",
                description="Colección de incidentes de DevOps",
                # IMPORTANTE: Desactivamos el vectorizador interno
                vectorizer_config=Configure.Vectorizer.none(),
                properties=[
                    Property(name="postgres_id", data_type=DataType.INT),
                    Property(name="title", data_type=DataType.TEXT),
                    Property(name="description", data_type=DataType.TEXT),
                    Property(name="source", data_type=DataType.TEXT),
                    Property(name="severity", data_type=DataType.TEXT),
                    Property(name="status", data_type=DataType.TEXT),
                ]
            )
            print("Colección 'Incident' (Manual) creada exitosamente.")

        if not client.collections.exists("Runbook"):
            client.collections.create(
                name="Runbook",
                description="Runbooks y documentos operativos para resolver incidentes",
                vectorizer_config=Configure.Vectorizer.none(),
                properties=[
                    Property(name="title", data_type=DataType.TEXT),
                    Property(name="applies_to", data_type=DataType.TEXT),
                    Property(name="symptoms", data_type=DataType.TEXT),
                    Property(name="steps", data_type=DataType.TEXT),
                ]
            )
            print("Colección 'Runbook' (Manual) creada exitosamente.")
    finally:
        client.close()


# Runbooks de ejemplo usados por el agente como conocimiento base (KB).
SAMPLE_RUNBOOKS = [
    {
        "title": "Saturación del pool de conexiones de PostgreSQL",
        "applies_to": "database",
        "symptoms": "connection_refused, connection_pool_exhausted, slow queries",
        "steps": "1) Confirmar en métricas el uso de conexiones. 2) Incrementar pool size y max_connections. "
                 "3) Matar sesiones idle usando pg_terminate_backend. 4) Reiniciar pgbouncer si aplica. 5) Escalar réplicas de lectura.",
    },
    {
        "title": "Errores 5xx y timeouts en API Gateway",
        "applies_to": "api-gateway",
        "symptoms": "504, upstream timeout, http 500",
        "steps": "1) Revisar logs del gateway por upstream. 2) Verificar salud de los servicios aguas arriba. "
                 "3) Reiniciar pods degradados. 4) Aumentar timeouts solo temporalmente. 5) Escalar réplicas del backend afectado.",
    },
    {
        "title": "OOM / fuga de memoria en workers",
        "applies_to": "worker",
        "symptoms": "out_of_memory_killed, high heap usage, crash loop",
        "steps": "1) Revisar métricas de RSS/heap. 2) Reiniciar el worker afectado. 3) Revisar el heap dump. "
                 "4) Ajustar límites de memoria y cola de jobs. 5) Desplegar fix de la fuga y monitorear.",
    },
    {
        "title": "Pico de CPU en API Gateway",
        "applies_to": "api-gateway",
        "symptoms": "cpu alto, latencia p95 alta, rate limit",
        "steps": "1) Identificar la ruta más costosa en logs. 2) Aplicar rate limiting. 3) Escalar horizontalmente. "
                 "4) Habilitar caché de respuestas.",
    },
    {
        "title": "Fallos de autenticación / JWT",
        "applies_to": "auth-service",
        "symptoms": "jwt_validation_failed, refresh token revoked, login failures",
        "steps": "1) Revisar logs de auth-service. 2) Verificar rotación de la clave JWT. 3) Limpiar tokens revocados. "
                 "4) Si la clave cambió, coordinar con todos los servicios consumidores.",
    },
    {
        "title": "Caché Redis lenta o evicción agresiva",
        "applies_to": "cache",
        "symptoms": "redis timeout, eviction rate high",
        "steps": "1) Revisar eviction_rate y maxmemory. 2) Aumentar memoria o ajustar política. 3) Pre-cargar claves críticas. "
                 "4) Validar conexiones de los clientes.",
    },
]


def seed_runbooks():
    """Indexa los runbooks de ejemplo en Weaviate si la colección está vacía."""
    # Fail-fast: si Ollama (embeddings) no responde, evita 6 timeouts de 10s.
    try:
        requests.get("http://host.docker.internal:11434/api/tags", timeout=2)
    except Exception:
        print("Ollama no disponible, omitiendo seed de runbooks.")
        return

    client = get_weaviate_client()
    try:
        collection = client.collections.get("Runbook")
        if collection.query.fetch_objects(limit=1).objects:
            print("Runbooks ya indexados, omitiendo seed.")
            return

        from app.services.incident import get_embedding_local

        for runbook in SAMPLE_RUNBOOKS:
            text_to_vectorize = f"{runbook['title']}. {runbook['symptoms']}"
            vector = get_embedding_local(text_to_vectorize)
            if vector:
                collection.data.insert(properties=runbook, vector=vector)
        print(f"Seed de {len(SAMPLE_RUNBOOKS)} runbooks completado.")
    except Exception as e:
        print(f"ADVERTENCIA: No se pudo sembrar los runbooks: {e}")
    finally:
        client.close()

def get_hf_embedding(text: str) -> list[float]:
    """Función para que Python llame a Hugging Face directamente vía HTTP."""
    url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_APIKEY}"}
    
    response = requests.post(url, headers=headers, json={"inputs": text})
    
    if response.status_code != 200:
        raise Exception(f"Error de red con Hugging Face desde Python: {response.text}")
        
    return response.json()