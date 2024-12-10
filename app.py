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
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document'
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def extract_data_from_response(response):
    """Extract data from response with detailed debugging"""
    debug_print("Analyzing response content...")
    
    try:
        content_type = response.headers.get('Content-Type', '')
        debug_print(f"Content-Type: {content_type}")
        
        # Try JSON first
        if 'application/json' in content_type:
            try:
                return response.json()
            except:
                debug_print("Failed to parse JSON response")
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug the HTML structure
        debug_print("HTML Title:", soup.title.string if soup.title else "No title found")
        debug_print("First 500 chars of HTML:", response.text[:500])
        
        # Look for data in scripts
        scripts = soup.find_all('script')
        debug_print(f"Found {len(scripts)} script tags")
        
        for script in scripts:
            if not script.string:
                continue
                
            script_content = str(script.string)
            debug_print("Analyzing script:", script_content[:200])
            
            # Look for various data patterns
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'window\.PROPOSAL_DATA\s*=\s*({.*?});',
                r'data-proposal\s*=\s*\'({.*?})\'',
                r'"proposal":\s*({.*?})\s*[,}]'
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, script_content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match.group(1))
                        debug_print("Found embedded data!")
                        return data
                    except:
                        continue
        
        # Look for specific elements
        elements = {
            'customer_name': ['customer-name', 'recipient-name', 'proposal-customer'],
            'system_size': ['system-size', 'proposal-system', 'system-details'],
            'total_cost': ['total-cost', 'proposal-cost', 'price-details']
        }
        
        data = {}
        for key, classes in elements.items():
            for class_name in classes:
                element = soup.find(class_=class_name)
                if element:
                    data[key] = element.text.strip()
                    debug_print(f"Found {key}: {data[key]}")
        
        if data:
            return data
            
        debug_print("No data found in response")
        return None
        
    except Exception as e:
        debug_print(f"Error extracting data: {str(e)}")
        return None

def get_proposal_data(link):
    """Get proposal data with progressive loading"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session
        session = requests.Session()
        
        # Get version first
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version_data = version_response.json()
        version = version_data.get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Initial page load
        debug_print("Loading initial page...")
        response = session.get(link, headers=HEADERS)
        debug_print(f"Initial Response Status: {response.status_code}")
        
        # Try to extract data
        data = extract_data_from_response(response)
        if data:
            return data
        
        # Wait and try again
        debug_print("Waiting for page load...")
        time.sleep(10)
        
        # Try different endpoints
        endpoints = [
            f"/api/v2/proposals/{proposal_id}/view",
            f"/api/v2/proposals/{proposal_id}/data",
            f"/api/v2/e-proposals/{proposal_id}/content",
            f"/api/v2/hlb/proposals/{proposal_id}"
        ]
        
        for endpoint in endpoints:
            url = f"https://v2.aurorasolar.com{endpoint}"
            debug_print(f"\nTrying endpoint: {url}")
            
            headers = HEADERS.copy()
            headers.update({
                'X-Aurora-Version': version,
                'Accept': 'application/json'
            })
            
            response = session.get(url, headers=headers)
            debug_print(f"Response Status: {response.status_code}")
            
            data = extract_data_from_response(response)
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
    st.write("Headers Used:", HEADERS)
