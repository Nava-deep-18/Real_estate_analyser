import pandas as pd
import sqlite3
import os

DB_PATH = "real_estate.db"
CSV_PATH = "kolkata_buy_vs_rent_full_analysis.csv"

def init_db(reload=True):
    """
    Initializes the SQLite database.
    If reload is True, it converts the detailed analysis CSV into a SQL table.
    """
    # 1. Connect to SQLite
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    
    if reload: 
        if os.path.exists(CSV_PATH):
            # 2. Load Data
            df = pd.read_csv(CSV_PATH)
            
            # 3. Clean Columns for SQL (remove spaces, special chars)
            # We want deterministic SQL queries, so simple names are better
            df.columns = [c.strip().replace(" ", "_").replace("(", "").replace(")", "").lower() for c in df.columns]
            
            # Explicitly ensure numeric types for critical calculation fields if they were read as strings
            # Only strictly necessary if the CSV has formatting like "1,000"
            # df['price'] = pd.to_numeric(df['price'], errors='coerce') 
            
            # 4. Write to SQL
            df.to_sql("properties", conn, if_exists="replace", index=False)
            print("Database initialized and data loaded from CSV.")
        else:
            print(f"Error: {CSV_PATH} not found.")
            
    return conn

def get_schema():
    """
    Returns the schema of the properties table to help with SQL generation.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(properties)")
    columns = cursor.fetchall()
    conn.close()
    
    # Format: (cid, name, type, notnull, dflt_value, pk)
    # We just return name and type
    schema_str = "Table: properties\nColumns:\n"
    for col in columns:
        schema_str += f"- {col[1]} ({col[2]})\n"
    return schema_str

def execute_sql_query(query):
    """
    Executes a read-only SQL query and returns the results as a DataFrame.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        # Security check: rudimentary prevention of write operations
        if any(x in query.upper() for x in ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER']):
            return None, "Error: Only SELECT queries are permitted."
            
        df = pd.read_sql_query(query, conn)
        return df, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()
