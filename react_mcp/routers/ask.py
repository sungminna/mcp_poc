from fastapi import APIRouter
from services.llm_service import llm_ask

router = APIRouter()

@router.get("/api/ask/{question}")
async def ask(question: str):
    res = await llm_ask(question)
    # Print the actual response content from res['response']
    if res and 'response' in res:
        data = res['response']
        print(f"LLM Response Content: {res['response']}")
    elif res and 'error' in res:
        print(f"LLM Error: {res['error']}")
    
    res = res['response']['messages'][-1].content

    return {"question": question, "response": res} 