# arxiv-ai-explorer
**ResearchMind - Intelligent ArXiv AI Explorer**

![Project Cover image](/project-cover-image.png)

Clean, human-friendly research assistant that helps you discover, analyze, and organize academic papers. It combines semantic search, citation-aware discovery, a knowledge graph, and multi-agent assistance to streamline literature review.

Still under development. If you find any issues or have ideas, feel free to open an issue or start a discussion.

## 🧠 Overview

Researchers face information overload and fragmented tooling. Wanted to create this tool to make the research process easier. With this tool, you can:
- **Search smarter** with semantic and keyword search backed by vector embeddings (dense + sparse) (Qdrant) and graph signals (Neo4j).
- **Explore citations** and related work via a **Neo4j knowledge graph**.
- **Parse papers** (PDF → structured content) with Docling.
- **Automate ingestion** and refresh (paper metadata, PDF parsing, chunking, embedding, Qdrant upsert, citation discovery, Neo4j upsert) tasks using **Airflow**.
- **Interact** with a multi-agent assistant for summaries, synthesis, and guidance.

Repository name: `arxiv-ai-explorer` • App name: `ResearchMind`.

## ✨ Features

- **Semantic search** over chunked paper content (Qdrant (dense + sparse)).
- **Citation discovery** via Semantic Scholar and internal tracking.
- **Knowledge graph** of papers, authors, concepts, and relationships (Neo4j, GDS/APOC enabled).
- **Multi-agent assistant** for analysis, synthesis, and context-aware chat (FastAPI backend).
- **PDF parsing pipeline** using Docling with table structure support.
- **User auth and preferences** with JWT and persisted settings.
- **Recommendations** (basic, not yet finished) based on the user's interests and interactions with papers.
- **Airflow DAGs** for ingestion, processing, citation refresh, and KG init.

## 🧱 Tech Stack

- **Backend**: FastAPI, (+ other libraries)
- **Data/Infra**: PostgreSQL, Qdrant, Neo4j, Airflow, Redis
- **AI**: sentence-transformers (dense + sparse), `openai-agents` for agents.
- **PDF**: Docling
- **Frontend**: React with TypeScript
- **Container/Orchestration**: Docker Compose

## ⚙️ Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend)
- Python 3.11+ (for local backend dev without Docker)

## 🚀 Quick Start (Docker)

1. Create `backend/.env` from example and fill required keys:
   - Look at `backend/.env.example` for more info. 
   - Database, JWT, OpenAI (optional), Semantic Scholar (optional), Neo4j password.
2. From `backend/`, start the stack:

   ```bash
   docker compose up --build
   ```

3. Services (default ports):
   - API: http://localhost:8000 (docs at `/docs`, health at `/health`)
   - Airflow: http://localhost:8080
   - Postgres: localhost:5433
   - Redis: localhost:6379
   - Qdrant UI: http://localhost:6333
   - Neo4j Browser: http://localhost:7474 (bolt at 7687)

4. Frontend (from `frontend/`):

   ```bash
   npm install
   npm start
   ```

   Proxy to backend is configured in `frontend/package.json`.


## 📚 Airflow pipelines

Located in `backend/airflow/dags`:

- **arxiv_ingestion_dag.py** : fetch new papers from arXiv, store metadata, schedule parsing.
- **paper_processing_dag.py** : PDF download, parsing, chunking, embedding, Qdrant upsert.
- **citation_refresh_dag.py** : discover and update citation links -> expand KG.
- **kg_init_dag.py** : bootstrap Neo4j schema and base entities.

Custom operators are in `backend/airflow/plugins` (arxiv, citation, KG, qdrant).

