# RAG-LLM

RAG-LLM is a full-stack RAG chat application that lets users chat with their documents using a FastAPI backend and a React/Vite frontend. It supports authentication, conversation history, document ingestion, and AI-assisted responses grounded in uploaded content.

## What it does

- Chat with an LLM using retrieved context from uploaded documents
- Store and manage conversations and chat history
- Upload documents for semantic retrieval and question answering
- Authenticate users with JWT-based session handling
- Expose a browsable API with FastAPI docs

## Tech stack

- Backend: FastAPI, SQLAlchemy, Pydantic, JWT, Uvicorn
- Frontend: React, TypeScript, Vite, Mantine
- Data & search: PostgreSQL, embeddings, document parsing
- AI integration: Hugging Face inference endpoint

## Project structure

- app/: FastAPI application, routers, services, schemas, and auth logic
- database/: SQL schema and database setup assets
- frontend/: Vite + React client
- scripts/: Setup and build utilities

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL running locally or remotely
- A Hugging Face API token (optional depending on your setup)

## Environment setup

Create a .env file in the project root with values similar to:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/fieldforce
JWT_SECRET_KEY=replace_with_a_long_random_secret
HUGGINGFACE_API_TOKEN=your_token_here
```

## Backend setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set up the database schema:

```powershell
./scripts/setup_database.ps1
```

Or import the SQL file manually if you prefer:

```powershell
psql -f database/schema.sql
```

Start the API:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs

## Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

The frontend will be available at:

- http://127.0.0.1:5173

## Typical workflow

1. Sign up or log in through the web app
2. Upload documents to build a knowledge base
3. Start or open a conversation
4. Ask questions and receive answers grounded in the uploaded content

## Notes

- The backend uses JWT-based auth and stores conversation-related data in PostgreSQL.
- The app is designed to be extended with more document sources, richer retrieval strategies, and additional model providers.

