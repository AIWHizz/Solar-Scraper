import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

st.set_page_config(page_title="Aurora Data Extractor", layout="wide")

def debug_print(msg, obj=None):
    """Helper function to print debug information"""
    st.write(f"DEBUG: {msg}")
    if obj:
        st.write(obj)

def setup_driver():
    """Setup Chrome driver with proper options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    return webdriver.Chrome(options=chrome_options)

def wait_for_page_load(driver, timeout=30):
    """Wait for page to fully load and render"""
    debug_print("Waiting for page to load...")
    
    try:
        # Wait for initial load
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        # Wait additional time for client-side rendering
        time.sleep(15)  # Wait for Aurora's client-side rendering
        
        debug_print("Page loaded!")
        return True
    except Exception as e:
        debug_print(f"Error waiting for page load: {str(e)}")
        return False

def extract_data_from_page(driver):
    """Extract data from loaded page"""
    debug_print("Extracting data from page...")
    
    try:
        # Wait for specific elements
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "script"))
        )
        
        # Get page source after client-side rendering
        page_source = driver.page_source
        debug_print("Got page source after rendering")
        
        # Look for data in various locations
        data_patterns = [
            (r'window\.__INITIAL_STATE__\s*=\s*({.*?});', 'INITIAL_STATE'),
            (r'window\.PROPOSAL_DATA\s*=\s*({.*?});', 'PROPOSAL_DATA'),
            (r'data-proposal\s*=\s*\'({.*?})\'', 'data-proposal'),
            (r'"proposal":\s*({.*?})\s*[,}]', 'proposal object')
        ]
        
        for pattern, pattern_name in data_patterns:
            matches = re.finditer(pattern, page_source, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match.group(1))
                    debug_print(f"Found {pattern_name} data")
                    return data
                except json.JSONDecodeError:
                    continue
        
        # If no JSON found, try to extract from HTML elements
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Look for specific elements
        data = {}
        elements_to_check = {
            'customer_name': ['customer-name', 'proposal-customer'],
            'system_size': ['system-size', 'proposal-system-size'],
            'total_cost': ['total-cost', 'proposal-cost']
        }
        
        for key, classes in elements_to_check.items():
            for class_name in classes:
                element = driver.find_elements(By.CLASS_NAME, class_name)
                if element:
                    data[key] = element[0].text.strip()
                    debug_print(f"Found {key}: {data[key]}")
        
        if data:
            return data
            
        debug_print("No data found in page")
        return None
        
    except Exception as e:
        debug_print(f"Error extracting data: {str(e)}")
        return None

def get_proposal_data(link):
    """Get proposal data with dynamic page loading"""
    try:
        debug_print(f"Processing link: {link}")
        
        # Setup driver
        driver = setup_driver()
        debug_print("Browser initialized")
        
        try:
            # Load page
            debug_print("Loading page...")
            driver.get(link)
            
            # Wait for page to load
            if wait_for_page_load(driver):
                # Extract data
                data = extract_data_from_page(driver)
                if data:
                    return data
            
            debug_print("Could not extract data from page")
            return None
            
        finally:
            driver.quit()
            debug_print("Browser closed")
    
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

with st.expander("How it works"):
    st.markdown("""
    This tool:
    1. Loads the proposal page in a headless browser
    2. Waits for client-side rendering (15 seconds)
    3. Extracts data from the rendered page
    4. Processes and returns the results
    
    Please be patient as it waits for Aurora's page to fully load!
    """)
