import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import time
import base64

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def decode_proposal_id(proposal_id):
    """Decode the proposal ID if it's base64 encoded"""
    try:
        # Add padding if needed
        padding = 4 - (len(proposal_id) % 4)
        if padding != 4:
            proposal_id += '=' * padding
        
        decoded = base64.urlsafe_b64decode(proposal_id)
        return decoded.hex()
    except:
        return proposal_id

def get_proposal_data(link):
    """Get proposal data with enhanced debugging"""
    try:
        # Extract and decode proposal ID
        proposal_id = link.split('/')[-1]
        decoded_id = decode_proposal_id(proposal_id)
        debug_print(f"Proposal ID: {proposal_id}")
        debug_print(f"Decoded ID: {decoded_id}")
        
        # Create session
        session = requests.Session()
        
        # Step 1: Get version and establish session
        debug_print("Getting Aurora version...")
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version = version_response.json().get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Base headers
        base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://v2.aurorasolar.com',
            'Referer': f'https://v2.aurorasolar.com/e-proposal/{proposal_id}',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Aurora-Version': version,
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # Step 2: Initial page load with proper headers
        debug_print("Loading initial page...")
        initial_url = f"https://v2.aurorasolar.com/e-proposal/{proposal_id}"
        initial_headers = base_headers.copy()
        initial_headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })
        
        response = session.get(initial_url, headers=initial_headers)
        debug_print(f"Initial page status: {response.status_code}")
        
        if response.status_code == 200:
            # Step 3: Handle CORS preflight
            debug_print("Sending CORS preflight...")
            options_headers = {
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'x-aurora-version,x-requested-with',
                'Origin': 'https://v2.aurorasolar.com'
            }
            
            session.options(initial_url, headers=options_headers)
            
            # Step 4: Try different API endpoints with proper headers
            endpoints = [
                ('data', f"/api/v2/proposals/{proposal_id}/data"),
                ('view', f"/api/v2/proposals/{proposal_id}/view"),
                ('hlb', f"/api/v2/hlb/proposals/{proposal_id}"),
                ('public', f"/api/v2/proposals/{proposal_id}/public")
            ]
            
            for name, endpoint in endpoints:
                url = f"https://v2.aurorasolar.com{endpoint}"
                debug_print(f"\nTrying {name} endpoint: {url}")
                
                # Add specific headers for this request
                request_headers = base_headers.copy()
                request_headers.update({
                    'X-Proposal-Token': proposal_id,
                    'Authorization': f'Proposal {proposal_id}'
                })
                
                debug_print("Using headers:", request_headers)
                
                response = session.get(url, headers=request_headers)
                debug_print(f"Response status: {response.status_code}")
                debug_print("Response headers:", dict(response.headers))
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        debug_print("Found JSON data!")
                        return data
                    except json.JSONDecodeError:
                        debug_print("Response content preview:", response.text[:500])
                        
                        # Try to parse HTML
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for data in specific elements
                        elements = {
                            'customer_name': soup.find(class_='customer-name'),
                            'system_size': soup.find(class_='system-size'),
                            'total_cost': soup.find(class_='total-cost')
                        }
                        
                        extracted_data = {}
                        for key, element in elements.items():
                            if element:
                                extracted_data[key] = element.text.strip()
                                debug_print(f"Found {key}: {extracted_data[key]}")
                        
                        if extracted_data:
                            return extracted_data
            
            debug_print("No data found in any endpoint")
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
    1. Decodes proposal ID
    2. Establishes proper session
    3. Handles CORS requirements
    4. Tries multiple endpoints
    5. Extracts data from responses
    """)
