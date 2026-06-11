
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
    Features robust error handling, spelling correction, and flexible number parsing.
    """
    system_prompt = f"""
    You are an expert SQL Generator for a Real Estate Analysis Database. 
    Your goal is to output VALID SQLite SQL based on the User's Query.

    DATABASE SCHEMA:
    {schema}

    -------------------------------------------------------------------------
    CRITICAL RULES - FOLLOW THESE STRICTLY:
    -------------------------------------------------------------------------
    1. **OUTPUT FORMAT**: 
       - Return *ONLY* the SQL query. 
       - Start with `SELECT * FROM properties`.
       - Do NOT output explanations or markdown formatting like "Here is the query".

    2. **SPELLING & FUZZY MATCHING**:
       - The user may make spelling mistakes (e.g., "kolkatta", "newtwn").
       - You MUST correct these key terms mentally and generate SQL with corrected wildcards.
       - ALWAYS use `LIKE` with wildcards for text fields.
       - Example: User "newtwn" -> SQL `address LIKE '%new town%' OR address LIKE '%newtown%'`.
       - Example: User "saltlake" -> SQL `address LIKE '%salt lake%' OR address LIKE '%saltlake%'`.

    3. **NUMBER PARSING**:
       - User may use shortcuts: 'k' (thousand), 'L' (Lakh/100,000), 'Cr' (Crore/10,000,000).
       - User may use currency symbols (₹, $, Rs).
       - YOU must convert these to pure integers in the SQL.
       - Example: "budget 20k to 30k" -> `rent BETWEEN 20000 AND 30000` (if renting) or `price BETWEEN ...` (if buying).
       - Example: "under 50L" -> `price < 5000000`.

    4. **INTENT FILTERING (Rent vs Buy)**:
       - **Rent Context**: If user says "rent", "lease", "to let", "booking" -> ADD `WHERE decision = 'RENT'`.
         - Use column `rent` for budget checks.
       - **Buy Context**: If user says "buy", "purchase", "invest", "sale" -> ADD `WHERE decision = 'BUY'`.
         - Use column `price` for budget checks.
       - If unclear, do not filter by decision, but default to checking `price` for budget unless 'rent' is implied by value size (<100k usually rent).

    5. **SORTING & LIMITS**:
       - "Best" usually means highest returns.
         - For BUY: `ORDER BY wealth_difference DESC`
         - For RENT: `ORDER BY wealth_difference ASC` (Optimized savings) or `rent ASC` (Cheapest).
       - "Cheapest" -> `ORDER BY price ASC` or `rent ASC`.
         - **DEFAULT LIMIT**: Always use `LIMIT 5` unless user asks for a specific number. 
       - Never return just 1 unless explicitly asked.


    6. **LOGIC CORRECTION (Checking for City Name)**:
       - **CRITICAL**: The database contains ONLY properties in **Kolkata**.
       - If user asks for "Kolkata", "Calcutta", or "city", do **NOT** add `address LIKE '%kolkata%'`. This excludes valid data where address is just "New Town" or "Salt Lake".
       - **ACTION**: Ignore "Kolkata" for location filtering. Only filter address if a *specific area* (e.g., "New Town", "Garia") is mentioned.
    -------------------------------------------------------------------------
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
        content = response.choices[0].message.content.strip()
        
        # --- ROBUST CLEANING ---
        import re
        # 1. Remove markdown code blocks (handle ```sql, ```sqlite, ```, etc)
        # Matches ```<optional_lang> <content> ```
        code_block = re.search(r"```(?:\w+)?\s*(SELECT.*?)```", content, re.DOTALL | re.IGNORECASE)
        if code_block:
            sql = code_block.group(1).strip()
        else:
            # 2. If no code blocks, look for the first SELECT statement
            select_match = re.search(r"(SELECT.*)", content, re.DOTALL | re.IGNORECASE)
            if select_match:
                sql = select_match.group(1).strip()
            else:
                # 3. Last resort clean
                sql = content.replace("```sql", "").replace("```sqlite", "").replace("```", "").strip()
        
        # FINAL SAFEGUARD: If SQL contains "LIKE '%kolkata%'" or similar, warn or strip it?
        # Better to rely on prompt, but we can do a quick replace if prompt fails.
        # Removing "AND address LIKE '%kolkata%'" risks breaking syntax if not careful.
        # We trust the prompt for now.
        
        return sql

    except Exception as e:
        print(f"Error generating SQL: {e}")
        # Fallback mechanism
        try:
            # Basic keyword extraction fallback
            conditions = []
            q = query.lower()
            if "rent" in q: conditions.append("decision = 'RENT'")
            elif "buy" in q: conditions.append("decision = 'BUY'")
            
            if "new town" in q or "newtown" in q: conditions.append("(address LIKE '%new town%' OR address LIKE '%newtown%')")
            
            base_sql = "SELECT * FROM properties"
            if conditions:
                base_sql += " WHERE " + " AND ".join(conditions)
            return base_sql + " LIMIT 5"
        except:
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
                vector_results = vector_store.semantic_search(query, n_results=5)

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
    
    EXPLAINING THE FINANCIAL DECISION:
      -Do mention the specific 'Wealth Difference' numeric value in the text.
    
    - **If 'RENT'**: 
      - Explain: "It is financially smarter to rent a SIMILAR property and invest the monthly savings (EMI vs Rent diff) into market instruments (SIPs)."
      - **CRITICAL HIGHLIGHT**: You MUST add the following clarification on a NEW LINE, using **BOLD** formatting to make it stand out:
      - "**NOTE: Clarify that the user should NOT try to rent *this specific* property (which is for sale), but rather look for a comparable rental to save wealth.
      
    - **If 'BUY'**:
      - Explain: "Buying this property and building equity outweighs the returns from renting and investing."
      -  Clarify: Ownership builds more net worth in this scenario.

    5. **PRESENTATION**: You MUST present **ALL** properties listed in the 'Context Data'.
       - If the context has 5 properties, you MUST write about all 5. 
       - Do NOT pick just the "best" one. The user wants to see the options.
       - Use a numbered list (1., 2., 3., etc) for clarity.
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
