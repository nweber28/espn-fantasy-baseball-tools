import streamlit as st
from utils.logging_utils import setup_logging

# Setup logging
logger = setup_logging()

# Set page config
st.set_page_config(
    page_title="Fantasy Baseball Analysis",
    page_icon="🏠",
    layout="wide"
)

# Main page content
st.title("Fantasy Baseball Analysis")
st.markdown("""
Welcome to the Fantasy Baseball Analysis tool! Use the sidebar to navigate between different analysis pages:

- **Pitcher Streaming**: Analyze pitcher matchups and streaming opportunities
- **Waiver Wire Analyzer**: Find valuable players on the waiver wire
""")

# Add version info
st.sidebar.markdown("---")
st.sidebar.info("Fantasy Baseball Analysis v1.0.0")
