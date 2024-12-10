import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import time
import base64
from urllib.parse import urljoin

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
    'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

@st.cache_data(ttl=3600)
def get_webpack_manifest():
    """Get webpack manifest to find correct asset paths"""
    try:
        manifest_url = "https://v2.aurorasolar.com/asset-manifest.json"
        response = requests.get(manifest_url)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def get_asset_url(manifest, asset_name):
    """Get correct URL for webpack asset"""
    if manifest and asset_name in manifest.get('files', {}):
        return urljoin("https://v2.aurorasolar.com/", manifest['files'][asset_name])
    return None

def extract_proposal_token(proposal_id):
    """Extract and decode proposal token"""
    try:
        # Base64 decode the proposal ID
        decoded = base64.urlsafe_b64decode(proposal_id + '=' * (-len(proposal_id) % 4))
        debug_print(f"Decoded proposal token: {decoded}")
        return decoded.decode('utf-8')
    except:
        return proposal_id

def get_proposal_data(link):
    """Get proposal data with webpack handling"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session
        session = requests.Session()
        
        # Get webpack manifest
        manifest = get_webpack_manifest()
        debug_print("Got webpack manifest:", manifest is not None)
        
        # Get current version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version_data = version_response.json()
        version = version_data.get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Get HLB bundle
        hlb_url = f"https://v2.aurorasolar.com/hlb.{version}.js"
        debug_print(f"Getting HLB bundle from: {hlb_url}")
        
        hlb_response = session.get(hlb_url)
        if hlb_response.status_code == 200:
            # Extract API endpoints from HLB bundle
            api_patterns = [
                r'"/api/v2/([^"]+)"',
                r'"/hlb/([^"]+)"',
                r'"/e-proposals/([^"]+)"'
            ]
            
            endpoints = []
            for pattern in api_patterns:
                matches = re.findall(pattern, hlb_response.text)
                endpoints.extend(matches)
            
            debug_print("Found API endpoints:", endpoints)
        
        # Extract proposal token
        token = extract_proposal_token(proposal_id)
        debug_print("Extracted token:", token)
        
        # Try different API patterns
        api_patterns = [
            ('hlb', f"/api/v2/hlb/proposals/{proposal_id}/data"),
            ('view', f"/api/v2/hlb/{proposal_id}/view"),
            ('content', f"/api/v2/e-proposals/{proposal_id}/content"),
            ('public', f"/api/v2/proposals/{proposal_id}/public")
        ]
        
        for endpoint_type, endpoint in api_patterns:
            url = f"https://v2.aurorasolar.com{endpoint}"
            debug_print(f"\nTrying {endpoint_type} endpoint: {url}")
            
            # Prepare headers for this request
            request_headers = HEADERS.copy()
            request_headers.update({
                'X-Aurora-Version': version,
                'X-Proposal-Token': token,
                'X-Request-ID': proposal_id,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            
            # Try OPTIONS first
            options_response = session.options(url, headers=request_headers)
            debug_print(f"OPTIONS Status: {options_response.status_code}")
            
            # Then make the actual request
            response = session.get(url, headers=request_headers)
            debug_print(f"GET Status: {response.status_code}")
            
            try:
                content_type = response.headers.get('Content-Type', '')
                debug_print(f"Content-Type: {content_type}")
                
                if 'application/json' in content_type:
                    data = response.json()
                    debug_print("Found JSON data!")
                    return data
                elif 'text/html' in content_type:
                    # Parse HTML response
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for data in scripts
                    for script in soup.find_all('script'):
                        if script.string:
                            # Try different data patterns
                            patterns = [
                                (r'window\.__INITIAL_STATE__\s*=\s*({.*?});', 'INITIAL_STATE'),
                                (r'window\.PROPOSAL_DATA\s*=\s*({.*?});', 'PROPOSAL_DATA'),
                                (r'{"proposal":\s*({.*?})\s*}', 'proposal object')
                            ]
                            
                            for pattern, pattern_name in patterns:
                                match = re.search(pattern, str(script.string), re.DOTALL)
                                if match:
                                    try:
                                        data = json.loads(match.group(1))
                                        debug_print(f"Found {pattern_name} data!")
                                        return data
                                    except:
                                        continue
            except Exception as e:
                debug_print(f"Error processing response: {str(e)}")
        
        return None
        
    except Exception as e:
        debug_print(f"Error during extraction: {str(e)}")
        return None

st.title("☀️ Aurora Proposal Data Extractor")
st.markdown("""
This tool extracts data from Aurora Solar proposals. 
Please paste a complete Aurora proposal link below.
""")

link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Extract Data", type="primary"):
    try:
        with st.spinner("Processing proposal (this may take a few moments)..."):
            data = get_proposal_data(link)
            
            if data:
                st.success("Data extracted!")
                st.json(data)
            else:
                st.error("Could not extract data. Please check the link and try again.")
    except Exception as e:
        st.error(f"Error: {str(e)}")

with st.expander("Debug Information"):
    st.markdown("""
    ### Headers Used
    These are the base headers used for requests:
    """)
    st.json(HEADERS)
