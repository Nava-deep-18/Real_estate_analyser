try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import streamlit as st
import pandas as pd
from rag import db, rag_engine, vector_store
import base64
import os
import plotly.express as px

# Function to encode image to base64
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Page Config
st.set_page_config(
    page_title="Real Estate Investment Analyzer",
    layout="wide"
)

# Custom CSS for Premium Glassmorphism Look (Fixed White Areas)
background_image_path = "image.jpg"
background_style = ""

if os.path.exists(background_image_path):
    bin_str = get_base64_of_bin_file(background_image_path)
    # Reduced overlay slightly for better brightness (0.9 -> 0.75) and visibility
    background_style = f"""
    .stApp {{
        background-image: linear-gradient(rgba(15, 23, 42, 0.75), rgba(15, 23, 42, 0.85)), url("data:image/jpg;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Outfit', sans-serif;
    }}
    """
else:
    # Fallback to gradient if image missing
    background_style = """
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        font-family: 'Outfit', sans-serif;
    }
    """

st.markdown(f"""
<style>
    /* Import Google Font 'Outfit' */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');

    /* --- 1. GLOBAL RESET & BACKGROUND --- */
    {background_style}
    
    /* Remove white background from header/footer */
    header[data-testid="stHeader"] {{
        background: transparent !important;
    }}
    div[data-testid="stBottom"] > div {{
        background-color: transparent !important;
    }}
    
    /* PULL CONTENT UP: Reduce top padding of the main container */
    .block-container {{
        padding-top: 1rem !important;
    }}
    
    /* --- 2. TEXT --- */
    /* Target specific text elements rather than global wildcards to avoid overlay issues */
    .stMarkdown, h1, h2, h3, p, li {{
        color: #e2e8f0 !important;
    }}

    h1 {{
        /* WARM GOLD GRADIENT - Premium look against dark backdrops */
        background: linear-gradient(to right, #facc15, #f8fafc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 800 !important;
        font-size: 3rem !important;
        letter-spacing: -1px;
    }}

    /* --- 3. INPUTS --- */
    .stChatInputContainer textarea {{
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }}
    
    .stTextArea textarea {{
        background-color: rgba(30, 41, 59, 0.6) !important;
        color: #f8fafc !important;
    }}

    /* --- 4. SIDEBAR & METRICS --- */
    section[data-testid="stSidebar"] {{
        background-color: #0b1120 !important;
    }}

    /* Fix Metric Visibility */
    [data-testid="stMetricValue"] {{
        color: #e2e8f0 !important;
        font-size: 26px !important;
        font-weight: 600 !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: #94a3b8 !important; /* Lighter Grey */
        font-size: 14px !important;
    }}
</style>
""", unsafe_allow_html=True)

# Application Title
st.title("Real Estate Investment Analyzer")


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

# Sidebar Navigation
page = st.sidebar.radio("Mode", ["🤖 AI Assistant", "📈 Market Analytics"], index=0)

# Sidebar for Creative/Analytical Specs
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📊 Market Pulse")
    
    # Quick Stats from DB
    try:
        conn = db.init_db(reload=False)
        total_props = pd.read_sql("SELECT COUNT(*) as count FROM properties", conn).iloc[0]['count']
        
        # Load simpler stats for sidebar here
        avg_price = pd.read_sql("SELECT AVG(price) as val FROM properties", conn).iloc[0]['val']
        avg_area = pd.read_sql("SELECT AVG(area) as val FROM properties", conn).iloc[0]['val']
        
        # Display - Stacked for better visibility
        st.metric("Total Properties", f"{total_props}")
        st.metric("Avg Price", f"₹{avg_price/100000:.1f} Lakhs")
        st.metric("Avg Size", f"{avg_area:,.0f} sqft")
        
    except Exception as e:
        st.error("Stats unavailable")

    st.markdown("---")
    st.markdown("### 🧠 AI Architecture")
    st.info(
        """
        **Hybrid RAG System**
        
        • **Router**: Classifies intent
        • **SQL**: Filtering
        • **Vector**: Knowledge
        • **LLM**: Synthesis
        """
    )
    
    with st.expander("Debug Mode (Schema)"):
         st.text_area("Schema", schema, height=150, disabled=True)

# ----------------- MAIN CONTENT -----------------

if page == "🤖 AI Assistant":
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

elif page == "📈 Market Analytics":
    st.subheader("📈 Real Estate Market Insights")
    
    # Lazy load full data for analytics
    try:
        conn = db.init_db(reload=False)
        df_full = pd.read_sql("SELECT * FROM properties", conn)
        
        # Pre-process for advanced metrics
        # 1. Price per Sqft
        df_full['price_per_sqft'] = df_full['price'] / df_full['area']
        
        # 2. Rental Yield (if rent exists)
        if 'rent' in df_full.columns:
             df_full['rental_yield'] = (df_full['rent'] * 12 / df_full['price']) * 100
             
        # Filter: Remove unrealistic yields > 6%
        if 'rental_yield' in df_full.columns:
            df_full = df_full[df_full['rental_yield'] <= 6]
        
        if df_full.empty:
            st.warning("No data available to generate analytics.")
        else:
            # Create Tabs for different views
            tab1, tab2, tab3 = st.tabs(["📍 Location & Value", "💰 Market Depth", "💎 Deal Discovery"])
            
            # --- TAB 1: LOCATION & VALUE ---
            with tab1:
                st.markdown("#### 1. Price Efficiency by Location")
                st.caption("Which areas are expensive per sqft? (Heatmap logic)")
                
                # Group by Location
                loc_stats = df_full.groupby('address').agg({
                    'price_per_sqft': 'mean',
                    'rental_yield': 'mean',
                    'price': 'count'
                }).reset_index()
                
                # Filter low data points
                loc_stats = loc_stats[loc_stats['price'] > 5].sort_values('price_per_sqft', ascending=False).head(15)
                
                # Chart 1: Price per Sqft
                fig_pps = px.bar(
                    loc_stats, x='address', y='price_per_sqft',
                    color='price_per_sqft',
                    title="Avg Price per Sqft by Top Locations",
                    labels={'price_per_sqft': 'Price/Sqft (₹)', 'address': 'Location'},
                    color_continuous_scale='RdBu_r'
                )
                st.plotly_chart(fig_pps, width="stretch")
                
                st.markdown("#### 2. Rental Yield Hotspots")
                # Chart 2: Yield
                fig_yield = px.bar(
                    loc_stats.sort_values('rental_yield', ascending=False), 
                    x='address', y='rental_yield',
                    color='rental_yield',
                    title="Top Areas for Rental Income (High Yield)",
                    labels={'rental_yield': 'Yield (%)', 'address': 'Location'},
                    color_continuous_scale='Turbo' 
                )
                st.plotly_chart(fig_yield, width="stretch")

            # --- TAB 2: MARKET DEPTH ---
            with tab2:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### 3. Bedroom Price Ranges")
                    # Box Plot to show ranges
                    fig_box = px.box(
                        df_full, x='bedrooms', y='price', 
                        color='bedrooms',
                        title="Price Min/Max Range by Bedroom Count",
                        points="outliers"
                    )
                    st.plotly_chart(fig_box, width="stretch")
                    
                with c2:
                    st.markdown("#### 4. Buy vs Rent Strategy")
                    # Distribution of Decisions
                    fig_pie = px.pie(
                        df_full, names='decision', 
                        title="System Recommendation Split (Buy vs Rent)",
                        color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    st.plotly_chart(fig_pie, width="stretch")

            # --- TAB 3: DEAL DISCOVERY ---
            with tab3:
                st.markdown("#### 5. Undervalued Property Finder")
                st.caption("Properties BELOW the trend line offer better value (larger size for lower price). Hover to see details.")
                
                # Scatter with Trendline
                fig_scatter = px.scatter(
                    df_full, x='area', y='price',
                    color='decision', 
                    size='bedrooms',
                    hover_data=['name', 'address', 'price_per_sqft'],
                    trendline="ols", # Ordinary Least Squares regression
                    title="Correlation: Price vs Area (with Fair Value Line)",
                    labels={'area': 'Size (sqft)', 'price': 'Price (₹)'},
                    template="plotly_dark"
                )
                st.plotly_chart(fig_scatter, width="stretch")

    except Exception as e:
        st.error(f"Could not load analytics: {e}")
