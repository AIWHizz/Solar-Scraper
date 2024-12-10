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
    """Get proposal data by simulating the frontend app"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session with proper headers
        session = requests.Session()
        
        # Step 1: Get the app version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version = version_response.json().get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Step 2: Initialize the app
        init_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Get the main page
        main_url = f"https://v2.aurorasolar.com/e-proposal/{proposal_id}"
        debug_print(f"Loading main page: {main_url}")
        response = session.get(main_url, headers=init_headers)
        
        # Step 3: Get the HLB bundle
        hlb_url = f"https://v2.aurorasolar.com/hlb.{version}.js"
        debug_print(f"Getting HLB bundle: {hlb_url}")
        hlb_response = session.get(hlb_url)
        
        if hlb_response.status_code == 200:
            # Extract API endpoints from HLB
            api_matches = re.findall(r'"/api/v2/([^"]+)"', hlb_response.text)
            debug_print("Found API endpoints:", api_matches)
        
        # Step 4: Get the proposal data
        api_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': main_url,
            'X-Aurora-Version': version,
            'X-Proposal-Token': proposal_id
        }
        
        # Try multiple API patterns
        api_patterns = [
            f"/api/v2/hlb/{proposal_id}",
            f"/api/v2/hlb/proposals/{proposal_id}",
            f"/api/v2/e-proposals/{proposal_id}",
            f"/api/v2/proposals/{proposal_id}/public"
        ]
        
        for endpoint in api_patterns:
            url = f"https://v2.aurorasolar.com{endpoint}"
            debug_print(f"\nTrying endpoint: {url}")
            
            response = session.get(url, headers=api_headers)
            debug_print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                debug_print(f"Content Type: {content_type}")
                
                # If HTML response, parse it
                if 'text/html' in content_type:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    debug_print("Parsing HTML response...")
                    
                    # Look for data in multiple ways
                    data = {}
                    
                    # Method 1: Look for specific elements
                    selectors = {
                        'customer_name': ['[data-customer-name]', '.customer-name', '#customer-name'],
                        'system_size': ['[data-system-size]', '.system-size', '#system-size'],
                        'total_cost': ['[data-total-cost]', '.total-cost', '#total-cost']
                    }
                    
                    for key, selector_list in selectors.items():
                        for selector in selector_list:
                            elements = soup.select(selector)
                            if elements:
                                data[key] = elements[0].text.strip()
                                debug_print(f"Found {key}: {data[key]}")
                    
                    # Method 2: Look for data attributes
                    for element in soup.find_all(attrs={"data-": True}):
                        for attr in element.attrs:
                            if attr.startswith('data-'):
                                try:
                                    data[attr[5:]] = element[attr]
                                    debug_print(f"Found data attribute: {attr[5:]}")
                                except:
                                    continue
                    
                    # Method 3: Look for JSON in scripts
                    for script in soup.find_all('script'):
                        if script.string:
                            patterns = [
                                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                                r'window\.PROPOSAL_DATA\s*=\s*({.*?});',
                                r'data-proposal\s*=\s*\'({.*?})\'',
                                r'"proposal":\s*({.*?})\s*[,}]'
                            ]
                            
                            for pattern in patterns:
                                match = re.search(pattern, str(script.string), re.DOTALL)
                                if match:
                                    try:
                                        json_data = json.loads(match.group(1))
                                        debug_print("Found JSON data in script!")
                                        return json_data
                                    except:
                                        continue
                    
                    if data:
                        return data
                
                # If JSON response, return it
                try:
                    return response.json()
                except:
                    debug_print("Not a JSON response")
        
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
    1. Initializes app environment
    2. Gets HLB bundle
    3. Extracts API endpoints
    4. Tries multiple data sources
    5. Parses responses for data
    """)
