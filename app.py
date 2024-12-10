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

# Enhanced headers with authentication
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0'
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def extract_data_from_html(html_content):
    """Extract data from HTML content with enhanced patterns"""
    debug_print("Extracting data from HTML...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Print first 500 chars of HTML for debugging
    debug_print("HTML Preview:", html_content[:500])
    
    data = {
        'customer_name': None,
        'system_size': None,
        'total_cost': None
    }
    
    # Customer Name patterns
    name_patterns = [
        r'Dear\s+([A-Za-z\s]+)',
        r'Proposal\s+for\s+([A-Za-z\s]+)',
        r'Customer:\s*([A-Za-z\s]+)',
        r'client-name["\']>([^<]+)',
        r'customer-name["\']>([^<]+)'
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, html_content, re.I)
        if match:
            data['customer_name'] = match.group(1).strip()
            debug_print(f"Found customer name: {data['customer_name']}")
            break
    
    # System Size patterns
    size_patterns = [
        r'(\d+\.?\d*)\s*kW\s+system',
        r'system\s+size:\s*(\d+\.?\d*)\s*kW',
        r'capacity:\s*(\d+\.?\d*)\s*kW',
        r'(\d+\.?\d*)\s*kW'
    ]
    
    for pattern in size_patterns:
        match = re.search(pattern, html_content, re.I)
        if match:
            data['system_size'] = f"{match.group(1)} kW"
            debug_print(f"Found system size: {data['system_size']}")
            break
    
    # Cost patterns
    cost_patterns = [
        r'\$\s*([\d,]+\.?\d*)',
        r'total\s+cost:\s*\$\s*([\d,]+\.?\d*)',
        r'price:\s*\$\s*([\d,]+\.?\d*)',
        r'total:\s*\$\s*([\d,]+\.?\d*)'
    ]
    
    for pattern in cost_patterns:
        match = re.search(pattern, html_content, re.I)
        if match:
            data['total_cost'] = f"${match.group(1)}"
            debug_print(f"Found total cost: {data['total_cost']}")
            break
    
    return data

def get_proposal_data(link):
    """Get proposal data with session handling"""
    session = requests.Session()
    
    # First request to get cookies and tokens
    try:
        debug_print("Making initial request...")
        response = session.get(link, headers=HEADERS)
        debug_print(f"Initial response status: {response.status_code}")
        
        if response.status_code == 200:
            # Extract CSRF token if present
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = soup.find('meta', {'name': 'csrf-token'})
            if csrf_token:
                session.headers.update({'X-CSRF-Token': csrf_token['content']})
                debug_print("Found and added CSRF token")
            
            # Extract data from HTML
            data = extract_data_from_html(response.text)
            
            if not any(data.values()):
                debug_print("No data found in initial HTML, trying alternative methods...")
                
                # Try to find data in script tags
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'window.' in str(script.string):
                        debug_print("Found potential data script")
                        # Look for various data patterns in script
                        try:
                            script_content = str(script.string)
                            data_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script_content, re.DOTALL)
                            if data_match:
                                json_data = json.loads(data_match.group(1))
                                debug_print("Found JSON data:", json_data)
                                return json_data
                        except Exception as e:
                            debug_print(f"Script parsing error: {str(e)}")
            
            return data
    except Exception as e:
        debug_print(f"Error during data extraction: {str(e)}")
        return None

st.title("☀️ Aurora Proposal Data Extractor")
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Process Link", type="primary"):
    try:
        with st.spinner("Processing proposal..."):
            extracted_data = get_proposal_data(link)
            
            if extracted_data:
                debug_print("Processing extracted data:", extracted_data)
                
                # Format data for display
                data = {
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Client Name': extracted_data.get('customer_name', 'Not Found'),
                    'System Size': extracted_data.get('system_size', 'Not Found'),
                    'Total Cost': extracted_data.get('total_cost', 'Not Found'),
                    'Price per Watt': 'Calculating...',
                    'Link': link
                }
                
                # Calculate price per watt if possible
                try:
                    if data['System Size'] != 'Not Found' and data['Total Cost'] != 'Not Found':
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
        st.write("Content Preview:", response.text[:1000] if hasattr(response, 'text') else "No content available")
