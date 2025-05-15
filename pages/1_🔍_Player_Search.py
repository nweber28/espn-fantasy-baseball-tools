"""
Player Search Page.

This page allows users to search for and analyze individual players.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

# Import from our modules
from utils.logging_utils import setup_logging
from utils.data_processing import convert_positions, process_team_rosters, process_fangraphs_data
from utils.name_utils import stem_name
from services.espn_service import ESPNService
from services.fangraphs_service import FanGraphsService
from config.settings import DEFAULT_LEAGUE_ID, cookies

# Setup logging
logger = setup_logging()

# Set page config
st.set_page_config(
    page_title="Player Search",
    page_icon="🔍",
    layout="wide"
)

# Title
st.title("🔍 Player Search")

# Get league ID and team from session state or use defaults
if 'league_id' in st.session_state:
    league_id = st.session_state.league_id
else:
    league_id = DEFAULT_LEAGUE_ID

my_team_id = st.session_state.get('my_team_id')
my_team_name = st.session_state.get('my_team_name')

# Show current settings in the sidebar
with st.sidebar:
    st.header("Current Settings")
    st.write(f"**League ID:** {league_id}")
    if my_team_name:
        st.write(f"**Your Team:** {my_team_name.split(' (')[0]}")
    else:
        st.write("**Your Team:** Not selected")
    
    st.header("Debug Options")
    show_debug = st.checkbox("Show Debug Info", value=False, help="Show debug information in the UI")

# Function to load player data
@st.cache_data(ttl=3600)
def load_player_data(cookies: dict):
    """Load and process player data from ESPN and FanGraphs."""
    with st.spinner("Loading player data..."):
        # Fetch data from ESPN
        espn_data = ESPNService.fetch_player_data(cookies)
        
        # Fetch projections from FanGraphs
        fg_batters_data = FanGraphsService.fetch_projections('batter')
        fg_pitchers_data = FanGraphsService.fetch_projections('pitcher')
        
        if not espn_data:
            st.error("Failed to fetch ESPN player data.")
            return None
            
        # Process ESPN data
        espn_df = pd.DataFrame(espn_data)
        logger.info(f"Created ESPN dataframe with {len(espn_df)} rows and {len(espn_df.columns)} columns")

        # Extract percentOwned from the ownership dictionary
        espn_df['percent_owned'] = espn_df['ownership'].apply(lambda x: x.get('percentOwned', 0) if isinstance(x, dict) else 0)
        espn_df = espn_df.drop('ownership', axis=1)
        
        # Add stemmed names to ESPN data for matching
        espn_df['stemmed_name'] = espn_df['fullName'].apply(stem_name)
        
        # Process FanGraphs data
        fg_pitchers_df = process_fangraphs_data(fg_pitchers_data, 'pitcher')
        fg_batters_df = process_fangraphs_data(fg_batters_data, 'batter')
        
        # Combine all FanGraphs data
        fg_combined_df = pd.concat([fg_pitchers_df, fg_batters_df], ignore_index=True)
        logger.info(f"Combined FanGraphs data: {len(fg_combined_df)} players")
        
        # Create a mapping from stemmed name to projection points
        proj_pts_map = dict(zip(fg_combined_df['StemmedName'], fg_combined_df['ProjPts']))
        logger.info(f"Created projection points mapping for {len(proj_pts_map)} players")
        
        # Add projection points to ESPN data
        espn_df['projPts'] = espn_df['stemmed_name'].map(proj_pts_map)
        
        # Fetch team roster data if league ID is provided
        team_rosters = {}
        player_team_map = {}
        teams_data = None
        
        if league_id:
            with st.spinner("Fetching team rosters..."):
                # Log the league ID
                logger.info(f"Fetching rosters for league ID: {league_id}")
                
                # First fetch the teams data
                teams_data = ESPNService.fetch_teams_data(league_id, cookies)
                if not teams_data:
                    st.warning("Failed to fetch teams data. Check your league ID and try again.")
                    logger.error("Failed to fetch teams data")
                else:
                    logger.info(f"Successfully fetched teams data with {len(teams_data.get('teams', []))} teams")
                    
                    # Then fetch the team rosters
                    roster_data = ESPNService.fetch_team_rosters(league_id, cookies)
                    
                    if roster_data:
                        team_rosters, player_team_map = process_team_rosters(roster_data, teams_data, espn_df)
                        
                        if team_rosters:
                            logger.info(f"Successfully processed {len(team_rosters)} teams with {len(player_team_map)} players")
                        else:
                            st.warning("Failed to process team rosters. Check your league ID and try again.")
                            logger.error("Failed to process team rosters")
                    else:
                        st.warning("Failed to fetch team rosters. Check your league ID and try again.")
                        logger.error("Failed to fetch team rosters")
        
        # Add team information to ESPN data
        espn_df['team_id'] = espn_df['id'].map(lambda x: player_team_map.get(x, {}).get('team_id', None))
        espn_df['team_name'] = espn_df['id'].map(lambda x: player_team_map.get(x, {}).get('team_abbrev', None))

        # Create simplified DataFrame with only the essential columns
        simplified_df = pd.DataFrame({
            'Name': espn_df['fullName'],
            'ID': espn_df['id'],
            'Percent Owned': espn_df['percent_owned'],
            'Eligible Positions': espn_df['eligibleSlots'].apply(convert_positions),
            'Projected Points': espn_df['projPts'].apply(lambda x: float(x) if pd.notnull(x) else None),
            'Team': espn_df['team_name'],
            'MLB Team': espn_df['proTeamId'],
            'Injury Status': espn_df['injuryStatus']
        })
        
        # Calculate percentage of players with matched projections
        matched_players = simplified_df['Projected Points'].notna().sum()
        total_players = len(simplified_df)
        match_percentage = (matched_players / total_players) * 100 if total_players > 0 else 0
        logger.info(f"Matched projections for {matched_players}/{total_players} players ({match_percentage:.1f}%)")
        
        return simplified_df

# Load player data
player_df = load_player_data(cookies)

if player_df is not None:
    # Add search functionality
    st.header("Search Players")
    
    # Create search filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_name = st.text_input("Player Name", "")
    
    with col2:
        position_options = ["All"] + sorted(list({pos for positions in player_df['Eligible Positions'].dropna() 
                                               for pos in positions.split(', ')}))
        search_position = st.selectbox("Position", position_options)
    
    with col3:
        team_options = ["All"] + sorted(player_df['Team'].dropna().unique().tolist())
        search_team = st.selectbox("Team", team_options)
        
    with col4:
        min_ownership = st.slider("Min. Ownership %", min_value=0.0, max_value=100.0, value=5.0, step=5.0)
    
    # Filter the data based on search criteria
    filtered_df = player_df.copy()
    
    # Filter out players with less than the specified ownership percentage
    filtered_df = filtered_df[filtered_df['Percent Owned'] >= min_ownership]
    
    if search_name:
        filtered_df = filtered_df[filtered_df['Name'].str.contains(search_name, case=False)]
    
    if search_position != "All":
        filtered_df = filtered_df[filtered_df['Eligible Positions'].str.contains(search_position, case=False)]
    
    if search_team != "All":
        filtered_df = filtered_df[filtered_df['Team'] == search_team]

    # Display the filtered data
    st.dataframe(
        filtered_df,
        use_container_width=True,
        column_config={
            "Name": st.column_config.TextColumn("Player Name"),
            "Eligible Positions": st.column_config.TextColumn("Positions"),
            "Projected Points": st.column_config.NumberColumn("Proj. Points", format="%.1f"),
            "Percent Owned": st.column_config.NumberColumn("% Owned", format="%.2f"),
            "Team": st.column_config.TextColumn("Fantasy Team"),
            "MLB Team": st.column_config.TextColumn("MLB Team"),
            "Injury Status": st.column_config.TextColumn("Status")
        }
    )
    
    # Show number of results
    st.write(f"Found {len(filtered_df)} players matching your search criteria (minimum {min_ownership}% ownership).")
    
    # Show debug info if enabled
    if show_debug:
        st.header("🐞 Debug Information")
        st.write(f"Total Players: {len(player_df)}")
        st.write(f"Players with Projections: {player_df['Projected Points'].notna().sum()}")
        st.write(f"Players on Teams: {player_df['Team'].notna().sum()}")
else:
    st.error("Failed to load player data. Please try again later.")
