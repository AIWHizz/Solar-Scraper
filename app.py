import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json

# Page config
st.set_page_config(
    page_title="Aurora Data Extractor",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame()

# Define headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/html, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
    'X-Requested-With': 'XMLHttpRequest'
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def extract_data(response_text, link):
    """Enhanced data extraction with debugging"""
    soup = BeautifulSoup(response_text, 'html.parser')
    debug_print("Parsing page content...")

    # Try to find embedded JSON data
    scripts = soup.find_all('script')
    debug_print(f"Found {len(scripts)} script tags")
    
    json_data = None
    for script in scripts:
        if script.string and ('__INITIAL_STATE__' in str(script.string) or 'PROPOSAL_DATA' in str(script.string)):
            try:
                json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', str(script.string), re.DOTALL)
                if json_match:
                    json_data = json.loads(json_match.group(1))
                    debug_print("Found JSON data:", json_data)
                    break
            except Exception as e:
                debug_print(f"JSON parsing error: {str(e)}")

    # Try API endpoint
    try:
        proposal_id = link.split('/')[-1]
        api_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/summary"
        api_response = requests.get(api_url, headers=HEADERS)
        debug_print(f"API Response Status: {api_response.status_code}")
        if api_response.status_code == 200:
            json_data = api_response.json()
            debug_print("API Data:", json_data)
    except Exception as e:
        debug_print(f"API error: {str(e)}")

    # Extract data from HTML as fallback
    debug_print("Searching HTML elements...")
    
    # Look for customer name
    customer_name = "Not Found"
    name_elements = [
        soup.find(class_=re.compile(r'customer.*name', re.I)),
        soup.find('h1', string=re.compile(r'Dear\s+\w+', re.I)),
        soup.find(string=re.compile(r'Dear\s+\w+', re.I))
    ]
    for elem in name_elements:
        if elem:
            customer_name = elem.text.strip()
            if 'Dear' in customer_name:
                customer_name = customer_name.replace('Dear', '').strip()
            debug_print(f"Found customer name: {customer_name}")
            break

    # Look for system size
    system_size = "Not Found"
    size_patterns = [
        r'(\d+(?:\.\d+)?)\s*kW\s*system',
        r'system\s*size:\s*(\d+(?:\.\d+)?)\s*kW',
        r'(\d+(?:\.\d+)?)\s*kW'
    ]
    for pattern in size_patterns:
        size_match = re.search(pattern, response_text, re.I)
        if size_match:
            system_size = f"{size_match.group(1)} kW"
            debug_print(f"Found system size: {system_size}")
            break

    # Look for price
    total_cost = "Not Found"
    price_patterns = [
        r'\$\s*([\d,]+(?:\.\d{2})?)',
        r'total\s*cost:\s*\$\s*([\d,]+(?:\.\d{2})?)',
        r'price:\s*\$\s*([\d,]+(?:\.\d{2})?)'
    ]
    for pattern in price_patterns:
        price_match = re.search(pattern, response_text, re.I)
        if price_match:
            total_cost = f"${price_match.group(1)}"
            debug_print(f"Found total cost: {total_cost}")
            break

    # Calculate price per watt
    price_per_watt = "Not Found"
    try:
        if system_size != "Not Found" and total_cost != "Not Found":
            size_kw = float(re.search(r'(\d+(?:\.\d+)?)', system_size).group(1))
            cost_value = float(re.sub(r'[^\d.]', '', total_cost))
            price_per_watt = f"${(cost_value / (size_kw * 1000)):.2f}"
            debug_print(f"Calculated price per watt: {price_per_watt}")
    except Exception as e:
        debug_print(f"Price calculation error: {str(e)}")

    return {
        'client_name': customer_name,
        'system_size': system_size,
        'total_cost': total_cost,
        'price_per_watt': price_per_watt
    }

# Title
st.title("☀️ Aurora Proposal Data Extractor")

# Input
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Process Link", type="primary"):
    try:
        with st.spinner("Processing proposal..."):
            response = requests.get(link, headers=HEADERS)
            st.write(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                extracted_data = extract_data(response.text, link)
                
                data = {
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Client Name': extracted_data['client_name'],
                    'System Size': extracted_data['system_size'],
                    'Price per Watt': extracted_data['price_per_watt'],
                    'Total Cost': extracted_data['total_cost'],
                    'Link': link
                }
                
                new_df = pd.DataFrame([data])
                if st.session_state.data.empty:
                    st.session_state.data = new_df
                else:
                    st.session_state.data = pd.concat([st.session_state.data, new_df], ignore_index=True)
                
                st.success("✅ Data extracted successfully!")
            else:
                st.error(f"Failed to fetch page: {response.status_code}")
    
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
        st.write("Response Headers:", dict(response.headers))
        if st.checkbox("Show Raw HTML"):
            st.code(response.text[:1000] + "...")
