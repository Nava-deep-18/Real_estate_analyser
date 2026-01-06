import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
import os
import uuid

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
    Ingests the Property Explanation Records into ChromaDB.
    Strictly follows Section 6: "Only these explanation records are eligible for embedding."
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    
    # Get or Create Collection
    # existing_collections = client.list_collections() # Check if needs reset?
    # For prototype, we verify if it exists.
    
    try:
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)
        # If it has data, assume it's loaded. 
        if collection.count() > 0:
            print(f"Vector Store already contains {collection.count()} records.")
            return
    except:
        # Create if not exists
        collection = client.create_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)

    print("Hydrating Vector Store with Property Explanation Records...")
    
    ids = []
    documents = []
    metadatas = []
    
    for index, row in df.iterrows():
        # Generate the Explanation Record (Text)
        # Logic duplicated from rag_engine for consistency, ensuring identical formatting
        
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
        
        # Section 7: "Permitted embedding sources: Property explanation records"
        documents.append(explanation_text)
        ids.append(f"prop_{index}")
        metadatas.append({
            "name": name, 
            "location": addr,
            "decision": decision,
            "source": "csv_analysis"
        })
        
    # Batch Add
    BATCH_SIZE = 100
    for i in range(0, len(documents), BATCH_SIZE):
        collection.add(
            ids=ids[i:i+BATCH_SIZE],
            documents=documents[i:i+BATCH_SIZE],
            metadatas=metadatas[i:i+BATCH_SIZE]
        )
        
    print(f"Successfully embedded {len(documents)} records into ChromaDB.")

def semantic_search(query, n_results=3):
    """
    Performs semantic retrieval.
    Useful for 'Educational' or 'Broad' queries where SQL is too rigid.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    # Flatten results
    docs = results['documents'][0]
    return "\n\n".join(docs)
