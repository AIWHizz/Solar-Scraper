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
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_hlb_data(proposal_id, version):
    """Get data using HLB endpoint"""
    session = requests.Session()
    
    # First, get the HLB JavaScript
    hlb_url = f"https://v2.aurorasolar.com/hlb.{version}.js"
    debug_print(f"Getting HLB JS from: {hlb_url}")
    
    js_response = session.get(hlb_url)
    debug_print(f"HLB JS Status: {js_response.status_code}")
    
    if js_response.status_code == 200:
        # Look for API endpoints in the JS
        api_patterns = [
            r'"(/api/v2/[^"]+)"',
            r'"(/hlb/[^"]+)"',
            r'"(/e-proposals/[^"]+)"'
        ]
        
        endpoints = []
        for pattern in api_patterns:
            matches = re.findall(pattern, js_response.text)
            endpoints.extend(matches)
        
        debug_print("Found API endpoints:", endpoints)
        
        # Try each potential endpoint
        headers = HEADERS.copy()
        headers.update({
            'X-Aurora-Version': version,
            'X-Proposal-ID': proposal_id,
            'Accept': 'application/json'
        })
        
        for endpoint in endpoints:
            url = f"https://v2.aurorasolar.com{endpoint}"
            if '{id}' in url:
                url = url.replace('{id}', proposal_id)
            elif '{proposalId}' in url:
                url = url.replace('{proposalId}', proposal_id)
                
            debug_print(f"Trying endpoint: {url}")
            response = session.get(url, headers=headers)
            debug_print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    debug_print("Not JSON response")
    
    return None

def get_proposal_data(link):
    """Get proposal data using HLB approach"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Get current version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version_data = version_response.json()
        version = version_data.get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Try HLB endpoint first
        data = get_hlb_data(proposal_id, version)
        if data:
            return data
            
        # If HLB fails, try direct API
        session = requests.Session()
        
        # Get the initial page to set up session
        initial_url = f"https://v2.aurorasolar.com/e-proposal/{proposal_id}"
        debug_print(f"Getting initial page: {initial_url}")
        
        headers = HEADERS.copy()
        headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Cache-Control': 'no-cache'
        })
        
        response = session.get(initial_url, headers=headers)
        debug_print(f"Initial Response Status: {response.status_code}")
        
        if response.status_code == 200:
            # Try the data endpoint
            data_url = f"https://v2.aurorasolar.com/api/v2/hlb/proposals/{proposal_id}"
            headers = HEADERS.copy()
            headers.update({
                'Accept': 'application/json',
                'X-Aurora-Version': version,
                'X-HLB-Token': proposal_id
            })
            
            debug_print(f"Trying data endpoint: {data_url}")
            response = session.get(data_url, headers=headers)
            debug_print(f"Data Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    debug_print("Not JSON response")
            
            # Try one more endpoint pattern
            alt_url = f"https://v2.aurorasolar.com/api/v2/hlb/{proposal_id}/data"
            debug_print(f"Trying alternative endpoint: {alt_url}")
            response = session.get(alt_url, headers=headers)
            
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    debug_print("Not JSON response")
        
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
    st.write("Base Headers:", HEADERS)
