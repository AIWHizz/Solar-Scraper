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

# Enhanced headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
    'X-Requested-With': 'XMLHttpRequest',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty'
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_proposal_data(link):
    """Get proposal data using multiple methods"""
    debug_print("Starting data extraction...")
    
    # Extract proposal ID
    proposal_id = link.split('/')[-1]
    debug_print(f"Proposal ID: {proposal_id}")
    
    # Try different API endpoints
    api_endpoints = [
        f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}",
        f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/summary",
        f"https://v2.aurorasolar.com/api/proposals/{proposal_id}",
        f"https://aurorasolar.com/api/v2/proposals/{proposal_id}"
    ]
    
    for endpoint in api_endpoints:
        try:
            debug_print(f"Trying endpoint: {endpoint}")
            response = requests.get(endpoint, headers=HEADERS)
            debug_print(f"API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    debug_print("API Response Data:", data)
                    return data
                except json.JSONDecodeError:
                    debug_print("Not valid JSON response")
                    continue
        except Exception as e:
            debug_print(f"API request error: {str(e)}")
    
    # If API fails, try direct page scraping
    try:
        debug_print("Attempting direct page scraping...")
        session = requests.Session()
        
        # First, get the page to obtain any necessary tokens
        page_response = session.get(link, headers=HEADERS)
        debug_print(f"Page Response Status: {page_response.status_code}")
        
        if page_response.status_code == 200:
            soup = BeautifulSoup(page_response.text, 'html.parser')
            
            # Look for data in script tags
            scripts = soup.find_all('script')
            debug_print(f"Found {len(scripts)} script tags")
            
            for script in scripts:
                if script.string:
                    # Look for various data patterns
                    patterns = [
                        r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                        r'window\.PROPOSAL_DATA\s*=\s*({.*?});',
                        r'proposal:\s*({.*?})',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, str(script.string), re.DOTALL)
                        if match:
                            try:
                                data = json.loads(match.group(1))
                                debug_print("Found embedded data:", data)
                                return data
                            except json.JSONDecodeError:
                                continue
            
            # If no JSON found, try HTML extraction
            debug_print("Attempting HTML extraction...")
            
            # Extract customer name
            name_elements = [
                soup.find(class_=re.compile(r'customer.*name', re.I)),
                soup.find(string=re.compile(r'Dear\s+[A-Za-z\s]+', re.I)),
                soup.find('h1', string=re.compile(r'[A-Za-z\s]+\'s\s+Proposal', re.I))
            ]
            
            # Extract system size
            size_elements = soup.find_all(string=re.compile(r'\d+\.?\d*\s*kW', re.I))
            
            # Extract cost
            cost_elements = soup.find_all(string=re.compile(r'\$\s*[\d,]+\.?\d*', re.I))
            
            return {
                'customer_name': next((e.text.strip() for e in name_elements if e), None),
                'system_size_kw': next((float(re.search(r'(\d+\.?\d*)', e).group(1)) 
                                     for e in size_elements if e), None),
                'total_cost': next((float(re.sub(r'[^\d.]', '', e)) 
                                  for e in cost_elements if e), None)
            }
    
    except Exception as e:
        debug_print(f"Scraping error: {str(e)}")
    
    return None

st.title("☀️ Aurora Proposal Data Extractor")
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Process Link", type="primary"):
    try:
        with st.spinner("Processing proposal..."):
            extracted_data = get_proposal_data(link)
            
            if extracted_data:
                debug_print("Processing extracted data:", extracted_data)
                
                # Process the data
                client_name = (extracted_data.get('customer_name') or 
                             extracted_data.get('customer', {}).get('name', 'Not Found'))
                
                system_size = (f"{extracted_data.get('system_size_kw', 0)} kW" if 'system_size_kw' in extracted_data 
                             else f"{extracted_data.get('system', {}).get('size_kw', 0)} kW")
                
                total_cost = (f"${extracted_data.get('total_cost', 0):,.2f}" if 'total_cost' in extracted_data 
                            else f"${extracted_data.get('pricing', {}).get('total_cost', 0):,.2f}")
                
                # Calculate price per watt
                try:
                    size_watts = float(re.search(r'(\d+\.?\d*)', system_size).group(1)) * 1000
                    cost_value = float(re.sub(r'[^\d.]', '', total_cost))
                    price_per_watt = f"${(cost_value / size_watts):.2f}"
                except:
                    price_per_watt = "Not Found"
                
                data = {
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Client Name': client_name,
                    'System Size': system_size,
                    'Price per Watt': price_per_watt,
                    'Total Cost': total_cost,
                    'Link': link
                }
                
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
        st.write("Response Headers:", dict(response.headers))
        if st.checkbox("Show Raw HTML"):
            st.code(response.text[:1000] + "...")
