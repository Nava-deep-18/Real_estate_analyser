
import os
import json
import pandas as pd
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

client = openai.OpenAI(
    api_key=api_key,
    base_url=base_url
)

def classify_intent(query):
    """
    Classifies the user query into one of the allowed intents:
    FILTER, EXPLAIN, COMPARE, EDUCATIONAL.
    """
    system_prompt = """
    You are an Intent Classifier for a Real Estate Investment Analyzer.
    Classify the user's query into EXACTLY one of the following categories:
    
    1. FILTER: Requests for listings, searching properties, or subsets (e.g., "Show me 3 BHKs in New Town", "Properties under 50L").
    2. EXPLAIN: Requests for reasoning behind a specific decision or property detail (e.g., "Why is this property a BUY?", "Explain the tax benefits for this flat").
    3. COMPARE: Requests to evaluate two or more properties against each other (e.g., "Compare the property in New Town vs the one in Salt Lake").
    4. EDUCATIONAL: General questions about tax concepts, financial logic, or definitions (e.g., "How is rental yield calculated?", "What is Section 24b?").
    
    Return ONLY the category name. Do not add punctuation or explanation.
    """
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip().upper()
    except Exception as e:
        return "FILTER" # Fallback safe default

def generate_sql_query(query, schema):
    """
    Converts a natural language query into a SQL query based on the schema.
    Strictly for filtering and sorting.
    """
    system_prompt = f"""
    You are a SQL Generator for a Real Estate database.
    Your task is to convert the User Query into a valid SQLite SQL query.
    
    SCHEMA:
    {schema}
    
    RULES:
    1. Table name is 'properties'.
    2. ONLY use SELECT statements.
    3. Select ALL columns (*) unless specific ones are irrelevant, but usually * is safest for the explanation layer.
    4. Do not hallucinates column names. Use ONLY those in the schema.
    5. 'wealth_difference' > 0 usually implies BUY is better, but check 'decision' column ('BUY' or 'RENT').
    6. For 'undervalued' or 'good deals', you might sort by wealth_difference DESC or yield DESC.
    7. Limit results to 5 unless asked otherwise.
    
    Return ONLY the SQL query. No markdown formatting.
    """
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.0
        )
        sql = response.choices[0].message.content.strip()
        # Clean potential markdown
        sql = sql.replace("```sql", "").replace("```", "").strip()
        return sql
    except Exception as e:
        print(f"Error generating SQL: {e}")
        
        # Simple Fallback Logic for Offline Mode
        query_lower = query.lower()
        conditions = []
        
        # Bed count detection
        import re
        bed_match = re.search(r'(\d+)\s*bhk', query_lower)
        if bed_match:
            conditions.append(f"bedrooms = {bed_match.group(1)}")
            
        # Location detection (simple heuristic)
        locations = ["new town", "salt lake", "rajarhat", "south kolkata"]
        for loc in locations:
            if loc in query_lower:
                conditions.append(f"address LIKE '%{loc}%'")
                
        # Rent vs Buy
        if "rent" in query_lower and "buy" not in query_lower:
             conditions.append("decision = 'RENT'")
        elif "buy" in query_lower and "rent" not in query_lower:
             conditions.append("decision = 'BUY'")

        if conditions:
            return f"SELECT * FROM properties WHERE {' AND '.join(conditions)} LIMIT 5"
            
        return "SELECT * FROM properties LIMIT 5"

def create_explanation_records(df):
    """
    Converts the DataFrame rows into text-based Property Explanation Records.
    Ref: Section 6 of Manual.
    """
    records = []
    
    if df is None or df.empty:
        return "No properties found matching the criteria."
        
    for index, row in df.iterrows():
        # Handle potential missing keys gracefully
        try:
            name = row.get('name', 'Unknown Property')
            addr = row.get('address', 'Unknown Location')
            price = row.get('price', 'N/A')
            rent = row.get('rent', 'N/A')
            area = row.get('area', 'N/A')
            decision = row.get('decision', 'N/A')
            wealth_diff = row.get('wealth_difference', '0')
            emi = row.get('monthly_emi', 'N/A') # Assuming column name
            
            total_tax = row.get('total_tax_paid', 'N/A')
            regime = row.get('chosen_tax_regime', 'N/A')
            
            # Create a structured text block
            record = f"""
            --- PROPERTY RECORD {index+1} ---
            Name: {name}
            Location: {addr}
            Size: {area} sqft
            Financials: Price: {price}, Monthly Rent: {rent}
            Analysis Decision: {decision}
            Wealth Difference (Buy vs Rent over 20y): {wealth_diff}
            Monthly EMI: {emi}
            Tax Strategy: {regime} with Total Tax Paid: {total_tax}
            
            (Note: This decision is based on a deterministic backend calculation. 
            Positive wealth difference favors BUY, negative favors RENT.)
            -------------------------------
            """
            records.append(record)
        except Exception as e:
            records.append(f"Error parsing row {index}: {e}")
            
    return "\n".join(records)

# from rag import vector_store

# ... (rest of imports)

def generate_rag_response(query, explanation_context, intent):
    """
    Generates the final human-readable response using the Explanation Records.
    Ref: Section 10 of Manual.
    """
    
    # Robust Hybrid Retrieval Logic
    additional_context = ""
    if intent == "EDUCATIONAL" or "No properties found" in explanation_context:
        try:
            # We strictly protect this call so it never crashes the main app
            from rag import vector_store
            
            # Refined Retrieval Strategy based on Intent
            if intent == "EDUCATIONAL":
                # Strict Filtering: Only look at educational concepts, and take the single best match
                # to avoid confusing the LLM with contradictory "rules of thumb" vs "exact methodology"
                vector_results = vector_store.semantic_search(query, n_results=1, where={"source": "educational_concept"})
            else:
                # Broad Retrieval: Look at everything (properties + concepts)
                vector_results = vector_store.semantic_search(query, n_results=3)

            if vector_results:
                 additional_context = f"\n\n--- RELEVANT KNOWLEDGE (Vector Retrieval) ---\n{vector_results}\n"
        except Exception as e:
            print(f"Vector search warning: {e}")
            
    final_context = explanation_context + additional_context

    previous_context_instruction = ""
    if intent == 'EDUCATIONAL':
        previous_context_instruction = "You are answering an educational question based on the retrieved knowledge."
    else:
        previous_context_instruction = "You are explaining verified financial results. Do NOT perform new calculations."

    system_prompt = f"""
    You are the Real Estate Investment Assistant.
    {previous_context_instruction}
    
    Your goal is to answer the user's query using the provided Context Data.
    
    CONTEXT DATA:
    {final_context}
    
    STRICT RULES:
    1. Do not invent numbers. Use only what is in the Context Data.
    2. If the user asks for a calculation (e.g., "Calculate the EMI"), REFUSE politely and state that the backend has already computed the optimal values shown in the records.
    3. Refer to the 'Analysis Decision' (BUY vs RENT) as the system's recommendation.
    4. Be professional and concise.
    
    IMPORTANT CLARIFICATION ON 'RENT' DECISION:
    When the decision is 'RENT', you MUST explain clearly that this means:
    "It is financially better to invest your capital in market instruments (e.g., SIPs) and rent a SIMILAR property in the same area."
    Clarify that the user should NOT try to rent *this specific* property (which is for sale), but rather look for a comparable rental to save wealth.
    """
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_msg = str(e)
        if "insufficient_quota" in error_msg:
             return (
                 "**⚠️ API Quota Exceeded (Offline Mode)**\n\n"
                 "I cannot generate a new custom explanation because the provided OpenAI API key has run out of credits.\n\n"
                 "**However, here is the verified data from the database:**\n"
                 "The system successfully filtered the properties. Please refer to the 'Explanation Data' or 'Raw Data' section to see the exact financial details computed by the backend."
             )
        return f"Error generating response: {e}"
