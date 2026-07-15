# DevOps Incident Triage

Un sistema inteligente para la clasificación, gestión y asignación de incidentes de DevOps. Utiliza Inteligencia Artificial y bases de datos vectoriales para analizar reportes, encontrar casos similares en el historial y sugerir soluciones mediante agentes autónomos.

---

## Características Principales

* **Clasificación Automática:** Análisis de incidentes mediante IA (LLM + LangChain) para determinar severidad y equipo responsable.
* **Búsqueda Semántica:** Integración con Weaviate (Base de Datos Vectorial) para encontrar incidentes pasados con contextos similares (RAG).
* **Gestión de Estado:** Almacenamiento relacional (SQLAlchemy) para el seguimiento tradicional del ciclo de vida del incidente.
* **Arquitectura Fullstack Dockerizada:** Entornos de frontend y backend separados y orquestados mediante Docker Compose.

---

## Stack Tecnológico y Versiones

El proyecto está construido con las siguientes tecnologías clave:

**Backend:**
* Python `3.10.0`
* FastAPI (API RESTful de alto rendimiento)
* Uvicorn (Servidor ASGI)
* LangChain & LLM (Agentes de IA)
* Weaviate Client (Base de datos vectorial)
* SQLAlchemy (ORM para base de datos relacional)

**Frontend:**
* Node.js `20` (Imagen Alpine en Docker)
* Vite (Bundler y servidor de desarrollo rápido)
* TypeScript (Tipado estricto)

**Infraestructura:**
* Docker & Docker Compose

---

## Estructura del Proyecto

El repositorio sigue una arquitectura de monorepo dividiendo claramente las responsabilidades:

* `backend/`: Contiene el código fuente de la API (FastAPI) y la lógica de los agentes de IA.
* `frontend/`: Contiene la interfaz de usuario construida con Vite + React y TypeScript.
* `docker-compose.yml`: Archivo de orquestación para levantar todos los servicios simultáneamente.

<img width="1682" height="519" alt="Arquitectura drawio" src="https://github.com/user-attachments/assets/2c9b0579-dc2d-432e-8098-b9fc0170867a" />

---

## Instalación y Uso Local

El proyecto está completamente dockerizado para garantizar que funcione idénticamente en cualquier entorno sin necesidad de instalar dependencias locales de Node o Python.

## Requisitos Previos

Para ejecutar este proyecto en tu entorno local, necesitas tener instalado:
* Git
* Docker Desktop (o el motor de Docker + Docker Compose)

**1. Clonar el repositorio:**
```bash```
```git clone [[https://github.com/tu-usuario/DevOps-Incident-Triage.git](https://github.com/tu-usuario/DevOps-Incident-Triage.git)](https://github.com/Thomasggrisales/DevOps-Incident-Triage.git)```
```cd DevOps-Incident-Triage```

**2. Construir contenedor
```Terminal```
```docker-compose up --build```

Opcional. En caso que se deba bajar el compose 
```Terminal```
```docker-compose down```


## English

# DevOps Incident Triage

An intelligent system for classifying, managing, and assigning DevOps incidents. It uses artificial intelligence and vector databases to analyze reports, find similar cases in the history, and suggest solutions through autonomous agents.

---

## Key Features

* **Automatic Classification:** AI-powered incident analysis (LLM + LangChain) to determine severity and the responsible team.
* **Semantic Search:** Integration with Weaviate (vector database) to find past incidents with similar contexts (RAG).
* **Status Management:** Relational storage (SQLAlchemy) for traditional incident lifecycle tracking.
* **Dockerized Full-Stack Architecture:** Separate frontend and backend environments orchestrated via Docker Compose.

---

## Technology Stack and Versions

The project is built using the following key technologies:

**Backend:**
* Python `3.10.0`
* FastAPI (High-performance RESTful API)
* Uvicorn (ASGI server)
* LangChain & LLM (AI agents)
* Weaviate Client (Vector database)
* SQLAlchemy (ORM for relational databases)

**Frontend:**
* Node.js `20` (Alpine image in Docker)
* Vite (Bundler and rapid development server)
* TypeScript (Strict typing)

**Infrastructure:**
* Docker & Docker Compose

---

## Project Structure

The repository follows a monorepo architecture with clearly separated responsibilities:

* `backend/`: Contains the API source code (FastAPI) and the logic for the AI agents.
* `frontend/`: Contains the user interface built with Vite, React, and TypeScript.
* `docker-compose.yml`: Orchestration file to start all services simultaneously.

---

## Local Installation and Usage

The project is fully Dockerized to ensure it runs identically in any environment without the need to install local Node or Python dependencies.

## Prerequisites

To run this project in your local environment, you need to have the following installed:
* Git
* Docker Desktop (or the Docker engine + Docker Compose)

**1. Clone the repository:**
```bash```
```git clone [[https://github.com/tu-usuario/DevOps-Incident-Triage.git](https://github.com/tu-usuario/DevOps-Incident-Triage.git)](https://github.com/Thomasggrisales/DevOps-Incident-Triage.git)```
```cd DevOps-Incident-Triage```

**2. Build the container:**
```Terminal```
```docker-compose up --build```

**Optional. If you need to stop Docker Compose** 
```Terminal```
```docker-compose down```



