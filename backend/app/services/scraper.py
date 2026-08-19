"""
Servicio de web scraping para obtener documentación DevOps de fuentes públicas.

Fuentes soportadas:
- GitHub repos (README, docs/, postmortems, runbooks)
- Status pages (Statuspage.io, Cachet, etc.)

Uso CLI (desde backend/):
    python -m app.services.scraper --source github --repo dastergon/postmortem-repository
    python -m app.services.scraper --source statuspage --url https://status.datadoghq.com
"""
import json
import os
import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Directorio temporal para contenido descargado
SCRAPER_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".scraper_cache")
os.makedirs(SCRAPER_CACHE_DIR, exist_ok=True)


class GitHubScraper:
    """Scrapea repos de GitHub para obtener runbooks, postmortems y guías."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self.base_url = "https://api.github.com"
    
    def get_repo_contents(self, repo: str, path: str = "") -> list[dict]:
        """Obtiene el contenido de un directorio del repositorio."""
        if path:
            url = f"{self.base_url}/repos/{repo}/contents/{path}"
        else:
            url = f"{self.base_url}/repos/{repo}/contents"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_file_content(self, repo: str, file_path: str) -> str:
        """Obtiene el contenido de un archivo específico."""
        url = f"{self.base_url}/repos/{repo}/contents/{file_path}"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # GitHub devuelve contenido en base64
        import base64
        if "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8")
        return ""
    
    def scrape_repo(self, repo: str, paths: list[str] = None) -> list[dict]:
        """
        Scrapea un repositorio completo buscando documentos relevantes.
        
        Args:
            repo: Repositorio en formato "owner/repo"
            paths: Rutas específicas a scrapear (default: ["", "docs", "runbooks", "postmortems"])
        
        Returns:
            Lista de documentos encontrados
        """
        if paths is None:
            paths = ["", "docs", "runbooks", "postmortems", "incidents"]
        
        documents = []
        visited_files = set()
        
        for path in paths:
            try:
                contents = self.get_repo_contents(repo, path)
                self._process_contents(repo, contents, documents, visited_files)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"  [ERROR] Error accediendo a {path} en {repo}: {e}")
        
        return documents
    
    def _process_contents(self, repo: str, contents: list[dict], documents: list[dict], visited: set):
        """Procesa recursivamente el contenido del repositorio."""
        for item in contents:
            if item["type"] == "file":
                # Procesar archivos markdown y texto
                if item["name"].endswith((".md", ".mdx", ".txt", ".rst")):
                    # Ignorar archivos de bajo valor
                    if item["name"].lower() in ["readme.md", "license.md", "license", "contributing.md", ".gitignore"]:
                        continue
                    if item["download_url"] and item["download_url"] not in visited:
                        visited.add(item["download_url"])
                        try:
                            content = self.get_file_content(repo, item["path"])
                            if content:
                                doc = self._parse_document(content, item["name"], item["path"], repo)
                                if doc:
                                    documents.append(doc)
                                    print(f"  [OK] {item['path']}")
                            time.sleep(0.2)
                        except Exception as e:
                            print(f"  [ERROR] Error leyendo {item['path']}: {e}")
            
            elif item["type"] == "dir":
                # Explorar subdirectorios relevantes
                try:
                    sub_contents = self.get_repo_contents(repo, item["path"])
                    self._process_contents(repo, sub_contents, documents, visited)
                    time.sleep(0.2)
                except Exception as e:
                    print(f"  [ERROR] Error accediendo a directorio {item['path']}: {e}")
    
    def _parse_document(self, content: str, filename: str, path: str, repo: str) -> Optional[dict]:
        """Parsea un documento markdown y extrae metadatos."""
        if len(content.strip()) < 100:  # Ignorar archivos muy cortos
            return None
        
        # Extraer título del contenido
        title = self._extract_title(content, filename)
        
        # Detectar tipo de documento
        doc_type = self._detect_doc_type(content, path)
        
        # Extraer síntomas si existen
        symptoms = self._extract_symptoms(content)
        
        # Extraer severidad si existe
        severity = self._extract_severity(content)
        
        return {
            "title": title,
            "content": content,
            "source": "github",
            "repo": repo,
            "path": path,
            "doc_type": doc_type,
            "symptoms": symptoms,
            "severity": severity,
            "filename": filename,
        }
    
    def _extract_title(self, content: str, filename: str) -> str:
        """Extrae el título del contenido markdown."""
        # Buscar encabezado H1
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # Usar nombre del archivo sin extensión
        return os.path.splitext(filename)[0].replace("-", " ").replace("_", " ").title()
    
    def _detect_doc_type(self, content: str, path: str) -> str:
        """Detecta el tipo de documento."""
        content_lower = content.lower()
        path_lower = path.lower()
        
        if "postmortem" in path_lower or "incident" in path_lower:
            return "postmortem"
        if "runbook" in path_lower or "troubleshoot" in path_lower:
            return "runbook"
        
        # Detectar por contenido
        if any(term in content_lower for term in ["postmortem", "incident report", "what happened"]):
            return "postmortem"
        if any(term in content_lower for term in ["runbook", "troubleshooting", "steps to resolve"]):
            return "runbook"
        
        return "runbook"  # Default
    
    def _extract_symptoms(self, content: str) -> str:
        """Extrae síntomas del documento."""
        symptoms = []
        
        # Buscar secciones de síntomas
        patterns = [
            r"#+\s*symptoms?\s*\n(.*?)(?=\n#|\Z)",
            r"#+\s*what went wrong\s*\n(.*?)(?=\n#|\Z)",
            r"#+\s*indicators?\s*\n(.*?)(?=\n#|\Z)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Limpiar y extraer puntos
                lines = [line.strip() for line in match.split("\n") if line.strip()]
                symptoms.extend([line.lstrip("- *•") for line in lines if line.startswith(("- ", "* ", "• "))])
        
        return "; ".join(symptoms[:5]) if symptoms else ""
    
    def _extract_severity(self, content: str) -> str:
        """Extrae severidad del documento."""
        content_lower = content.lower()
        
        if any(term in content_lower for term in ["critical", "severe", "p0", "p1"]):
            return "critical"
        if any(term in content_lower for term in ["high", "major", "p2"]):
            return "high"
        if any(term in content_lower for term in ["medium", "moderate", "p3"]):
            return "medium"
        
        return "low"


class StatusPageScraper:
    """Scrapea status pages para obtener incidentes históricos."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; DevOpsIncidentTriage/1.0)"
        })
    
    def scrape_statuspage(self, url: str) -> list[dict]:
        """
        Scrapea una página de status (Statuspage.io).
        
        Args:
            url: URL de la página de status (ej: https://status.datadoghq.com)
        
        Returns:
            Lista de incidentes encontrados
        """
        documents = []
        
        # Primero intentar la API de Statuspage.io (más confiable)
        api_docs = self._try_statuspage_api(url)
        documents.extend(api_docs)
        
        if documents:
            return documents
        
        # Fallback a scraping HTML si la API no está disponible
        try:
            history_url = f"{url.rstrip('/')}/history"
            response = self.session.get(history_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Buscar incidentes en diferentes estructuras comunes
            incident_elements = (
                soup.find_all("div", class_=re.compile(r"incident")) or
                soup.find_all("article") or
                soup.find_all("div", {"data-id": True})
            )
            
            for element in incident_elements[:20]:
                try:
                    doc = self._parse_statuspage_incident(element, url)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    print(f"  [ERROR] Error parseando incidente: {e}")
            
        except Exception as e:
            print(f"  [ERROR] Error scrapeando status page {url}: {e}")
        
        return documents
    
    def _parse_statuspage_incident(self, element, base_url: str) -> Optional[dict]:
        """Parsea un elemento de incidente de Statuspage."""
        # Buscar título
        title_elem = element.find(["h3", "h4", "strong", "a"])
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        if not title:
            return None
        
        # Buscar descripción
        desc_elem = element.find("p") or element.find("div", class_="")
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Buscar fecha
        time_elem = element.find("time")
        date_str = time_elem.get("datetime", "") if time_elem else ""
        
        # Buscar estado
        status_elem = element.find(class_=re.compile(r"status|impact"))
        status = status_elem.get_text(strip=True) if status_elem else "resolved"
        
        # Detectar componentes afectados
        components = []
        comp_elems = element.find_all(class_=re.compile(r"component"))
        for comp in comp_elems:
            components.append(comp.get_text(strip=True))
        
        return {
            "title": title,
            "content": f"## Incidente\n\n**Fecha:** {date_str}\n**Estado:** {status}\n\n{description}",
            "source": "statuspage",
            "doc_type": "postmortem",
            "symptoms": "; ".join(components) if components else "",
            "severity": self._map_status_to_severity(status),
            "date": date_str,
            "status": status,
        }
    
    def _try_statuspage_api(self, base_url: str) -> list[dict]:
        """Intenta usar la API de Statuspage.io si está disponible."""
        documents = []
        
        try:
            # Intentar endpoint de incidentes directamente
            api_url = f"{base_url.rstrip('/')}/api/v2/incidents.json"
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for incident in data.get("incidents", []):
                    doc = {
                        "title": incident.get("name", "Incidente sin título"),
                        "content": self._format_api_incident(incident),
                        "source": "statuspage_api",
                        "doc_type": "postmortem",
                        "symptoms": "; ".join([comp.get("name", "") for comp in incident.get("components", [])]),
                        "severity": self._map_impact_to_severity(incident.get("impact", "")),
                        "date": incident.get("created_at", ""),
                        "status": incident.get("status", ""),
                    }
                    documents.append(doc)
            
            if not documents:
                # Fallback a summary.json
                api_url = f"{base_url.rstrip('/')}/api/v2/summary.json"
                response = self.session.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for incident in data.get("incidents", []):
                        doc = {
                            "title": incident.get("name", "Incidente sin título"),
                            "content": self._format_api_incident(incident),
                            "source": "statuspage_api",
                            "doc_type": "postmortem",
                            "symptoms": "; ".join([comp.get("name", "") for comp in incident.get("components", [])]),
                            "severity": self._map_impact_to_severity(incident.get("impact", "")),
                            "date": incident.get("created_at", ""),
                            "status": incident.get("status", ""),
                        }
                        documents.append(doc)
        
        except Exception:
            pass  # API no disponible
        
        return documents
    
    def _format_api_incident(self, incident: dict) -> str:
        """Formatea un incidente de la API."""
        parts = [
            f"## {incident.get('name', 'Incidente')}\n",
            f"**Fecha:** {incident.get('created_at', 'N/A')}",
            f"**Estado:** {incident.get('status', 'N/A')}",
            f"**Impacto:** {incident.get('impact', 'N/A')}",
            "",
        ]
        
        # Agregar body si existe
        body = incident.get("body", "")
        if body:
            parts.append(body)
            parts.append("")
        
        # Agregar actualizaciones del incidente
        updates = incident.get("incident_updates", [])
        if updates:
            parts.append("### Actualizaciones\n")
            for update in updates[:5]:  # Limitar a 5 actualizaciones más recientes
                update_body = update.get("body", "")
                update_status = update.get("status", "")
                update_date = update.get("created_at", "")
                if update_body:
                    parts.append(f"**{update_date}** ({update_status}):")
                    parts.append(update_body)
                    parts.append("")
        
        return "\n".join(parts)
    
    def _map_status_to_severity(self, status: str) -> str:
        """Mapea estado de Statuspage a severidad."""
        status_lower = status.lower()
        if "critical" in status_lower or "major" in status_lower:
            return "critical"
        if "minor" in status_lower:
            return "medium"
        return "low"
    
    def _map_impact_to_severity(self, impact: str) -> str:
        """Mapea impacto de Statuspage API a severidad."""
        impact_lower = impact.lower()
        if "critical" in impact_lower:
            return "critical"
        if "major" in impact_lower:
            return "high"
        if "minor" in impact_lower:
            return "medium"
        return "low"


def scrape_github_repo(repo: str, token: Optional[str] = None) -> list[dict]:
    """Función de conveniencia para scrapeear un repositorio de GitHub."""
    scraper = GitHubScraper(token=token)
    return scraper.scrape_repo(repo)


def scrape_status_page(url: str) -> list[dict]:
    """Función de conveniencia para scrapeear una status page."""
    scraper = StatusPageScraper()
    return scraper.scrape_statuspage(url)


def save_scraped_documents(documents: list[dict], output_dir: str = None) -> str:
    """Guarda documentos scrapeados en formato markdown para ingesta."""
    if output_dir is None:
        output_dir = os.path.join(SCRAPER_CACHE_DIR, "scraped_docs")
    
    os.makedirs(output_dir, exist_ok=True)
    
    saved_files = []
    for doc in documents:
        # Crear nombre de archivo seguro
        safe_title = re.sub(r'[^\w\s-]', '', doc["title"])[:50]
        safe_title = re.sub(r'[-\s]+', '-', safe_title).strip('-')
        filename = f"{doc['source']}_{safe_title}.md"
        filepath = os.path.join(output_dir, filename)
        
        # Crear contenido markdown con frontmatter
        frontmatter = f"""---
title: "{doc['title']}"
source: "{doc['source']}"
doc_type: "{doc['doc_type']}"
symptoms: "{doc.get('symptoms', '')}"
severity: "{doc.get('severity', 'medium')}"
---

"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter + doc["content"])
        
        saved_files.append(filepath)
    
    return output_dir


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Web scraping para documentación DevOps")
    parser.add_argument("--source", choices=["github", "statuspage"], required=True,
                        help="Tipo de fuente a scrapeear")
    parser.add_argument("--repo", help="Repositorio de GitHub (formato: owner/repo)")
    parser.add_argument("--url", help="URL de la status page")
    parser.add_argument("--output", help="Directorio de salida para documentos")
    
    args = parser.parse_args()
    
    if args.source == "github" and args.repo:
        print(f"Scrapeando repositorio: {args.repo}")
        docs = scrape_github_repo(args.repo)
        print(f"Encontrados {len(docs)} documentos")
        
        if docs:
            output_dir = save_scraped_documents(docs, args.output)
            print(f"Documentos guardados en: {output_dir}")
    
    elif args.source == "statuspage" and args.url:
        print(f"Scrapeando status page: {args.url}")
        docs = scrape_status_page(args.url)
        print(f"Encontrados {len(docs)} incidentes")
        
        if docs:
            output_dir = save_scraped_documents(docs, args.output)
            print(f"Documentos guardados en: {output_dir}")
    
    else:
        print("Error: Especifica --repo para GitHub o --url para status pages")
