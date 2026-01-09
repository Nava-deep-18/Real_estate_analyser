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
    
    /* Remove white background from the top header */
    header[data-testid="stHeader"] {
        background: transparent !important;
        backdrop-filter: none !important;
    }

    /* Remove white background from the bottom sticky input container */
    div[data-testid="stBottom"] > div {
        background-color: transparent !important;
        background: transparent !important;
    }
    
    /* --- 2. TYPOGRAPHY --- */
    h1, h2, h3, p, div, span, li {
        font-family: 'Outfit', sans-serif !important;
        color: #e2e8f0 !important;
    }

    h1 {
        background: linear-gradient(to right, #60a5fa, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700 !important;
    }

    /* --- 3. CHAT INTERFACE --- */
    
    /* Transparent container for messages */
    .stChatMessage {
        background-color: transparent !important;
    }

    /* Bubble styling */
    .stChatMessageContent {
        background: rgba(30, 41, 59, 0.7) !important;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* User Message - Blue Tint */
    div[data-testid="stChatMessage"]:nth-child(odd) .stChatMessageContent {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(37, 99, 235, 0.15) 100%) !important;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }

    /* --- 4. INPUT FIELD STYLING --- */
    .stChatInputContainer textarea {
        background-color: #1e293b !important; /* Dark Slate */
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px;
    }
    
    .stChatInputContainer textarea:focus {
        border-color: #60a5fa !important;
        box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.3) !important;
    }

    /* --- 5. SIDEBAR & COMPONENTS --- */
    section[data-testid="stSidebar"] {
        background-color: #0b1120 !important; /* Very Dark Blue */
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    div[data-testid="stExpander"] {
        background-color: transparent !important;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
    }
    
    /* --- 6. TEXT AREA & INPUT WIDGETS (Fixes White Schema Box) --- */
    .stTextArea textarea {
        background-color: rgba(30, 41, 59, 0.6) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }
    
    .stTextArea label {
        color: #e2e8f0 !important;
    }

    .stSpinner > div {
        border-color: #60a5fa transparent #c084fc transparent !important;
    }

</style>
""", unsafe_allow_html=True)

# Application Title
st.title("🏠 Real Estate Investment Analyzer")
st.markdown("### Deterministic Backend • RAG Explanation Layer")

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
                conn = db.init_db(reload=False)
                df = pd.read_sql("SELECT * FROM properties", conn)
                vector_store.initialize_vector_store(df)
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
    st.info("This panel shows the RAG pipeline steps for verification.")

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
