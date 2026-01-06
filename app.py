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


# Custom CSS for Premium Look
st.markdown("""
<style>
    /* Force text color for markdown to ensure visibility */
    .stMarkdown, p, h1, h2, h3, li {
        color: #2c3e50 !important;
    }
    
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        color: #2c3e50;
        font-weight: 700;
    }
    
    /* Styling for chat messages */
    .stChatMessage {
        background-color: transparent !important;
    }
    
    .stChatMessageContent {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        color: #2c3e50 !important;
    }
</style>
""", unsafe_allow_html=True)

# Application Title
st.title("🏠 Real Estate Investment Ruler")
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

