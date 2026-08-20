"""
Tarea programada para mantener actualizados los documentos de Weaviate.

Scrapea fuentes configuradas periódicamente y re-indexa en Weaviate.
"""
import os
import time
import threading
from datetime import datetime

# Fuentes configuradas por defecto (se pueden override con variables de entorno)
DEFAULT_GITHUB_REPOS = [
    "dfds/postmortems",
]
DEFAULT_STATUS_PAGES = [
    "https://www.githubstatus.com",
]

_auto_scrape_enabled = os.getenv("AUTO_SCRAPE_ENABLED", "true").lower() == "true"
_auto_scrape_interval = int(os.getenv("AUTO_SCRAPE_INTERVAL_HOURS", "24"))
_auto_scrape_running = False


def run_auto_scrape(force: bool = False) -> dict:
    """
    Ejecuta el scrape completo de todas las fuentes configuradas.
    
    Args:
        force: Si True, re-indexa todo aunque ya existan datos.
    
    Returns:
        dict con estadísticas del scrape.
    """
    global _auto_scrape_running
    
    if _auto_scrape_running:
        print("[auto-scrape] Ya está en ejecución, omitiendo.")
        return {"status": "skipped", "reason": "already_running"}
    
    _auto_scrape_running = True
    start_time = time.time()
    
    try:
        from app.services.scraper import scrape_github_repo, scrape_status_page, save_scraped_documents
        from app.services.ingest import ingest_documents, DOCS_DIR
        
        # Leer fuentes de variables de entorno o usar defaults
        github_repos = os.getenv("GITHUB_REPOS", "").split(",") if os.getenv("GITHUB_REPOS") else DEFAULT_GITHUB_REPOS
        status_pages = os.getenv("STATUS_PAGES", "").split(",") if os.getenv("STATUS_PAGES") else DEFAULT_STATUS_PAGES
        
        # Limpiar strings vacíos
        github_repos = [r.strip() for r in github_repos if r.strip()]
        status_pages = [s.strip() for s in status_pages if s.strip()]
        
        print(f"\n{'='*60}")
        print(f"[auto-scrape] Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Repos GitHub: {github_repos}")
        print(f"  Status pages: {status_pages}")
        print(f"{'='*60}\n")
        
        all_docs = []
        
        # Scrapear repos de GitHub
        for repo in github_repos:
            try:
                print(f"[auto-scrape] Scrapeando repo: {repo}")
                docs = scrape_github_repo(repo, method="git")
                print(f"  Encontrados {len(docs)} documentos")
                all_docs.extend(docs)
            except Exception as e:
                print(f"  [ERROR] Error scrapeando {repo}: {e}")
        
        # Scrapear status pages
        for url in status_pages:
            try:
                print(f"[auto-scrape] Scrapeando status page: {url}")
                docs = scrape_status_page(url)
                print(f"  Encontrados {len(docs)} incidentes")
                all_docs.extend(docs)
            except Exception as e:
                print(f"  [ERROR] Error scrapeando {url}: {e}")
        
        # Guardar documentos scrapeados
        if all_docs:
            output_dir = save_scraped_documents(all_docs)
            print(f"\n[auto-scrape] {len(all_docs)} documentos guardados en: {output_dir}")
        
        # Re-ingerir en Weaviate
        print("\n[auto-scrape] Ingeriendo en Weaviate...")
        stats = ingest_documents(force=force)
        
        elapsed = time.time() - start_time
        result = {
            "status": "completed",
            "scraped": len(all_docs),
            "ingested": stats,
            "elapsed_seconds": round(elapsed, 1),
            "timestamp": datetime.now().isoformat(),
        }
        
        print(f"\n[auto-scrape] Completado en {elapsed:.1f}s")
        print(f"  Scrapeados: {len(all_docs)}")
        print(f"  Ingeridos: {stats}")
        
        return result
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[auto-scrape] Error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "elapsed_seconds": round(elapsed, 1),
            "timestamp": datetime.now().isoformat(),
        }
    finally:
        _auto_scrape_running = False


def _auto_scrape_loop(interval_hours: int):
    """Loop infinito que ejecuta auto-scrape cada X horas."""
    # Esperar 60s después del startup para no sobrecargar
    time.sleep(60)
    
    while True:
        try:
            run_auto_scrape(force=False)
        except Exception as e:
            print(f"[auto-scrape] Error en loop: {e}")
        
        # Dormir hasta la siguiente ejecución
        sleep_seconds = interval_hours * 3600
        print(f"[auto-scrape] Próxima ejecución en {interval_hours}h")
        time.sleep(sleep_seconds)


def start_auto_scrape_background():
    """Inicia el thread de auto-scrape en background (llamar en startup)."""
    if not _auto_scrape_enabled:
        print("[auto-scrape] Deshabilitado (AUTO_SCRAPE_ENABLED=false)")
        return
    
    print(f"[auto-scrape] Habilitado (cada {_auto_scrape_interval}h)")
    thread = threading.Thread(
        target=_auto_scrape_loop,
        args=(_auto_scrape_interval,),
        daemon=True,
        name="auto-scrape",
    )
    thread.start()
    print("[auto-scrape] Thread iniciado en background.")


def is_auto_scrape_running() -> bool:
    """Indica si hay un scrape en ejecución."""
    return _auto_scrape_running


def get_auto_scrape_config() -> dict:
    """Devuelve la configuración actual del auto-scrape."""
    return {
        "enabled": _auto_scrape_enabled,
        "interval_hours": _auto_scrape_interval,
        "running": _auto_scrape_running,
        "github_repos": os.getenv("GITHUB_REPOS", "").split(",") if os.getenv("GITHUB_REPOS") else DEFAULT_GITHUB_REPOS,
        "status_pages": os.getenv("STATUS_PAGES", "").split(",") if os.getenv("STATUS_PAGES") else DEFAULT_STATUS_PAGES,
    }
