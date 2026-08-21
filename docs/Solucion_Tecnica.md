# DevOps Incident Triage Copilot — Documento de Solución

## Contexto del Proyecto

El objetivo era construir un **copilot agéntico de IA** que asista a ingenieros on-call en el triage de incidentes de un sistema de producción simulado. Dado un flujo de alertas y logs, el agente debe:

1. Planificar una secuencia de pasos (clasificar, investigar, proponer fix, verificar)
2. Invocar herramientas (API de métricas/logs, búsqueda en runbooks/KB)
3. Mantener estado a lo largo del incidente (hipótesis, acciones tomadas, checks pendientes)
4. Manejar errores comunes con gracia
5. Registrar todas las decisiones y llamadas a herramientas para inspección posterior
6. Proveer una interfaz web/chat para iniciar sesiones, ver el razonamiento del agente y aprobar/rechazar acciones de riesgo

---

## 1. Mapeo de Requisitos a Solución

| # | Requisito Original | Cómo se implementó | Archivos clave |
|---|-------------------|-------------------|----------------|
| 1 | **Copilot agéntico para triage** | Agente LangGraph con pipeline de 5 nodos (classify → investigate → propose_fix → verify → finish) que procesa alertas de forma autónoma | `backend/app/ai/agent.py` |
| 2 | **Planificar secuencia de pasos** | Grafo de estado con nodos secuenciales. Cada nodo ejecuta una fase del triage y pasa el resultado al siguiente | `backend/app/ai/agent.py:264-284` (StateGraph) |
| 3 | **Invocar herramientas (métricas, logs, runbooks)** | 9 herramientas disponibles vía MCP y directamente: fetch_service_logs, fetch_service_metrics, search_runbook, search_similar_incidents, etc. | `backend/app/mcp/server.py`, `backend/app/ai/tools.py` |
| 4 | **Mantener estado del incidente** | PostgresSaver como checkpointer de LangGraph. El estado (hipótesis, severidad, evidencia, fix, verificación) persiste entre mensajes | `backend/app/ai/agent.py:68` (checkpointer), `backend/app/db/models.py:48` (AgentSession con conversation JSON) |
| 5 | **Manejar errores con gracia** | Fallback heurístico en cada nodo: si Ollama no responde, cada nodo genera respuestas por defecto para que el flujo no se rompa | `backend/app/ai/agent.py` (cada nodo tiene try/except con defaults) |
| 6 | **Registrar decisiones y tool calls** | Integración con Langfuse para trazabilidad. Cada ejecución del agente se registra con metadata (incident_id, source, session_id) | `backend/app/ai/langfuse_setup.py`, `backend/app/api/incidents.py:286-293` |
| 7 | **Interfaz web con razonamiento y aprobación** | React + Vite con chat, panel de razonamiento del agente, botones de aprobar/rechazar fix, historial de conversación persistente | `frontend/src/components/Chat.tsx`, `frontend/src/components/Incidents.tsx` |

---

## 2. Decisiones de Stack Tecnológico

### Stack original sugerido vs. Stack implementado

| Capa | Sugerido | Implementado | Justificación |
|------|----------|--------------|---------------|
| **UI** | Chainlit/Streamlit/Gradio | **React + Vite + Tailwind** | UI customizada con diseño profesional, paginación, filtros, dashboard con métricas. Chainlit/Streamlit son limitados para UIs personalizadas |
| **Agente** | LangGraph/CrewAI | **LangGraph** | LangGraph ofrece control fino sobre el grafo de estado, checkpointing en Postgres, y soporte nativo para herramientas. CrewAI es más adecuado para multi-agente |
| **LLM** | Cualquier LLM | **Ollama (mistral)** | LLM local, sin costo de API, sin latencia de red, sin dependencia externa.妙妙妙妙妙 |
| **Observabilidad** | Langfuse | **Langfuse** | Integración directa con LangChain/LangGraph. Registra traces, tool calls, y decisiones del agente |
| **Vector DB** | ChromaDB/Weaviate/FAISS | **Weaviate 1.27.0** | Búsqueda híbrida (vectorial + keyword), soporte nativo para hybrid(), escalabilidad, API REST completa |
| **Deploy** | Docker/Docker Compose | **Docker Compose** | 4 servicios: Postgres, Weaviate, Backend, Frontend. Hot reload para desarrollo |

### Otras decisiones clave

- **FastAPI** sobre Django/Flask: async nativo, Pydantic v2 integrado, auto-generación de Swagger
- **SQLAlchemy** sobre raw SQL: ORM para mapeo de modelos, migraciones, relaciones
- **Pydantic v2** sobre v1: validación más estricta, mejor rendimiento
- **bcrypt==3.2.2** (pinneado): `bcrypt>=4.0` rompe passlib

---

## 3. Arquitectura del Agente

### Grafo de Estado (LangGraph)

```python
# backend/app/ai/agent.py
StateGraph(IncidentState)
    .add_node("classify", classify_node)
    .add_node("investigate", investigate_node)
    .add_node("propose_fix", propose_fix_node)
    .add_node("verify", verify_node)
    .add_node("finish", finish_node)
    .add_node("handle_error", handle_error_node)
    .add_edge(START, "classify")
    .add_edge("classify", "investigate")
    .add_edge("investigate", "propose_fix")
    .add_edge("propose_fix", "verify")
    .add_edge("verify", "finish")
    .add_edge("finish", END)
    .add_edge("handle_error", END)
```

### Estado Compartido (IncidentState)

```python
class IncidentState(TypedDict):
    incident: dict          # Datos del incidente
    messages: list[dict]    # Historial de conversación
    hypothesis: str         # Hipótesis actual del agente
    severity: str           # critical/high/medium/low
    owner_team: str         # Equipo responsable
    actions_taken: list     # Acciones ya ejecutadas
    pending_checks: list    # Checks que faltan por verificar
    evidence: list          # Evidencia recolectada (tool calls)
    plan: list              # Plan de investigación
    fix: str                # Fix propuesto
    fix_risk: str           # Riesgo del fix (low/medium/high)
    needs_approval: bool    # Si requiere aprobación humana
    verification: str       # Plan de verificación
    verdict: str            # confirmed/uncertain/refuted
    summary: str            # Resumen final
    error: str              # Error si falló
    error_count: int        # Contador de errores
```

### Flujo de Ejecución

1. **classify**: El LLM analiza la alerta y clasifica severidad + equipo + hipótesis inicial
2. **investigate**: El agente selecciona hasta 3 servicios sospechosos, busca runbooks e incidentes similares en Weaviate, ejecuta herramientas de diagnóstico (logs, métricas, health checks, historial de deploys, alertas, queries SQL)
3. **propose_fix**: Basado en runbooks cuando están disponibles, propone pasos concretos. Siempre setting `needs_approval = True`
4. **verify**: Define plan de monitoreo (métricas, ventana ≥15 min, umbrales) y veredicto
5. **finish**: Genera resumen final estructurado

---

## 4. Persistencia de Estado

### Checkpointing en Postgres

```python
# backend/app/ai/agent.py
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
agent_graph = workflow.compile(checkpointer=checkpointer)
```

- **PostgresSaver** almacena el estado completo del grafo después de cada nodo
- Al reanudar una conversación, LangGraph carga el checkpoint y reanuda desde donde quedó
- Si Postgres no está disponible, degrada a MemorySaver (en memoria)

### Modelo AgentSession

```python
# backend/app/db/models.py
class AgentSession(Base):
    __tablename__ = "agent_sessions"
    id = Column(String, primary_key=True)  # UUID
    incident_id = Column(Integer)          # FK a Incident
    conversation = Column(JSON)            # Historial de mensajes
    status = Column(String, default="active")
```

- Cada sesión está vinculada a un incidente
- La conversación se persiste como JSON
- El agente puede recuperar contexto de sesiones anteriores

---

## 5. Invocación de Herramientas

### Doble camino: MCP + Directo

```
Agente LangGraph
    ├── MCP Client (async) → FastMCP Server (stdio)
    │       └── 9 herramientas expuestas
    └── Fallback: implementaciones directas en tools.py
```

**MCP (Model Context Protocol)**:
- Servidor FastMCP en `backend/app/mcp/server.py`
- Cliente async en `backend/app/mcp/client.py`
- Comunicación vía stdio (sin red)

**Fallback directo**:
- Si MCP no está disponible, el agente usa implementaciones directas en `tools.py`
- Misma funcionalidad, sin dependencia del servidor MCP

### Herramientas disponibles

| Herramienta | Fuente | Descripción |
|-------------|--------|-------------|
| `fetch_service_logs` | Simulator | Logs simulados con timestamps |
| `fetch_service_metrics` | Simulator | CPU, memoria, latencia, errores |
| `search_runbook` | Weaviate | Búsqueda híbrida en runbooks |
| `search_similar_incidents` | Weaviate | Incidentes históricos similares |
| `update_incident_status` | PostgreSQL | Actualizar estado del incidente |
| `fetch_deployment_history` | Simulator | Historial de deploys recientes |
| `check_service_health` | Simulator | Estado: healthy/degraded/down |
| `get_alert_history` | Simulator | Alertas recientes |
| `query_database` | PostgreSQL | Query SQL de solo lectura |

---

## 6. Manejo de Errores

### Fallback Heurístico

Cada nodo del agente tiene un bloque try/except que genera respuestas por defecto si el LLM falla:

```python
def classify_node(state):
    try:
        # Intentar generar clasificación con el LLM
        response = llm.invoke(prompt)
        parsed = parse_json(response)
        return {"severity": parsed["severity"], ...}
    except Exception:
        # Fallback: usar valores por defecto
        return {
            "severity": "medium",
            "owner_team": "operations",
            "hypothesis": "Análisis pendiente - modo degradado",
        }
```

### Degradación del MCP

Si el servidor MCP no está disponible:
1. El agente detecta la falla
2. Usa implementaciones directas en `tools.py`
3. El flujo continúa sin interrupciones

### Degradación de Langfuse

Si las claves de Langfuse no están configuradas:
1. `get_langfuse_handler()` retorna `None`
2. El agente ejecuta sin callbacks de trazabilidad
3. La funcionalidad principal no se afecta

---

## 7. Observabilidad con Langfuse

### Integración

```python
# backend/app/ai/langfuse_setup.py
from langfuse.callback import CallbackHandler

def get_langfuse_handler():
    if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
        return CallbackHandler(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
    return None  # Degradación silenciosa
```

### Qué se registra

- **Trace completa**: Cada ejecución del agente (classify → investigate → → verify → finish)
- **Tool calls**: Cada invocación de herramienta con inputs y outputs
- **Llamadas al LLM**: Prompts, respuestas, tokens usados
- **Metadata**: incident_id, source, session_id, tags
- **Errores**: Excepciones capturadas en cada nodo

### Cómo se usa

```python
# backend/app/api/incidents.py
with trace_context(
    langfuse_handler,
    trace_name="incident-triage-agent",
    session_id=session.id,
    metadata={"incident_id": incident.id, "source": incident.source},
    tags=["incident-triage", "langgraph"],
):
    result = agent_graph.invoke(initial_state, config=config)
```

---

## 8. Interfaz Web — Flujo de Aprobación

### Flujo completo

```
Usuario ingresa alerta en Chat
    ↓
Agente clasifica, investiga, propone fix
    ↓
Frontend recibe respuesta con needs_approval: true
    ↓
Se muestra card de aprobación con fix y riesgo
    ↓
Usuario hace click en "Aprobar" o "Rechazar"
    ↓
Frontend POST /incidents/approval/ con decisión
    ↓
Backend actualiza estado del incidente:
  - Aprobado → status = "resolved"
  - Rechazado → status = "open"
    ↓
Se registra en StatusHistory (changed_by: "human_operator")
    ↓
Se agrega línea a la conversación: "[DECISIÓN HUMANA]..."
```

### Persistencia del estado de aprobación

- Los campos `needs_approval`, `fix`, `fix_risk` se guardan en cada mensaje del agente en la conversación JSON
- Al recargar la página o navegar desde la lista de incidentes, el historial se reconstruye con estos campos
- Los botones de aprobar/rechazar aparecen si el fix está pendiente

### Navegación incidente → chat

- `GET /incidents/{id}/session` retorna la sesión existente o crea una nueva
- El chat carga el historial completo y muestra el header del incidente (título, severidad, estado)
- Al enviar mensajes dentro de un incidente existente, se envía `incident_id` al backend para que no detecte el mensaje como un incidente nuevo

---

## 9. RAG (Retrieval-Augmented Generation)

### Pipeline de ingesta

```
Documentos Markdown (runbooks/postmortems)
    ↓
YAML frontmatter (title, applies_to, severity, symptoms)
    ↓
Chunking (~1500 chars, 200 overlap, paragraph-aware)
    ↓
Embeddings via Ollama (all-MiniLM)
    ↓
Almacenamiento en Weaviate (collections: Runbook, Incident)
    ↓
Búsqueda híbrida (vectorial + keyword) con alpha=0.7
```

### Scraping de fuentes externas

- **GitHub**: Clona repositorios de postmortems (ej: `dfds/postmortems`)
- **Statuspage.io**: API de status pages públicas (ej: `githubstatus.com`)
- **Auto-scraping**: Background thread que re-scrapea cada N horas
- **Cache**: Documentos scraped se guardan en `backend/.scraper_cache/`

### Búsqueda en el agente

```python
# El agente busca runbooks e incidentes similares
search_runbook(query="API Gateway 504 error", limit=3)
search_similar_incidents(query="high latency payments api", limit=3)
```

- Búsqueda **híbrida** (vectorial + keyword) con `HybridFusion.RELATIVE_SCORE`
- **Alpha = 0.7** (70% vectorial, 30% keyword)
- Resultados priorizados por relevancia semántica

---

## 10. Simulación del Sistema de Producción

### Servicios simulados

| Servicio | Descripción |
|----------|-------------|
| `api-gateway` | Gateway principal de la API |
| `auth-service` | Servicio de autenticación |
| `database` | PostgreSQL principal |
| `redis-cache` | Cache Redis |
| `worker` | Procesador de tareas en background |

### Datos simulados

- **Logs**: Timestamps, levels (INFO/WARN/ERROR), messages contextuales
- **Métricas**: CPU (0-100%), memoria (0-100%), latencia (10-500ms), errores (0-50)
- **Deployments**: Historial de releases con timestamps
- **Health checks**: Estado del servicio (healthy/degraded/down)
- **Alertas**: Alertas recientes con severidad y timestamps

### Determinismo

- Los datos se generan con seeds basados en el nombre del servicio y timestamp
- Esto garantiza que las mismas consultas retornen los mismos resultados
- Facilita testing y reproducción de escenarios

---

## 11. Testing

### Backend (pytest)

```bash
cd backend
pytest -v
```

- **test_auth.py**: Registro, login, forgot-password, reset-password
- **test_incidents.py**: CRUD de incidentes, chat, approval

### Frontend (vitest)

```bash
cd frontend
npm run test
```

- **Login.test.tsx**: Renderizado, envío de formulario
- **Dashboard.test.tsx**: Renderizado de métricas
- **api.test.ts**: Función apiFetch con autenticación

---

## 12. Conclusiones

### Lo que se logró

1. **Copilot agéntico completo**: Agente LangGraph con pipeline de 5 nodos, 9 herramientas, búsqueda RAG
2. **Persistencia de estado**: Checkpointing en Postgres, sesiones vinculadas a incidentes
3. **Interfaz profesional**: React + Vite con dashboard, lista de incidentes, chat con aprobación
4. **Observabilidad**: Langfuse para trazabilidad de decisiones y tool calls
5. **Manejo de errores**: Fallback heurístico en cada nodo, degradación graciosa
6. **RAG completo**: Scraping de fuentes externas, ingesta automática, búsqueda híbrida
7. **Docker completo**: 4 servicios orquestados, hot reload para desarrollo

### Stack elegido vs. sugerido

| Capa | Sugerido | Elegido | Ventaja |
|------|----------|---------|---------|
| UI | Chainlit/Streamlit | React + Vite | UI customizada, profesional, escalable |
| Agente | LangGraph/CrewAI | LangGraph | Control fino, checkpointing, multi-tool |
| LLM | Cualquier LLM | Ollama (mistral) | Local, sin costo, sin latencia |
| Vector DB | ChromaDB/Weaviate/FAISS | Weaviate | Búsqueda híbrida, API REST, escalable |
| Deploy | Docker | Docker Compose | Orquestación completa, 4 servicios |

### El proyecto demuestra

- **Viabilidad de LLMs locales** para casos de uso empresariales
- **Importancia del human-in-the-loop** en sistemas de IA crítica
- **Valor de RAG** para enriquecer el contexto del agente con conocimiento organizacional
- **Necesidad de observabilidad** en sistemas agénticos para debugging y auditoría
