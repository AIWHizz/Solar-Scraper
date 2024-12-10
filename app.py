import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import time

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Sec-Ch-Ua': '"Not_A Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1'
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_proposal_data(link):
    """Get proposal data with extended wait time"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session
        session = requests.Session()
        
        # Initial page load with wait
        debug_print("Loading initial page and waiting 45 seconds...")
        response = session.get(link, headers=HEADERS)
        debug_print(f"Initial Response Status: {response.status_code}")
        
        # Wait for page load
        time.sleep(45)
        
        # Get the page again after waiting
        debug_print("Getting page after wait...")
        response = session.get(link, headers=HEADERS)
        debug_print(f"Response Status: {response.status_code}")
        debug_print("Response Headers:", dict(response.headers))
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            debug_print("Page Title:", soup.title.string if soup.title else "No title")
            
            # Look for data in scripts
            scripts = soup.find_all('script')
            debug_print(f"Found {len(scripts)} script tags")
            
            for script in scripts:
                if not script.string:
                    continue
                    
                script_content = str(script.string)
                debug_print("Analyzing script content:", script_content[:200])
                
                # Look for data patterns
                patterns = [
                    (r'window\.__INITIAL_STATE__\s*=\s*({.*?});', 'INITIAL_STATE'),
                    (r'window\.PROPOSAL_DATA\s*=\s*({.*?});', 'PROPOSAL_DATA'),
                    (r'data-proposal\s*=\s*\'({.*?})\'', 'data-proposal'),
                    (r'"proposal":\s*({.*?})\s*[,}]', 'proposal object'),
                    (r'{"customer":.*?"system":.*?}', 'full object')
                ]
                
                for pattern, pattern_name in patterns:
                    matches = re.finditer(pattern, script_content, re.DOTALL)
                    for match in matches:
                        try:
                            data = json.loads(match.group(1))
                            debug_print(f"Found {pattern_name} data!")
                            return data
                        except json.JSONDecodeError:
                            continue
            
            # Look for specific elements if no JSON found
            debug_print("Looking for specific elements...")
            elements = {
                'customer_name': ['customer-name', 'recipient-name'],
                'system_size': ['system-size', 'system-details'],
                'total_cost': ['total-cost', 'price-details']
            }
            
            data = {}
            for key, classes in elements.items():
                for class_name in classes:
                    elements = soup.find_all(class_=class_name)
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text:
                            data[key] = text
                            debug_print(f"Found {key}: {text}")
            
            if data:
                return data
            
            # Try one more time with different headers
            debug_print("Trying one final request...")
            headers = HEADERS.copy()
            headers.update({
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            })
            
            final_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/view"
            response = session.get(final_url, headers=headers)
            
            try:
                return response.json()
            except:
                debug_print("Final attempt failed")
        
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
        with st.spinner("Processing proposal (please wait 45 seconds for page load)..."):
            data = get_proposal_data(link)
            
            if data:
                st.success("Data extracted!")
                st.json(data)
            else:
                st.error("Could not extract data. Please check the link and try again.")
    except Exception as e:
        st.error(f"Error: {str(e)}")

with st.expander("Debug Information"):
    st.write("Headers Used:", HEADERS)
