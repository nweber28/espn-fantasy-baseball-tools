import streamlit as st
import pandas as pd
import requests
from unidecode import unidecode
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Waiver Wire Analyzer",
    page_icon="📈",
    layout="wide"
)

# Title
st.title("📈 Waiver Wire Analyzer")

# Position ID to name mapping
POSITION_MAP = {
    0: "C",
    1: "1B",
    2: "2B",
    3: "3B",
    4: "SS",
    5: "OF",
    6: "MI",
    7: "CI",
    8: "LF",
    9: "CF",
    10: "RF",
    11: "DH",
    12: "UTIL",
    13: "P",
    14: "SP",
    15: "RP",
    16: "BN",
    17: "IL",
    18: "NA",
    19: "IF"
}

# Utility functions
def stem_name(name: str) -> str:
    """Standardize player name for matching."""
    # Special case mappings for players with name discrepancies
    mappings = {
        'ben-williamson': 'benjamin-williamson', 
        'zach-dezenzo': 'zachary-dezenzo',
        'cj-abrams': 'c.j.-abrams',
        'jt-realmuto': 'j.t.-realmuto',
        'aj-pollock': 'a.j.-pollock'
    }
    # Clean and standardize the name
    clean_name = unidecode(name.lower().replace('.', '').replace(' ', '-'))
    return mappings.get(clean_name, clean_name)

def convert_positions(positions_list):
    """Convert position IDs to position names, showing only key positions."""
    if not isinstance(positions_list, list):
        return ""
    
    # Define the positions we want to display
    display_positions = {"C", "1B", "2B", "3B", "SS", "OF", "SP", "RP", "DH"}
    
    # Map position IDs to their names and filter for display positions
    positions = []
    
    for pos in positions_list:
        pos_name = POSITION_MAP.get(pos, str(pos))
        
        # Convert all outfield positions (LF, CF, RF) to just "OF"
        if pos_name in ["LF", "CF", "RF"]:
            pos_name = "OF"
            
        # Only include the position if it's in our display set
        if pos_name in display_positions and pos_name not in positions:
            positions.append(pos_name)
    
    return ", ".join(positions)

# Function to fetch player data from ESPN
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_espn_player_data():
    url = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/2025/players?scoringPeriodId=0&view=players_wl"
    
    headers = {
        "X-Fantasy-Filter": '{"filterActive":{"value":true}}',
        "sec-ch-ua-platform": "macOS",
        "Referer": "https://fantasy.espn.com/",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "X-Fantasy-Platform": "kona-PROD-ea1dac81fac83846270c371702992d3a2f69aa70",
        "sec-ch-ua-mobile": "?0",
        "X-Fantasy-Source": "kona",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        logger.info("Fetching ESPN player data")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched ESPN player data: {len(data)} players")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching ESPN data: {e}")
        st.error(f"Error fetching ESPN data: {e}")
        return None

# Function to fetch ESPN league teams data
@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def fetch_espn_teams_data(league_id, season_id=2025):
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/{season_id}/segments/0/leagues/{league_id}"
    
    headers = {
        "sec-ch-ua-platform": "macOS",
        "Referer": "https://fantasy.espn.com/",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "X-Fantasy-Platform": "kona-PROD-ea1dac81fac83846270c371702992d3a2f69aa70",
        "sec-ch-ua-mobile": "?0",
        "X-Fantasy-Source": "kona",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        logger.info(f"Fetching ESPN teams data for league {league_id}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched ESPN teams data: {len(data.get('teams', []))} teams")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching ESPN teams data: {e}")
        st.error(f"Error fetching ESPN teams data: {e}")
        return None

# Function to fetch ESPN league team rosters
@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def fetch_espn_team_rosters(league_id, season_id=2025):
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/{season_id}/segments/0/leagues/{league_id}?view=mRoster"
    
    headers = {
        "sec-ch-ua-platform": "macOS",
        "Referer": "https://fantasy.espn.com/",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "X-Fantasy-Platform": "kona-PROD-ea1dac81fac83846270c371702992d3a2f69aa70",
        "sec-ch-ua-mobile": "?0",
        "X-Fantasy-Source": "kona",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        logger.info(f"Fetching ESPN team rosters for league {league_id}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Debug logs for response structure
        if 'teams' in data:
            logger.info(f"Successfully fetched roster data with {len(data['teams'])} teams")
            for i, team in enumerate(data['teams']):
                roster_entries = team.get('roster', {}).get('entries', [])
                logger.info(f"Team {i+1}: {team.get('name')} - {len(roster_entries)} players")
        else:
            logger.warning(f"Roster data missing 'teams' key. Keys: {list(data.keys())}")
            
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching ESPN team rosters: {e}")
        st.error(f"Error fetching ESPN team rosters: {e}")
        return None

# Function to fetch FanGraphs batter projections
@st.cache_data(ttl=3600)
def fetch_fangraphs_batters():
    url = "https://www.fangraphs.com/api/fantasy/auction-calculator/data?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=bat&players=&proj=rthebatx&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0"
    
    headers = {
        "sec-ch-ua-platform": "macOS",
        "Referer": "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=bat&players=&proj=rthebatx&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0"
    }
    
    try:
        logger.info("Fetching FanGraphs batter data")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if 'data' in data:
            logger.info(f"Successfully fetched FanGraphs batter data: {len(data['data'])} batters")
        else:
            logger.warning("FanGraphs batter data missing 'data' key")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching FanGraphs batter data: {e}")
        st.error(f"Error fetching FanGraphs batter data: {e}")
        return None

# Function to fetch FanGraphs pitcher projections
@st.cache_data(ttl=3600)
def fetch_fangraphs_pitchers():
    url = "https://www.fangraphs.com/api/fantasy/auction-calculator/data?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=pit&players=&proj=ratcdc&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0"
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "sec-ch-ua-platform": "macOS",
        "referer": "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=pit&players=&proj=rthebatx&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }
    
    try:
        logger.info("Fetching FanGraphs pitcher data")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if 'data' in data:
            logger.info(f"Successfully fetched FanGraphs pitcher data: {len(data['data'])} pitchers")
        else:
            logger.warning("FanGraphs pitcher data missing 'data' key")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching FanGraphs pitcher data: {e}")
        st.error(f"Error fetching FanGraphs pitcher data: {e}")
        return None

# Process FanGraphs data into a standardized format
def process_fangraphs_data(data, player_type):
    if not data or 'data' not in data:
        logger.warning(f"No valid data for {player_type}s processing")
        return pd.DataFrame()
        
    records = []
    for player in data.get('data', []):
        name = player.get("PlayerName", "")
        if not name:
            continue
            
        stemmed_name = stem_name(name)
        
        # Safely get projection points
        try:
            proj_pts = float(player.get("rPTS", 0))
        except (ValueError, TypeError):
            logger.warning(f"Invalid projection points for {name}: {player.get('rPTS')}")
            proj_pts = 0.0
        
        record = {
            "Name": name,
            "StemmedName": stemmed_name,
            "Team": player.get("Team", ""),
            "Pos": player.get("POS", ""),
            "ProjPts": proj_pts,
            "PlayerType": player_type
        }
        records.append(record)
    
    logger.info(f"Processed {len(records)} {player_type} records")    
    return pd.DataFrame(records)

# Process team roster data
def process_team_rosters(roster_data, teams_data, espn_df):
    if not roster_data or 'teams' not in roster_data:
        logger.warning("Invalid roster data structure")
        return {}, {}
    
    # Create a map of team ID to abbreviation
    team_abbrev_map = {}
    if teams_data and 'teams' in teams_data:
        for team in teams_data.get('teams', []):
            team_id = team.get('id')
            abbrev = team.get('abbrev', f'Team {team_id}')
            team_abbrev_map[team_id] = abbrev
            logger.info(f"Found team abbreviation: {abbrev} for team ID: {team_id}")
    
    team_rosters = {}
    player_team_map = {}
    
    for team in roster_data.get('teams', []):
        team_id = team.get('id')
        # Use abbreviation if available, otherwise fall back to name
        team_name = team.get('name', f'Team {team_id}')
        team_abbrev = team_abbrev_map.get(team_id, team_name)
        
        logger.info(f"Processing team: {team_abbrev} (ID: {team_id})")
        
        team_rosters[team_id] = {
            'name': team_name,
            'abbrev': team_abbrev,
            'players': []
        }
        
        # Get roster entries for this team
        roster_entries = team.get('roster', {}).get('entries', [])
        logger.info(f"Team {team_abbrev} has {len(roster_entries)} roster entries")
        
        for entry in roster_entries:
            player_id = entry.get('playerId')
            
            # Add player to team map
            player_team_map[player_id] = {
                'team_id': team_id, 
                'team_name': team_name,
                'team_abbrev': team_abbrev
            }
            
            # Find player in ESPN data
            player_data = espn_df[espn_df['id'] == player_id]
            
            if not player_data.empty:
                # Debug the player data
                player_name = player_data['fullName'].iloc[0]
                
                # Safely access projPts
                proj_pts = None
                if 'projPts' in player_data.columns:
                    try:
                        proj_pts = float(player_data['projPts'].iloc[0]) if not pd.isna(player_data['projPts'].iloc[0]) else None
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid projection points for {player_name}: {player_data['projPts'].iloc[0]}")
                
                player_info = {
                    'id': player_id,
                    'name': player_name,
                    'positions': convert_positions(player_data['eligibleSlots'].iloc[0]),
                    'projPts': proj_pts
                }
                team_rosters[team_id]['players'].append(player_info)
                logger.info(f"Added player: {player_name} to team {team_abbrev}")
            else:
                logger.warning(f"Player ID {player_id} not found in ESPN data")
    
    logger.info(f"Processed {len(player_team_map)} players across {len(team_rosters)} teams")
    return team_rosters, player_team_map

# Add league ID input in the sidebar
with st.sidebar:
    st.header("ESPN Fantasy Settings")
    league_id = st.text_input("League ID", value="339466431", help="Enter your ESPN Fantasy Baseball League ID")
    
    # Add debug toggle
    show_debug = st.checkbox("Show Debug Info", value=False, help="Show debug information in the UI")

# Fetch all data
with st.spinner("Fetching player data..."):
    espn_data = fetch_espn_player_data()
    fg_batters_data = fetch_fangraphs_batters()
    fg_pitchers_data = fetch_fangraphs_pitchers()

if espn_data:
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
    
    # Combine all FanGraphs data with pitcher priority
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
            teams_data = fetch_espn_teams_data(league_id)
            if not teams_data:
                st.error("Failed to fetch teams data. Check your league ID and try again.")
                logger.error("Failed to fetch teams data")
            else:
                logger.info(f"Successfully fetched teams data with {len(teams_data.get('teams', []))} teams")
                
                # Then fetch the team rosters
                roster_data = fetch_espn_team_rosters(league_id)
                
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
        'Team': filtered_espn_df['team_name']
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
                # Define roster slot structure
                roster_slots = {
                    "C": 1,
                    "1B": 1,
                    "2B": 1, 
                    "3B": 1,
                    "SS": 1,
                    "OF": 3,
                    "UTIL": 1,  # Any hitter
                    "P": 7      # Any pitcher (SP or RP) - 7 total pitcher slots
                }
                
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
                        'is_hitter': is_hitter
                    })
                
                # Roster optimization function
                def optimize_roster(players, slots):
                    # Sort players by projected points (highest first)
                    sorted_players = sorted(players, key=lambda p: p['projected_points'], reverse=True)
                    
                    # Initialize assigned slots
                    assignments = {position: [] for position in slots.keys()}
                    assignments["BN"] = []  # Bench
                    
                    # Track which players have been assigned
                    assigned_players = set()
                    
                    # First pass - try to fill each position with the best available player
                    for position, count in slots.items():
                        eligible_players = [
                            p for p in sorted_players 
                            if p['name'] not in assigned_players and 
                                (position in p['positions'] or 
                                (position == "UTIL" and p['is_hitter']) or
                                (position == "P" and p['is_pitcher']))
                        ]
                        
                        # Assign up to 'count' players to this position
                        for i in range(min(count, len(eligible_players))):
                            assignments[position].append(eligible_players[i])
                            assigned_players.add(eligible_players[i]['name'])
                    
                    # Assign remaining players to bench
                    for player in sorted_players:
                        if player['name'] not in assigned_players:
                            assignments["BN"].append(player)
                            assigned_players.add(player['name'])
                    
                    return assignments
                
                # Run the optimization
                with st.spinner("Optimizing roster..."):
                    optimized_roster = optimize_roster(processed_roster, roster_slots)
                
                # Display the optimized roster
                st.write("### Optimized Starting Lineup")
                
                # Display starters by position
                starting_slots = []
                for position, count in roster_slots.items():
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
                            "Projected Points": player["projected_points"]
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
                        "Projected Points": st.column_config.NumberColumn("Proj. Points", format="%.1f")
                    }
                )
                
                # Display bench players
                st.write("### Bench Players")
                bench_players = [{
                    "Name": player["name"],
                    "Eligible Positions": ", ".join(player["positions"]),
                    "Projected Points": player["projected_points"]
                } for player in optimized_roster["BN"]]
                
                bench_df = pd.DataFrame(bench_players)
                
                if not bench_df.empty:
                    st.dataframe(
                        bench_df,
                        use_container_width=True,
                        column_config={
                            "Name": st.column_config.TextColumn("Player Name"),
                            "Eligible Positions": st.column_config.TextColumn("Eligible At"),
                            "Projected Points": st.column_config.NumberColumn("Proj. Points", format="%.1f")
                        }
                    )
                else:
                    st.info("No bench players available")
                
                # Calculate team statistics
                total_projected_points = sum(player["projected_points"] for position, players in optimized_roster.items() 
                                           if position != "BN" for player in players)
                
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
                                'percent_owned': player['Percent Owned']
                            })
                        
                        # Combine team roster with free agents
                        combined_roster = processed_roster + processed_free_agents
                        
                        # Save original optimal lineup for comparison
                        original_starters = set()
                        for position, players in optimized_roster.items():
                            if position != "BN":
                                for player in players:
                                    original_starters.add(player['name'])
                        
                        # Run optimization with combined roster
                        optimized_combined = optimize_roster(combined_roster, roster_slots)
                        
                        # Identify free agents who made it into the starting lineup
                        recommended_pickups = []
                        
                        # Get new starters
                        new_starters = set()
                        new_starter_details = {}
                        for position, players in optimized_combined.items():
                            if position != "BN":
                                for player in players:
                                    new_starters.add(player['name'])
                                    new_starter_details[player['name']] = {
                                        'position': position,
                                        'projected_points': player['projected_points']
                                    }
                        
                        # Find free agents who made it into starting lineup
                        free_agent_names = {player['name'] for player in processed_free_agents}
                        recommended_free_agents = new_starters.intersection(free_agent_names)
                        
                        # Identify who they would replace
                        replaced_players = original_starters - new_starters
                        
                        # Create recommendations with details
                        for fa_name in recommended_free_agents:
                            # Find the free agent in the processed free agents list
                            fa = next((p for p in processed_free_agents if p['name'] == fa_name), None)
                            
                            if fa:
                                # Find position they'd play
                                position = new_starter_details[fa_name]['position']
                                
                                # Find who they replace (player at same position not in new lineup)
                                potential_replacements = []
                                for original_player in processed_roster:
                                    # Check if the player is not in the new starters
                                    if original_player['name'] not in new_starters:
                                        # Check if they can play the same position
                                        if position in original_player['positions'] or \
                                           (position == "UTIL" and original_player['is_hitter']) or \
                                           (position == "P" and original_player['is_pitcher']):
                                            potential_replacements.append({
                                                'name': original_player['name'],
                                                'projected_points': original_player['projected_points']
                                            })
                                
                                # Sort by projected points to find the most likely replacement
                                if potential_replacements:
                                    potential_replacements.sort(key=lambda p: p['projected_points'], reverse=True)
                                    replaced_player = potential_replacements[0]
                                    
                                    # Calculate projected points improvement
                                    improvement = fa['projected_points'] - replaced_player['projected_points']
                                    
                                    if improvement > 0:
                                        recommended_pickups.append({
                                            'Add': fa_name,
                                            'Position': position,
                                            'Drop': replaced_player['name'],
                                            'Proj. Points Improvement': improvement,
                                            'FA Percent Owned': fa['percent_owned']
                                        })
                        
                        # Sort recommendations by projected points improvement
                        recommended_pickups.sort(key=lambda r: r['Proj. Points Improvement'], reverse=True)
                        
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
                                    "FA Percent Owned": st.column_config.NumberColumn("% Owned", format="%.2f")
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
        st.write(f"*\*Showing {len(free_agents_df)} free agents with at least 0.05% ownership*")
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
