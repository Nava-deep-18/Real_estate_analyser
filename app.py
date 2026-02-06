try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import os
from rag import db, rag_engine, vector_store

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def render_glass_card(title, caption, fig, height=450):
    """Wraps a native Plotly chart in a styled Container to create a Glassmorphism Card effect."""
    with st.container(border=True):
        st.markdown(f'<h4 style="color: #e2e8f0; margin: 0; font-weight: 600;">{title}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p style="color: #94a3b8; font-size: 0.9rem; margin-top: 5px; margin-bottom: 15px;">{caption}</p>', unsafe_allow_html=True)
        if fig:
           
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(0,0,0,0)", 
                margin=dict(t=20, l=0, r=0, b=0), 
                height=height-80
            )
            st.plotly_chart(fig, use_container_width=True)

def inject_custom_css(background_image_path="image.jpg"):
    bg_style = ""
    if os.path.exists(background_image_path):
        bin_str = get_base64_of_bin_file(background_image_path)
        bg_style = f"""background-image: linear-gradient(rgba(15, 23, 42, 0.75), rgba(15, 23, 42, 0.85)), url("data:image/jpg;base64,{bin_str}");"""
    else:
        bg_style = "background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);"

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@600;800&family=Playfair+Display:wght@700&display=swap');
        .stApp {{ {bg_style} background-size: cover; background-attachment: fixed; font-family: 'Outfit', sans-serif; }}
        html, body, [class*="css"] {{ font-family: 'Outfit', sans-serif !important; }}
        header[data-testid="stHeader"], div[data-testid="stBottom"] > div {{ background: transparent !important; }}
        .block-container {{ padding-top: 1rem !important; }}
        h1, h2, h3, h4, h5, h6, p, li, span, div {{ color: #e2e8f0; }}
        h1 {{ background: linear-gradient(to right, #94a3b8, #f1f5f9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-family: 'Playfair Display', serif !important; font-weight: 700 !important; font-size: 3.5rem !important; letter-spacing: 0px; margin-bottom: 0.5rem !important; }}
        section[data-testid="stSidebar"] {{ background-color: #0b1120 !important; border-right: 1px solid rgba(255,255,255,0.05); }}
        .sidebar-header {{ font-size: 1.1rem; font-weight: 600; color: #94a3b8; margin-top: 20px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }}
        div[role="radiogroup"] {{ background-color: #1e293b; padding: 5px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }}
        div[role="radiogroup"] label:hover {{ color: #e2e8f0 !important; }}
        div[data-testid="stMetric"] {{ background: rgba(30, 41, 59, 0.4) !important; backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px !important; padding: 15px !important; }}
        div[data-testid="stMetric"]:hover {{ transform: translateY(-2px); border-color: rgba(226, 232, 240, 0.4); }}
        [data-testid="stMetricLabel"] {{ font-size: 13px !important; color: #94a3b8 !important; font-weight: 500 !important; }}
        [data-testid="stMetricValue"] {{ font-size: 24px !important; font-weight: 700 !important; color: #e2e8f0 !important; }}
        
        .stChatInputContainer textarea {{ background-color: #0f172a !important; color: #f8fafc !important; border-radius: 25px !important; border: 1px solid rgba(255,255,255,0.1) !important; }}
        .stChatInputContainer textarea:focus {{ border-color: #e2e8f0 !important; box-shadow: 0 0 0 1px #e2e8f0 !important; }}
        .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {{ background-color: rgba(30, 41, 59, 0.4); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); }}
        .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {{ background-color: rgba(15, 23, 42, 0.6); border-left: 3px solid #e2e8f0; border-radius: 0 15px 15px 0; }}
        
        .stTabs [data-baseweb="tab-list"] {{ background-color: transparent; gap: 8px; }}
        .stTabs [data-baseweb="tab"] {{ background-color: rgba(255,255,255,0.05); border-radius: 8px; color: #cbd5e1; border: 1px solid transparent; padding: 8px 16px; }}
        .stTabs [aria-selected="true"] {{ background-color: rgba(226, 232, 240, 0.1) !important; color: #e2e8f0 !important; border-color: rgba(226, 232, 240, 0.3) !important; }}
        
        /* Glass Card Container Styling */
        div[data-testid="stVerticalBlockBorderWrapper"] > div > div {{ 
            background: rgba(30, 41, 59, 0.5) !important; 
            backdrop-filter: blur(12px) !important; 
            border-radius: 16px !important; 
            border: 1px solid rgba(255, 255, 255, 0.1) !important; 
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.3) !important;
            padding: 24px !important; /* Increased padding */
        }}
        div[data-testid="stVerticalBlockBorderWrapper"] h4 {{ margin-top: 0 !important; padding-top: 0 !important; font-size: 1.3rem !important; }}
        
        /* Code Block Styling */
        div[data-testid="stCode"], code {{ 
            background-color: #0f172a !important; 
            color: #e2e8f0 !important; 
            border-radius: 8px !important; 
        }}
        div[data-testid="stCode"] pre {{
            background-color: #0f172a !important;
        }}

        /* Dataframe/Table Fixes */
        div[data-testid="stDataFrame"] {{
            background-color: transparent !important;
        }}
        div[data-testid="stDataFrame"] div[class*="stDataFrame"] {{
            background-color: transparent !important;
        }}
        /* Table Headers */
        div[data-testid="stDataFrame"] th {{
            background-color: #1e293b !important;
            color: #e2e8f0 !important; 
            border-bottom: 1px solid rgba(255,255,255,0.1) !important;
        }}
        /* Table Cells */
        div[data-testid="stDataFrame"] td {{
            color: #cbd5e1 !important;
            background-color: rgba(30, 41, 59, 0.4) !important;
            border-bottom: 1px solid rgba(255,255,255,0.05) !important;
        }}
        /* Row Hover */
        div[data-testid="stDataFrame"] tr:hover td {{
             background-color: rgba(255, 255, 255, 0.1) !important;
        }}
    </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="Real Estate Investment Analyzer", layout="wide")
inject_custom_css()
st.title("Real Estate Investment Analyzer")

if "messages" not in st.session_state: st.session_state.messages = []

@st.cache_resource
def init_data():
    conn = db.init_db(reload=True)
    return db.get_schema()

try:
    schema = init_data()
    if "vector_db_ready" not in st.session_state:
        with st.spinner("Checking AI Knowledge Base..."):
             if vector_store.needs_hydration():
                 conn = db.init_db(reload=False)
                 vector_store.initialize_vector_store(pd.read_sql("SELECT * FROM properties", conn))
             else:
                 vector_store.initialize_vector_store(None)
             st.session_state.vector_db_ready = True
    st.success("👋 Welcome! I'm ready to help. Ask me about property prices, trends, or specific locations.")
except Exception as e:
    st.error(f"System Error: {e}")
    st.stop()

# SIDEBAR & NAVIGATION 
page = st.sidebar.radio("Mode", ["🤖 AI Assistant", "📈 Market Analytics"])

with st.sidebar:
    st.markdown("---")
    st.markdown('<p class="sidebar-header">📊 Market Pulse</p>', unsafe_allow_html=True)
    try:
        conn = db.init_db(reload=False)
        stats = pd.read_sql("SELECT COUNT(*) as c, AVG(price) as p, AVG(area) as a FROM properties", conn).iloc[0]
        st.metric("Total Properties", f"{stats['c']}")
        st.metric("Avg Price", f"₹{stats['p']/100000:.1f} Lakhs")
        st.metric("Avg Size", f"{stats['a']:,.0f} sqft")
    except: st.error("Stats unavailable")
    
    st.markdown("---")
    st.info("**Hybrid RAG System**\n\n• Router: Intent\n• SQL: Filtering\n• Vector: Semantic Search\n• LLM: Synthesis")

# PAGE LOGIC 
if page == "🤖 AI Assistant":
    if not st.session_state.messages:
        st.markdown('<div style="text-align: center; margin-top: 10px; margin-bottom: 20px;"><h1 style="font-size: 3.5rem;">Hello, Investor.</h1><p style="color: #94a3b8; font-size: 1.2rem;">I\'m your AI Real Estate Consultant.</p></div>', unsafe_allow_html=True)
        cols = st.columns(3)
        prompts = [("🔍 Find", "Show me 3 BHK flats under 80L"), ("📊 Compare", "Compare rental yield of AA1 vs AA2"), ("💡 Learn", "How Buy vs rent is decided")]
        for c, (h, p) in zip(cols, prompts):
            c.markdown(f'<div class="css-card" style="padding: 20px; text-align: center;"><h3 style="color: #e2e8f0;">{h}</h3><p style="font-size: 0.9rem;">"{p}"</p></div>', unsafe_allow_html=True)

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"])

    if prompt := st.chat_input("Ask about properties..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.status("Processing Query...", expanded=True) as status:
            intent = rag_engine.classify_intent(prompt)
            st.write(f"**Intent:** `{intent}`")
            explanation, context_df = "", None
            
            if intent in ["FILTER", "COMPARE", "EXPLAIN"]:
                sql = rag_engine.generate_sql_query(prompt, schema)
                st.code(sql, "sql")
                context_df, error = db.execute_sql_query(sql)
                if error: 
                    st.error(f"SQL Error: {error}")
                    explanation = f"Error: {error}"
                else: 
                    st.write(f"✅ Retrieved {len(context_df)} records.")
                    explanation = rag_engine.create_explanation_records(context_df)
            elif intent == "EDUCATIONAL":
                explanation = "General educational question."
            
            response = rag_engine.generate_rag_response(prompt, explanation, intent)
            status.update(label="Complete", state="complete", expanded=False)
            
        st.chat_message("assistant").markdown(response)
        if context_df is not None and not context_df.empty:
            with st.expander("View Raw Data"): st.dataframe(context_df)
        st.session_state.messages.append({"role": "assistant", "content": response})

elif page == "📈 Market Analytics":
    st.subheader("📈 Real Estate Market Insights")
    try:
        df = pd.read_sql("SELECT * FROM properties", db.init_db(reload=False))
        if df.empty:
            st.warning("No data available.")
        else:
            df['price_per_sqft'] = df['price'] / df['area']
            if 'rent' in df.columns: df['rental_yield'] = (df['rent'] * 12 / df['price']) * 100
            
            t1, t2, t3, t4 = st.tabs(["📍 Location", "💰 Market", "💎 Value", "🏦 Wealth"])
            
            with t1:
                loc = df.groupby('address').agg({'price_per_sqft':'mean', 'rental_yield':'mean', 'price':'count'}).reset_index()
                loc = loc[loc['price']>5].sort_values('price_per_sqft', ascending=False).head(15)
                render_glass_card("Price Efficiency", "Top areas by Price/Sqft", px.bar(loc, x='address', y='price_per_sqft', color='price_per_sqft', color_continuous_scale='RdBu_r'))
                render_glass_card("Rental Yields", "Top areas by Rental Yield", px.bar(loc.sort_values('rental_yield', ascending=False), x='address', y='rental_yield', color='rental_yield', color_continuous_scale='Turbo'))
            
            with t2:
                c1, c2 = st.columns(2)
                with c1: render_glass_card("Price Ranges", "Min/Max Price by Bedroom", px.box(df, x='bedrooms', y='price', color='bedrooms'), height=500)
                with c2: render_glass_card("Buy vs Rent", "System Recommendation Split", px.pie(df, names='decision', color_discrete_sequence=px.colors.sequential.RdBu), height=500)
            
            with t3:
                render_glass_card("Undervalued Finder", "Properties below trend line", px.scatter(df, x='area', y='price', color='decision', size='bedrooms', hover_data=['address'], trendline="ols", template="plotly_dark"))
                
            with t4:
                if 'wealth_difference' in df.columns:
                    df['wealth_difference'] = pd.to_numeric(df['wealth_difference'], errors='coerce')
                    wealth = df.groupby('address')['wealth_difference'].mean().reset_index().sort_values('wealth_difference', ascending=False).head(15)
                    render_glass_card("Wealth Potential", "Avg Wealth Gain (Buy vs Rent)", px.bar(wealth, x='address', y='wealth_difference', color='wealth_difference', color_continuous_scale='Viridis'))
                else: st.info("Wealth data missing.")

    except Exception as e: st.error(f"Error: {e}")
