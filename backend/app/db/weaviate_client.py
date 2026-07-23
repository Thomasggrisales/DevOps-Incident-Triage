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
    """Crea la colección indicando que nosotros daremos los vectores manualmente."""
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