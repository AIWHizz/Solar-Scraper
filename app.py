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

def get_auth_token(proposal_id):
    """Get authentication token for proposal"""
    auth_url = "https://v2.aurorasolar.com/api/v2/token"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Origin': 'https://v2.aurorasolar.com',
        'Referer': 'https://v2.aurorasolar.com/'
    }
    
    payload = {
        "token": proposal_id,
        "type": "proposal"
    }
    
    response = requests.post(auth_url, json=payload, headers=headers)
    debug_print(f"Auth response status: {response.status_code}")
    
    if response.status_code == 200:
        return response.json().get('token')
    return None

def get_proposal_data(link):
    """Get proposal data using authentication token"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session
        session = requests.Session()
        
        # Get auth token
        auth_token = get_auth_token(proposal_id)
        debug_print(f"Auth token: {auth_token}")
        
        # Get version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version = version_response.json().get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Base headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Version': '2',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://v2.aurorasolar.com',
            'Referer': 'https://v2.aurorasolar.com/',
            'X-Requested-With': 'XMLHttpRequest',
            'X-Aurora-Version': version,
            'Authorization': f'Bearer {auth_token}' if auth_token else None
        }
        
        # Try different endpoints with proper authentication
        endpoints = [
            ('view', f"/api/v2/e-proposals/view"),
            ('proposal', f"/api/v2/e-proposals/{proposal_id}"),
            ('public', f"/api/v2/proposals/{proposal_id}/public"),
            ('summary', f"/api/v2/proposals/{proposal_id}/summary")
        ]
        
        for name, endpoint in endpoints:
            url = f"https://v2.aurorasolar.com{endpoint}"
            debug_print(f"\nTrying {name} endpoint: {url}")
            
            response = session.get(
                url, 
                headers=headers,
                params={'token': proposal_id} if 'view' in endpoint else None
            )
            
            debug_print(f"Response Status: {response.status_code}")
            debug_print("Response Headers:", dict(response.headers))
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                debug_print(f"Content Type: {content_type}")
                
                if 'application/json' in content_type:
                    return response.json()
                elif 'text/html' in content_type:
                    # Try to find JSON in HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    debug_print("Page Content Preview:", response.text[:500])
                    
                    # Look for specific script tags
                    for script in soup.find_all('script'):
                        if script.string and any(x in str(script.string) for x in ['__INITIAL_STATE__', 'PROPOSAL_DATA']):
                            debug_print("Found potential data script:", script.string[:200])
                            
                            # Try to extract JSON
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
        
        # If no data found through API, try final direct approach
        debug_print("Trying final direct approach...")
        direct_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/data"
        headers['Accept'] = '*/*'
        response = session.get(direct_url, headers=headers)
        
        if response.status_code == 200:
            try:
                return response.json()
            except:
                debug_print("Final attempt failed")
        
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
    1. Gets authentication token
    2. Uses token to access API
    3. Tries multiple endpoints
    4. Extracts data from response
    """)
