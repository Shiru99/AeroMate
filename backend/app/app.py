import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# LangGraph & LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict, List

# Load Environment Variables
load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    print("⚠️  WARNING: GOOGLE_API_KEY is missing in your .env file!")

# Define the Graph State
class State(TypedDict):
    # 'add_messages' means: when a node returns a message, append it to the list
    # rather than overwriting the whole list.
    messages: Annotated[List, add_messages]

# 3. Initialize the Model
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.2)

# 4. Define the Nodes
def chatbot_node(state: State):
    """
    The main worker node. 
    It takes the current state (conversation history),
    sends it to Gemini, and returns the AI's response.
    """
    # Invoke the LLM with the history of messages
    response = llm.invoke(state["messages"])
    
    # Return the new message to update the state
    return {"messages": [response]}

# 5. Build the Graph
workflow = StateGraph(State)

# Add our single node
workflow.add_node("chatbot", chatbot_node)

# Define the flow: Start -> Chatbot -> End
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)

# Compile the graph into a runnable application
graph = workflow.compile()

# 6. Setup FastAPI
app = FastAPI(title="AeroMate Backend")

# Define the data format coming from Frontend
class ChatRequest(BaseModel):
    message: str
    thread_id: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    API Endpoint that Frontend calls.
    """
    try:
        input_data = {"messages": [("user", request.message)]}
        
        result = graph.invoke(input_data)
        
        ai_response = result["messages"][-1].content
        
        return {"response": ai_response}
    
    except Exception as e:
        # If something breaks, send error to Frontend
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def home():
    """
    Simple check to see if the server is up.
    """
    return {"message": "AeroMate Backend is running!", "status": "active"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker/Kubernetes probes.
    """
    # You can add logic here later to check DB connection too
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)