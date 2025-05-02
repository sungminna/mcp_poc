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
- Python 3.10 or later
- A valid OpenAI API key
- Docker (optional, for full-stack local deployment)

---

## Installation
```bash
# Clone the repo
git clone https://github.com/your-org/LangGraph_proto.git
cd LangGraph_proto/lucia

# Install dependencies via Poetry
poetry install

# Activate virtual environment
poetry shell
```

Alternatively, use `pip`:
```bash
pip install .
```

---

## Configuration
Create a `.env` file in the `lucia/` directory or set environment variables directly:
```dotenv
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL_NAME=gpt-4.1-nano
EMBEDDING_MODEL_NAME=text-embedding-3-small

# Redis caching (optional)
USE_REDIS_CACHE=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
CACHE_TTL_SECONDS=86400

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# ClickHouse (optional)
CLICKHOUSE_URI=http://localhost:8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=password
CLICKHOUSE_DATABASE=default

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
```  

Lucia will automatically load these settings via `pydantic`.

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
Lucia includes two demo scripts:

- `te.py`: Simple end-to-end test
- `agents/chitchat.py`: Interactive chat agent with persistence

```bash
# Run the test script
python te.py

# Run the interactive chat agent
python agents/chitchat.py
```

---

## Docker Compose
Spin up local dependencies with Docker Compose:

```bash
docker-compose up -d
```
This launches Redis, Neo4j, ClickHouse, and Milvus. Ensure the services are healthy before running Lucia.

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
- Run linting: `flake8 lucia`
- Run type checks: `mypy lucia`
- Run tests (if added): `pytest`

---

## License
[MIT](LICENSE)