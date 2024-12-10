# [Previous imports remain the same]
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# [Previous AuroraWebScraper class remains the same]

def create_summary_stats(df):
    """Generate summary statistics"""
    stats = {
        "Total Proposals": len(df),
        "Average System Size": f"{df['System Size (kW)'].mean():.2f} kW",
        "Average Price/Watt": f"${df['Price per Watt ($)'].mean():.2f}",
        "Average Bill Offset": f"{df['Bill Offset (%)'].mean():.1f}%",
        "Total System Value": f"${df['Total Cost ($)'].sum():,.2f}",
        "Average Monthly Savings": f"${(df['Before Monthly Bill ($)'] - df['After Monthly Bill ($)']).mean():.2f}"
    }
    return stats

def create_visualizations(df):
    """Create interactive visualizations"""
    # System Size vs Price scatter plot
    fig1 = px.scatter(df, 
        x='System Size (kW)', 
        y='Total Cost ($)',
        title='System Size vs Total Cost',
        trendline="ols"
    )

    # Monthly Bill Comparison
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        name='Before Solar',
        x=df['Client Name'],
        y=df['Before Monthly Bill ($)']
    ))
    fig2.add_trace(go.Bar(
        name='After Solar',
        x=df['Client Name'],
        y=df['After Monthly Bill ($)']
    ))
    fig2.update_layout(title='Monthly Bill Comparison by Client')

    # Efficiency Distribution
    fig3 = px.histogram(df, 
        x='Efficiency (%)',
        title='System Efficiency Distribution'
    )

    return [fig1, fig2, fig3]

def main():
    st.set_page_config(
        page_title="Aurora Proposal Data Extractor",
        page_icon="☀️",
        layout="wide"
    )
    
    st.title("☀️ Aurora Proposal Data Extractor")
    
    # Initialize session state
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame()
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["Data Entry", "Dashboard", "Analysis", "Data Export"])
    
    with tab1:
        st.subheader("Enter Proposal Links")
        
        # Multiple link processing
        links_text = st.text_area(
            "Paste Aurora Proposal Link(s)",
            placeholder="Enter one or multiple links (one per line)",
            height=100
        )
        
        if st.button("Process Links", type="primary"):
            links = [link.strip() for link in links_text.split('\n') if link.strip()]
            
            progress_bar = st.progress(0)
            for i, link in enumerate(links):
                try:
                    with st.spinner(f"Processing link {i+1} of {len(links)}..."):
                        scraper = AuroraWebScraper()
                        data = scraper.extract_data(link)
                        
                        new_df = pd.DataFrame([data])
                        if st.session_state.data.empty:
                            st.session_state.data = new_df
                        else:
                            st.session_state.data = pd.concat([st.session_state.data, new_df], ignore_index=True)
                        
                    progress_bar.progress((i + 1) / len(links))
                except Exception as e:
                    st.error(f"❌ Error processing link {link}: {str(e)}")
            
            st.success("✅ Processing complete!")

    with tab2:
        if not st.session_state.data.empty:
            st.subheader("Dashboard")
            
            # Summary Statistics
            stats = create_summary_stats(st.session_state.data)
            cols = st.columns(3)
            for i, (stat, value) in enumerate(stats.items()):
                with cols[i % 3]:
                    st.metric(stat, value)
            
            # Visualizations
            st.subheader("Visualizations")
            figs = create_visualizations(st.session_state.data)
            for fig in figs:
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        if not st.session_state.data.empty:
            st.subheader("Data Analysis")
            
            # Filtering
            st.subheader("Filter Data")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                min_size = st.number_input("Min System Size (kW)", 
                    min_value=float(st.session_state.data['System Size (kW)'].min()),
                    max_value=float(st.session_state.data['System Size (kW)'].max())
                )
            
            with col2:
                max_price = st.number_input("Max Price per Watt ($)",
                    min_value=float(st.session_state.data['Price per Watt ($)'].min()),
                    max_value=float(st.session_state.data['Price per Watt ($)'].max())
                )
            
            with col3:
                min_offset = st.number_input("Min Bill Offset (%)",
                    min_value=float(st.session_state.data['Bill Offset (%)'].min()),
                    max_value=float(st.session_state.data['Bill Offset (%)'].max())
                )
            
            # Apply filters
            filtered_df = st.session_state.data[
                (st.session_state.data['System Size (kW)'] >= min_size) &
                (st.session_state.data['Price per Watt ($)'] <= max_price) &
                (st.session_state.data['Bill Offset (%)'] >= min_offset)
            ]
            
            st.dataframe(filtered_df, use_container_width=True)

    with tab4:
        if not st.session_state.data.empty:
            st.subheader("Export Data")
            
            # Download options
            export_format = st.radio("Select export format:", ["Excel", "CSV"])
            
            if export_format == "Excel":
                st.markdown(get_table_download_link(st.session_state.data), unsafe_allow_html=True)
            else:
                csv = st.session_state.data.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="aurora_data.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()
