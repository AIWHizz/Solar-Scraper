import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import time

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_proposal_data(link):
    """Get proposal data using share token approach"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session
        session = requests.Session()
        
        # Step 1: Create share token
        share_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/share-token"
        share_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Origin': 'https://v2.aurorasolar.com',
            'Referer': link
        }
        
        debug_print("Requesting share token...")
        share_response = session.post(share_url, headers=share_headers)
        debug_print(f"Share token response: {share_response.status_code}")
        
        # Step 2: Get the public share URL
        public_url = f"https://v2.aurorasolar.com/p/{proposal_id}"
        debug_print(f"Accessing public URL: {public_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        response = session.get(public_url, headers=headers)
        debug_print(f"Public page response: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            debug_print("Parsing public page...")
            
            # Extract data from the public view
            data = {}
            
            # Method 1: Direct element extraction
            selectors = {
                'customer_name': ['h1.customer-name', '.recipient-name', '.proposal-header h1'],
                'system_size': ['.system-size', '.system-details', '[data-system-size]'],
                'total_cost': ['.total-cost', '.price-total', '[data-total-cost]']
            }
            
            for key, selector_list in selectors.items():
                for selector in selector_list:
                    elements = soup.select(selector)
                    if elements:
                        data[key] = elements[0].text.strip()
                        debug_print(f"Found {key}: {data[key]}")
            
            # Method 2: Look for data attributes
            for element in soup.find_all(True):
                for attr in element.attrs:
                    if attr.startswith('data-'):
                        try:
                            key = attr.replace('data-', '')
                            data[key] = element[attr]
                            debug_print(f"Found data attribute: {key}")
                        except:
                            continue
            
            # Method 3: Extract from JSON-LD
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    json_data = json.loads(script.string)
                    debug_print("Found JSON-LD data")
                    return json_data
                except:
                    continue
            
            if data:
                return data
            
            # Method 4: Try public API endpoint
            public_api_url = f"https://v2.aurorasolar.com/api/v2/public/proposals/{proposal_id}"
            headers['Accept'] = 'application/json'
            
            debug_print(f"Trying public API: {public_api_url}")
            api_response = session.get(public_api_url, headers=headers)
            
            if api_response.status_code == 200:
                try:
                    return api_response.json()
                except:
                    debug_print("Failed to parse API response")
        
        return None
        
    except Exception as e:
        debug_print(f"Error during extraction: {str(e)}")
        return None

st.title("☀️ Aurora Proposal Data Extractor")
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Extract Data", type="primary"):
    try:
        with st.spinner("Processing proposal..."):
            data = get_proposal_data(link)
            
            if data:
                st.success("Data extracted!")
                st.json(data)
            else:
                st.error("Could not extract data")
    except Exception as e:
        st.error(f"Error: {str(e)}")

with st.expander("How it works"):
    st.markdown("""
    1. Creates a public share token
    2. Accesses public view
    3. Extracts data from public page
    4. Uses multiple extraction methods
    """)
