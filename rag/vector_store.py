import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
import os
import uuid
import json

# Initialize Chroma Client with Logic defined in Manual
# "Vector Store: FAISS, pgvector, or Chroma" -> Using Chroma (Local/File-based)

CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "property_explanations"

def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)

def get_embedding_function():
    # Using a local model to avoid API costs/limits for bulk embedding
    # This is "equivalent" to OpenAI embeddings as permitted.
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

def initialize_vector_store(df):
    """
    Ingests Property Records AND Educational Concepts into ChromaDB.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    
    # Get or Create Collection
    try:
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)
    except:
        collection = client.create_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)

    # 1. Hydrate Property Records (only if empty to avoid dups)
    if collection.count() == 0:
        print("Hydrating Vector Store with Property Explanation Records...")
        
        ids = []
        documents = []
        metadatas = []
        
        for index, row in df.iterrows():
            name = row.get('name', 'Unknown')
            addr = row.get('address', 'Unknown')
            price = str(row.get('price', 'N/A'))
            rent = str(row.get('rent', 'N/A'))
            decision = row.get('decision', 'N/A')
            wealth_diff = str(row.get('wealth_difference', '0'))
            emi = str(row.get('monthly_emi', 'N/A'))
            regime = row.get('chosen_tax_regime', 'N/A')
            total_tax = str(row.get('total_tax_paid', 'N/A'))
            
            explanation_text = f"""
            Property: {name}
            Location: {addr}
            Financials: Price {price}, Rent {rent}, EMI {emi}
            Decision: {decision}
            Wealth Difference: {wealth_diff}
            Tax Regime: {regime}, Tax Paid: {total_tax}
            Rationale: This property in {addr} is calculated to be a {decision}.
            """
            
            documents.append(explanation_text)
            ids.append(f"prop_{index}")
            metadatas.append({
                "name": name, 
                "location": addr,
                "decision": decision,
                "source": "csv_analysis"
            })
            
        BATCH_SIZE = 100
        for i in range(0, len(documents), BATCH_SIZE):
            collection.add(
                ids=ids[i:i+BATCH_SIZE],
                documents=documents[i:i+BATCH_SIZE],
                metadatas=metadatas[i:i+BATCH_SIZE]
            )
        print(f"Successfully embedded {len(documents)} property records.")
    else:
        print(f"Vector Store already contains {collection.count()} property records.")

    # 2. Check/Inject Educational Concepts (Always check if missing)
    # We query specifically for educational sources to see if they are missing
    try:
        edu_check = collection.get(where={"source": "educational_concept"}, limit=1)
        if len(edu_check['ids']) == 0:
            print("Injecting Educational Concepts...")
            json_path = os.path.join(os.path.dirname(__file__), "educational_concepts.json")
            
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    concepts = json.load(f)
                
                edu_ids = []
                edu_docs = []
                edu_metas = []
                
                for i, concept in enumerate(concepts):
                    # Richer context format for the LLM
                    text = f"Topic: {concept['topic']}\nQuestion: {concept['question']}\nExplanation: {concept['content']}"
                    
                    edu_ids.append(f"edu_{i}")
                    edu_docs.append(text)
                    edu_metas.append({
                        "source": "educational_concept", 
                        "topic": concept['topic']
                    })
                
                if edu_ids:
                    collection.add(
                        ids=edu_ids,
                        documents=edu_docs,
                        metadatas=edu_metas
                    )
                    print(f"Successfully embedded {len(edu_ids)} educational concepts.")
            else:
                print("Warning: educational_concepts.json not found.")
        else:
             print("Educational concepts already present.")
             
    except Exception as e:
        print(f"Error checking educational concepts: {e}")

def semantic_search(query, n_results=3, where=None):
    """
    Performs semantic retrieval.
    Useful for 'Educational' or 'Broad' queries where SQL is too rigid.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where
    )
    
    # Flatten results
    if results['documents']:
        docs = results['documents'][0]
        return "\n\n".join(docs)
    return ""
