import weaviate
import os
from weaviate.classes.config import Property, DataType, Configure

WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "weaviate")
HUGGINGFACE_APIKEY = os.getenv("HUGGINGFACE_APIKEY")

def get_weaviate_client():
    """Conecta a Weaviate inyectando la llave de Hugging Face en los headers."""
    return weaviate.connect_to_custom(
        http_host=WEAVIATE_HOST,
        http_port=8080,
        http_secure=False,
        grpc_host=WEAVIATE_HOST,
        grpc_port=50051,
        grpc_secure=False,
        headers={
            "X-HuggingFace-Api-Key": HUGGINGFACE_APIKEY  
        }
    )

def init_weaviate_schema():
    """Crea la colección usando la API de Inferencia de Hugging Face."""
    client = get_weaviate_client()
    try:
        

        if not client.collections.exists("Incident"):
            client.collections.create(
                name="Incident",
                description="Colección de incidentes de DevOps",
                vectorizer_config=Configure.Vectorizer.text2vec_huggingface(
                    model="sentence-transformers/all-MiniLM-L6-v2" 
                ),
                properties=[
                    Property(name="postgres_id", data_type=DataType.INT, skip_vectorization=True),
                    Property(name="title", data_type=DataType.TEXT),
                    Property(name="description", data_type=DataType.TEXT),
                    Property(name="source", data_type=DataType.TEXT, skip_vectorization=True),
                    Property(name="severity", data_type=DataType.TEXT, skip_vectorization=True),
                    Property(name="status", data_type=DataType.TEXT, skip_vectorization=True),
                ]
            )
            print("Colección 'Incident' (Hugging Face) creada exitosamente en Weaviate.")
    finally:
        client.close()