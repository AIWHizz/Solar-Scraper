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
    'Access-Control-Request-Method': 'GET',
    'Access-Control-Request-Headers': 'authorization,content-type,x-aurora-version',
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_proposal_data(link):
    """Get proposal data with CORS handling"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session
        session = requests.Session()
        
        # Step 1: CORS Preflight
        options_headers = HEADERS.copy()
        options_headers.update({
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'authorization,content-type,x-aurora-version'
        })
        
        preflight_url = f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}"
        debug_print("Sending OPTIONS request...")
        
        options_response = session.options(preflight_url, headers=options_headers)
        debug_print(f"OPTIONS Response Status: {options_response.status_code}")
        debug_print("OPTIONS Headers:", dict(options_response.headers))
        
        # Step 2: Get version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version_data = version_response.json()
        version = version_data.get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Step 3: Initial auth request
        auth_url = "https://v2.aurorasolar.com/api/v2/auth"
        auth_headers = HEADERS.copy()
        auth_headers.update({
            'Content-Type': 'application/json',
            'X-Aurora-Version': version
        })
        
        auth_data = {
            "grant_type": "proposal_token",
            "proposal_token": proposal_id
        }
        
        debug_print("Sending auth request...")
        auth_response = session.post(auth_url, headers=auth_headers, json=auth_data)
        debug_print(f"Auth Response Status: {auth_response.status_code}")
        
        if auth_response.status_code == 200:
            try:
                auth_data = auth_response.json()
                debug_print("Auth Response:", auth_data)
                token = auth_data.get('access_token')
            except:
                debug_print("No auth token received")
                token = None
        
        # Step 4: Try different API endpoints with proper headers
        api_endpoints = [
            f"/api/v2/proposals/{proposal_id}/view",
            f"/api/v2/proposals/{proposal_id}/data",
            f"/api/v2/e-proposals/{proposal_id}/content",
            f"/api/v2/hlb/proposals/{proposal_id}"
        ]
        
        for endpoint in api_endpoints:
            url = f"https://v2.aurorasolar.com{endpoint}"
            debug_print(f"\nTrying endpoint: {url}")
            
            request_headers = HEADERS.copy()
            request_headers.update({
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Aurora-Version': version,
                'Authorization': f'Bearer {token}' if token else None,
                'X-Proposal-Token': proposal_id
            })
            
            # First send OPTIONS
            debug_print("Sending endpoint OPTIONS...")
            options_response = session.options(url, headers=options_headers)
            debug_print(f"Endpoint OPTIONS Status: {options_response.status_code}")
            
            # Then send GET
            debug_print("Sending GET request...")
            response = session.get(url, headers=request_headers)
            debug_print(f"GET Response Status: {response.status_code}")
            debug_print("Response Headers:", dict(response.headers))
            
            try:
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    data = response.json()
                    debug_print("Found JSON response:", data)
                    return data
                else:
                    debug_print(f"Non-JSON content type: {content_type}")
                    debug_print("Response preview:", response.text[:500])
            except Exception as e:
                debug_print(f"Error processing response: {str(e)}")
        
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
