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
    'Accept-Version': '2',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Content-Type': 'application/json'
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_auth_token(proposal_id):
    """Get authentication token"""
    auth_url = "https://v2.aurorasolar.com/api/v2/auth/token"
    payload = {
        "proposal_id": proposal_id,
        "grant_type": "proposal_token"
    }
    
    debug_print("Attempting to get auth token...")
    response = requests.post(auth_url, json=payload, headers=HEADERS)
    debug_print(f"Auth Response Status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            debug_print("Auth Response:", data)
            return data.get('access_token')
        except:
            debug_print("Failed to parse auth response")
    return None

def get_proposal_data(link):
    """Get proposal data with proper authentication"""
    try:
        # Step 1: Get version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version_data = version_response.json()
        version = version_data.get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Step 2: Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Step 3: Get auth token
        auth_token = get_auth_token(proposal_id)
        if auth_token:
            debug_print("Got auth token")
        
        # Step 4: Set up session with proper headers
        session = requests.Session()
        headers = HEADERS.copy()
        headers.update({
            'X-Aurora-Version': version,
            'X-Auth-Token': auth_token if auth_token else proposal_id,
            'Authorization': f'Bearer {auth_token}' if auth_token else None
        })
        
        # Step 5: Try different endpoints with proper authentication
        endpoints = [
            ("https://v2.aurorasolar.com/api/v2/e-proposals/view", "view"),
            (f"https://v2.aurorasolar.com/api/v2/e-proposals/{proposal_id}", "proposal"),
            (f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/public", "public"),
            (f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/summary", "summary")
        ]
        
        for url, endpoint_type in endpoints:
            debug_print(f"\nTrying {endpoint_type} endpoint: {url}")
            debug_print("Using headers:", headers)
            
            response = session.get(url, headers=headers)
            debug_print(f"Response Status: {response.status_code}")
            debug_print("Response Headers:", dict(response.headers))
            
            if response.status_code == 200:
                try:
                    content_type = response.headers.get('Content-Type', '')
                    debug_print(f"Content Type: {content_type}")
                    
                    if 'application/json' in content_type:
                        data = response.json()
                        debug_print(f"Found JSON data in {endpoint_type}")
                        return data
                    else:
                        debug_print("Response Content Preview:", response.text[:500])
                        
                        # Try to find JSON in HTML
                        if 'text/html' in content_type:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            scripts = soup.find_all('script')
                            
                            for script in scripts:
                                if script.string:
                                    # Look for various data patterns
                                    patterns = [
                                        r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                                        r'window\.PROPOSAL_DATA\s*=\s*({.*?});',
                                        r'{"customer":.*"system":.*}'
                                    ]
                                    
                                    for pattern in patterns:
                                        match = re.search(pattern, str(script.string), re.DOTALL)
                                        if match:
                                            try:
                                                data = json.loads(match.group(1))
                                                debug_print(f"Found embedded data in {endpoint_type}")
                                                return data
                                            except:
                                                continue
                
                except Exception as e:
                    debug_print(f"Error processing {endpoint_type} response: {str(e)}")
        
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
