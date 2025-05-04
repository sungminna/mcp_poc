"""Simple test script demonstrating usage of the KnowledgePipeline."""

"""Usage:
    PYTHONPATH=.. poetry run python te.py
"""

import asyncio
from lucia.pipeline_factory import get_knowledge_pipeline

async def tes():
    """Run the KnowledgePipeline with a sample message for demonstration."""
    pipeline = get_knowledge_pipeline()
    user_message = "난 밥이 좋아"
    result = await pipeline.process(user_message, "test_user")
    print(result)

if __name__ == "__main__":
    asyncio.run(tes())