import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Aurora Data Extractor",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame()

# Title
st.title("☀️ Aurora Proposal Data Extractor")

# Input
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Process Link", type="primary"):
    try:
        with st.spinner("Processing..."):
            # Setup headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/json'
            }
            
            # Get proposal ID
            proposal_id = link.split('/')[-1]
            
            # Try API endpoint
            api_url = f"https://v2.aurorasolar.com/api/proposals/{proposal_id}"
            response = requests.get(api_url, headers=headers)
            
            # Debug info
            st.write(f"Status Code: {response.status_code}")
            
            # Store data
            data = {
                'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Client Name': "Debug",
                'System Size': "Debug",
                'Price per Watt': "Debug",
                'Total Cost': "Debug",
                'Link': link
            }
            
            # Add to dataframe
            new_df = pd.DataFrame([data])
            if st.session_state.data.empty:
                st.session_state.data = new_df
            else:
                st.session_state.data = pd.concat([st.session_state.data, new_df], ignore_index=True)
            
        st.success("✅ Processed successfully!")
        
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Display data
if not st.session_state.data.empty:
    st.subheader("Extracted Data")
    st.dataframe(st.session_state.data)
    
    # Download button
    csv = st.session_state.data.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="aurora_data.csv",
        mime="text/csv"
    )
