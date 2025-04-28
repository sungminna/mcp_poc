# Lucia Python Package

Lucia is a flexible, extensible AI library for:

- **Keyword Extraction** via pluggable extractors.
- **Embeddings** through abstract `EmbeddingClient` implementations.
- **Vector Storage** with `VectorStore` interfaces (e.g., Milvus).
- **Personal Info Extraction & Graph Storage** using `InfoExtractor` and `InfoStore` (e.g., Neo4j).
- **KnowledgePipeline** tying these components together.

## Installation

```bash
cd lucia
poetry install
```

## Quick Start

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from neo4j import AsyncGraphDatabase

from lucia import (
    LangChainKeywordExtractor,
    OpenAIEmbeddingClient,
    MilvusVectorStore,
    LangChainInfoExtractor,
    Neo4jInfoStore,
    KnowledgePipeline,
)

# Setup Neo4j info store
neo4j_driver = AsyncGraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "password"))
info_store = Neo4jInfoStore(driver=neo4j_driver)

# Instantiate pipeline components
keyword_extractor = LangChainKeywordExtractor()
embedding_client = OpenAIEmbeddingClient(model_name="text-embedding-3-small")
vector_store = MilvusVectorStore()
info_extractor = LangChainInfoExtractor()

# Create pipeline
pipeline = KnowledgePipeline(
    keyword_extractor=keyword_extractor,
    embedding_client=embedding_client,
    vector_store=vector_store,
    info_extractor=info_extractor,
    info_store=info_store,
)

# Process a user message
result = asyncio.run(pipeline.process(
    user_message="I love hiking and reading books.",
    username="alice",
))

print(result)
```

## Extensibility

- Swap out `KeywordExtractor`, `EmbeddingClient`, `VectorStore`, `InfoExtractor`, or `InfoStore` with custom implementations.

## License

MIT 