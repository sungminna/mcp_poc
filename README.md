# velt

**velt** is a FastAPI-based backend application that integrates a ReAct language agent (via LangGraph), a Neo4j knowledge graph, a Milvus vector store, PostgreSQL, and Redis to deliver a personalized, retrieval-augmented conversational chatbot experience.

---
## Demo Service: https://delosplatform.com

## Contact: sungmin.na330@gmail.com

## Directory: https://my.surfit.io/w/528136765
---

## 🚀 Project Overview
![image](https://github.com/user-attachments/assets/6006246e-763e-4eef-b0b0-feca5bae6b50)

- LLM과 대화를 통해 개인화된 정보를 수집한다. 추후에 수집된 정보를 기반으로 개인화된 답변을 제공한다. 
- 개인화된(취향, 상태, 등..)에 대한 정보는 그래프 DB에 저장한다. 유저 질의와 유사한 키워드를 찾기 위해 벡터 DB도 활용한다.
- 그래프 형태 및 구성
  - 유저) 나는 햄버거를 좋아해
  - LLM) 그렇구나!!
  - 유저 질의에서 LLM을 활용해 관계를 추출한다
  - Knowledge Graph: (유저) --좋아한다-- (햄버거) --포함한다-- (음식)
  - 위와 같은 형태로 저장된다. 상위의 개념도 같이 그래프에 넣어 현실 대화를 대응할 수 있다. ex)나는 어떤 음식을 좋아해? or 오늘 저녁에 먹을 음식 추천해줘
- 그래프 탐색
  - Q) 나 미술 좋아하니?
  - LLM) 너가 미술을 좋아한다고 말한적이 있네...
  - 유저 질의에서 LLM을 활용해 키워드를 추출한다
  - 그래프에서 1홉 및 2홉의 노드(객체)와 직접적인 엣지(관계)를 모두 검색한다.
  - 추가로 그래프와 연결된 하위 개념도 검색한다. ex) 키워드가 음식인 경우 햄버거와의 관계도 추가한다
  - 관계를 LLM의 프롬프트에 추가해 증강된 답변을 유저에게 제공한다
- 검증 결과
  - 노드와 엣지 각각 적절한 탐색을 수행하고 관련된 정보를 기반으로 LLM이 답변을 해 준다
  - DB접근에 병목이 있는 것으로 추정(최적화 필요)
  - 적절한 데이터로 LLM이 증강되고 있지만, Relevent한 답변을 제공하고 있는지는 추가 파악 필요(성능 향상 필요)
  - 동적으로 Graph를 구축하고, 이를 기반으로 초개인화된 LLM을 구축할 수 있다
- 추가 사항
  - 유저와 유저간의 관계를 분석할 것이 아니라면, 단순 RDB기반으로 구축 가능하다.(성능이나 용량 면에서 추가 교차 검증 필요)
  - 실시간 대규모 환경에서의 GraphDB(Neo.4j)의 성능 검증이 필요하다
  - 프롬프트의 개선이 필요하다. 엣지 케이스에 대한 처리를 해 주었음에도 불구하고 Instruction을 따르지 않는 경우가 드물게 있다. (모델 성능 이슈?)
  - 현재는 DB쿼리를 하드코딩하여 사용하고 있다. Text to Cypher(SQL)을 활용해 MCP로 사용 가능할 것으로 보인다. (성능 검증 필요)
  - RAG의 한계? 컨텍스트를 증강하게 되면 오히려 컨텍스트에 치중한 답변을 제시한다. 즉, 그라운딩 없이 대화하는 것에 비해 부자연스러운 답변을 제시한다. (해결 필요)

---
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

