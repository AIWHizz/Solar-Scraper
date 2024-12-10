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
    """Get proposal data using hybrid approach"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session with specific headers
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Origin': 'https://v2.aurorasolar.com',
            'Referer': f'https://v2.aurorasolar.com/e-proposal/{proposal_id}',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Pragma': 'no-cache'
        }
        
        # Step 1: Initial page load
        debug_print("Loading initial page...")
        initial_response = session.get(link, headers=headers)
        debug_print(f"Initial response status: {initial_response.status_code}")
        
        if initial_response.status_code == 200:
            # Step 2: Look for data loading endpoints
            soup = BeautifulSoup(initial_response.text, 'html.parser')
            scripts = soup.find_all('script')
            
            for script in scripts:
                debug_print("Analyzing script:", script.string[:200] if script.string else "No content")
                if script.string and 'api' in script.string.lower():
                    endpoints = re.findall(r'"/api/v2/[^"]+?"', script.string)
                    debug_print("Found endpoints:", endpoints)
            
            # Step 3: Try direct data access with different content types
            content_types = [
                'application/json',
                'text/event-stream',
                'application/x-www-form-urlencoded'
            ]
            
            for content_type in content_types:
                headers['Accept'] = content_type
                data_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/data"
                debug_print(f"Trying {content_type} request to {data_url}")
                
                try:
                    response = session.get(data_url, headers=headers, timeout=10)
                    debug_print(f"Response status: {response.status_code}")
                    debug_print("Response headers:", dict(response.headers))
                    
                    if response.status_code == 200:
                        try:
                            return response.json()
                        except:
                            debug_print(f"Not JSON response for {content_type}")
                except:
                    continue
            
            # Step 4: Try WebSocket-style endpoint
            ws_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/ws"
            headers['Upgrade'] = 'websocket'
            headers['Connection'] = 'Upgrade'
            
            debug_print("Trying WebSocket-style request...")
            try:
                response = session.get(ws_url, headers=headers, timeout=10)
                debug_print(f"WebSocket response status: {response.status_code}")
                if response.status_code == 200:
                    try:
                        return response.json()
                    except:
                        debug_print("Not JSON response from WebSocket endpoint")
            except:
                debug_print("WebSocket request failed")
            
            # Step 5: Final attempt - look for embedded data
            debug_print("Looking for embedded data...")
            patterns = [
                (r'window\.__INITIAL_STATE__\s*=\s*({.*?});', 'INITIAL_STATE'),
                (r'window\.PROPOSAL_DATA\s*=\s*({.*?});', 'PROPOSAL_DATA'),
                (r'data-proposal\s*=\s*\'({.*?})\'', 'data-proposal'),
                (r'"proposal":\s*({.*?})\s*[,}]', 'proposal object'),
                (r'{"customer":.*?"system":.*?}', 'full object')
            ]
            
            for pattern, name in patterns:
                matches = re.finditer(pattern, initial_response.text, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match.group(1))
                        debug_print(f"Found {name} data!")
                        return data
                    except:
                        continue
        
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
    1. Loads initial page
    2. Analyzes loading patterns
    3. Tries multiple endpoints
    4. Attempts different protocols
    5. Looks for embedded data
    """)
