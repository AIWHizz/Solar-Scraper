import streamlit as st
import requests
import json
import time
import re
from urllib.parse import quote

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_proposal_data(link):
    """Get proposal data using direct API approach"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session
        session = requests.Session()
        
        # Step 1: Get version
        try:
            version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
            version = version_response.json().get('version')
            debug_print(f"Aurora Version: {version}")
        except:
            version = "0.10876.0"  # Fallback version
        
        # Step 2: Initial page load with wait
        debug_print("Loading initial page...")
        initial_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://v2.aurorasolar.com/',
            'Origin': 'https://v2.aurorasolar.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        
        response = session.get(link, headers=initial_headers)
        debug_print(f"Initial Response Status: {response.status_code}")
        
        # Step 3: Wait for page load
        debug_print("Waiting 45 seconds for page load...")
        time.sleep(45)
        
        # Step 4: Try different API endpoints
        api_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://v2.aurorasolar.com',
            'Referer': f'https://v2.aurorasolar.com/e-proposal/{proposal_id}',
            'X-Aurora-Version': version,
            'X-Proposal-Token': proposal_id,
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        endpoints = [
            f"/api/v2/proposals/{proposal_id}/share",
            f"/api/v2/proposals/{proposal_id}/public",
            f"/api/v2/e-proposals/{proposal_id}/data",
            f"/api/v2/hlb/proposals/{proposal_id}",
            f"/api/v2/proposals/{proposal_id}/view"
        ]
        
        for endpoint in endpoints:
            url = f"https://v2.aurorasolar.com{endpoint}"
            debug_print(f"\nTrying endpoint: {url}")
            
            response = session.get(url, headers=api_headers)
            debug_print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    debug_print("Found JSON data!")
                    return data
                except json.JSONDecodeError:
                    # If not JSON, try to extract from HTML
                    try:
                        # Look for data in scripts
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
                                    data = json.loads(match)
                                    debug_print("Found embedded data!")
                                    return data
                                except:
                                    continue
                    except:
                        continue
        
        # If no data found, try parsing the final page
        debug_print("Trying final page parse...")
        response = session.get(link, headers=initial_headers)
        
        if response.status_code == 200:
            # Extract any visible data
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = {}
            elements = {
                'customer_name': ['customer-name', 'recipient-name'],
                'system_size': ['system-size', 'system-details'],
                'total_cost': ['total-cost', 'price-details']
            }
            
            for key, classes in elements.items():
                for class_name in classes:
                    element = soup.find(class_=class_name)
                    if element:
                        data[key] = element.text.strip()
                        debug_print(f"Found {key}: {element.text.strip()}")
            
            if data:
                return data
        
        return None
        
    except Exception as e:
        debug_print(f"Error during extraction: {str(e)}")
        return None

st.title("☀️ Aurora Proposal Data Extractor")
st.markdown("""
This tool extracts data from Aurora Solar proposals.
Please note: It will wait 45 seconds for the page to fully load.
""")

link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Extract Data", type="primary"):
    try:
        with st.spinner("Processing proposal (please wait 45 seconds)..."):
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
    This tool:
    1. Loads the initial page
    2. Waits 45 seconds for JavaScript execution
    3. Tries multiple API endpoints
    4. Attempts to extract data from HTML
    """)
