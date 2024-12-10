import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import base64
import time

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://v2.aurorasolar.com',
    'Referer': 'https://v2.aurorasolar.com/',
    'X-Requested-With': 'XMLHttpRequest',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty'
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def analyze_js_content(js_content):
    """Analyze JavaScript content for API patterns"""
    debug_print("Analyzing JavaScript content...")
    
    # Look for API configuration
    api_patterns = [
        r'baseURL:\s*[\'"]([^\'"]+)[\'"]',
        r'endpoint:\s*[\'"]([^\'"]+)[\'"]',
        r'url:\s*[\'"]([^\'"]+proposals[^\'"]+)[\'"]',
        r'headers:\s*({[^}]+})'
    ]
    
    findings = {}
    for pattern in api_patterns:
        matches = re.findall(pattern, js_content)
        if matches:
            debug_print(f"Found pattern matches: {matches}")
            findings[pattern] = matches
    
    return findings

def get_proposal_data(link):
    """Get proposal data with enhanced JS analysis"""
    try:
        # Extract proposal ID
        proposal_id = link.split('/')[-1]
        debug_print(f"Proposal ID: {proposal_id}")
        
        # Get current version
        version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
        version_data = version_response.json()
        version = version_data.get('version')
        debug_print(f"Aurora Version: {version}")
        
        # Create session
        session = requests.Session()
        
        # Get HLB JavaScript
        hlb_url = f"https://v2.aurorasolar.com/hlb.{version}.js"
        debug_print(f"Getting HLB JS from: {hlb_url}")
        
        js_response = session.get(hlb_url)
        debug_print(f"HLB JS Status: {js_response.status_code}")
        
        if js_response.status_code == 200:
            # Analyze JS content
            js_findings = analyze_js_content(js_response.text)
            debug_print("JavaScript Analysis:", js_findings)
            
            # Get the initial page
            initial_url = f"https://v2.aurorasolar.com/e-proposal/{proposal_id}"
            initial_headers = HEADERS.copy()
            initial_headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
                'X-Aurora-Version': version
            })
            
            debug_print("Getting initial page...")
            response = session.get(initial_url, headers=initial_headers)
            debug_print(f"Initial Response Status: {response.status_code}")
            
            if response.status_code == 200:
                # Extract any tokens or config from the page
                soup = BeautifulSoup(response.text, 'html.parser')
                scripts = soup.find_all('script')
                
                config_data = None
                for script in scripts:
                    if script.string and 'window.__INITIAL_STATE__' in str(script.string):
                        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', str(script.string), re.DOTALL)
                        if match:
                            try:
                                config_data = json.loads(match.group(1))
                                debug_print("Found config data:", config_data)
                            except:
                                pass
            
            # Try different API patterns
            api_patterns = [
                f"/api/v2/hlb/proposals/{proposal_id}",
                f"/api/v2/hlb/{proposal_id}/view",
                f"/api/v2/hlb/{proposal_id}/data",
                f"/api/v2/e-proposals/{proposal_id}/shared"
            ]
            
            for endpoint in api_patterns:
                url = f"https://v2.aurorasolar.com{endpoint}"
                debug_print(f"\nTrying endpoint: {url}")
                
                headers = HEADERS.copy()
                headers.update({
                    'X-Aurora-Version': version,
                    'X-Proposal-Token': proposal_id,
                    'Accept': 'application/json'
                })
                
                if config_data and config_data.get('token'):
                    headers['Authorization'] = f"Bearer {config_data['token']}"
                
                debug_print("Using headers:", headers)
                
                response = session.get(url, headers=headers)
                debug_print(f"Response Status: {response.status_code}")
                debug_print("Response Headers:", dict(response.headers))
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        debug_print("Found JSON data!")
                        return data
                    except json.JSONDecodeError:
                        debug_print("Response content preview:", response.text[:500])
                        
                        # Try to find JSON in HTML response
                        if 'text/html' in response.headers.get('Content-Type', ''):
                            soup = BeautifulSoup(response.text, 'html.parser')
                            for script in soup.find_all('script'):
                                if script.string:
                                    json_patterns = [
                                        r'window\.__PROPOSAL_DATA__\s*=\s*({.*?});',
                                        r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                                        r'{"proposal":\s*({.*?})\s*}',
                                        r'data-proposal=\'({.*?})\''
                                    ]
                                    
                                    for pattern in json_patterns:
                                        match = re.search(pattern, str(script.string), re.DOTALL)
                                        if match:
                                            try:
                                                data = json.loads(match.group(1))
                                                debug_print("Found embedded JSON data!")
                                                return data
                                            except:
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
    st.write("Base Headers:", HEADERS)
