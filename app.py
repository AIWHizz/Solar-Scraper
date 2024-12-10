import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import base64

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
    'X-Requested-With': 'XMLHttpRequest',
    'Authorization': 'Bearer null',  # Will be updated with actual token
    'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def analyze_frontend_js(version):
    """Analyze the frontend JS for API patterns"""
    url = f"https://v2.aurorasolar.com/frontend.{version}.js"
    debug_print(f"Analyzing frontend JS from: {url}")
    
    response = requests.get(url)
    if response.status_code == 200:
        js_content = response.text
        
        # Look for API endpoints
        api_patterns = [
            r'"/api/v2/proposals/([^"]+)"',
            r'"/api/v2/e-proposals/([^"]+)"',
            r'"proposals/([^"]+)/data"',
            r'"proposals/([^"]+)/content"'
        ]
        
        found_patterns = []
        for pattern in api_patterns:
            matches = re.findall(pattern, js_content)
            if matches:
                found_patterns.extend(matches)
        
        debug_print("Found API patterns:", found_patterns)
        
        # Look for authentication methods
        auth_patterns = [
            r'headers:\s*{([^}]+)}',
            r'Authorization.*Bearer',
            r'x-aurora-version'
        ]
        
        for pattern in auth_patterns:
            matches = re.findall(pattern, js_content)
            if matches:
                debug_print(f"Found auth pattern: {pattern}", matches)
        
        return js_content
    return None

def get_proposal_data(link):
    """Get proposal data using frontend JS analysis"""
    try:
        # Step 1: Get Aurora version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version_data = version_response.json()
        version = version_data.get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Step 2: Analyze frontend JS
        js_content = analyze_frontend_js(version)
        if not js_content:
            debug_print("Could not get frontend JS")
            return None
        
        # Step 3: Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Step 4: Try different endpoint patterns
        session = requests.Session()
        
        endpoints = [
            (f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/hlb", "HLB"),
            (f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/view", "View"),
            (f"https://v2.aurorasolar.com/api/v2/e-proposals/{proposal_id}/data", "Data"),
            (f"https://v2.aurorasolar.com/api/v2/e-proposals/{proposal_id}/content", "Content")
        ]
        
        headers = HEADERS.copy()
        headers.update({
            'X-Aurora-Version': version,
            'X-Proposal-Token': proposal_id,
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        for endpoint, endpoint_type in endpoints:
            debug_print(f"Trying {endpoint_type} endpoint: {endpoint}")
            
            response = session.get(endpoint, headers=headers)
            debug_print(f"{endpoint_type} Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    debug_print(f"Found JSON data in {endpoint_type} endpoint")
                    return data
                except json.JSONDecodeError:
                    debug_print(f"Not JSON response from {endpoint_type} endpoint")
                    
                if 'text/html' in response.headers.get('Content-Type', ''):
                    soup = BeautifulSoup(response.text, 'html.parser')
                    scripts = soup.find_all('script')
                    
                    for script in scripts:
                        if script.string and 'window.__INITIAL_STATE__' in str(script.string):
                            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', str(script.string), re.DOTALL)
                            if match:
                                try:
                                    data = json.loads(match.group(1))
                                    debug_print(f"Found data in {endpoint_type} script")
                                    return data
                                except json.JSONDecodeError:
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

with st.expander("Debug Information"):
    st.write("Headers:", HEADERS)
