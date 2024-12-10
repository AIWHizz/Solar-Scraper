import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import time

# Page config
st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame()

# Enhanced headers to mimic browser behavior
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
    'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_proposal_data(link):
    """Get proposal data using API endpoints"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session for consistent cookies
        session = requests.Session()
        
        # First, try the direct API endpoint
        api_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/summary"
        debug_print(f"Trying API endpoint: {api_url}")
        
        response = session.get(api_url, headers=HEADERS)
        debug_print(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                debug_print("API Response Data:", data)
                return data
            except json.JSONDecodeError:
                debug_print("Failed to parse API JSON response")
        
        # If direct API fails, try the proposal content endpoint
        content_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/content"
        debug_print(f"Trying content endpoint: {content_url}")
        
        response = session.get(content_url, headers=HEADERS)
        debug_print(f"Content Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                debug_print("Content Response Data:", data)
                return data
            except json.JSONDecodeError:
                debug_print("Failed to parse content JSON response")
        
        # If API endpoints fail, try scraping the proposal page
        debug_print("Trying direct page access")
        response = session.get(link, headers=HEADERS)
        
        if response.status_code == 200:
            # Try to find embedded data
            soup = BeautifulSoup(response.text, 'html.parser')
            scripts = soup.find_all('script')
            
            for script in scripts:
                if script.string and 'window.__INITIAL_STATE__' in str(script.string):
                    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', str(script.string), re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            debug_print("Found embedded data:", data)
                            return data
                        except json.JSONDecodeError:
                            continue
        
        # If all else fails, try the legacy endpoint
        legacy_url = f"https://aurorasolar.com/api/proposals/{proposal_id}"
        debug_print(f"Trying legacy endpoint: {legacy_url}")
        
        response = session.get(legacy_url, headers=HEADERS)
        if response.status_code == 200:
            try:
                data = response.json()
                debug_print("Legacy Response Data:", data)
                return data
            except json.JSONDecodeError:
                debug_print("Failed to parse legacy JSON response")
        
        return None
        
    except Exception as e:
        debug_print(f"Error during extraction: {str(e)}")
        return None

st.title("☀️ Aurora Proposal Data Extractor")
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Process Link", type="primary"):
    try:
        with st.spinner("Processing proposal..."):
            extracted_data = get_proposal_data(link)
            
            if extracted_data:
                debug_print("Processing extracted data")
                
                # Initialize data with default values
                data = {
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Client Name': 'Not Found',
                    'System Size': 'Not Found',
                    'Price per Watt': 'Not Found',
                    'Total Cost': 'Not Found',
                    'Link': link
                }
                
                # Try to extract client name
                if 'customer' in extracted_data:
                    data['Client Name'] = extracted_data['customer'].get('name', 'Not Found')
                elif 'customerName' in extracted_data:
                    data['Client Name'] = extracted_data['customerName']
                
                # Try to extract system size
                if 'system' in extracted_data:
                    size = extracted_data['system'].get('size_kw')
                    if size:
                        data['System Size'] = f"{size} kW"
                
                # Try to extract cost
                if 'pricing' in extracted_data:
                    cost = extracted_data['pricing'].get('total_cost')
                    if cost:
                        data['Total Cost'] = f"${cost:,.2f}"
                        
                        # Calculate price per watt if we have both size and cost
                        if 'system' in extracted_data and extracted_data['system'].get('size_kw'):
                            size_watts = float(extracted_data['system']['size_kw']) * 1000
                            price_per_watt = cost / size_watts
                            data['Price per Watt'] = f"${price_per_watt:.2f}"
                
                new_df = pd.DataFrame([data])
                if st.session_state.data.empty:
                    st.session_state.data = new_df
                else:
                    st.session_state.data = pd.concat([st.session_state.data, new_df], ignore_index=True)
                
                st.success("✅ Data extracted successfully!")
            else:
                st.error("Could not extract data from the proposal")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Display data
if not st.session_state.data.empty:
    st.subheader("Extracted Data")
    st.dataframe(st.session_state.data)
    
    csv = st.session_state.data.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="aurora_data.csv",
        mime="text/csv"
    )

# Debug information
with st.expander("Debug Information"):
    st.write("Headers Used:", HEADERS)
    if 'response' in locals():
        st.write("Response Status Code:", response.status_code)
        st.write("Response Headers:", dict(response.headers))
        st.write("Content Type:", response.headers.get('content-type'))
