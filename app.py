import streamlit as st
import pandas as pd
from rag import db, rag_engine, vector_store
import os

# Page Config
st.set_page_config(
    page_title="Real Estate Investment Analyzer",
    page_icon="🏠",
    layout="wide"
)

# Custom CSS for Premium Glassmorphism Look (Fixed White Areas)
st.markdown("""
<style>
    /* Import Google Font 'Outfit' */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');

    /* --- 1. GLOBAL RESET & BACKGROUND --- */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        font-family: 'Outfit', sans-serif;
    }
    
    /* Remove white background from header/footer */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    div[data-testid="stBottom"] > div {
        background-color: transparent !important;
    }
    
    /* --- 2. TEXT --- */
    /* Target specific text elements rather than global wildcards to avoid overlay issues */
    .stMarkdown, h1, h2, h3, p, li {
        color: #e2e8f0 !important;
    }

    h1 {
        background: linear-gradient(to right, #60a5fa, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* --- 3. INPUTS --- */
    .stChatInputContainer textarea {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    
    .stTextArea textarea {
        background-color: rgba(30, 41, 59, 0.6) !important;
        color: #f8fafc !important;
    }

    /* --- 4. SIDEBAR --- */
    section[data-testid="stSidebar"] {
        background-color: #0b1120 !important;
    }
</style>
""", unsafe_allow_html=True)

# Application Title
st.title("🏠 Real Estate Investment Analyzer")
st.markdown("### • Built using RAG")

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize DB (Cached)
@st.cache_resource
def initialize_system():
    conn = db.init_db(reload=True)
    return db.get_schema()

# Initialize Vector Store (Lazy Load with Session State)
def ensure_vector_db():
    if "vector_db_ready" not in st.session_state:
        with st.spinner("Checking AI Knowledge Base..."):
            try:
                # OPTIMIZATION: Check if Vector DB is already hydrated to avoid expensive SQL read
                if vector_store.needs_hydration():
                    conn = db.init_db(reload=False)
                    df = pd.read_sql("SELECT * FROM properties", conn)
                    vector_store.initialize_vector_store(df)
                else:
                    # DB exists! Skip loading the dataframe, just check educational concepts
                    vector_store.initialize_vector_store(df=None)
                
                st.session_state.vector_db_ready = True
            except Exception as e:
                st.error(f"Vector DB Init Failed: {e}")

try:
    schema = initialize_system()
    st.success("System Online: Database Loaded & Schema Verified")
    ensure_vector_db()

except Exception as e:
    st.error(f"System Error: {e}")
    st.stop()

# Sidebar for Debugging/Transparency
with st.sidebar:
    st.header("System Internals")
    st.text_area("Database Schema", schema, height=200, disabled=True)

# Chat Interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("Ask about properties (e.g., 'Show me 3 BHK in New Town')"):
    # 1. Display User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Process Intent
    with st.status("Processing Query...", expanded=True) as status:
        
        # Step A: Intent Classification
        st.write("🔍 Classifying Intent...")
        intent = rag_engine.classify_intent(prompt)
        st.write(f"**Intent Detected:** `{intent}`")
        
        # Step B: SQL Generation (if needed)
        explanation_data = ""
        context_df = None
        
        if intent in ["FILTER", "COMPARE", "EXPLAIN"]:
            st.write("💻 Generating SQL Query...")
            sql_query = rag_engine.generate_sql_query(prompt, schema)
            st.code(sql_query, language="sql")
            
            # Step C: Execution
            st.write("🗄️ Retrieving Data...")
            context_df, error = db.execute_sql_query(sql_query)
            
            if error:
                st.error(f"SQL Error: {error}")
                explanation_data = f"Error executing retrieval: {error}"
            else:
                record_count = len(context_df) if context_df is not None else 0
                st.write(f"✅ Retrieved {record_count} records.")
                
                # Step D: Explanation Generation
                explanation_data = rag_engine.create_explanation_records(context_df)
        elif intent == "EDUCATIONAL":
            st.write("📚 Educational Query Detected. Skipping SQL.")
            explanation_data = "User asked a general educational question."
        
        # Step E: LLM Response
        st.write("🤖 Generating Response...")
        final_response = rag_engine.generate_rag_response(prompt, explanation_data, intent)
        
        status.update(label="Complete", state="complete", expanded=False)

    # 3. Display Assistant Response
    with st.chat_message("assistant"):
        st.markdown(final_response)
        
        # Optional: Show data table if available
        if context_df is not None and not context_df.empty:
            with st.expander("View Raw Data (Deterministic Output)"):
                st.dataframe(context_df)
                
    st.session_state.messages.append({"role": "assistant", "content": final_response})
