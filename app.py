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

# Define headers at the global scope
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
}

# Title
st.title("☀️ Aurora Proposal Data Extractor")

# Input
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Process Link", type="primary"):
    try:
        with st.spinner("Processing..."):
            # Get the page content
            response = requests.get(link, headers=HEADERS)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find client name
            name_elements = [
                soup.find('div', {'class': 'customer-name'}),
                soup.find('h1', {'class': 'customer-name'}),
                soup.find('span', {'class': 'customer-name'}),
                soup.find(string=lambda t: t and 'Dear' in t)
            ]
            client_name = next((elem.text.strip() for elem in name_elements if elem), "Not Found")
            
            # Find system size
            size_patterns = [
                soup.find(string=lambda t: t and 'kW' in t),
                soup.find('div', string=lambda t: t and 'kW' in t),
                soup.find('span', string=lambda t: t and 'kW' in t)
            ]
            system_size = next((elem.strip() for elem in size_patterns if elem), "Not Found")
            
            # Find price information
            price_patterns = [
                soup.find(string=lambda t: t and '$' in t),
                soup.find('div', string=lambda t: t and '$' in t),
                soup.find('span', string=lambda t: t and '$' in t)
            ]
            total_cost = next((elem.strip() for elem in price_patterns if elem), "Not Found")
            
            # Debug information
            st.write("Raw Data Found:")
            st.write(f"Name: {client_name}")
            st.write(f"Size: {system_size}")
            st.write(f"Cost: {total_cost}")
            
            # Store data
            data = {
                'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Client Name': client_name,
                'System Size': system_size,
                'Price per Watt': "Calculating...",
                'Total Cost': total_cost,
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

# Add debug information
with st.expander("Debug Information"):
    st.write("Last Response Status:", getattr(response, 'status_code', 'No request made yet') if 'response' in locals() else "No request made yet")
    st.write("Headers Used:", HEADERS)
