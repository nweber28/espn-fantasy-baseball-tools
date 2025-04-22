import streamlit as st

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
- **Team Rosters**: View and analyze team rosters from your ESPN league
""")
