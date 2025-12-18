import os
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(BASE_DIR, "chroma_db")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004") 

# 1. Load the Database ONCE (Global Variable)
if os.path.exists(DB_DIR):
    print("Loading Vector Database...")
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    
    vector_store = Chroma(
        persist_directory=DB_DIR,
        embedding_function=embeddings
    )
else:
    print("WARNING: Vector DB not found. Run ingest.py first!")
    vector_store = None


@tool
def get_aviation_info(query: str, airline_filter: str = None) -> str:
    """
    Searches the AeroMate Knowledge Base for official aviation documents. 
    Use this tool to answer user questions about baggage, refunds, security, or passenger rights.

    Args:
        query: The specific question or topic to search for (e.g., "pet policy for international flights", "compensation for 4 hour delay").
        
        airline_filter: (Optional) Limits the search to a specific authority or airline.
            - "IndiGo": Use for Indigo-specific queries (baggage fees, check-in rules).
            - "Air India": Use for Air India-specific queries (student offers, international baggage).
            - "DGCA": Use for GENERAL passenger rights, laws, compensation, refunds, or denied boarding. (Example: "What are my rights if flight is cancelled?").
            - "BCAS": Use for SECURITY related queries (prohibited items, sharp objects, power banks).
            - "Ministry of Civil Aviation": Use for general passenger charter queries.
            
            *IMPORTANT*: If the user does not mention an airline, do not guess. Leave this filter empty (None) to search everything.
    """
    if not vector_store:
        return "Error: Knowledge base is offline."

    print(f"🔍 Searching for: '{query}' | Filter Request: {airline_filter}")
    
    search_kwargs = {"k": 8}
    
    if airline_filter:
        filter_map = {
            "indigo": "IndiGo",
            "air india": "Air India",
            "airindia": "Air India",
            "dgca": "DGCA",
            "bcas": "BCAS",
            "security": "BCAS"
        }
        
        clean_filter = filter_map.get(airline_filter.lower(), airline_filter)
        
        search_kwargs["filter"] = {"publisher": clean_filter}
        print(f"   👉 Applying Filter: {{'publisher': '{clean_filter}'}}")
    
    try:
        retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
        docs = retriever.invoke(query)
        
        # FALLBACK LOGIC (Safety Net)
        if not docs and airline_filter:
            print(f"   ⚠️ Filter returned 0 results. Retrying broad search...")
            del search_kwargs["filter"]
            retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
            docs = retriever.invoke(query)
            
        if not docs:
            return "No relevant documents found in the database."
            
        # 6. Format Output
        # Using 'publisher' here too since that's what's in your metadata
        return "\n\n".join([
            f"Source: {d.metadata.get('publisher', 'Unknown')} ({d.metadata.get('type', 'Doc')}) | {d.page_content}" 
            for d in docs
        ])

    except Exception as e:
        return f"Retrieval Error: {str(e)}"