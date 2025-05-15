import streamlit as st
from utils.logging_utils import setup_logging
from config.settings import DEFAULT_LEAGUE_ID, cookies
from services.espn_service import ESPNService

# Setup logging
logger = setup_logging()

# Set page config
st.set_page_config(
    page_title="Fantasy Baseball Setup",
    page_icon="⚾",
    layout="wide"
)

# Initialize session state for league ID and my team if they don't exist
if 'league_id' not in st.session_state:
    st.session_state.league_id = DEFAULT_LEAGUE_ID
if 'my_team_id' not in st.session_state:
    st.session_state.my_team_id = None
if 'my_team_name' not in st.session_state:
    st.session_state.my_team_name = None
if 'teams_data' not in st.session_state:
    st.session_state.teams_data = None

# Main page content
st.title("⚾ Fantasy Baseball Setup")

# Create a setup form for League ID
with st.form("league_setup_form"):
    st.markdown("""
    ## Welcome to Fantasy Baseball Analysis!
    
    Please enter your ESPN Fantasy Baseball League ID below to get started.
    This ID will be used across all analysis tools.
    """)
    
    # League ID input
    league_id = st.text_input(
        "ESPN League ID", 
        value=st.session_state.league_id,
        help="Enter your ESPN Fantasy Baseball League ID. This can be found in the URL of your league page."
    )
    
    # Submit button
    submitted = st.form_submit_button("Save League ID")
    
    if submitted:
        st.session_state.league_id = league_id
        # Reset team selection when league changes
        st.session_state.my_team_id = None
        st.session_state.my_team_name = None
        st.session_state.teams_data = None
        st.success(f"League ID saved: {league_id}")
        logger.info(f"User set League ID to: {league_id}")
        # Force a rerun to update the page with team selection
        st.rerun()

# After league ID is set, fetch teams and allow team selection
if st.session_state.league_id:
    # Fetch teams data if not already in session state
    if st.session_state.teams_data is None:
        with st.spinner("Fetching teams from your league..."):
            teams_data = ESPNService.fetch_teams_data(st.session_state.league_id, cookies)
            if teams_data and 'teams' in teams_data:
                st.session_state.teams_data = teams_data
                logger.info(f"Successfully fetched {len(teams_data['teams'])} teams")
            else:
                st.error("Failed to fetch teams. Please check your League ID and try again.")
                logger.error("Failed to fetch teams data")
    
    # If teams data is available, show team selection
    if st.session_state.teams_data and 'teams' in st.session_state.teams_data:
        st.markdown("---")
        st.markdown("## Select Your Team")
        st.markdown("Choose your team from the list below. This will personalize analysis for your team.")
        
        # Create a list of teams for the selectbox
        teams = st.session_state.teams_data['teams']
        team_options = [(team['id'], f"{team['abbrev']}") for team in teams]
        
        # Add a "None" option
        team_options.insert(0, (None, "-- Select Your Team --"))
        
        # Get the current selection or default to None
        current_selection_index = 0
        if st.session_state.my_team_id is not None:
            for i, (team_id, _) in enumerate(team_options):
                if team_id == st.session_state.my_team_id:
                    current_selection_index = i
                    break
        
        # Create the selectbox
        selected_option = st.selectbox(
            "Your Team",
            options=range(len(team_options)),
            format_func=lambda i: team_options[i][1],
            index=current_selection_index
        )
        
        selected_team_id, selected_team_name = team_options[selected_option]
        
        # Save button for team selection
        if st.button("Save Team Selection"):
            if selected_team_id is not None:
                st.session_state.my_team_id = selected_team_id
                st.session_state.my_team_name = selected_team_name
                st.success(f"Your team set to: {selected_team_name}")
                logger.info(f"User set their team to: {selected_team_name} (ID: {selected_team_id})")
            else:
                st.session_state.my_team_id = None
                st.session_state.my_team_name = None
                st.info("No team selected")
                logger.info("User cleared team selection")

# Show instructions after setup is complete
if st.session_state.league_id:
    st.markdown("---")
    st.markdown("""
    ## Next Steps
    
    Your league settings have been saved. You can now use the sidebar to navigate to different analysis tools:
    
    - **Player Search**: Search for and analyze individual players
    - **Trade Evaluator**: Compare players and evaluate potential trades
    - **Waiver Wire Analyzer**: Find valuable players on the waiver wire
    - **Pitcher Streaming**: Analyze pitcher matchups and find streaming opportunities
    
    Each tool will use your configured league ID and team automatically.
    """)
    
    # Show current settings in the sidebar
    st.sidebar.header("Current Settings")
    st.sidebar.write(f"**League ID:** {st.session_state.league_id}")
    if st.session_state.my_team_name:
        st.sidebar.write(f"**Your Team:** {st.session_state.my_team_name.split(' (')[0]}")
    else:
        st.sidebar.write("**Your Team:** Not selected")

# Add version info
st.sidebar.markdown("---")
st.sidebar.info("Fantasy Baseball Analysis v1.1.0")
