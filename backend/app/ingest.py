import os
from typing import List, Set
import re

# LangChain Imports
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from dotenv import load_dotenv

# ==========================================
# 1. CONFIGURATION
# ==========================================

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(BASE_DIR, "backend", "data")
DB_DIR = os.path.join(BASE_DIR, "chroma_db")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004") 

# ==========================================
# 2. METADATA REGISTRY
# ==========================================

FILE_REGISTRY = {
    # --- SECURITY & PROHIBITED ITEMS ---
    "BCAS permitted and prohibited items list.pdf": {
        "publisher": "BCAS",
        "scope": "ALL",
        "type": "Regulation",
        "priority": "High",
        "topics": ["Security", "Prohibited Items", "Hand Luggage", "Check-in Baggage", "Liquids"],
        "description": "Official list of items allowed and banned in airport security."
    },

    # --- DGCA REGULATIONS (THE LAW) ---
    "DGCA - D3M-M6.pdf": {
        "publisher": "DGCA",
        "scope": "ALL",
        "type": "Regulation",
        "priority": "High",
        "topics": ["Unruly Passengers", "No Fly List", "Behavior", "Banning"],
        "description": "Rules regarding handling of disruptive passengers and no-fly list criteria."
    },
    "DGCA - D3M-M1.pdf": {
        "publisher": "DGCA",
        "scope": "ALL",
        "type": "Regulation",
        "priority": "High",
        "topics": ["Disability", "Wheelchair", "Medical Assistance", "PRM"],
        "description": "Rights and facilities for persons with disability or reduced mobility."
    },
    "DGCA - D3M-M2.pdf": {
        "publisher": "DGCA",
        "scope": "ALL",
        "type": "Regulation",
        "priority": "High",
        "topics": ["Refunds", "Tickets", "Fare", "Public Transport Undertakings"],
        "description": "Refund of Airline tickets to passengers of public transport undertakings."
    },
    "DGCA - D3M-M4.pdf": {
        "publisher": "DGCA",
        "scope": "ALL",
        "type": "Regulation",
        "priority": "High",
        "topics": ["Denied Boarding", "Cancellation", "Flight Delays", "Compensation", "Facilities"],
        "description": "Facilities to be provided to passengers by airlines due to denied boarding, cancellation of flights and delays in flights"
    },
    "Ministry of Civil Aviation - Passenger Charter.pdf": {
        "publisher": "MoCA",
        "scope": "ALL",
        "type": "Charter",
        "priority": "Medium",
        "topics": ["General Rights", "Overview", "Grievance"],
        "description": "Citizen's charter summarizing passenger rights."
    },

    # --- AIRLINE SPECIFIC (THE CONTRACT) ---
    "IndiGo - Conditions of Carriage - Domestic.pdf": {
        "publisher": "IndiGo",
        "scope": "INDIGO",
        "type": "Policy",
        "priority": "Medium",
        "topics": ["Baggage Allowance", "Check-in", "Fees", "Domestic"],
        "description": "IndiGo specific rules for domestic travel."
    },
    "IndiGo - Conditions of Carriage - International.pdf": {
        "publisher": "IndiGo",
        "scope": "INDIGO",
        "type": "Policy",
        "priority": "Medium",
        "topics": ["Baggage Allowance", "Visa", "International", "Passport"],
        "description": "IndiGo specific rules for international travel."
    },
    "Air India - Conditions of Carriage.pdf": {
        "publisher": "Air India",
        "scope": "AIR_INDIA",
        "type": "Policy",
        "priority": "Medium",
        "topics": ["Baggage Allowance", "Meals", "Student Offer", "Pets"],
        "description": "Air India general terms and conditions."
    }
}


# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def get_existing_files_in_db() -> Set[str]:
    """
    Checks the Chroma DB metadata and returns a set of filenames 
    that have already been processed and stored.
    """
    if not os.path.exists(DB_DIR):
        return set()

    try:
        # Initialize in read-only mode to check content
        embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
        vector_store = Chroma(
            persist_directory=DB_DIR,
            embedding_function=embeddings
        )
        
        # Fetch only metadata (lighter than fetching full documents)
        existing_data = vector_store.get() 
        metadatas = existing_data.get("metadatas", [])
        
        # Extract unique filenames
        existing_files = set()
        for meta in metadatas:
            if meta and "filename" in meta:
                existing_files.add(meta["filename"])
                
        return existing_files
    except Exception as e:
        print(f"⚠️ Warning: Could not read existing DB. Assuming empty. Error: {e}")
        return set()

def clean_text(text: str) -> str:
    """
    Cleans PDF artifacts while preserving semantic structure.
    """
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t\xa0]+', ' ', text)
    return text.strip()

# ==========================================
# 3. INGESTION FUNCTIONS
# ==========================================

def load_and_process_documents(existing_files: Set[str]) -> List[Document]:
    """Loads PDFs, injects metadata, and splits text."""
    all_documents = []
    
    if not os.path.exists(DOCS_DIR):
        print(f"❌ Error: Directory '{DOCS_DIR}' not found.")
        return []

    for filename, metadata in FILE_REGISTRY.items():
        if filename in existing_files:
            print(f"⏩ Skipping '{filename}' (Already embedded)")
            continue

        file_path = os.path.join(DOCS_DIR, filename)
        
        if not os.path.exists(file_path):
            print(f"⚠️ Warning: File '{filename}' not found in {DOCS_DIR}, skipping.")
            continue
            
        print(f"📄 Loading: {filename}...")
        
        try:
            loader = PyPDFLoader(file_path)
            raw_docs = loader.load()
            
            keys_to_remove = ["producer", "creator", "creationdate", "moddate", "source"]
            
            for doc in raw_docs:
                for key in keys_to_remove:
                    doc.metadata.pop(key, None)

                doc.metadata.update(metadata)
                doc.metadata["filename"] = filename
                clean_content = clean_text(doc.page_content)
                
                if "topics" in doc.metadata and isinstance(doc.metadata["topics"], list):
                    doc.metadata["topics"] = ", ".join(doc.metadata["topics"])
                
                topic_str = doc.metadata["topics"]
                
                doc.page_content = (
                    f"Publisher: {metadata['publisher']} | "
                    f"Applies To: {metadata['scope']} | "
                    f"Type: {metadata['type']} | "
                    f"Topics: {topic_str}\n"
                    f"Content: {clean_content}"
                )
            
            all_documents.extend(raw_docs)
            
        except Exception as e:
            print(f"❌ Failed to load {filename}: {e}")

    return all_documents

def split_documents(documents: List[Document]) -> List[Document]:
    """Splits documents into semantic chunks."""
    
    # Standard Splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,    # Good balance for RAG
        chunk_overlap=200,  # Context overlap
        separators=["\n\n", "\n", " ", ""]
    )
    
    splits = text_splitter.split_documents(documents)
    print(f"✂️  Split {len(documents)} source docs into {len(splits)} chunks.")
    return splits

def create_vector_db():
    """Main ingestion function."""

    # 1. Check Existing Files
    existing_files = get_existing_files_in_db()
    print(f"🔍 Found {len(existing_files)} files already in database.")

    # 2. Load ONLY new files
    docs = load_and_process_documents(existing_files)
    
    if not docs:
        print("🎉 Database is up to date! No new files to embed.")
        return {"status": "skipped", "count": 0}

    # 3. Split
    splits = split_documents(docs)

    # 4. Initialize Embeddings
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY missing in environment variables.")
        
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

    # 5. Add to Vector Store (Append mode)
    print("💾 Adding new documents to Vector Store...")
    vector_store = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    
    print(f"✅ Success! Added {len(splits)} new chunks to '{DB_DIR}'.")
    return {"status": "success", "chunks": len(splits)}

if __name__ == "__main__":
    create_vector_db()