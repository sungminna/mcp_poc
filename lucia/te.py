import asyncio
from lucia.pipeline_factory import get_knowledge_pipeline

# PYTHONPATH=.. poetry run python te.py

async def tes():
    pipeline = get_knowledge_pipeline()
    user_message = "난 밥이 좋아"
    result = await pipeline.process(user_message, "test_user")
    print(result)

if __name__ == "__main__":
    asyncio.run(tes())