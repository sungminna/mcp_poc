import asyncio
from lucia.extractors.openai_extractors import OpenAIKeywordExtractor, OpenAIInfoExtractor
from lucia.extractors.models import ExtractedKeywordList, ExtractedInfoList
from lucia.clients.openai_client import OpenAIClient
from lucia.vectorstores.milvus_vector_store import MilvusVectorStore
from lucia.stores.info_store_neo4j import Neo4jInfoStore
from lucia.pipelines.knowledge_pipeline import KnowledgePipeline
from lucia.pipelines.search_pipeline import SearchPipeline
from lucia.embeddings.openai_embedding_client import OpenAIEmbeddingClient
from dotenv import load_dotenv

load_dotenv()

# PYTHONPATH=.. poetry run python te.py

async def tes():
    kw_extractor = OpenAIKeywordExtractor(client=OpenAIClient())
    info_extractor = OpenAIInfoExtractor(client=OpenAIClient())
    embedding_client = OpenAIEmbeddingClient(use_cache=True)
    vector_store = MilvusVectorStore()
    info_store = Neo4jInfoStore()
    pipeline = KnowledgePipeline(keyword_extractor=kw_extractor, embedding_client=embedding_client, vector_store=vector_store, info_extractor=info_extractor, info_store=info_store)
    user_message = "i like pizza"
    result = await pipeline.process(user_message, "test_user")
    print(result)

if __name__ == "__main__":
    asyncio.run(tes())