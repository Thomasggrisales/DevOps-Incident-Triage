import weaviate
import os
from weaviate.classes.config import Property, DataType, Configure

WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "localhost")

def get_weaviate_client():
    """Conecta a Weaviate de forma local sin keys externas."""
    return weaviate.connect_to_custom(
        http_host=WEAVIATE_HOST,
        http_port=8080,
        http_secure=False,
        grpc_host=WEAVIATE_HOST,
        grpc_port=50051,
        grpc_secure=False
    )

def init_weaviate_schema():
    """Crea la colección usando el modelo Transformer local."""
    client = get_weaviate_client()
    try:


        if not client.collections.exists("Incident"):
            client.collections.create(
                name="Incident",
                description="Colección de incidentes de DevOps",
                # Cambiamos de text2vec_huggingface a text2vec_transformers
                vectorizer_config=Configure.Vectorizer.text2vec_transformers(),
                properties=[
                    Property(name="postgres_id", data_type=DataType.INT, skip_vectorization=True),
                    Property(name="title", data_type=DataType.TEXT),
                    Property(name="description", data_type=DataType.TEXT),
                    Property(name="source", data_type=DataType.TEXT, skip_vectorization=True),
                    Property(name="severity", data_type=DataType.TEXT, skip_vectorization=True),
                    Property(name="status", data_type=DataType.TEXT, skip_vectorization=True),
                ]
            )
            print("Colección 'Incident' (Local Transformers) creada exitosamente en Weaviate.")
    finally:
        client.close