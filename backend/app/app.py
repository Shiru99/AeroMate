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

# 1. Load Environment Variables
load_dotenv()

# Check if API Key exists
if not os.getenv("GOOGLE_API_KEY"):
    print("⚠️  WARNING: GOOGLE_API_KEY is missing in your .env file!")

# 2. Define the Graph State
# This dictates what data passes between nodes.
class State(TypedDict):
    # 'add_messages' means: when a node returns a message, append it to the list
    # rather than overwriting the whole list.
    messages: Annotated[List, add_messages]

# 3. Initialize the Model
# We use Gemini 1.5 Flash because it is fast and free-tier eligible.
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
    thread_id: str  # Included for future use (Persistence)

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    API Endpoint that Frontend calls.
    """
    try:
        # Prepare the input for the graph
        # We wrap the user's string in a format LangGraph understands
        input_data = {"messages": [("user", request.message)]}
        
        # Run the graph!
        # This will jump through the nodes (Start -> Chatbot -> End)
        result = graph.invoke(input_data)
        
        # Extract the text content from the last message (the AI's reply)
        ai_response = result["messages"][-1].content
        
        return {"response": ai_response}
    
    except Exception as e:
        # If something breaks, send error to Frontend
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Entry point for running the script directly
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)