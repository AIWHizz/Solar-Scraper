import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.express as px
from datetime import datetime

class AuroraScraper:
    def extract_data(self, link):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(link, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = {
                'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Client Name': self._extract_text(soup, 'customer-name'),
                'System Size': self._extract_system_size(soup),
                'Price per Watt': self._extract_price(soup),
                'Total Cost': self._extract_cost(soup),
                'Link': link
            }
            return data
        except Exception as e:
            raise Exception(f"Failed to extract data: {str(e)}")

    def _extract_text(self, soup, class_name):
        element = soup.find(class_=class_name)
        return element.text.strip() if element else "Not found"

    def _extract_system_size(self, soup):
        # Add specific extraction logic
        return "TBD"

    def _extract_price(self, soup):
        # Add specific extraction logic
        return "TBD"

    def _extract_cost(self, soup):
        # Add specific extraction logic
        return "TBD"

def main():
    st.set_page_config(page_title="Aurora Proposal Data Extractor", layout="wide")
    
    st.title("☀️ Aurora Proposal Data Extractor")
    
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame()
    
    link = st.text_input("Paste Aurora Proposal Link:")
    
    if st.button("Process Link", type="primary"):
        try:
            with st.spinner("Processing proposal..."):
                scraper = AuroraScraper()
                data = scraper.extract_data(link)
                
                new_df = pd.DataFrame([data])
                if st.session_state.data.empty:
                    st.session_state.data = new_df
                else:
                    st.session_state.data = pd.concat([st.session_state.data, new_df], ignore_index=True)
                
            st.success("✅ Data extracted successfully!")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
    if not st.session_state.data.empty:
        st.subheader("Extracted Data")
        st.dataframe(st.session_state.data)
        
        # Download button
        csv = st.session_state.data.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="aurora_data.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
