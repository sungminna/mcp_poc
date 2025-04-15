from fastapi import APIRouter
from pydantic import BaseModel
from services.llm_service import llm_ask

router = APIRouter()

# Define a Pydantic model for the request body
class ChatRequest(BaseModel):
    user_message: str

# Change method to POST and path, expect ChatRequest in body
@router.post("/api/chat/")
async def ask(request: ChatRequest): # Function accepts ChatRequest model
    # Get question from the request body
    question = request.user_message 
    
    res = await llm_ask(question)
    
    # Print the actual response content from res['response']
    if res and 'response' in res:
        # Assuming res['response'] structure based on previous code
        # Adjust this part if the actual structure of res['response'] is different
        try:
            llm_content = res['response']['messages'][-1].content
            print(f"LLM Response Content: {llm_content}")
            # Return only the content string
            return {"question": question, "ai_response": llm_content} 
        except (KeyError, IndexError, TypeError) as e:
             print(f"Error extracting content from LLM response: {e}, response: {res['response']}")
             return {"question": question, "ai_response": "Error processing LLM response."} 

    elif res and 'error' in res:
        print(f"LLM Error: {res['error']}")
        return {"question": question, "ai_response": f"LLM Error: {res['error']}"} 
    else:
        print(f"Unknown LLM response structure: {res}")
        return {"question": question, "ai_response": "Unknown error from LLM service."} 