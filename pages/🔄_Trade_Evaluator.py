"""
Trade Evaluator Page.

This page helps users evaluate potential fantasy baseball trades.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

# Import from our modules
from utils.logging_utils import setup_logging
from utils.data_processing import convert_positions, process_team_rosters, process_fangraphs_data
from utils.name_utils import stem_name
from services.espn_service import ESPNService
from services.fangraphs_service import FanGraphsService
from config.settings import DEFAULT_LEAGUE_ID

# Setup logging
logger = setup_logging()

# Set page config
st.set_page_config(
    page_title="Trade Evaluator",
    page_icon="🔄",
    layout="wide"
)

# --- Page Header ---
st.title("🔄 Trade Evaluator")
st.markdown("""
Use this tool to evaluate potential trades in your fantasy baseball league. 
Compare player values, projections, and see who comes out ahead in the deal.
""")

# --- Sidebar ---
st.sidebar.header("Trade Settings")
league_id = st.sidebar.text_input("League ID", value=DEFAULT_LEAGUE_ID)

# Initialize session state for selected players if it doesn't exist
if 'selected_players_team1' not in st.session_state:
    st.session_state.selected_players_team1 = []
if 'selected_players_team2' not in st.session_state:
    st.session_state.selected_players_team2 = []

# --- Data Loading Functions ---
@st.cache_data(ttl=3600)
def load_player_data(league_id: str):
    """Load player data from FanGraphs and ESPN."""
    with st.spinner("Loading player data..."):
        # Get batter projections
        batter_data = FanGraphsService.fetch_projections('batter', for_streamer_analysis=False)
        batter_df = process_fangraphs_data(batter_data, 'batter')
        
        # Get pitcher projections
        pitcher_data = FanGraphsService.fetch_projections('pitcher')
        pitcher_df = process_fangraphs_data(pitcher_data, 'pitcher')
        
        # Get ESPN player data
        espn_data = ESPNService.fetch_player_data()
        
        # Process roster data using the same approach as Waiver Wire Analyzer
        rostered_players = {}
        espn_df = None
        
        if espn_data:
            # Create DataFrame from ESPN data
            espn_df = pd.DataFrame(espn_data)
            logger.info(f"Created ESPN dataframe with {len(espn_df)} rows")
            
            # Add stemmed names to ESPN data for matching
            if 'fullName' in espn_df.columns:
                espn_df['stemmed_name'] = espn_df['fullName'].apply(stem_name)
                
                # Get teams and rosters
                teams_data = ESPNService.fetch_teams_data(league_id)
                roster_data = ESPNService.fetch_team_rosters(league_id)
                
                if teams_data and roster_data:
                    team_rosters, player_team_map = process_team_rosters(roster_data, teams_data, espn_df)
                    
                    if team_rosters:
                        # Create a mapping of stemmed names to team info
                        for team_id, team_data in team_rosters.items():
                            for player in team_data['players']:
                                player_name = player['name']
                                stemmed_name = stem_name(player_name)
                                
                                # Store positions for roster optimization later
                                positions = player.get('positions', '')
                                
                                rostered_players[stemmed_name] = {
                                    'team_id': team_id,
                                    'team_name': team_data['abbrev'],  # Use abbreviation instead of name
                                    'team_abbrev': team_data['abbrev'],
                                    'positions': positions  # Store positions for roster optimization
                                }
        
        # Create a combined player database with position eligibility
        combined_players = []
        
        # Process batters
        for _, batter in batter_df.iterrows():
            player_info = {
                'Name': batter['Name'],
                'StemmedName': batter['StemmedName'],
                'Team': batter['Team'],  # MLB team
                'Pos': batter['Pos'],
                'ProjPts': batter['ProjPts'],
                'PlayerType': 'Batter',
                'Team Owner': rostered_players.get(batter['StemmedName'], {}).get('team_name', None),
                'Positions': rostered_players.get(batter['StemmedName'], {}).get('positions', '')
            }
            combined_players.append(player_info)
        
        # Process pitchers
        for _, pitcher in pitcher_df.iterrows():
            player_info = {
                'Name': pitcher['Name'],
                'StemmedName': pitcher['StemmedName'],
                'Team': pitcher['Team'],  # MLB team
                'Pos': pitcher['Pos'],
                'ProjPts': pitcher['ProjPts'],
                'PlayerType': 'Pitcher',
                'Team Owner': rostered_players.get(pitcher['StemmedName'], {}).get('team_name', None),
                'Positions': rostered_players.get(pitcher['StemmedName'], {}).get('positions', '')
            }
            combined_players.append(player_info)
        
        # Create DataFrames
        combined_df = pd.DataFrame(combined_players)
        
        # Get unique team names for the trade team selection
        team_names = sorted(combined_df['Team Owner'].dropna().unique())
        
        return {
            'combined': combined_df,
            'espn_df': espn_df,
            'team_names': team_names
        }

# --- Load Data ---
try:
    data = load_player_data(league_id)
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.exception(e)
    data = {
        'combined': pd.DataFrame(),
        'espn_df': None,
        'team_names': []
    }

# --- Trade Setup ---
st.header("Trade Setup")
col1, col2 = st.columns(2)

with col1:
    team1 = st.selectbox("Team 1:", options=data['team_names'], index=0 if data['team_names'] else None, key="team1")

with col2:
    team2 = st.selectbox("Team 2:", options=data['team_names'], index=min(1, len(data['team_names'])-1) if len(data['team_names']) > 1 else None, key="team2")

# --- Display Player Data ---
st.header("Player Selection")

# Split into two columns for team selection
team1_col, team2_col = st.columns(2)

with team1_col:
    st.subheader(f"{team1} Players")
    
    # Filter players for team1
    team1_players = data['combined'][data['combined']['Team Owner'] == team1].copy()
    
    # Add selection column
    team1_players['Selected'] = team1_players['Name'].apply(
        lambda x: x in st.session_state.selected_players_team1
    )
    
    # Sort by PlayerType, then ProjPts (descending)
    team1_players = team1_players.sort_values(
        by=['PlayerType', 'ProjPts'], 
        ascending=[True, False]
    )
    
    # Display team1 player data with selection checkboxes
    if not team1_players.empty:
        # Use data editor for team1
        edited_team1 = st.data_editor(
            team1_players[['Selected', 'Name', 'Pos', 'ProjPts']],
            column_config={
                "Selected": st.column_config.CheckboxColumn("Select", help="Select player for trade"),
                "Name": st.column_config.TextColumn("Player Name"),
                "Pos": st.column_config.TextColumn("Position"),
                "ProjPts": st.column_config.NumberColumn("Projected Points", format="%.1f")
            },
            hide_index=True,
            use_container_width=True,
            key="team1_editor"
        )
        
        # Update team1 selections
        team1_selections = []
        for _, row in edited_team1.iterrows():
            if row['Selected']:
                team1_selections.append(row['Name'])
        
        st.session_state.selected_players_team1 = team1_selections
    else:
        st.warning(f"No player data available for {team1}")

with team2_col:
    st.subheader(f"{team2} Players")
    
    # Filter players for team2
    team2_players = data['combined'][data['combined']['Team Owner'] == team2].copy()
    
    # Add selection column
    team2_players['Selected'] = team2_players['Name'].apply(
        lambda x: x in st.session_state.selected_players_team2
    )
    
    # Sort by PlayerType, then ProjPts (descending)
    team2_players = team2_players.sort_values(
        by=['PlayerType', 'ProjPts'], 
        ascending=[True, False]
    )
    
    # Display team2 player data with selection checkboxes
    if not team2_players.empty:
        # Use data editor for team2
        edited_team2 = st.data_editor(
            team2_players[['Selected', 'Name', 'Pos', 'ProjPts']],
            column_config={
                "Selected": st.column_config.CheckboxColumn("Select", help="Select player for trade"),
                "Name": st.column_config.TextColumn("Player Name"),
                "Pos": st.column_config.TextColumn("Position"),
                "ProjPts": st.column_config.NumberColumn("Projected Points", format="%.1f")
            },
            hide_index=True,
            use_container_width=True,
            key="team2_editor"
        )
        
        # Update team2 selections
        team2_selections = []
        for _, row in edited_team2.iterrows():
            if row['Selected']:
                team2_selections.append(row['Name'])
        
        st.session_state.selected_players_team2 = team2_selections
    else:
        st.warning(f"No player data available for {team2}")

# --- Trade Evaluation ---
st.header("Trade Evaluation")

# Display selected players for each team
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"{team1} Gives:")
    if st.session_state.selected_players_team1:
        # Get data for selected players
        team1_players = data['combined'][data['combined']['Name'].isin(st.session_state.selected_players_team1)]
        st.dataframe(
            team1_players[['Name', 'Pos', 'ProjPts']],
            hide_index=True,
            use_container_width=True
        )
        team1_total = team1_players['ProjPts'].sum()
        st.metric("Total Points", f"{team1_total:.1f}")
    else:
        st.info("No players selected")

with col2:
    st.subheader(f"{team2} Gives:")
    if st.session_state.selected_players_team2:
        # Get data for selected players
        team2_players = data['combined'][data['combined']['Name'].isin(st.session_state.selected_players_team2)]
        st.dataframe(
            team2_players[['Name', 'Pos', 'ProjPts']],
            hide_index=True,
            use_container_width=True
        )
        team2_total = team2_players['ProjPts'].sum()
        st.metric("Total Points", f"{team2_total:.1f}")
    else:
        st.info("No players selected")

# Show trade analysis if players are selected for both teams
if st.session_state.selected_players_team1 and st.session_state.selected_players_team2:
    st.subheader("Trade Analysis")
    
    # Calculate point difference
    point_diff = team1_total - team2_total
    
    if abs(point_diff) < 5:
        st.success("This trade appears to be fair based on projected points.")
    elif point_diff > 0:
        st.warning(f"{team2} is giving up {abs(point_diff):.1f} more projected points in this trade.")
    else:
        st.warning(f"{team1} is giving up {abs(point_diff):.1f} more projected points in this trade.")
    
    # Add a button to clear selections
    if st.button("Clear Selections"):
        st.session_state.selected_players_team1 = []
        st.session_state.selected_players_team2 = []
        st.rerun()
else:
    st.info("Select players from both teams to evaluate the trade.")
