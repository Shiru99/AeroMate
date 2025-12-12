import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

import time

# LangGraph & LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict, List

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.checkpoint.memory import InMemorySaver

# Load Environment Variables
load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    print("⚠️  WARNING: GOOGLE_API_KEY is missing in your .env file!")

# Define the Graph State
class ChatState(TypedDict):
    # 'add_messages' means: when a node returns a message, append it to the list
    # rather than overwriting the whole list.
    messages: Annotated[List[BaseMessage], add_messages]

# 3. Initialize the Model
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.2)

checkpointer = InMemorySaver()

# 4. Define the Nodes
def chatbot_node(state: ChatState):
    """
    The main worker node. 
    It takes the current state (conversation history),
    sends it to Gemini, and returns the AI's response.
    """
    # Invoke the LLM with the history of messages
    user_message = state["messages"]

    # response = llm.invoke(user_message)

    # add sleep for 1 seconds to simulate processing time 
    time.sleep(1)

    response = AIMessage("Totally! Here's a fun fact: Did you know that honey never spoils? Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible!")
    
    # Return the new message to update the state
    return {"messages": [response]}

# 5. Build the Graph
workflow = StateGraph(ChatState)

# Add our single node
workflow.add_node("chatbot", chatbot_node)

# Define the flow: Start -> Chatbot -> End
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)

# Compile the graph into a runnable application
graph = workflow.compile(checkpointer=checkpointer)

# 6. Setup FastAPI
app = FastAPI(title="AeroMate Backend")

# Define the data format coming from Frontend
class ChatRequest(BaseModel):
    message: str
    thread_id: str

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

@app.get("/history/{thread_id}")
async def get_chat_history(thread_id: str):
    """
    Fetch the conversation history for a specific user thread.
    """
    try:
        print(f"Fetching history for thread: {thread_id}")
        config = {"configurable": {"thread_id": thread_id}}
        
        current_state = graph.get_state(config)

        time.sleep(1)
        
        if not current_state.values:
            return {"history": []}
            
        messages = current_state.values.get("messages", [])
        
        # 4. Convert LangChain Messages to Streamlit Format
        # LangChain uses .type='human'/'ai', Streamlit uses role='user'/'assistant'
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

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    API Endpoint for handling chat messages
    """
    try:
        print(f"Received message for thread {request.thread_id}: {request.message}")
        
        user_message = {"messages": [("user", request.message)]}

        config = {"configurable": {"thread_id": request.thread_id}}
        
        result = graph.invoke(user_message, config=config)
        
        ai_response = result["messages"][-1].content

        # --- DEBUG: PROOF OF CONTEXT ---
        # Get the latest state from the checkpointer to see what is stored
        snapshot = graph.get_state(config)
        print(f"Current Context Memory ({len(snapshot.values['messages'])} msgs):")
        for m in snapshot.values['messages']:
            print(f" - {m.type}: {m.content[:20]}...") 
        # -------------------------------
        
        return {"response": ai_response}
    
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)