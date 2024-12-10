import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json

st.set_page_config(page_title="Aurora Data Investigator", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
}

def get_version():
    """Get the current Aurora frontend version"""
    try:
        version_url = "https://aurora-v2.s3.amazonaws.com/fallback-version.json"
        response = requests.get(version_url)
        if response.status_code == 200:
            version_data = response.json()
            st.write("Version Data:", version_data)
            return version_data.get('version')
    except Exception as e:
        st.write(f"Error getting version: {str(e)}")
    return None

def investigate_proposal(link):
    """Investigate a proposal link"""
    st.write("=== INVESTIGATING PROPOSAL ===")
    
    # Extract proposal ID
    proposal_id = link.split('/')[-1]
    st.write(f"Proposal ID: {proposal_id}")
    
    # Get current version
    version = get_version()
    st.write(f"Current Version: {version}")
    
    session = requests.Session()
    
    # Try different endpoints with detailed logging
    endpoints = [
        f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}",
        f"https://v2.aurorasolar.com/api/v2/e-proposals/{proposal_id}",
        f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/data",
        f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/content"
    ]
    
    for endpoint in endpoints:
        st.write(f"\nTrying endpoint: {endpoint}")
        try:
            # First try without version
            response = session.get(endpoint, headers=HEADERS)
            st.write(f"Status: {response.status_code}")
            st.write("Headers:", dict(response.headers))
            
            # Try to parse as JSON
            try:
                data = response.json()
                st.write("JSON Response:", data)
                continue
            except:
                st.write("Not JSON response")
            
            # Look for JavaScript files
            if 'text/html' in response.headers.get('Content-Type', ''):
                soup = BeautifulSoup(response.text, 'html.parser')
                scripts = soup.find_all('script')
                st.write(f"Found {len(scripts)} script tags")
                
                for script in scripts:
                    if script.string and ('window.__INITIAL_STATE__' in str(script.string) or 'PROPOSAL_DATA' in str(script.string)):
                        st.write("Found data script:")
                        st.code(script.string[:500])
            
            # Try with version header
            if version:
                headers_with_version = HEADERS.copy()
                headers_with_version['X-Aurora-Version'] = version
                response = session.get(endpoint, headers=headers_with_version)
                st.write(f"Status with version header: {response.status_code}")
                
                try:
                    data = response.json()
                    st.write("JSON Response with version:", data)
                except:
                    st.write("Not JSON response with version")
            
        except Exception as e:
            st.write(f"Error: {str(e)}")

st.title("🔍 Aurora API Investigator")
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Investigate", type="primary"):
    if not link:
        st.error("Please enter a proposal link")
    else:
        investigate_proposal(link)

with st.expander("Debug Information"):
    st.markdown("""
    This investigator will:
    1. Extract the proposal ID
    2. Get the current Aurora version
    3. Try different API endpoints
    4. Look for embedded data
    5. Show all responses
    
    Please paste a complete proposal link to begin investigation.
    """)
