"""
Pipeline de ingesta de documentos para Weaviate.

Lee runbooks y postmortems en formato Markdown con frontmatter YAML,
genera embeddings con Ollama (all-MiniLM) y los almacena en Weaviate.

Uso CLI (desde backend/):
    python -m app.services.ingest

También se puede llamar desde el lifespan de FastAPI.
"""
import glob
import os
import re
import time

import frontmatter

from app.db.weaviate_client import get_weaviate_client
from app.services.incident import get_embedding_local

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs")
SCRAPER_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".scraper_cache", "scraped_docs")
MAX_CHUNK_CHARS = 1500
CHUNK_OVERLAP = 200


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Divide el texto en chunks respetando párrafos cuando es posible."""
    if len(text) <= max_chars:
        return [text.strip()]

    paragraphs = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                for i in range(0, len(para), max_chars - overlap):
                    chunks.append(para[i : i + max_chars].strip())
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)
    return chunks


def _load_documents(docs_dir: str) -> list[dict]:
    """Carga todos los archivos .md del directorio docs/ y del scraper cache."""
    documents = []
    patterns = ["runbooks/*.md", "postmortems/*.md"]

    for pattern in patterns:
        for filepath in glob.glob(os.path.join(docs_dir, pattern)):
            with open(filepath, encoding="utf-8") as f:
                post = frontmatter.load(f)

            title = post.metadata.get("title", os.path.basename(filepath))
            applies_to = post.metadata.get("applies_to", "general")
            severity = post.metadata.get("severity", "medium")
            symptoms = post.metadata.get("symptoms", "")
            doc_type = "runbook" if "runbook" in pattern else "postmortem"
            body = post.content.strip()

            if not body:
                continue

            chunks = _chunk_text(body)
            for i, chunk in enumerate(chunks):
                documents.append({
                    "title": title,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "applies_to": applies_to,
                    "severity": severity,
                    "symptoms": symptoms if isinstance(symptoms, str) else str(symptoms),
                    "body": chunk,
                    "doc_type": doc_type,
                    "source_file": os.path.basename(filepath),
                })
    
    # Cargar documentos scrapeados del cache
    if os.path.exists(SCRAPER_CACHE_DIR):
        for filepath in glob.glob(os.path.join(SCRAPER_CACHE_DIR, "*.md")):
            try:
                with open(filepath, encoding="utf-8") as f:
                    post = frontmatter.load(f)
                
                title = post.metadata.get("title", os.path.basename(filepath))
                doc_type = post.metadata.get("doc_type", "runbook")
                symptoms = post.metadata.get("symptoms", "")
                severity = post.metadata.get("severity", "medium")
                source = post.metadata.get("source", "web")
                body = post.content.strip()
                
                if not body:
                    continue
                
                chunks = _chunk_text(body)
                for i, chunk in enumerate(chunks):
                    documents.append({
                        "title": title,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "applies_to": source,
                        "severity": severity,
                        "symptoms": symptoms if isinstance(symptoms, str) else str(symptoms),
                        "body": chunk,
                        "doc_type": doc_type,
                        "source_file": f"scraped_{os.path.basename(filepath)}",
                    })
            except Exception as e:
                print(f"  [ERROR] Error cargando {filepath}: {e}")
    
    return documents


def _embedding_text(doc: dict) -> str:
    """Compone el texto que se vectoriza para búsqueda semántica."""
    parts = [doc["title"]]
    if doc["symptoms"]:
        parts.append(doc["symptoms"])
    parts.append(doc["body"][:500])
    return ". ".join(parts)


def ingest_documents(docs_dir: str = DOCS_DIR, force: bool = False) -> dict:
    """
    Ingesta documentos en Weaviate de forma idempotente.

    Args:
        docs_dir: directorio raíz de docs (runbooks/ y postmortems/).
        force: si True, re-indexa todo borrando los existentes.

    Returns:
        {"runbooks": N, "postmortems": M, "errors": E}
    """
    try:
        requests_get = __import__("requests").get
        requests_get("http://host.docker.internal:11434/api/tags", timeout=2)
    except Exception:
        print("Ollama no disponible, omitiendo ingesta.")
        return {"runbooks": 0, "postmortems": 0, "errors": 1}

    docs = _load_documents(docs_dir)
    if not docs:
        print(f"No se encontraron documentos en {docs_dir}")
        return {"runbooks": 0, "postmortems": 0, "errors": 0}

    client = get_weaviate_client()
    stats = {"runbooks": 0, "postmortems": 0, "errors": 0}

    try:
        runbook_col = client.collections.get("Runbook")
        incident_col = client.collections.get("Incident")

        if force:
            try:
                runbook_col.delete_many()
                incident_col.delete_many()
                print("Colecciones limpiadas (--force).")
            except Exception:
                pass

        for doc in docs:
            try:
                text_to_embed = _embedding_text(doc)
                vector = get_embedding_local(text_to_embed)
                if not vector:
                    print(f"  [SKIP] No se pudo generar vector para '{doc['title']}' chunk {doc['chunk_index']}")
                    stats["errors"] += 1
                    continue

                chunk_id = f"{doc['source_file']}::{doc['chunk_index']}"

                if doc["doc_type"] == "runbook":
                    properties = {
                        "title": f"{doc['title']} (parte {doc['chunk_index'] + 1}/{doc['total_chunks']})" if doc["total_chunks"] > 1 else doc["title"],
                        "applies_to": doc["applies_to"],
                        "symptoms": doc["symptoms"],
                        "steps": doc["body"],
                    }
                    runbook_col.data.insert(properties=properties, vector=vector)
                    stats["runbooks"] += 1
                else:
                    properties = {
                        "postgres_id": 0,
                        "title": f"{doc['title']} (parte {doc['chunk_index'] + 1}/{doc['total_chunks']})" if doc["total_chunks"] > 1 else doc["title"],
                        "description": doc["body"],
                        "source": doc["applies_to"],
                        "severity": doc["severity"],
                        "status": "resolved",
                    }
                    incident_col.data.insert(properties=properties, vector=vector)
                    stats["postmortems"] += 1

                print(f"  [OK] {doc['doc_type']}: {doc['title']} (chunk {doc['chunk_index'] + 1}/{doc['total_chunks']})")
                time.sleep(0.1)

            except Exception as e:
                print(f"  [ERROR] {doc['title']}: {e}")
                stats["errors"] += 1

    finally:
        client.close()

    print(f"\nIngesta completada: {stats['runbooks']} runbooks, {stats['postmortems']} postmortems, {stats['errors']} errores.")
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingesta documentos en Weaviate")
    parser.add_argument("--force", action="store_true", help="Re-indexa todo borrando los existentes")
    parser.add_argument("--dir", default=DOCS_DIR, help="Directorio de docs (default: backend/docs/)")
    parser.add_argument("--scrape-github", nargs="+", help="Repositorios de GitHub a scrapeear (formato: owner/repo)")
    parser.add_argument("--scrape-statuspage", nargs="+", help="URLs de status pages a scrapeear")
    parser.add_argument("--skip-scrape", action="store_true", help="Omitir ingesta de documentos scrapeados")
    args = parser.parse_args()

    # Scraping de fuentes web si se solicita
    if args.scrape_github or args.scrape_statuspage:
        from app.services.scraper import scrape_github_repo, scrape_status_page, save_scraped_documents
        
        all_docs = []
        
        if args.scrape_github:
            for repo in args.scrape_github:
                print(f"\nScrapeando repositorio: {repo}")
                docs = scrape_github_repo(repo)
                print(f"  Encontrados {len(docs)} documentos")
                all_docs.extend(docs)
        
        if args.scrape_statuspage:
            for url in args.scrape_statuspage:
                print(f"\nScrapeando status page: {url}")
                docs = scrape_status_page(url)
                print(f"  Encontrados {len(docs)} incidentes")
                all_docs.extend(docs)
        
        if all_docs:
            output_dir = save_scraped_documents(all_docs)
            print(f"\nDocumentos scrapeados guardados en: {output_dir}")

    # Ingesta en Weaviate
    result = ingest_documents(docs_dir=args.dir, force=args.force)
    print(result)
