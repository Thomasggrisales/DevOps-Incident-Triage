import weaviate
import os

weavite_URL = os.getenv("WEAVIATE_URL", "http://localhost:8081")

def get_weaviate_client():
    client = weaviate.connect_to_local(
        host="localhost",
        port=8081,
        grpc_port=50051
    )
    return client

def init_weaviate_schema():
    client = get_weaviate_client()
    if not client.collections.exists("Incident"):
        client.collections.create("Incident")
    client.close()