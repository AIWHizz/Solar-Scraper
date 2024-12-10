import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json

# Page config
st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def extract_proposal_data(response_text):
    """Extract data with specific focus on finding known patterns"""
    debug_print("Starting detailed extraction...")
    
    # Store the full response for debugging
    with st.expander("Full Response Text"):
        st.code(response_text)
    
    # First, look for any script tags containing our data
    soup = BeautifulSoup(response_text, 'html.parser')
    scripts = soup.find_all('script')
    
    debug_print(f"Found {len(scripts)} script tags")
    
    # Search for specific data patterns
    data_patterns = {
        'name': r'(?:customer|client)(?:["\']\s*:\s*["\'](Rob Appleyard|[^"\']+))',
        'size': r'(\d+(?:\.\d+)?)\s*kW',
        'cost': r'\$\s*([\d,]+(?:\.\d+)?)',
    }
    
    extracted_data = {}
    
    # Search through the entire response text first
    for key, pattern in data_patterns.items():
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        if matches:
            debug_print(f"Found {key} matches:", matches)
            extracted_data[key] = matches[0]
    
    # If we didn't find the data, try parsing each script tag
    if not extracted_data:
        for script in scripts:
            if script.string:
                script_text = str(script.string)
                # Look for window.__INITIAL_STATE__ or similar data
                if '__INITIAL_STATE__' in script_text or 'PROPOSAL_DATA' in script_text:
                    debug_print("Found potential data script")
                    try:
                        # Try to extract JSON data
                        json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script_text, re.DOTALL)
                        if json_match:
                            json_data = json.loads(json_match.group(1))
                            debug_print("Extracted JSON data:", json_data)
                            # Look for customer data in the JSON
                            if 'customer' in json_data:
                                extracted_data['name'] = json_data['customer'].get('name')
                            if 'system' in json_data:
                                extracted_data['size'] = json_data['system'].get('size_kw')
                            if 'pricing' in json_data:
                                extracted_data['cost'] = json_data['pricing'].get('total_cost')
                    except Exception as e:
                        debug_print(f"JSON parsing error: {str(e)}")
    
    # Try direct HTML elements if we still don't have the data
    if not extracted_data.get('name'):
        # Look for specific HTML elements that might contain the name
        name_elements = [
            soup.find('div', string=re.compile(r'Rob\s+Appleyard')),
            soup.find(class_=re.compile(r'customer-name')),
            soup.find('h1', string=re.compile(r'Rob\s+Appleyard')),
            soup.find(string=re.compile(r'Dear\s+Rob\s+Appleyard'))
        ]
        
        for elem in name_elements:
            if elem:
                debug_print("Found name element:", elem)
                extracted_data['name'] = elem.text.strip()
                break
    
    return extracted_data

def get_proposal_data(link):
    """Get proposal data with enhanced error handling"""
    session = requests.Session()
    
    try:
        # First request to get the page
        debug_print("Making initial request...")
        response = session.get(link, headers=HEADERS)
        debug_print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            extracted_data = extract_proposal_data(response.text)
            debug_print("Extracted data:", extracted_data)
            
            # Format the data
            return {
                'customer_name': extracted_data.get('name', 'Not Found'),
                'system_size': f"{extracted_data.get('size', 'Not Found')} kW" if extracted_data.get('size') else 'Not Found',
                'total_cost': f"${extracted_data.get('cost', 'Not Found')}" if extracted_data.get('cost') else 'Not Found'
            }
    except Exception as e:
        debug_print(f"Error during extraction: {str(e)}")
    
    return None

# Main interface
st.title("☀️ Aurora Proposal Data Extractor")
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Process Link", type="primary"):
    try:
        with st.spinner("Processing proposal..."):
            extracted_data = get_proposal_data(link)
            
            if extracted_data:
                debug_print("Final extracted data:", extracted_data)
                
                data = {
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Client Name': extracted_data['customer_name'],
                    'System Size': extracted_data['system_size'],
                    'Total Cost': extracted_data['total_cost'],
                    'Price per Watt': 'Calculating...',
                    'Link': link
                }
                
                # Calculate price per watt if possible
                try:
                    if 'Not Found' not in [data['System Size'], data['Total Cost']]:
                        size_kw = float(re.search(r'(\d+\.?\d*)', data['System Size']).group(1))
                        cost = float(re.sub(r'[^\d.]', '', data['Total Cost']))
                        data['Price per Watt'] = f"${(cost / (size_kw * 1000)):.2f}"
                except Exception as e:
                    debug_print(f"Price calculation error: {str(e)}")
                
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
