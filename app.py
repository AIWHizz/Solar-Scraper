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
    'Host': 'v2.aurorasolar.com',
    'Connection': 'keep-alive',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty'
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def get_token(proposal_id):
    """Get proposal token using their token endpoint"""
    token_url = "https://v2.aurorasolar.com/api/v2/token"
    payload = {
        "token": proposal_id,
        "type": "proposal"
    }
    
    debug_print("Requesting token...")
    response = requests.post(token_url, json=payload, headers=HEADERS)
    debug_print(f"Token Response Status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            return response.json().get('token')
        except:
            pass
    return None

def get_proposal_data(link):
    """Get proposal data using proper token authentication"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Create session for consistent cookies
        session = requests.Session()
        
        # First, try to get the proposal page to get any necessary cookies
        debug_print("Getting initial page...")
        initial_response = session.get(link, headers=HEADERS)
        debug_print(f"Initial Response Status: {initial_response.status_code}")
        
        # Get token
        token = get_token(proposal_id)
        if token:
            debug_print("Got token:", token)
        
        # Update headers with token
        headers = HEADERS.copy()
        headers.update({
            'Authorization': f'Bearer {token}' if token else None,
            'X-Proposal-Token': proposal_id
        })
        
        # Try different API patterns
        api_patterns = [
            f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/shared",
            f"https://v2.aurorasolar.com/api/v2/e-proposals/{proposal_id}/shared",
            f"https://v2.aurorasolar.com/api/v2/proposals/{proposal_id}/public-view",
            f"https://v2.aurorasolar.com/api/v2/e-proposals/{proposal_id}/public"
        ]
        
        for url in api_patterns:
            debug_print(f"\nTrying endpoint: {url}")
            
            response = session.get(url, headers=headers)
            debug_print(f"Response Status: {response.status_code}")
            debug_print("Response Headers:", dict(response.headers))
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    debug_print("Found JSON response:", data)
                    return data
                except json.JSONDecodeError:
                    content_type = response.headers.get('Content-Type', '')
                    debug_print(f"Not JSON response (Content-Type: {content_type})")
                    
                    if 'text/html' in content_type:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for data in meta tags
                        meta_tags = soup.find_all('meta', {'name': re.compile(r'proposal-.*')})
                        if meta_tags:
                            data = {}
                            for tag in meta_tags:
                                key = tag.get('name', '').replace('proposal-', '')
                                value = tag.get('content', '')
                                data[key] = value
                            if data:
                                debug_print("Found data in meta tags:", data)
                                return data
        
        # If no data found through API, try parsing the HTML
        debug_print("Attempting to parse HTML response...")
        soup = BeautifulSoup(initial_response.text, 'html.parser')
        
        # Look for customer name
        customer_patterns = [
            'proposal-customer-name',
            'customer-name',
            'recipient-name'
        ]
        
        for pattern in customer_patterns:
            element = soup.find(attrs={'data-testid': pattern}) or soup.find(class_=pattern)
            if element:
                debug_print(f"Found customer name: {element.text}")
                return {
                    'customer_name': element.text.strip(),
                    'proposal_id': proposal_id
                }
        
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
