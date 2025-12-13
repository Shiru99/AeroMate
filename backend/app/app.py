import os
import time
from typing import Annotated, TypedDict, List, AsyncGenerator

# Third-Party Imports
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# LangChain & LangGraph Imports
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver

# ==========================================
# 1. CONFIGURATION & ENVIRONMENT
# ==========================================
load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    print("⚠️  WARNING: GOOGLE_API_KEY is missing in your .env file!")

MODEL_NAME = os.getenv("MODEL_NAME")
TEMPERATURE = os.getenv("TEMPERATURE")

if not MODEL_NAME:
    print("⚠️  WARNING: MODEL_NAME is missing in your .env file! Using default.")
    MODEL_NAME = "gemini-2.0-flash-lite"

if not TEMPERATURE:
    print("⚠️  WARNING: TEMPERATURE is missing in your .env file! Using default.")
    TEMPERATURE = 0.2
else:
    TEMPERATURE = float(TEMPERATURE)

# ==========================================
# 2. DATA MODELS (SCHEMAS)
# ==========================================
class ChatRequest(BaseModel):
    """Schema for incoming chat requests"""
    message: str
    thread_id: str

class ChatState(TypedDict):
    """Schema for the LangGraph state"""
    messages: Annotated[List[BaseMessage], add_messages]

# ==========================================
# 3. CORE LOGIC (LLM & GRAPH)
# ==========================================

# Initialize LLM
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=TEMPERATURE)

def chatbot_node(state: ChatState):
    """
    The main worker node. 
    Takes the conversation history, calls Gemini, and returns the response.
    """
    user_message = state["messages"]
    response = llm.invoke(user_message)
    return {"messages": [response]}

def build_graph():
    """Compiles and returns the LangGraph workflow."""
    workflow = StateGraph(ChatState)
    
    # Add Nodes
    workflow.add_node("chatbot", chatbot_node)
    
    # Add Edges
    workflow.add_edge(START, "chatbot")
    workflow.add_edge("chatbot", END)
    
    # Compile with Memory
    memory = InMemorySaver()
    return workflow.compile(checkpointer=memory)

# Initialize the Graph Application
our_graph = build_graph()

# ==========================================
# 4. API SETUP
# ==========================================
app = FastAPI(title="AeroMate Backend")

@app.get("/")
async def home():
    """Root endpoint to verify the server is active."""
    return {"message": "AeroMate Backend is running!", "status": "active"}

@app.get("/health")
async def health_check():
    """Health check for Docker/K8s probes."""
    return {"status": "healthy"}

# ==========================================
# 5. CHAT ENDPOINTS
# ==========================================

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Standard Request-Response Chat Endpoint.
    Waits for the full generation before returning.
    """
    try:
        print(f"Incoming (Sync): '{request.message}' | Thread ID: {request.thread_id}")
        
        # Prepare input and config
        user_message = {"messages": [("user", request.message)]}
        config = {"configurable": {"thread_id": request.thread_id}}
        
        # Execute Graph
        result = our_graph.invoke(user_message, config=config)
        
        # Extract Response
        ai_response = result["messages"][-1].content
        
        # Optional: Print memory stats
        print_context_memory(request.thread_id)
        
        return {"response": ai_response}
    
    except Exception as e:
        print(f"Error in /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chatstream")
async def chat_endpoint_stream(request: ChatRequest):
    """
    Streaming Chat Endpoint.
    Yields chunks of text as they are generated.
    """
    try:
        print(f"Incoming (Stream): '{request.message}' | Thread ID: {request.thread_id}")
        
        config = {"configurable": {"thread_id": request.thread_id}}
        user_message = {"messages": [("user", request.message)]}
        
        async def event_stream() -> AsyncGenerator[str, None]:
            """Generator that yields LLM chunks."""
            async for event in our_graph.astream_events(user_message, config=config, version="v1"):
                if event["event"] == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield content
            
            # Post-generation tasks
            print_context_memory(request.thread_id)

        return StreamingResponse(event_stream(), media_type="text/plain")
    
    except Exception as e:
        print(f"Error in /chatstream: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 6. HISTORY ENDPOINT
# ==========================================

@app.get("/history/{thread_id}")
async def get_chat_history(thread_id: str):
    """
    Fetches and formats conversation history for the frontend.
    """
    try:
        print(f"Fetching history for thread: {thread_id}")
        config = {"configurable": {"thread_id": thread_id}}
        
        current_state = our_graph.get_state(config)

        # Small delay to ensure state consistency if called immediately after chat
        time.sleep(0.5)
        
        if not current_state.values:
            return {"history": []}
            
        messages = current_state.values.get("messages", [])
        
        # Format messages for Frontend (converting LangChain types to simple dicts)
        formatted_history = []
        for msg in messages:
            role = "user" if msg.type == "human" else "assistant"
            formatted_history.append({
                "role": role,
                "content": msg.content
            })
            
        return {"history": formatted_history}

    except Exception as e:
        print(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 7. UTILITIES
# =========================================
"""Utility functions for AeroMate backend."""
def print_context_memory(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = our_graph.get_state(config)
    print(f"Context Memory for thread '{thread_id}' ({len(snapshot.values['messages'])} msgs):")
    for m in snapshot.values['messages']:
        print(f" - {m.type}: {m.content[:36]}...")

# ==========================================
# 8. ENTRY POINT
# ==========================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)