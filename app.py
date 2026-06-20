import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Supply Chain PoC")
st.title("📦 Simple Inventory Dashboard")

# 1. Yahan apni Sheet ki details daalein
SHEET_ID = '1E5X0bWQ6P3HVHcjTZvsojrR1phu_sGd8f67cbz15RSk' # e.g., 1BxiMVs0XRA5nFMdKvBdBZjgm...
GID = '1019333533' # Aapke Live_Inventory tab ka GID number

# 2. Direct CSV export URL banayein
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# 3. Data load karne ka function (with caching to keep it fast)
@st.cache_data(ttl=60) # 60 seconds baad data auto-refresh hoga
def get_data_from_sheet():
    # Pandas directly URL se CSV padh sakta hai!
    df = pd.read_csv(CSV_URL)
    return df

# 4. Data dashboard mein show karein
try:
    df = get_data_from_sheet()
    st.success("✅ Google Sheet connected successfully!")
    
    # Executive KPIs
    col1, col2 = st.columns(2)
    # Assuming your sheet has columns 'SKU' and 'Stock on Hand'
    col1.metric("Total SKUs Managed", len(df))
    if 'Stock on Hand' in df.columns:
        col2.metric("Total Units in Facility", int(df['Stock on Hand'].sum()))
    
    st.divider()
    
    # Table display karein
    st.subheader("Live Inventory Feed")
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Data load nahi ho paaya. Please check Sheet ID and permissions. Error: {e}")
