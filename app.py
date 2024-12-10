import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import time

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_proposal_data(link):
    """Get proposal data with progressive loading"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session for consistent cookies
        session = requests.Session()
        
        # Step 1: Get version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version_data = version_response.json()
        version = version_data.get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Step 2: Initial page load
        initial_headers = HEADERS.copy()
        initial_headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Cache-Control': 'no-cache'
        })
        
        debug_print("Loading initial page...")
        response = session.get(link, headers=initial_headers)
        debug_print(f"Initial Response Status: {response.status_code}")
        
        # Step 3: Get HLB JavaScript
        hlb_url = f"https://v2.aurorasolar.com/hlb.{version}.js"
        debug_print(f"Getting HLB JS from: {hlb_url}")
        
        js_response = session.get(hlb_url)
        debug_print(f"HLB JS Status: {js_response.status_code}")
        
        if js_response.status_code == 200:
            # Look for API endpoints in JS
            endpoints = re.findall(r'"(/api/v2/[^"]+)"', js_response.text)
            debug_print("Found API endpoints:", endpoints)
        
        # Step 4: Try different data endpoints with delays
        endpoints = [
            f"/api/v2/hlb/proposals/{proposal_id}/data",
            f"/api/v2/hlb/{proposal_id}/view",
            f"/api/v2/e-proposals/{proposal_id}/content",
            f"/api/v2/proposals/{proposal_id}/public"
        ]
        
        for endpoint in endpoints:
            url = f"https://v2.aurorasolar.com{endpoint}"
            debug_print(f"\nTrying endpoint: {url}")
            
            # Add delay to simulate page load
            time.sleep(2)
            
            headers = HEADERS.copy()
            headers.update({
                'X-Aurora-Version': version,
                'X-Proposal-Token': proposal_id,
                'Accept': 'application/json',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            
            debug_print("Using headers:", headers)
            
            response = session.get(url, headers=headers)
            debug_print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    # Try to parse as JSON first
                    data = response.json()
                    debug_print("Found JSON response!")
                    return data
                except json.JSONDecodeError:
                    # If not JSON, try to find data in HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for data in scripts
                    for script in soup.find_all('script'):
                        if script.string:
                            # Try different data patterns
                            patterns = [
                                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                                r'window\.PROPOSAL_DATA\s*=\s*({.*?});',
                                r'{"proposal":\s*({.*?})\s*}',
                                r'data-proposal=\'({.*?})\''
                            ]
                            
                            for pattern in patterns:
                                match = re.search(pattern, str(script.string), re.DOTALL)
                                if match:
                                    try:
                                        data = json.loads(match.group(1))
                                        debug_print("Found embedded data!")
                                        return data
                                    except:
                                        continue
        
        # If no data found through API, try parsing the initial HTML
        debug_print("Trying to parse initial HTML...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for specific elements
        data = {}
        elements = {
            'customer_name': ['customer-name', 'proposal-customer'],
            'system_size': ['system-size', 'proposal-system-size'],
            'total_cost': ['total-cost', 'proposal-cost']
        }
        
        for key, classes in elements.items():
            for class_name in classes:
                element = soup.find(class_=class_name)
                if element:
                    data[key] = element.text.strip()
                    debug_print(f"Found {key}: {data[key]}")
        
        if data:
            return data
        
        return None
        
    except Exception as e:
        debug_print(f"Error during extraction: {str(e)}")
        return None

st.title("☀️ Aurora Proposal Data Extractor")
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Extract Data", type="primary"):
    try:
        with st.spinner("Processing proposal (this may take 15-20 seconds)..."):
            data = get_proposal_data(link)
            
            if data:
                st.success("Data extracted!")
                st.json(data)
            else:
                st.error("Could not extract data")
    except Exception as e:
        st.error(f"Error: {str(e)}")

with st.expander("Debug Information"):
    st.write("Base Headers:", HEADERS)
