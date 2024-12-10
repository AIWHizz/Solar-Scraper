import streamlit as st
import requests
import json
import time
from urllib.parse import quote

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_proposal_data_playwright(link):
    """Get data using PlayWright Cloud's free API"""
    try:
        # Encode our JavaScript to execute
        script = quote("""
            async () => {
                await new Promise(r => setTimeout(r, 45000));
                return {
                    initialState: window.__INITIAL_STATE__,
                    proposalData: window.PROPOSAL_DATA,
                    customerData: document.querySelector('[data-customer]')?.dataset?.customer,
                    elementData: {
                        customerName: document.querySelector('.customer-name')?.textContent,
                        systemSize: document.querySelector('.system-size')?.textContent,
                        totalCost: document.querySelector('.total-cost')?.textContent
                    }
                };
            }
        """)
        
        # Use PlayWright Cloud's free API
        url = f"https://chrome.browserless.io/function?code={script}&url={quote(link)}"
        
        debug_print("Sending request to PlayWright Cloud...")
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
            
        # Fallback to direct API approach if PlayWright fails
        return get_proposal_data_direct(link)
        
    except Exception as e:
        debug_print(f"Error with PlayWright: {str(e)}")
        return get_proposal_data_direct(link)

def get_proposal_data_direct(link):
    """Fallback method using direct API calls"""
    try:
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Get Aurora version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version = version_response.json().get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Create session with specific headers
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://v2.aurorasolar.com',
            'Referer': 'https://v2.aurorasolar.com/',
            'X-Aurora-Version': version,
            'X-Proposal-Token': proposal_id,
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # Try multiple endpoint patterns
        endpoints = [
            f"/api/v2/proposals/{proposal_id}/share",
            f"/api/v2/proposals/{proposal_id}/public",
            f"/api/v2/e-proposals/{proposal_id}/data",
            f"/api/v2/hlb/proposals/{proposal_id}"
        ]
        
        for endpoint in endpoints:
            url = f"https://v2.aurorasolar.com{endpoint}"
            debug_print(f"Trying endpoint: {url}")
            
            response = session.get(url, headers=headers)
            debug_print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    continue
                    
        # If direct API calls fail, try parsing the main page
        response = session.get(link, headers=headers)
        if response.status_code == 200:
            # Look for data in various formats
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'window\.PROPOSAL_DATA\s*=\s*({.*?});',
                r'data-proposal\s*=\s*\'({.*?})\'',
                r'"proposal":\s*({.*?})\s*[,}]'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response.text, re.DOTALL)
                for match in matches:
                    try:
                        return json.loads(match)
                    except:
                        continue
        
        return None
        
    except Exception as e:
        debug_print(f"Error during direct extraction: {str(e)}")
        return None

def get_proposal_data(link):
    """Main function that tries both methods"""
    # Try PlayWright first
    data = get_proposal_data_playwright(link)
    if data:
        return data
        
    # Fallback to direct method
    return get_proposal_data_direct(link)

st.title("☀️ Aurora Proposal Data Extractor")
st.markdown("""
This tool extracts data from Aurora Solar proposals.
Please note: It will try multiple methods to get the data.
""")

link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Extract Data", type="primary"):
    try:
        with st.spinner("Processing proposal (please wait)..."):
            data = get_proposal_data(link)
            
   
