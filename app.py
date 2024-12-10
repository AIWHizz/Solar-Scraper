import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json

# Page config
st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
}

def investigate_response(response):
    """Investigate the response type and content"""
    st.write("=== RESPONSE INVESTIGATION ===")
    st.write(f"Status Code: {response.status_code}")
    st.write(f"Content Type: {response.headers.get('Content-Type')}")
    st.write("Response Headers:", dict(response.headers))
    
    # Try to parse as JSON
    try:
        json_data = response.json()
        st.write("Successfully parsed as JSON:", json_data)
        return "json", json_data
    except json.JSONDecodeError:
        st.write("Not valid JSON")
    
    # Look at raw content
    st.write("First 1000 characters of raw content:")
    st.code(response.text[:1000])
    
    # Try to detect content type
    if response.text.strip().startswith('{') or response.text.strip().startswith('['):
        st.write("Content appears to be JSON but couldn't parse")
    elif response.text.strip().startswith('<!DOCTYPE html>'):
        st.write("Content appears to be HTML")
    elif response.text.strip().startswith('<?xml'):
        st.write("Content appears to be XML")
    else:
        st.write("Unknown content type")
    
    return "unknown", None

def try_different_urls(base_url):
    """Try different variations of the URL"""
    urls_to_try = [
        base_url,  # Original URL
        base_url.replace('/e-proposal/', '/api/v2/proposals/'),  # API endpoint
        base_url.replace('/e-proposal/', '/api/proposals/'),  # Alternative API
        f"https://v2.aurorasolar.com/api/v2/proposals/{base_url.split('/')[-1]}/summary",  # Summary endpoint
        f"https://v2.aurorasolar.com/api/v2/proposals/{base_url.split('/')[-1]}/content"   # Content endpoint
    ]
    
    st.write("=== TRYING DIFFERENT URLS ===")
    
    session = requests.Session()
    
    for url in urls_to_try:
        st.write(f"\nTrying URL: {url}")
        try:
            response = session.get(url, headers=HEADERS)
            content_type, data = investigate_response(response)
            if content_type == "json":
                return data
        except Exception as e:
            st.write(f"Error with URL {url}: {str(e)}")
    
    return None

st.title("🔍 Aurora Response Investigator")
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Investigate", type="primary"):
    try:
        with st.spinner("Investigating response..."):
            data = try_different_urls(link)
            
            if data:
                st.success("Found parseable data!")
                st.json(data)
            else:
                st.warning("Could not find parseable data in any endpoint")
                
    except Exception as e:
        st.error(f"Error during investigation: {str(e)}")

with st.expander("Tips"):
    st.markdown("""
    This investigator will:
    1. Try different URL variations
    2. Check response types
    3. Attempt to parse content
    4. Show raw response data
    
    Look for:
    - JSON endpoints
    - API redirects
    - Authentication requirements
    - Content-Type headers
    """)
