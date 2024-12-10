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
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_frontend_url(version):
    """Get the frontend JS URL based on version"""
    return f"https://v2.aurorasolar.com/frontend.{version}.js"

def get_proposal_data(link):
    """Get proposal data following Aurora's frontend pattern"""
    session = requests.Session()
    
    try:
        # Step 1: Get the current version
        debug_print("Getting Aurora version...")
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version_data = version_response.json()
        version = version_data.get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Step 2: Get the proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Step 3: Get the frontend JS
        frontend_url = get_frontend_url(version)
        debug_print(f"Getting frontend JS from: {frontend_url}")
        js_response = session.get(frontend_url)
        debug_print(f"Frontend JS Status: {js_response.status_code}")
        
        # Step 4: Try the e-proposal endpoint with proper headers
        proposal_url = f"https://v2.aurorasolar.com/api/v2/e-proposals/{proposal_id}"
        headers = HEADERS.copy()
        headers.update({
            'X-Aurora-Version': version,
            'X-Proposal-Token': proposal_id
        })
        
        debug_print(f"Trying proposal endpoint: {proposal_url}")
        debug_print("Using headers:", headers)
        
        response = session.get(proposal_url, headers=headers)
        debug_print(f"Proposal Response Status: {response.status_code}")
        debug_print("Response Headers:", dict(response.headers))
        
        # Try different content types
        try:
            data = response.json()
            debug_print("Found JSON data:", data)
            return data
        except:
            debug_print("Not JSON response, trying alternative methods...")
        
        # Try alternative endpoint
        data_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/data?version={version}"
        debug_print(f"Trying data endpoint: {data_url}")
        
        response = session.get(data_url, headers=headers)
        debug_print(f"Data Response Status: {response.status_code}")
        
        try:
            data = response.json()
            debug_print("Found JSON data:", data)
            return data
        except:
            debug_print("Not JSON response from data endpoint")
        
        # Try one more endpoint pattern
        content_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/content"
        headers['Accept'] = 'application/json, text/plain, */*'
        
        debug_print(f"Trying content endpoint: {content_url}")
        response = session.get(content_url, headers=headers)
        debug_print(f"Content Response Status: {response.status_code}")
        
        try:
            data = response.json()
            debug_print("Found JSON data:", data)
            return data
        except:
            debug_print("Not JSON response from content endpoint")
            
        # If we got here, try to extract from HTML
        debug_print("Attempting HTML extraction...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for data in script tags
        for script in soup.find_all('script'):
            if script.string and ('window.__INITIAL_STATE__' in str(script.string)):
                debug_print("Found __INITIAL_STATE__ script")
                match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', str(script.string), re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        debug_print("Successfully parsed __INITIAL_STATE__ data")
                        return data
                    except:
                        debug_print("Failed to parse __INITIAL_STATE__ data")
        
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
