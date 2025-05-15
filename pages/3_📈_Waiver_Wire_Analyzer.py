"""
Waiver Wire Analyzer Page.

This page helps users identify valuable players available on the waiver wire.
"""
import streamlit as st
import pandas as pd
import numpy as np
import json
import concurrent.futures
from typing import Dict, Any, List, Optional, Tuple
from config.settings import cookies

# Import from our modules
from utils.logging_utils import setup_logging
from utils.data_processing import convert_positions, process_team_rosters, process_fangraphs_data, cached_stem_name
from utils.name_utils import stem_name
from utils.roster_utils import optimize_roster, optimize_dataframe_memory
from utils.waiver_utils import find_waiver_replacements
from services.espn_service import ESPNService
from services.fangraphs_service import FanGraphsService
from config.settings import DEFAULT_LEAGUE_ID, DEFAULT_ROSTER_SLOTS

# Setup logging
logger = setup_logging()

# No need to initialize service instances as we're using static methods

# Set page config
st.set_page_config(
    page_title="Waiver Wire Analyzer",
    page_icon="📈",
    layout="wide"
)

# Title
st.title("📈 Waiver Wire Analyzer")

# Get league ID and team from session state or use defaults
if 'league_id' in st.session_state:
    league_id = st.session_state.league_id
else:
    league_id = DEFAULT_LEAGUE_ID

my_team_id = st.session_state.get('my_team_id')
my_team_name = st.session_state.get('my_team_name')

# Show current settings and add debug toggle in sidebar
with st.sidebar:
    st.header("Current Settings")
    st.write(f"**League ID:** {league_id}")
    if my_team_name:
        st.write(f"**Your Team:** {my_team_name.split(' (')[0]}")
    else:
        st.write("**Your Team:** Not selected")
    st.header("Debug Options")
    show_debug = st.checkbox("Show Debug Info", value=False, help="Show debug information in the UI")

# Fetch all data
with st.spinner("Fetching player data..."):
    # Use ThreadPoolExecutor to fetch data in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Start all fetch operations concurrently
        espn_future = executor.submit(ESPNService.fetch_player_data, cookies)
        fg_batters_future = executor.submit(FanGraphsService.fetch_projections, 'batter')
        fg_pitchers_future = executor.submit(FanGraphsService.fetch_projections, 'pitcher')
        
        # Get results as they complete
        espn_data = espn_future.result()
        fg_batters_data = fg_batters_future.result()
        fg_pitchers_data = fg_pitchers_future.result()

if espn_data:
    # Process ESPN data
    espn_df = pd.DataFrame(espn_data)
    logger.info(f"Created ESPN dataframe with {len(espn_df)} rows and {len(espn_df.columns)} columns")
    
    # Extract percentOwned from the ownership dictionary using vectorized operations
    if 'ownership' in espn_df.columns:
        # Create a function to safely extract percentOwned
        def extract_percent_owned(ownership):
            if isinstance(ownership, dict):
                return ownership.get('percentOwned', 0)
            return 0
        
        # Apply the function to the entire column at once
        espn_df['percent_owned'] = espn_df['ownership'].apply(extract_percent_owned)
        espn_df = espn_df.drop('ownership', axis=1)
    
    # Add stemmed names to ESPN data for matching using cached version
    espn_df['stemmed_name'] = espn_df['fullName'].apply(cached_stem_name)
    
    # Process FanGraphs data using vectorized operations
    fg_pitchers_df = process_fangraphs_data(fg_pitchers_data, 'pitcher')
    fg_batters_df = process_fangraphs_data(fg_batters_data, 'batter')
    
    # Combine all FanGraphs data with pitcher priority
    fg_combined_df = pd.concat([fg_pitchers_df, fg_batters_df], ignore_index=True)
    logger.info(f"Combined FanGraphs data: {len(fg_combined_df)} players")
    
    # Create a mapping from stemmed name to projection points using vectorized operations
    proj_pts_map = dict(zip(fg_combined_df['StemmedName'], fg_combined_df['ProjPts']))
    logger.info(f"Created projection points mapping for {len(proj_pts_map)} players")
    
    # Add projection points to ESPN data using vectorized mapping
    espn_df['projPts'] = espn_df['stemmed_name'].map(proj_pts_map)
    
    # Optimize memory usage - but only for columns that are safe
    try:
        espn_df = optimize_dataframe_memory(espn_df)
    except Exception as e:
        logger.warning(f"Error optimizing dataframe memory: {e}")
        # Continue without optimization if it fails
    
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
                st.error("Failed to fetch teams data. Check your league ID and try again.")
                logger.error("Failed to fetch teams data")
            else:
                logger.info(f"Successfully fetched teams data with {len(teams_data.get('teams', []))} teams")
                
                # Then fetch the team rosters
                roster_data = ESPNService.fetch_team_rosters(league_id, cookies)
                
                if roster_data:
                    # Log some info about the roster data for debugging
                    if 'teams' in roster_data:
                        logger.info(f"Roster data contains {len(roster_data['teams'])} teams")
                    else:
                        logger.warning(f"Roster data doesn't contain 'teams' key. Keys: {list(roster_data.keys())}")
                        # Show a sample of the response
                        sample_data = json.dumps(roster_data, indent=2)[:500] + "..."
                        logger.info(f"Sample roster data: {sample_data}")
                    
                    team_rosters, player_team_map = process_team_rosters(roster_data, teams_data, espn_df)
                    
                    if team_rosters:
                        logger.info(f"Successfully processed {len(team_rosters)} teams with {len(player_team_map)} players")
                    else:
                        st.error("Failed to process team rosters. Check your league ID and try again.")
                        logger.error("Failed to process team rosters")
                else:
                    st.error("Failed to fetch team rosters. Check your league ID and try again.")
                    logger.error("Failed to fetch team rosters")
    
    # Add team information to ESPN data
    espn_df['team_id'] = espn_df['id'].map(lambda x: player_team_map.get(x, {}).get('team_id', None))
    espn_df['team_name'] = espn_df['id'].map(lambda x: player_team_map.get(x, {}).get('team_abbrev', None))
    
    # Log team mapping results
    mapped_players = espn_df[espn_df['team_name'].notnull()].shape[0]
    logger.info(f"Mapped {mapped_players} players to teams out of {len(espn_df)} total players")
    
    # Filter out players with ownership less than 0.05%
    filtered_espn_df = espn_df[espn_df['percent_owned'] >= 0.05]
    logger.info(f"Filtered to {len(filtered_espn_df)} players with at least 0.05% ownership")
    
    # Calculate percentage of players with matched projections
    matched_players = filtered_espn_df['projPts'].notna().sum()
    total_players = len(filtered_espn_df)
    match_percentage = (matched_players / total_players) * 100 if total_players > 0 else 0
    logger.info(f"Matched projections for {matched_players}/{total_players} players ({match_percentage:.1f}%)")
    
    # Create simplified DataFrame with only the essential columns
    simplified_df = pd.DataFrame({
        'Name': filtered_espn_df['fullName'],
        'Percent Owned': filtered_espn_df['percent_owned'],
        'Eligible Positions': filtered_espn_df['eligibleSlots'].apply(convert_positions),
        'Projected Points': filtered_espn_df['projPts'].apply(lambda x: float(x) if pd.notnull(x) else None),
        'Team': filtered_espn_df['team_name'],
        'Injury Status': filtered_espn_df.get('injuryStatus')
    })
    
    # Sort by Projected Points (descending)
    simplified_df = simplified_df.sort_values('Projected Points', ascending=False, na_position='last').reset_index(drop=True)
    logger.info(f"Final dataframe has {len(simplified_df)} rows")
    
    # Get all available team abbreviations
    available_teams = sorted([team for team in simplified_df['Team'].dropna().unique() if isinstance(team, str) and team.strip()])
    
    # Optimized Roster section
    if available_teams:
        st.header("🧙‍♂️ Optimized Roster")
        
        # Team abbreviation filter
        selected_team = st.selectbox(
            "Select Team:", 
            options=available_teams,
            index=0 if available_teams else None,
            help="View optimized roster for selected team"
        )
        
        # Filter for selected team
        if selected_team:
            team_roster = simplified_df[simplified_df['Team'] == selected_team].copy()
            
            if not team_roster.empty:
                # Process the team roster to extract position eligibility
                processed_roster = []
                for _, player in team_roster.iterrows():
                    # Split the positions string into a list
                    positions = [pos.strip() for pos in player['Eligible Positions'].split(',') if pos.strip()]
                    
                    # Determine player type (hitter or pitcher)
                    is_pitcher = any(pos in ["SP", "RP", "P"] for pos in positions)
                    is_hitter = any(pos in ["C", "1B", "2B", "3B", "SS", "OF", "DH"] for pos in positions)
                    
                    processed_roster.append({
                        'name': player['Name'],
                        'positions': positions,
                        'projected_points': player['Projected Points'] if not pd.isna(player['Projected Points']) else 0,
                        'is_pitcher': is_pitcher,
                        'is_hitter': is_hitter,
                        'injury_status': player['Injury Status']
                    })
                
                # Run the optimization
                with st.spinner("Optimizing roster..."):
                    optimized_roster, _ = optimize_roster(processed_roster, DEFAULT_ROSTER_SLOTS)
                
                # Display the optimized roster
                st.write("### Optimized Starting Lineup")
                
                # Display IL players first if any
                if "IL" in optimized_roster and optimized_roster["IL"]:
                    il_slots = []
                    for player in optimized_roster["IL"]:
                        il_slots.append({
                            "Position": "IL",
                            "Name": player["name"],
                            "Eligible Positions": ", ".join(player["positions"]),
                            "Projected Points": player["projected_points"],
                            "Injury Status": player.get("injury_status")
                        })
                    
                    il_df = pd.DataFrame(il_slots)
                    st.write("#### Injured List")
                    st.dataframe(
                        il_df,
                        use_container_width=True,
                        column_config={
                            "Position": st.column_config.TextColumn("Pos"),
                            "Name": st.column_config.TextColumn("Player Name"),
                            "Eligible Positions": st.column_config.TextColumn("Eligible At"),
                            "Projected Points": st.column_config.NumberColumn("Proj. Points", format="%.1f"),
                            "Injury Status": st.column_config.TextColumn("Status")
                        }
                    )
                
                st.write("#### Starting Lineup")
                
                # Display starters by position
                starting_slots = []
                for position, count in DEFAULT_ROSTER_SLOTS.items():
                    players_at_position = optimized_roster[position]
                    for i in range(min(count, len(players_at_position))):
                        player = players_at_position[i]
                        # For pitchers, show their actual position (SP or RP) if available
                        display_position = position
                        if position == "P" and ("SP" in player["positions"] or "RP" in player["positions"]):
                            if "SP" in player["positions"]:
                                display_position = "SP"
                            elif "RP" in player["positions"]:
                                display_position = "RP"
                        
                        starting_slots.append({
                            "Position": display_position,
                            "Name": player["name"],
                            "Eligible Positions": ", ".join(player["positions"]),
                            "Projected Points": player["projected_points"],
                            "Injury Status": player.get("injury_status")
                        })
                
                # Sort the starters by position order for display
                position_order = ["C", "1B", "2B", "3B", "SS", "OF", "UTIL", "SP", "RP", "P"]
                position_rank = {pos: i for i, pos in enumerate(position_order)}
                
                starting_slots_df = pd.DataFrame(starting_slots)
                # Handle cases where display_position might not be in position_rank
                starting_slots_df["PositionRank"] = starting_slots_df["Position"].apply(
                    lambda x: position_rank.get(x, position_rank.get("P", 9))
                )
                starting_slots_df = starting_slots_df.sort_values("PositionRank").drop("PositionRank", axis=1)
                
                # Display starters
                st.dataframe(
                    starting_slots_df,
                    use_container_width=True,
                    column_config={
                        "Position": st.column_config.TextColumn("Pos"),
                        "Name": st.column_config.TextColumn("Player Name"),
                        "Eligible Positions": st.column_config.TextColumn("Eligible At"),
                        "Projected Points": st.column_config.NumberColumn("Proj. Points", format="%.1f"),
                        "Injury Status": st.column_config.TextColumn("Status")
                    }
                )
                
                # Display bench players
                st.write("### Bench Players")
                bench_players = [{
                    "Name": player["name"],
                    "Eligible Positions": ", ".join(player["positions"]),
                    "Projected Points": player["projected_points"],
                    "Injury Status": player.get("injury_status")
                } for player in optimized_roster["BN"]]
                
                bench_df = pd.DataFrame(bench_players)
                
                if not bench_df.empty:
                    st.dataframe(
                        bench_df,
                        use_container_width=True,
                        column_config={
                            "Name": st.column_config.TextColumn("Player Name"),
                            "Eligible Positions": st.column_config.TextColumn("Eligible At"),
                            "Projected Points": st.column_config.NumberColumn("Proj. Points", format="%.1f"),
                            "Injury Status": st.column_config.TextColumn("Status")
                        }
                    )
                else:
                    st.info("No bench players available")
                
                # Calculate team statistics
                total_projected_points = sum(player["projected_points"] for position, players in optimized_roster.items() 
                                           if position != "BN" and position != "IL" for player in players)
                
                st.metric("Total Projected Points (Starting Lineup)", f"{total_projected_points:.1f}")
                
                # Free Agent Optimizer section
                st.write("### 🚀 Recommended Free Agent Pickups")
                
                # Get free agents
                free_agents = simplified_df[(simplified_df['Team'].isna()) | (simplified_df['Team'] == "")].copy()
                
                if not free_agents.empty:
                    with st.spinner("Analyzing free agent pool for possible improvements..."):
                        # Process free agents to match team roster format
                        processed_free_agents = []
                        for _, player in free_agents.iterrows():
                            # Split the positions string into a list
                            positions = [pos.strip() for pos in player['Eligible Positions'].split(',') if pos.strip()]
                            
                            # Determine player type (hitter or pitcher)
                            is_pitcher = any(pos in ["SP", "RP", "P"] for pos in positions)
                            is_hitter = any(pos in ["C", "1B", "2B", "3B", "SS", "OF", "DH"] for pos in positions)
                            
                            processed_free_agents.append({
                                'name': player['Name'],
                                'positions': positions,
                                'projected_points': player['Projected Points'] if not pd.isna(player['Projected Points']) else 0,
                                'is_pitcher': is_pitcher,
                                'is_hitter': is_hitter,
                                'percent_owned': player['Percent Owned'],
                                'injury_status': player['Injury Status']  # Add injury status
                            })
                        
                        # Combine team roster with free agents
                        combined_roster = processed_roster + processed_free_agents
                        
                        # Run optimization with combined roster
                        optimized_combined, _ = optimize_roster(combined_roster, DEFAULT_ROSTER_SLOTS)
                        
                        # Use the waiver_utils function to find recommended pickups
                        from utils.waiver_utils import find_waiver_replacements
                        recommended_pickups = find_waiver_replacements(
                            optimized_roster,
                            optimized_combined,
                            processed_roster,
                            processed_free_agents
                        )
                        
                        # Display recommendations
                        if recommended_pickups:
                            # Create DataFrame for display
                            recommendations_df = pd.DataFrame(recommended_pickups)
                            
                            # Add a plus sign to positive values for display
                            recommendations_df['Display Improvement'] = recommendations_df['Proj. Points Improvement'].apply(
                                lambda x: f"+{x:.1f}" if x > 0 else f"{x:.1f}"
                            )
                            
                            # Remove the original numeric column and keep only the display version
                            recommendations_df = recommendations_df.drop(columns=['Proj. Points Improvement'])
                            
                            st.dataframe(
                                recommendations_df,
                                use_container_width=True,
                                column_config={
                                    "Add": st.column_config.TextColumn("Add Player"),
                                    "Position": st.column_config.TextColumn("Position"),
                                    "Drop": st.column_config.TextColumn("Drop Player"),
                                    "Display Improvement": st.column_config.TextColumn("Pts Improvement"),
                                    "FA Percent Owned": st.column_config.NumberColumn("% Owned", format="%.2f"),
                                    "Injury Status": st.column_config.TextColumn("Status")
                                }
                            )
                        else:
                            st.info("No recommended free agent pickups found to improve your roster.")
                else:
                    st.info("No free agents available to analyze.")
            else:
                st.info(f"No players found for team {selected_team}")
        else:
            st.info("Please select a team to view the optimized roster")
    else:
        st.info("No teams available. Please enter a valid League ID.")
    
    # Free Agent Pool section
    st.header("🏄‍♂️ Free Agent Pool")
    free_agents_df = simplified_df[simplified_df['Team'].isna() | (simplified_df['Team'] == "")].copy()
    
    if not free_agents_df.empty:
        # Drop the Team column since it's not needed for free agents
        free_agents_df = free_agents_df.drop(columns=['Team'])
        
        st.dataframe(
            free_agents_df, 
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn("Name"),
                "Percent Owned": st.column_config.NumberColumn("% Owned", format="%.2f"),
                "Eligible Positions": st.column_config.TextColumn("Positions"),
                "Projected Points": st.column_config.NumberColumn("Proj. Points", format="%.1f"),
            }
        )
        st.write(f"*Showing {len(free_agents_df)} free agents with at least 0.05% ownership*")
    else:
        st.info("No free agents found. Check your league ID and make sure rosters are properly loaded.")
    
    # Display the debug info
    if show_debug:
        st.header("🐞 Debug Information")
        st.write(f"League ID: {league_id}")
        st.write(f"Total ESPN Players: {len(espn_df)}")
        st.write(f"FanGraphs Batters: {len(fg_batters_df)}")
        st.write(f"FanGraphs Pitchers: {len(fg_pitchers_df)}")
        st.write(f"Players Matched to Teams: {mapped_players}")
        st.write(f"Players with Projections: {matched_players}/{total_players} ({match_percentage:.1f}%)")
        
        if team_rosters:
            st.write(f"Teams Found: {len(team_rosters)}")
            for team_id, team_data in team_rosters.items():
                st.write(f"- {team_data['abbrev']}: {len(team_data['players'])} players")
else:
    st.error("Failed to fetch player data. Please try again later.")
