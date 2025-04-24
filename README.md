# react-mcp

**react-mcp** is a FastAPI-based backend application that integrates a ReAct language agent (via LangChain), a Neo4j knowledge graph, a Milvus vector store, PostgreSQL, and Redis to deliver a personalized, retrieval-augmented conversational chatbot experience.

---

## 🚀 Project Overview

- **Personalized Chatbot**: Leverages user profile data, preferences, and relationships stored in Neo4j to provide context-aware responses.
- **Retrieval-Augmented Generation**: Uses Milvus to store and search OpenAI embeddings of user data and chatbot context, enriching prompts for the REACT agent.
- **Structured Personal Information**: Extracts user statements, preferences, and attributes as structured JSON, then persists them into Neo4j nodes and relationships.
- **Asynchronous & Scalable**: Built on FastAPI with async SQLAlchemy, async Neo4j driver, and async Redis/Milvus clients for high throughput.
- **Secure & Rate-Limited**: JWT-based authentication, bcrypt password hashing, and per-endpoint rate limiting with slowapi.

---

## 📚 Features

- **User Management**: Signup, login, and profile endpoints with JWT authentication.
- **Graph Storage**: Save and update user information as nodes and relationships in Neo4j.
- **Vector Embeddings**: Generate OpenAI embeddings with Redis caching, store vectors in Milvus, and perform similarity search.
- **Chat Sessions**: Create and retrieve chat sessions and messages from PostgreSQL.
- **REACT Agent**: Orchestrate LangChain's REACT agent for dynamic question answering and task execution.
- **Tool Integration**: Example external tool servers (weather, math) to demonstrate agent tool usage.
- **Rate Limiting**: Control request throughput per endpoint (e.g., chat, login, register).

---

## 🛠️ Tech Stack

| Component          | Library / Tool                               |
|--------------------|----------------------------------------------|
| Framework          | FastAPI, Uvicorn                             |
| HTTP & ASGI Server | Uvicorn                                      |
| Knowledge Graph    | Neo4j (neo4j-driver)                         |
| Vector Store       | Milvus (pymilvus)                            |
| Embedding Model    | OpenAI embeddings (text-embedding-3-small)   |
| Database           | PostgreSQL (asyncpg), SQLAlchemy AsyncSession |
| Caching            | Redis (aioredis)                             |
| Authentication     | JWT (python-jose), bcrypt (passlib[bcrypt])  |
| Rate Limiting      | slowapi                                      |
| LLM Agent          | LangChain, langgraph, langchain-openai       |
| Logging & Tracing  | Python logging, Langfuse                     |
| Packaging & Deploy | Poetry, Docker                               |

---

## 📐 Architecture & Workflow

1. **Application Startup** (`lifespan` hook in `main.py`):
   - Create PostgreSQL tables via SQLAlchemy migrations.
   - Connect to Neo4j, verify connectivity, and create unique constraints.
   - Connect to Milvus and ensure the collection and index exist.
2. **User Flow**:
   - **Signup**: Save user to PostgreSQL and create a corresponding `User` node in Neo4j.
   - **Login**: Issue JWT access tokens upon valid credentials.
3. **Chat Flow**:
   - **Session Management**: Store chat sessions and messages in PostgreSQL.
   - **Message Handling**:
     - Extract personal information (key, value, relationship) from user messages.
     - Persist structured data into Neo4j as `Information` nodes and `RELATES_TO` edges.
     - Generate or retrieve embeddings for data points and store/search in Milvus.
     - Extract keywords from user input and perform vector similarity search in Milvus to retrieve relevant concepts.
     - Fetch related graph data from Neo4j (direct relations and 1-hop children) for context.
     - Combine context and call the LangChain REACT agent to generate a response.
     - Save the agent's response back to PostgreSQL.
4. **Background & Tooling**:
   - **External Tools**: `weather_server.py` and `math_server.py` simulate tool APIs for the REACT agent.
   - **Rate Limiting**: Enforce per-endpoint limits (e.g., chat, login) using slowapi.
   - **Tracing & Logging**: Log requests and LLM callbacks via Python logging and Langfuse.

---

## 📂 Directory Structure

```
react_mcp/
├── main.py
├── database.py
├── core/
│   ├── config.py
│   └── security.py
├── routers/
│   ├── auth.py
│   ├── users.py
│   ├── general.py
│   └── ask.py
├── services/
│   ├── neo4j_service.py
│   ├── milvus_service.py
│   └── llm_service.py
├── crud/
│   ├── user.py
│   └── chat.py
├── models/
├── prompts.py
├── client.py
├── weather_server.py
├── math_server.py
├── pyproject.toml
├── poetry.lock
├── Dockerfile
└── README.md
```

Additionally, the `velt/` directory at the repository root contains the SvelteKit frontend application.

---

## ⚙️ Installation

1. **Prerequisites**:
   - Python 3.13+
   - Poetry
   - Docker (optional)
   - Node.js & npm (for frontend)

2. **Clone & Setup Backend**:
   ```bash
   git clone <repository_url>
   cd <repository_root>/react_mcp
   poetry install
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in `react_mcp/` with the following keys:
   ```ini
   SECRET_KEY=
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password
   MILVUS_HOST=localhost
   MILVUS_PORT=19530
   REDIS_URL=redis://localhost:6379
   LANGFUSE_SECRET_KEY=
   LANGFUSE_PUBLIC_KEY=
   LANGFUSE_HOST=http://localhost:3000
   RATE_LIMIT_CHAT=30/minute
   RATE_LIMIT_LOGIN=10/minute
   RATE_LIMIT_REGISTER=5/hour
   CORS_ALLOW_ORIGINS=*
   ```

4. **Run the Backend**:
   ```bash
   poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Run the Frontend (Optional)**:
   ```bash
   cd ../velt
   npm install
   npm run dev
   ```

---

## 📡 API Endpoints

### Authentication
- **POST** `/api/v1/auth/token` — Obtain JWT access token

### Users
- **POST** `/api/v1/users/` — Register a new user
- **GET** `/api/v1/users/me` — Get profile of current user
- **GET** `/api/v1/users/{user_id}` — Get user by ID
- **GET** `/api/v1/users/` — List all users (requires auth)

### Chat
- **POST** `/api/v1/chat/` — Send a chat message → Agent response
- **GET** `/api/v1/chat/sessions` — List chat sessions
- **GET** `/api/v1/chat/{session_id}/messages` — Get messages in a session
- **DELETE** `/api/v1/chat/{session_id}` — Delete session and messages

### General
- **GET** `/` — Health check / Hello world
- **GET** `/items/{item_id}` — Sample test endpoint

---

## 🏗️ Frontend (velt)

The `velt` folder contains a SvelteKit application that consumes this backend API.

```bash
cd velt
npm install
npm run dev
```

Build & preview:

```bash
npm run build
npm run preview
```

---

## ✨ Contributing

Contributions are welcome! Please open issues or pull requests.

---

## 📄 License

This project is licensed under the MIT License.

