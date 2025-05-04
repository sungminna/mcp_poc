# Lucia AI Toolkit

A modular Python library for personal information extraction, keyword extraction, embeddings, and storage in graph and vector databases.

Key features:
- **Personal Info Extraction & Graph Storage**: Extract user preferences and attributes and store them in Neo4j or ClickHouse.
- **Keyword Extraction & Embedding**: Extract keywords and generate vector embeddings via OpenAI API with optional Redis caching.
- **Pluggable Components**: Swap in custom `KeywordExtractor`, `InfoExtractor`, `EmbeddingClient`, `VectorStore`, or `InfoStore` implementations.
- **Pre-built Pipelines**: `KnowledgePipeline` for info extraction + embeddings, and `SearchPipeline` for retrieval and context enrichment.
- **Interactive Agents**: Ready-to-use scripts (`te.py`, `agents/chitchat.py`) for quick demos.
- **Local Deployment**: Docker Compose setup for Redis, Neo4j, ClickHouse, and Milvus.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Quick Start](#quick-start)
   - [KnowledgePipeline Example](#knowledgepipeline-example)
   - [SearchPipeline Example](#searchpipeline-example)
5. [Interactive Scripts](#interactive-scripts)
6. [Docker Compose](#docker-compose)
7. [Customization](#customization)
8. [Development](#development)
9. [License](#license)

---

## Prerequisites
- Python >=3.13,<4.0 (as defined in `pyproject.toml`)
- [Poetry](https://python-poetry.org/) for package management
- A valid OpenAI API key
- Docker and Docker Compose (optional, for full-stack local deployment of dependencies)

---

## Installation
Make sure you have Poetry installed.

```bash
# Clone the repo
git clone https://github.com/your-org/LangGraph_proto.git # Replace with the actual repo URL if different
cd LangGraph_proto/lucia

# Install dependencies and the lucia package in editable mode
poetry install

# Activate the virtual environment managed by Poetry
poetry shell
# Now you can run python scripts directly, e.g., python te.py
# Alternatively, without activating the shell, use 'poetry run':
# poetry run python te.py
```

Alternatively, use `pip`:
```bash
pip install .
```

---

## Configuration
Create a `.env` file in the root of the `lucia/` directory (where `pyproject.toml` resides) or set environment variables directly. Lucia uses `pydantic-settings` to automatically load these.

```dotenv
# Required
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL_NAME=gpt-4.1-nano # Or another model like gpt-4o, gpt-4-turbo
EMBEDDING_MODEL_NAME=text-embedding-3-small # Or another embedding model

# Neo4j (Required by default InfoStore)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password # Use the password set in docker-compose.yml or your Neo4j instance
NEO4J_DATABASE=neo4j

# Milvus (Required by default VectorStore)
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Redis Caching (Optional)
# Set USE_REDIS_CACHE=true to enable
USE_REDIS_CACHE=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD= # Set if your Redis requires a password
CACHE_TTL_SECONDS=86400 # Optional: Cache time-to-live in seconds (default: None)

# ClickHouse InfoStore (Optional, if you implement/use it)
CLICKHOUSE_URI=http://localhost:8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=password # Use the password set in docker-compose.yml or your ClickHouse instance
CLICKHOUSE_DATABASE=default
```

Ensure the connection details match your running services (either local, Docker, or cloud-based).

---

## Quick Start
Below are code snippets demonstrating how to use Lucia's pipelines in your project.

### KnowledgePipeline Example
Extract personal info and keyword embeddings:

```python
import asyncio
from lucia.extractors.openai_extractors import OpenAIKeywordExtractor, OpenAIInfoExtractor
from lucia.embeddings.openai_embedding_client import OpenAIEmbeddingClient
from lucia.vectorstores.milvus_vector_store import MilvusVectorStore
from lucia.stores.info_store_neo4j import Neo4jInfoStore
from lucia.pipelines.knowledge_pipeline import KnowledgePipeline

async def main():
    # Instantiate components
    kw_extractor = OpenAIKeywordExtractor()
    info_extractor = OpenAIInfoExtractor()
    embedding_client = OpenAIEmbeddingClient(use_cache=True)
    vector_store = MilvusVectorStore()
    info_store = Neo4jInfoStore()

    # Build pipeline
    pipeline = KnowledgePipeline(
        keyword_extractor=kw_extractor,
        embedding_client=embedding_client,
        vector_store=vector_store,
        info_extractor=info_extractor,
        info_store=info_store,
    )

    # Process a user message
    result = await pipeline.process(
        user_message="I love hiking and reading books.",
        username="alice"
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### SearchPipeline Example
Extract keywords, store embeddings, and retrieve related personal info:

```python
import asyncio
from lucia.extractors.openai_extractors import OpenAIKeywordExtractor, OpenAIInfoExtractor
from lucia.embeddings.openai_embedding_client import OpenAIEmbeddingClient
from lucia.vectorstores.milvus_vector_store import MilvusVectorStore
from lucia.stores.info_store_neo4j import Neo4jInfoStore
from lucia.pipelines.search_pipeline import SearchPipeline

async def search_example():
    # Re-use same components from KnowledgePipeline example
    kw_extractor = OpenAIKeywordExtractor()
    info_extractor = OpenAIInfoExtractor()
    embedding_client = OpenAIEmbeddingClient(use_cache=True)
    vector_store = MilvusVectorStore()
    info_store = Neo4jInfoStore()

    # Build search pipeline
    search_pipeline = SearchPipeline(
        keyword_extractor=kw_extractor,
        embedding_client=embedding_client,
        vector_store=vector_store,
        info_extractor=info_extractor,
        info_store=info_store,
    )

    # Process a user query
    result = await search_pipeline.process(
        user_message="What preferences have I shared?",
        username="alice"
    )
    print("Keywords:", result['keywords'])
    print("Relationships:", result['relationships'])

if __name__ == "__main__":
    asyncio.run(search_example())
```

---

## Interactive Scripts
Lucia includes two demo scripts that can be run using Poetry:

- `te.py`: Simple end-to-end test demonstrating pipeline usage.
- `agents/chitchat.py`: Interactive chat agent that uses pipelines for knowledge persistence and retrieval.

```bash
# Ensure your .env file is configured and dependencies (like Neo4j, Milvus) are running

# Option 1: Activate the virtual environment first
poetry shell
python te.py
python agents/chitchat.py

# Option 2: Use 'poetry run' directly
poetry run python te.py
poetry run python agents/chitchat.py
```

---

## Docker Compose
To easily run the required external dependencies (Neo4j, Milvus, Redis) locally, use the provided `docker-compose.yml` file.

```bash
# Navigate to the lucia directory
cd path/to/LangGraph_proto/lucia

# Start all services in detached mode
docker-compose up -d

# Check the status of the containers (wait until health status is 'healthy')
docker-compose ps

# View logs for a specific service (e.g., milvus-standalone)
docker-compose logs -f milvus-standalone_lucia

# Access service UIs:
# - Neo4j Browser: http://localhost:7474 (Use neo4j/password to login)
# - Milvus Attu UI: http://localhost:7000

# Stop and remove containers, networks, and volumes
docker-compose down # Add -v to remove volumes as well
```
Ensure the services are healthy before running Lucia scripts that depend on them. The configuration in `.env` should match the ports and credentials defined in `docker-compose.yml`.

---

## Customization
Lucia's design is fully pluggable. To add or replace components:

1. Implement the abstract interfaces in:
   - `lucia/extractors/extractor.py`
   - `lucia/embeddings/embedding_client.py`
   - `lucia/vectorstores/vector_store.py`
   - `lucia/stores/info_store.py`
2. Pass your custom classes into `KnowledgePipeline` or `SearchPipeline`.

Example:
```python
from my_package.custom_vector_store import MyVectorStore
pipeline = KnowledgePipeline(..., vector_store=MyVectorStore(), ...)
```

---

## Development & Testing
Use Poetry to manage the development environment and run tools.

```bash
# Activate environment
poetry shell

# Run linting (example using flake8, adjust if using ruff, black etc.)
# Install development dependencies if needed: poetry install --with dev
flake8 lucia

# Run type checks (example using mypy)
mypy lucia

# Run tests (if configured with pytest)
pytest

# Alternatively, run commands directly with 'poetry run'
poetry run flake8 lucia
poetry run mypy lucia
poetry run pytest
```

---

## License
[Apache-2.0](LICENSE)