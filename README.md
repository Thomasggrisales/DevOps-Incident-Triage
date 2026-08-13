# DevOps Incident Triage

Un sistema inteligente para la clasificación, gestión y asignación de incidentes de DevOps. Utiliza Inteligencia Artificial y bases de datos vectoriales para analizar reportes, encontrar casos similares en el historial y sugerir soluciones mediante agentes autónomos.

---

## Características Principales

* **Clasificación Automática:** Análisis de incidentes mediante IA (LLM + LangChain) para determinar severidad y equipo responsable.
* **Búsqueda Semántica:** Integración con Weaviate (Base de Datos Vectorial) para encontrar incidentes pasados con contextos similares (RAG).
* **Gestión de Estado:** Almacenamiento relacional (SQLAlchemy) para el seguimiento tradicional del ciclo de vida del incidente.
* **Autenticación JWT:** Registro e inicio de sesión con tokens Bearer; los endpoints de incidentes están protegidos.
* **Asistente de Triage:** Chat con agente LangGraph que investiga, propone fixes y solicita aprobación humana.
* **Dashboard y Página de Incidentes:** Métricas (totales, severidad, MTTR) y listado con filtros y búsqueda.
* **Arquitectura Fullstack Dockerizada:** Entornos de frontend y backend separados y orquestados mediante Docker Compose.

---

## Stack Tecnológico y Versiones

**Backend:**
* Python `3.10`+ (Docker) / `3.13` (local)
* FastAPI (API RESTful de alto rendimiento)
* Uvicorn (Servidor ASGI)
* LangChain & LangGraph (Agentes de IA)
* Weaviate Client (Base de datos vectorial)
* SQLAlchemy (ORM) + PostgreSQL
* PyJWT, passlib/bcrypt (autenticación)
* Pydantic v2

**Frontend:**
* Node.js `20` (Imagen Alpine en Docker)
* Vite + React `19` (Bundler y servidor de desarrollo)
* TypeScript (Tipado estricto)
* Tailwind CSS

**Infraestructura:**
* Docker & Docker Compose
* PostgreSQL, Weaviate, Langfuse (observabilidad)

---

## Estructura del Proyecto

* `backend/`: Contiene el código fuente de la API (FastAPI) y la lógica de los agentes de IA.
* `frontend/`: Contiene la interfaz de usuario construida con Vite + React y TypeScript.
* `docker-compose.yml`: Archivo de orquestación para levantar todos los servicios simultáneamente.
* `.env.example`: Plantilla de variables de entorno requeridas.

<img width="1682" height="519" alt="Arquitectura drawio" src="https://github.com/user-attachments/assets/2c9b0579-dc2d-432e-8098-b9fc0170867a" />

## Arquitectura Agéntica
<img width="1570" height="334" alt="DiagramaOrquestacion drawio" src="https://github.com/user-attachments/assets/f8df87d8-4d11-4b2f-8e22-7b9026f2c9dd" />

---

## Instalación y Uso Local

### Requisitos Previos

* Git
* Docker Desktop (o el motor de Docker + Docker Compose)

**1. Clonar el repositorio:**
```bash
git clone https://github.com/Thomasggrisales/DevOps-Incident-Triage.git
cd DevOps-Incident-Triage
```

**2. Configurar variables de entorno:**
```bash
cp .env.example .env
# Edita SECRET_KEY con una clave propia (python -c "import secrets; print(secrets.token_urlsafe(64))")
```

**3. Construir y levantar los contenedores:**
```bash
docker compose up --build
```

Para detener los servicios:
```bash
docker compose down
```

La API estará disponible en `http://localhost:8000` (documentación interactiva en `http://localhost:8000/docs`) y el frontend en `http://localhost:5173`.

### Autenticación

1. Registra un usuario en `POST /auth/register` (o desde `/docs`).
2. Inicia sesión en `POST /auth/login` y guarda el `access_token`.
3. Usa el token en el header `Authorization: Bearer <token>` en las llamadas a `/incidents/*`. El frontend lo adjunta automáticamente tras iniciar sesión.
4. Recuperación de contraseña: `POST /auth/forgot-password` devuelve un token de 30 minutos (mientras no haya infraestructura de correo) y `POST /auth/reset-password` lo canjea por una contraseña nueva.

---

## English

# DevOps Incident Triage

An intelligent system for classifying, managing, and assigning DevOps incidents. It uses artificial intelligence and vector databases to analyze reports, find similar cases in the history, and suggest solutions through autonomous agents.

---

## Key Features

* **Automatic Classification:** AI-powered incident analysis (LLM + LangChain) to determine severity and the responsible team.
* **Semantic Search:** Integration with Weaviate (vector database) to find past incidents with similar contexts (RAG).
* **Status Management:** Relational storage (SQLAlchemy) for traditional incident lifecycle tracking.
* **JWT Authentication:** User registration and login with Bearer tokens; incident endpoints are protected.
* **Triage Assistant:** Chat with a LangGraph agent that investigates, proposes fixes, and requests human approval.
* **Dashboard & Incidents Page:** Metrics (totals, severity, MTTR) and a list with filters and search.
* **Dockerized Full-Stack Architecture:** Separate frontend and backend environments orchestrated via Docker Compose.

---

## Technology Stack and Versions

**Backend:**
* Python `3.10`+ (Docker) / `3.13` (local)
* FastAPI (High-performance RESTful API)
* Uvicorn (ASGI server)
* LangChain & LangGraph (AI agents)
* Weaviate Client (Vector database)
* SQLAlchemy (ORM) + PostgreSQL
* PyJWT, passlib/bcrypt (authentication)
* Pydantic v2

**Frontend:**
* Node.js `20` (Alpine image in Docker)
* Vite + React `19` (Bundler and rapid development server)
* TypeScript (Strict typing)
* Tailwind CSS

**Infrastructure:**
* Docker & Docker Compose
* PostgreSQL, Weaviate, Langfuse (observability)

---

## Project Structure

* `backend/`: Contains the API source code (FastAPI) and the logic for the AI agents.
* `frontend/`: Contains the user interface built with Vite, React, and TypeScript.
* `docker-compose.yml`: Orchestration file to start all services simultaneously.
* `.env.example`: Template of the required environment variables.

---

## Local Installation and Usage

### Prerequisites

* Git
* Docker Desktop (or the Docker engine + Docker Compose)

**1. Clone the repository:**
```bash
git clone https://github.com/Thomasggrisales/DevOps-Incident-Triage.git
cd DevOps-Incident-Triage
```

**2. Set up environment variables:**
```bash
cp .env.example .env
# Edit SECRET_KEY with your own (python -c "import secrets; print(secrets.token_urlsafe(64))")
```

**3. Build and start the containers:**
```bash
docker compose up --build
```

To stop the services:
```bash
docker compose down
```

The API will be available at `http://localhost:8000` (interactive docs at `http://localhost:8000/docs`) and the frontend at `http://localhost:5173`.

### Authentication

1. Register a user via `POST /auth/register` (or from `/docs`).
2. Log in via `POST /auth/login` and keep the `access_token`.
3. Send the token in the `Authorization: Bearer <token>` header for `/incidents/*` calls. The frontend attaches it automatically after login.
4. Password recovery: `POST /auth/forgot-password` returns a 30-minute token (until email infrastructure is added) and `POST /auth/reset-password` redeems it for a new password.
