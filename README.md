# DevOps Incident Triage

Sistema inteligente de **clasificación, gestión y asignación de incidentes DevOps**. Utiliza un agente de IA (LLM local vía Ollama + LangGraph) y búsqueda vectorial (Weaviate/RAG) para analizar alertas, encontrar casos históricos similares y proponer fixes con aprobación humana.

<img width="1682" height="614" alt="Arquitectura" src="https://github.com/user-attachments/assets/088478a0-6e9c-44e4-9199-45153212e05e" />

---

## Stack Tecnologico

| Capa | Tecnologias |
|------|------------|
| **Frontend** | React 19, Vite 8, TypeScript, Tailwind CSS 3.4, React Router 7, Zustand |
| **Backend** | Python 3.10, FastAPI, SQLAlchemy, Pydantic v2, Uvicorn |
| **IA/Agent** | LangGraph, LangChain, ChatOllama (mistral), Langfuse (trazabilidad) |
| **MCP** | Model Context Protocol (FastMCP), langchain-mcp-adapters |
| **RAG** | Weaviate 1.27.0 (busqueda hibrida), embeddings via Ollama (all-MiniLM) |
| **Scraping** | requests, BeautifulSoup4, readability-lxml, markdownify |
| **Auth** | JWT (PyJWT), passlib + bcrypt 3.2.2 |
| **Base de datos** | PostgreSQL 15, Weaviate (vectores) |
| **Infra** | Docker Compose, hot reload |

---

## Arquitectura

<img width="1570" height="334" alt="DiagramaOrquestacion drawio" src="https://github.com/user-attachments/assets/f8df87d8-4d11-4b2f-8e22-7b9026f2c9dd" />

### Flujo del Agente de IA

```
START -> classify -> investigate -> propose_fix -> verify -> finish -> END
                                                         |
                                                    (error) -> handle_error -> END
```

1. **classify** - Clasifica severidad (critical/high/medium/low), equipo responsable e hipotesis inicial
2. **investigate** - Selecciona servicios sospechosos, busca runbooks e incidentes similares, ejecuta herramientas de diagnostico (logs, metricas, health checks, historial de deploys, alertas, queries SQL)
3. **propose_fix** - Propone pasos concretos de remedicion basados en runbooks. Siempre requiere aprobacion humana
4. **verify** - Define plan de monitoreo (metricas, ventana >=15 min, umbrales) y veredicto
5. **finish** - Genera resumen final con severidad, equipo, hipotesis, evidencia, fix, verificacion

### Caracteristicas del Agente

- **Fallback heuristico**: Si Ollama no esta disponible, cada nodo tiene respuestas por defecto para que el flujo no se rompa
- **Checkpoint en Postgres**: El estado del agente persiste entre mensajes (hipotesis, evidencia, checks pendientes)
- **Trazabilidad**: Integracion opcional con Langfuse para monitorear cada ejecucion

---

## Estructura del Proyecto

```
DevOps-Incident-Triage/
├── docker-compose.yml          # Orquestacion de servicios
├── .env.example                # Plantilla de variables de entorno
├── README.md
├── backend/
│   ├── main.py                 # Entrypoint FastAPI
│   ├── Dockerfile              # python:3.10-slim
│   ├── requirements.txt
│   ├── app/
│   │   ├── api/
│   │   │   ├── incidents.py    # Endpoints de incidentes, chat, approval
│   │   │   └── auth.py         # Registro, login, forgot/reset password
│   │   ├── ai/
│   │   │   ├── agent.py        # Grafo LangGraph (classify->investigate->...)
│   │   │   ├── tools.py        # 4 tools @tool (diagnostics + simulator)
│   │   │   └── langfuse_setup.py
│   │   ├── mcp/
│   │   │   ├── server.py       # FastMCP server (9 tools via stdio)
│   │   │   └── client.py       # MCP client con fallback
│   │   ├── services/
│   │   │   ├── incident.py     # CRUD + search + embedding
│   │   │   ├── ingest.py       # Pipeline RAG (markdown -> Weaviate)
│   │   │   ├── scraper.py      # GitHub scraper + Statuspage scraper
│   │   │   ├── auto_scrape.py  # Background auto-scraping
│   │   │   ├── simulator.py    # Servicios simulados (logs, metrics)
│   │   │   └── diagnostics.py  # Deployment history, health, alerts, SQL
│   │   ├── db/
│   │   │   ├── database.py     # SQLAlchemy engine
│   │   │   ├── models.py       # User, Incident, StatusHistory, AgentSession
│   │   │   └── weaviate_client.py  # Singleton Weaviate client
│   │   ├── core/
│   │   │   ├── security.py     # JWT + password hashing
│   │   │   └── deps.py         # get_current_user dependency
│   │   └── schemas/
│   │       └── incident.py     # Pydantic models
│   ├── docs/
│   │   ├── runbooks/           # 6 runbooks (markdown + YAML frontmatter)
│   │   └── postmortems/        # 2 postmortems
│   └── tests/                  # pytest (auth + incidents)
└── frontend/
    ├── src/
    │   ├── App.tsx             # Rutas: /login, /register, /dashboard, /incidents, /chat, /chat/:incidentId
    │   ├── api.ts              # fetch wrapper con Bearer token
    │   └── components/
    │       ├── Login.tsx
    │       ├── Register.tsx
    │       ├── ForgotPassword.tsx
    │       ├── Dashboard.tsx   # Metricas: totales, MTTR, por severidad/estado
    │       ├── Incidents.tsx   # Lista, filtros, busqueda, paginacion (20/page)
    │       └── Chat.tsx        # Agente + approval flow + historial
    ├── Dockerfile              # node:20-alpine
    └── package.json
```

---

## Prerrequisitos

- **Docker** y **Docker Compose** instalados
- **Ollama** corriendo en la maquina host con los modelos:
  ```bash
  ollama pull mistral          # LLM principal
  ollama pull all-minilm       # Embeddings
  ```
- **Git** (para clonar y para scraping de GitHub)

---

## Instalacion y Ejecucion

```bash
# 1. Clonar el repositorio
git clone https://github.com/Thomasggrisales/DevOps-Incident-Triage.git
cd DevOps-Incident-Triage

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env y generar un SECRET_KEY:
# python -c "import secrets; print(secrets.token_urlsafe(64))"

# 3. Levantar todo con Docker
docker compose up --build

# 4. Detener
docker compose down
# Para limpiar datos:
docker compose down -v
```

### Servicios y Puertos

| Servicio | URL | Descripcion |
|----------|-----|-------------|
| **Frontend** | http://localhost:5173 | Interfaz web (React + Vite) |
| **Backend API** | http://localhost:8000 | API REST (FastAPI) |
| **Swagger Docs** | http://localhost:8080/docs | Documentacion interactiva de la API |
| **Weaviate** | http://localhost:8080 | Base de datos vectorial |

---

## Variables de Entorno

| Variable | Requerida | Default | Descripcion |
|----------|-----------|---------|-------------|
| `POSTGRES_USER` | Si | - | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | Si | - | Contrasena de PostgreSQL |
| `POSTGRES_DB` | Si | - | Nombre de la base de datos |
| `DATABASE_URL` | Si | - | URL de conexion a Postgres |
| `SECRET_KEY` | Si | - | Clave secreta para JWT |
| `WEAVIATE_HOST` | No | `weaviate` | Host de Weaviate |
| `LANGFUSE_PUBLIC_KEY` | No | - | Clave publica de Langfuse (trazabilidad) |
| `LANGFUSE_SECRET_KEY` | No | - | Clave secreta de Langfuse |
| `LANGFUSE_HOST` | No | `https://cloud.langfuse.com` | Host de Langfuse |
| `AUTO_SCRAPE_ENABLED` | No | `false` | Auto-scraping al iniciar |
| `AUTO_SCRAPE_INTERVAL_HOURS` | No | `24` | Intervalo de re-scraping |
| `GITHUB_REPOS` | No | - | Repos a scrapeear (formato: `owner/repo`) |
| `STATUS_PAGES` | No | - | Status pages a scrapeear |

> **Nota:** Ollama debe correr en el host. El backend lo alcanza via `host.docker.internal:11434`.

---

## API Endpoints

### Autenticacion (`/auth`)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `POST` | `/auth/register` | Registrar usuario |
| `POST` | `/auth/login` | Iniciar sesion -> `{access_token, user}` |
| `POST` | `/auth/forgot-password` | Solicitar reset de contrasena |
| `POST` | `/auth/reset-password` | Cambiar contrasena con token |

### Incidentes (`/incidents`) - Requiere JWT

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `POST` | `/incidents/` | Crear incidente |
| `GET` | `/incidents/` | Listar incidentes (skip, limit) |
| `GET` | `/incidents/stats/` | Metricas del dashboard (totales, MTTR, por estado/severidad) |
| `GET` | `/incidents/search/?q=` | Busqueda semantica en Weaviate |
| `GET` | `/incidents/{id}` | Detalle de un incidente |
| `GET` | `/incidents/{id}/session` | Obtener/crear sesion del agente para un incidente |
| `POST` | `/incidents/chat/` | Chatear con el agente de triage |
| `POST` | `/incidents/approval/` | Aprobar/rechazar fix propuesto |
| `GET` | `/incidents/scrape/status` | Estado del auto-scraping |
| `POST` | `/incidents/scrape/run` | Ejecutar scraping manual |

### Chat del Agente

```json
POST /incidents/chat/
{
  "question": "El API Gateway esta devolviendo 504 en produccion",
  "session_id": "uuid-opcional",
  "incident_id": 8
}
```

**Respuesta:**
```json
{
  "session_id": "uuid",
  "answer": "Resumen del analisis...",
  "new_session": false,
  "state": {
    "severity": "critical",
    "owner_team": "platform",
    "hypothesis": "...",
    "fix": "...",
    "fix_risk": "medium",
    "needs_approval": true,
    "verification": "...",
    "verdict": "confirmed"
  }
}
```

### Aprobacion

```json
POST /incidents/approval/
{
  "session_id": "uuid",
  "decision": "approved",
  "comment": "Opcional"
}
```

---

## Herramientas MCP (Model Context Protocol)

El agente expone herramientas via un servidor FastMCP:

| Herramienta | Descripcion |
|-------------|-------------|
| `fetch_service_logs` | Logs simulados de un servicio |
| `fetch_service_metrics` | CPU, memoria, latencia, errores |
| `search_runbook` | Busqueda hibrida en base de conocimiento (Weaviate) |
| `search_similar_incidents` | Incidentes historicos similares |
| `update_incident_status` | Actualizar estado del incidente |
| `fetch_deployment_history` | Historial de deploys recientes |
| `check_service_health` | Estado del servicio (healthy/degraded/down) |
| `get_alert_history` | Alertas recientes del servicio |
| `query_database` | Query SQL de solo lectura |

### Ejecucion standalone del MCP server

```bash
cd backend
python -m app.mcp.server
```

---

## RAG (Retrieval-Augmented Generation)

### Pipeline de Ingesta

1. **Documentos**: Markdown con YAML frontmatter (`title`, `applies_to`, `severity`, `symptoms`)
   - `backend/docs/runbooks/` - 6 runbooks (api-gateway-5xx, auth-jwt, high-latency, postgres-pool, redis-cache, worker-oom)
   - `backend/docs/postmortems/` - 2 postmortems
2. **Scraping**: GitHub repos y Statuspage.io
   - Scraped docs se guardan en `backend/.scraper_cache/`
3. **Chunking**: ~1500 chars, 200 overlap,-aware
4. **Embeddings**: Ollama `all-MiniLM` (local)
5. **Almacenamiento**: Weaviate collections `Runbook` e `Incident` (busqueda hibrida)

### CLI de Ingesta

```bash
cd backend

# Ingesta basica
python -m app.services.ingest

# Con scraping de GitHub
python -m app.services.ingest --scrape-github dfds/postmortems

# Con scraping de status pages
python -m app.services.ingest --scrape-statuspage https://www.githubstatus.com

# Usar API de GitHub en vez de git clone
python -m app.services.ingest --scrape-github dfds/postmortems --scrape-method api

# Forzar re-indexacion
python -m app.services.ingest --force
```

---

## Frontend

### Rutas

| Ruta | Componente | Descripcion |
|------|------------|-------------|
| `/login` | Login | Inicio de sesion |
| `/register` | Register | Registro de usuario |
| `/forgot-password` | ForgotPassword | Recuperacion de contrasena |
| `/dashboard` | Dashboard | Metricas: totales, MTTR, por severidad/estado |
| `/incidents` | Incidents | Lista con filtros, busqueda y paginacion (20/page) |
| `/chat` | Chat | Nuevo incidente via chat |
| `/chat/:incidentId` | Chat | Chat con incidente existente (carga historial + sesion) |

### Funcionalidades

- **Dashboard**: Metricas en tiempo real (total, activos, resueltos, criticos, MTTR, por severidad/estado)
- **Incidents**: Filtros por estado, busqueda por titulo/ID, paginacion con 20 items por pagina
- **Chat**: Agente de triage con aprobacion de fixes (aprobar/rechazar), historial persistente
- **Approval Flow**: Botones de aprobar/rechazar que actualizan el estado del incidente

---

## Testing

### Backend (pytest)

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

### Frontend (vitest)

```bash
cd frontend
npm install
npm run test
```

---

## Modelos de Datos

### User
- `id`, `email` (unique), `hashed_password`, `name`, `role` (admin/devops), `is_active`, `created_at`

### Incident
- `id`, `title`, `description`, `source`, `severity` (critical/high/medium/low/pending), `status` (open/investigating/resolved), `created_at`

### StatusHistory
- `id`, `incident_id` (FK), `old_status`, `new_status`, `changed_at`, `changed_by` (System_AI/human_operator)

### AgentSession
- `id` (UUID), `user_id`, `incident_id`, `title`, `status` (active/closed), `conversation` (JSON), `created_at`, `updated_at`

---

## Licencia

Proyecto academico - DevOps Incident Triage
