import os
import uuid
import time
try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None

class VectorMemory:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorMemory, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        if not chromadb:
            print("--- [Memory] Warning: chromadb not installed. Vector memory disabled. ---")
            self.collection = None
            self.initialized = True
            return

        db_path = "storage/chroma_db"
        os.makedirs(db_path, exist_ok=True)
        
        # Use simple default embedding function (sbert/all-MiniLM-L6-v2 is standard default in chromadb)
        # Or explicitly use sentence-transformers if needed. 
        # For now, relying on chromadb's default (onnx/quantized) which is locally contained.
        try:
            self.client = chromadb.PersistentClient(path=db_path)
            self.collection = self.client.get_or_create_collection(name="agent_history")
            print(f"--- [Memory] Vector Store initialized at {db_path} ---")
        except Exception as e:
            print(f"--- [Memory] Failed to initialize Vector Store: {e} ---")
            self.collection = None

        self.initialized = True

    def add_interaction(self, session_id: str, user_query: str, dag_json: str, result: str):
        if not self.collection:
            return

        doc_id = str(uuid.uuid4())
        # We store the problem and the solution structure
        # In a real system, you might embed query and result separately
        text_to_embed = f"Mission: {user_query}\nPlan: {dag_json}\nResult: {result}"
        
        self.collection.add(
            documents=[text_to_embed],
            metadatas=[{
                "session_id": session_id,
                "type": "mission_record",
                "timestamp": time.time(),
                "query": user_query # Store raw query in metadata for easier display
            }],
            ids=[doc_id]
        )
        print(f"--- [Memory] Remembered interaction {doc_id} ---")

    def retrieve_relevant(self, query: str, n_results: int = 2):
        if not self.collection:
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            # Flatten results
            hits = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i]
                    hits.append({
                        "content": doc,
                        "metadata": meta,
                        "distance": results["distances"][0][i] if results["distances"] else None
                    })
            return hits
        except Exception as e:
            print(f"--- [Memory] Retrieval failed: {e} ---")
            return []
