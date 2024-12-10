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
    'Cache-Control': 'no-cache',
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

def extract_data_from_html(html_content):
    """Extract data from HTML with detailed debugging"""
    debug_print("Analyzing HTML content...")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Print page title for verification
    title = soup.find('title')
    if title:
        debug_print(f"Page Title: {title.text}")
    
    # Look for data in scripts
    scripts = soup.find_all('script')
    debug_print(f"Found {len(scripts)} script tags")
    
    data_patterns = [
        (r'window\.__INITIAL_STATE__\s*=\s*({.*?});', 'INITIAL_STATE'),
        (r'window\.PROPOSAL_DATA\s*=\s*({.*?});', 'PROPOSAL_DATA'),
        (r'data-proposal\s*=\s*\'({.*?})\'', 'data-proposal'),
        (r'proposal:\s*({.*?})\s*[,}]', 'proposal object')
    ]
    
    for script in scripts:
        if not script.string:
            continue
            
        script_content = str(script.string)
        debug_print(f"Analyzing script: {script_content[:200]}...")
        
        for pattern, pattern_name in data_patterns:
            matches = re.finditer(pattern, script_content, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match.group(1))
                    debug_print(f"Found {pattern_name} data:", data)
                    return data
                except json.JSONDecodeError:
                    debug_print(f"Failed to parse {pattern_name} JSON")
    
    # Look for data in meta tags
    meta_tags = soup.find_all('meta')
    meta_data = {}
    for tag in meta_tags:
        name = tag.get('name', '')
        content = tag.get('content', '')
        if name and content:
            meta_data[name] = content
    
    if meta_data:
        debug_print("Found meta data:", meta_data)
    
    # Look for specific elements
    elements_to_check = [
        ('div', {'class': 'customer-name'}),
        ('div', {'class': 'proposal-details'}),
        ('div', {'data-testid': 'customer-name'}),
        ('div', {'data-testid': 'system-size'}),
        ('div', {'data-testid': 'total-cost'})
    ]
    
    for tag, attrs in elements_to_check:
        elem = soup.find(tag, attrs)
        if elem:
            debug_print(f"Found element {tag} with {attrs}:", elem.text.strip())
    
    return None

def get_proposal_data(link):
    """Get proposal data with enhanced error handling and debugging"""
    try:
        debug_print(f"Processing link: {link}")
        
        # Create session for consistent cookies
        session = requests.Session()
        
        # First request: Get the main page
        debug_print("Making initial request...")
        response = session.get(link, headers=HEADERS, allow_redirects=True)
        debug_print(f"Initial Response Status: {response.status_code}")
        debug_print("Response Headers:", dict(response.headers))
        
        if response.status_code == 200:
            # Try to extract data from HTML
            data = extract_data_from_html(response.text)
            if data:
                return data
            
            # If no data found, try to get the frontend JS
            debug_print("Checking for frontend.js...")
            soup = BeautifulSoup(response.text, 'html.parser')
            js_files = [script['src'] for script in soup.find_all('script', src=True)]
            
            for js_file in js_files:
                if 'frontend' in js_file or 'main' in js_file:
                    debug_print(f"Found JS file: {js_file}")
                    js_response = session.get(js_file, headers=HEADERS)
                    if js_response.status_code == 200:
                        debug_print("Got JS content, looking for API patterns...")
                        
                        # Look for API endpoints in JS
                        api_patterns = [
                            r'"/api/v2/([^"]+)"',
                            r'"/e-proposals/([^"]+)"',
                            r'"proposals/([^"]+)/data"'
                        ]
                        
                        for pattern in api_patterns:
                            matches = re.findall(pattern, js_response.text)
                            if matches:
                                debug_print(f"Found API patterns: {matches}")
        
        debug_print("No data found in initial response")
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
