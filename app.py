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
    """Get proposal data with enhanced content extraction"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session
        session = requests.Session()
        
        # Get version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version = version_response.json().get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Initial headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://v2.aurorasolar.com',
            'Referer': 'https://v2.aurorasolar.com/',
            'X-Aurora-Version': version,
            'X-Proposal-Token': proposal_id,
            'Connection': 'keep-alive'
        }
        
        # First, try to get the main page
        debug_print("Getting main page...")
        response = session.get(link, headers=headers)
        debug_print(f"Main page status: {response.status_code}")
        
        if response.status_code == 200:
            debug_print("Got main page, looking for data...")
            soup = BeautifulSoup(response.text, 'html.parser')
            debug_print("Page content preview:", response.text[:500])
            
            # Look for specific elements
            for element in soup.find_all(True):  # Get all elements
                debug_print(f"Found element: {element.name} - {element.get('class', ['no-class'])}")
                
                # Look for data attributes
                for attr in element.attrs:
                    if 'data-' in attr:
                        debug_print(f"Found data attribute: {attr} = {element[attr]}")
                        try:
                            data = json.loads(element[attr])
                            return data
                        except:
                            continue
        
        # Wait for potential JavaScript execution
        debug_print("Waiting 45 seconds...")
        time.sleep(45)
        
        # Try API endpoints with JSON headers
        api_headers = headers.copy()
        api_headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        endpoints = [
            ('hlb', f"/api/v2/hlb/proposals/{proposal_id}"),
            ('view', f"/api/v2/proposals/{proposal_id}/view"),
            ('data', f"/api/v2/e-proposals/{proposal_id}/data"),
            ('content', f"/api/v2/e-proposals/{proposal_id}/content")
        ]
        
        for name, endpoint in endpoints:
            url = f"https://v2.aurorasolar.com{endpoint}"
            debug_print(f"\nTrying {name} endpoint: {url}")
            
            response = session.get(url, headers=api_headers)
            debug_print(f"Response Status: {response.status_code}")
            debug_print("Response Headers:", dict(response.headers))
            
            if response.status_code == 200:
                debug_print("Response Content:", response.text[:500])
                
                try:
                    data = response.json()
                    debug_print(f"Found JSON in {name} endpoint!")
                    return data
                except json.JSONDecodeError:
                    debug_print(f"Not JSON response from {name} endpoint")
                    
                    # Try to find JSON in HTML
                    if 'text/html' in response.headers.get('Content-Type', ''):
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for JSON in scripts
                        for script in soup.find_all('script'):
                            if script.string:
                                patterns = [
                                    r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                                    r'window\.PROPOSAL_DATA\s*=\s*({.*?});',
                                    r'data-proposal\s*=\s*\'({.*?})\'',
                                    r'"proposal":\s*({.*?})\s*[,}]',
                                    r'{"customer":.*?"system":.*?}'
                                ]
                                
                                for pattern in patterns:
                                    match = re.search(pattern, str(script.string), re.DOTALL)
                                    if match:
                                        try:
                                            data = json.loads(match.group(1))
                                            debug_print(f"Found embedded data in {name} endpoint!")
                                            return data
                                        except:
                                            continue
        
        debug_print("Could not extract data")
        return None
        
    except Exception as e:
        debug_print(f"Error during extraction: {str(e)}")
        return None

st.title("☀️ Aurora Proposal Data Extractor")
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Extract Data", type="primary"):
    try:
        with st.spinner("Processing proposal (please wait 45 seconds)..."):
            data = get_proposal_data(link)
            
            if data:
                st.success("Data extracted!")
                st.json(data)
            else:
                st.error("Could not extract data")
                
            st.write("Debug Information")
            st.write("Headers:", HEADERS)
    except Exception as e:
        st.error(f"Error: {str(e)}")
