import weaviate
import os
from weaviate.classes.config import Property, DataType, Configure

WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "weaviate")

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
    """Crea las colecciones con soporte para hybrid search (vector + BM25)."""
    client = get_weaviate_client()
    try:
        if not client.collections.exists("Incident"):
            client.collections.create(
                name="Incident",
                description="Colección de incidentes de DevOps",
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
            print("Colección 'Incident' creada exitosamente.")

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
            print("Colección 'Runbook' creada exitosamente.")
    finally:
        client.close()


def seed_runbooks():
    """Indexa los runbooks en Weaviate usando el pipeline de ingesta."""
    from app.services.ingest import ingest_documents, DOCS_DIR

    client = get_weaviate_client()
    try:
        collection = client.collections.get("Runbook")
        if collection.query.fetch_objects(limit=1).objects:
            print("Runbooks ya indexados, omitiendo seed.")
            return
    finally:
        client.close()

    if os.path.exists(DOCS_DIR):
        print("Iniciando ingesta de documentos desde docs/...")
        ingest_documents(docs_dir=DOCS_DIR)
    else:
        print(f"Directorio {DOCS_DIR} no encontrado, omitiendo ingesta.")