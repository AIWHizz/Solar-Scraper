import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import time
import asyncio
import aiohttp

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document',
    'Cache-Control': 'max-age=0'
}

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def parse_html_content(html_content):
    """Parse HTML content for proposal data"""
    debug_print("Parsing HTML content...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Print the first 1000 characters of HTML for debugging
    debug_print("HTML Preview:", html_content[:1000])
    
    data = {}
    
    # Look for scripts containing data
    scripts = soup.find_all('script')
    debug_print(f"Found {len(scripts)} script tags")
    
    for script in scripts:
        if not script.string:
            continue
            
        script_content = str(script.string)
        debug_print("Analyzing script content:", script_content[:200])
        
        # Look for various data patterns
        patterns = [
            (r'window\.__INITIAL_STATE__\s*=\s*({.*?});', 'INITIAL_STATE'),
            (r'window\.PROPOSAL_DATA\s*=\s*({.*?});', 'PROPOSAL_DATA'),
            (r'data-proposal\s*=\s*\'({.*?})\'', 'data-proposal'),
            (r'"proposal":\s*({.*?})\s*[,}]', 'proposal object')
        ]
        
        for pattern, pattern_name in patterns:
            matches = re.finditer(pattern, script_content, re.DOTALL)
            for match in matches:
                try:
                    json_data = json.loads(match.group(1))
                    debug_print(f"Found {pattern_name} data:", json_data)
                    return json_data
                except json.JSONDecodeError:
                    debug_print(f"Failed to parse {pattern_name} JSON")
    
    # Look for specific elements
    elements_to_check = {
        'customer_name': ['customer-name', 'recipient-name', 'proposal-customer'],
        'system_size': ['system-size', 'proposal-system', 'system-details'],
        'total_cost': ['total-cost', 'proposal-cost', 'price-details']
    }
    
    for key, classes in elements_to_check.items():
        for class_name in classes:
            element = soup.find(class_=class_name)
            if element:
                data[key] = element.text.strip()
                debug_print(f"Found {key}: {data[key]}")
    
    # Look for meta tags
    meta_tags = soup.find_all('meta')
    for tag in meta_tags:
        name = tag.get('name', '')
        if name and ('proposal' in name.lower() or 'customer' in name.lower()):
            content = tag.get('content', '')
            debug_print(f"Found meta tag {name}: {content}")
            data[name] = content
    
    return data if data else None

def get_proposal_data(link):
    """Get proposal data with progressive loading"""
    try:
        debug_print(f"Processing link: {link}")
        
        # Create session
        session = requests.Session()
        
        # Step 1: Initial page load
        debug_print("Making initial request...")
        response = session.get(link, headers=HEADERS)
        debug_print(f"Initial response status: {response.status_code}")
        
        if response.status_code == 200:
            # Extract data from HTML
            debug_print("Extracting data from HTML...")
            data = parse_html_content(response.text)
            
            if data:
                return data
            
            # If no data found, try alternative methods
            debug_print("No data found in initial HTML, trying alternative methods...")
            
            # Get version
            version_response = requests.get("https://aurora-v2.s3.amazonaws.com/fallback-version.json")
            version_data = version_response.json()
            version = version_data.get('version')
            
            # Try loading frontend.js
            js_url = f"https://v2.aurorasolar.com/frontend.{version}.js"
            js_response = session.get(js_url)
            
            if js_response.status_code == 200:
                debug_print("Got frontend.js, looking for data patterns...")
                js_content = js_response.text
                
                # Look for data in JavaScript
                data_patterns = [
                    r'customer:\s*({[^}]+})',
                    r'proposal:\s*({[^}]+})',
                    r'data:\s*({[^}]+})'
                ]
                
                for pattern in data_patterns:
                    matches = re.finditer(pattern, js_content, re.DOTALL)
                    for match in matches:
                        try:
                            data = json.loads(match.group(1))
                            debug_print("Found data in JavaScript:", data)
                            return data
                        except:
                            continue
            
            # Wait and try one more time
            debug_print("Waiting for page to load...")
            time.sleep(5)
            
            response = session.get(link, headers=HEADERS)
            data = parse_html_content(response.text)
            
            return data
            
        return None
        
    except Exception as e:
        debug_print(f"Error during extraction: {str(e)}")
        return None

st.title("☀️ Aurora Proposal Data Extractor")
link = st.text_input("Paste Aurora Proposal Link:")

if st.button("Extract Data", type="primary"):
    try:
        with st.spinner("Processing proposal (this may take 15-20 seconds)..."):
            data = get_proposal_data(link)
            
            if data:
                st.success("Data extracted!")
                st.json(data)
            else:
                st.error("Could not extract data")
    except Exception as e:
        st.error(f"Error: {str(e)}")

with st.expander("Debug Information"):
    st.write("Headers Used:", HEADERS)
