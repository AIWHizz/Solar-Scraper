import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import time
import sseclient  # We'll handle this with pure requests

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_proposal_data(link):
    """Get proposal data using event stream approach"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session with specific headers
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/event-stream',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Origin': 'https://v2.aurorasolar.com',
            'Referer': f'https://v2.aurorasolar.com/e-proposal/{proposal_id}',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        # First, get the initial page to establish session
        debug_print("Getting initial page...")
        initial_response = session.get(link, headers=headers)
        debug_print(f"Initial response status: {initial_response.status_code}")
        
        if initial_response.status_code == 200:
            # Look for WebSocket URL or Event Stream endpoint
            matches = re.findall(r'(wss://[^"]+|\/api\/v2\/stream[^"]+)"', initial_response.text)
            if matches:
                debug_print(f"Found potential stream endpoints: {matches}")
            
            # Try to get data through event stream
            stream_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/stream"
            debug_print(f"Trying event stream: {stream_url}")
            
            headers['Accept'] = 'text/event-stream'
            
            try:
                with session.get(stream_url, headers=headers, stream=True, timeout=50) as response:
                    debug_print(f"Stream response status: {response.status_code}")
                    
                    # Read stream for up to 45 seconds
                    start_time = time.time()
                    buffer = ""
                    
                    while time.time() - start_time < 45:
                        chunk = response.raw.read(1024).decode('utf-8')
                        if not chunk:
                            break
                            
                        buffer += chunk
                        debug_print(f"Received chunk: {chunk[:200]}")
                        
                        # Look for JSON data in buffer
                        json_matches = re.finditer(r'({[^}]+})', buffer)
                        for match in json_matches:
                            try:
                                data = json.loads(match.group(1))
                                if isinstance(data, dict) and ('proposal' in data or 'customer' in data):
                                    debug_print("Found data in stream!")
                                    return data
                            except:
                                continue
                        
                        time.sleep(1)  # Small delay between reads
            
            except Exception as e:
                debug_print(f"Stream error: {str(e)}")
            
            # If stream fails, try direct data endpoint
            data_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/data"
            headers['Accept'] = 'application/json'
            
            debug_print(f"Trying direct data endpoint: {data_url}")
            response = session.get(data_url, headers=headers)
            
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    debug_print("Failed to parse JSON from data endpoint")
            
            # Final attempt: parse the fully loaded page
            debug_print("Trying final page parse...")
            final_response = session.get(link, headers={'Accept': 'text/html'})
            
            if final_response.status_code == 200:
                soup = BeautifulSoup(final_response.text, 'html.parser')
                
                # Look for data in script tags
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
                                    return json.loads(match.group(1))
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
        with st.spinner("Processing proposal (this may take up to 45 seconds)..."):
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
    1. Connects to Aurora's event stream
    2. Listens for data updates
    3. Processes streaming data
    4. Falls back to direct API if needed
    """)
