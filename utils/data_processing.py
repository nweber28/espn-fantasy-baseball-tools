"""
Utilities for processing and transforming data.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple
from config.constants import POSITION_MAP, TEAM_MAP
from utils.name_utils import stem_name

logger = logging.getLogger(__name__)

# Create a name stemming cache for better performance
name_stem_cache = {}

def cached_stem_name(name):
    """Cached version of stem_name for better performance."""
    if name not in name_stem_cache:
        name_stem_cache[name] = stem_name(name)
    return name_stem_cache[name]

def convert_positions(positions_list: List[int]) -> str:
    """
    Convert position IDs to position names, showing only key positions.
    
    Args:
        positions_list: List of position IDs
        
    Returns:
        Comma-separated string of position names
    """
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

def map_team_abbr(abbr: str) -> str:
    """
    Standardize team abbreviations.
    
    Args:
        abbr: Team abbreviation
        
    Returns:
        Standardized team abbreviation
    """
    return TEAM_MAP.get(abbr, abbr)

def process_fangraphs_data(data: Dict[str, Any], player_type: str) -> pd.DataFrame:
    """
    Process FanGraphs data into a standardized DataFrame using vectorized operations.
    
    Args:
        data: Raw FanGraphs data
        player_type: Type of player ('batter' or 'pitcher')
        
    Returns:
        Processed DataFrame
    """
    if not data or 'data' not in data:
        logger.warning(f"No valid data for {player_type}s processing")
        return pd.DataFrame()
    
    # Create DataFrame directly from the data
    df = pd.DataFrame(data.get('data', []))
    
    # Filter out rows with no PlayerName
    df = df[df['PlayerName'].notna() & (df['PlayerName'] != "")]
    
    if df.empty:
        return pd.DataFrame()
    
    # Create stemmed names using vectorized operation
    df['StemmedName'] = df['PlayerName'].apply(cached_stem_name)
    
    # Safely convert projection points to float
    df['ProjPts'] = pd.to_numeric(df['rPTS'], errors='coerce').fillna(0.0)
    
    # Create base DataFrame with common columns
    result_df = pd.DataFrame({
        "Name": df['PlayerName'],
        "StemmedName": df['StemmedName'],
        "Team": df['Team'].fillna(""),
        "Pos": df['POS'].fillna(""),
        "ProjPts": df['ProjPts'],
        "PlayerType": player_type
    })
    
    # Add specific stats based on player type
    if player_type == 'batter':
        # Convert PA to float and calculate PtsPerPA
        result_df['PA'] = pd.to_numeric(df['PA'], errors='coerce').fillna(0.0)
        # Vectorized division with handling for zero division
        result_df['PtsPerPA'] = np.divide(
            result_df['ProjPts'], 
            result_df['PA'], 
            out=np.zeros_like(result_df['ProjPts']), 
            where=result_df['PA'] != 0
        )
    else:
        # Convert IP to float and calculate PtsPerIP
        result_df['IP'] = pd.to_numeric(df['IP'], errors='coerce').fillna(0.0)
        # Vectorized division with handling for zero division
        result_df['PtsPerIP'] = np.divide(
            result_df['ProjPts'], 
            result_df['IP'], 
            out=np.zeros_like(result_df['ProjPts']), 
            where=result_df['IP'] != 0
        )
    
    logger.info(f"Processed {len(result_df)} {player_type} records")    
    return result_df

def process_team_rosters(roster_data: Dict[str, Any], teams_data: Dict[str, Any], 
                        espn_df: pd.DataFrame) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    """
    Process team roster data from ESPN API using vectorized operations where possible.
    
    Args:
        roster_data: Raw roster data from ESPN API
        teams_data: Raw teams data from ESPN API
        espn_df: DataFrame of ESPN player data
        
    Returns:
        Tuple of (team_rosters, player_team_map)
    """
    if not roster_data or 'teams' not in roster_data:
        logger.warning("Invalid roster data structure")
        return {}, {}
    
    # Create a map of team ID to abbreviation
    team_abbrev_map = {}
    if teams_data and 'teams' in teams_data:
        # Extract team data in a vectorized way
        teams_list = teams_data.get('teams', [])
        team_ids = [team.get('id') for team in teams_list]
        team_abbrevs = [team.get('abbrev', f'Team {team.get("id")}') for team in teams_list]
        team_abbrev_map = dict(zip(team_ids, team_abbrevs))
        logger.info(f"Found {len(team_abbrev_map)} team abbreviations")
    
    team_rosters = {}
    player_team_map = {}
    
    # Create a lookup dictionary for player data
    player_lookup = {}
    if 'id' in espn_df.columns:
        player_lookup = espn_df.set_index('id').to_dict('index')
    
    for team in roster_data.get('teams', []):
        team_id = team.get('id')
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
        
        # Process all players for this team at once
        player_ids = [entry.get('playerId') for entry in roster_entries]
        
        # Add all players to team map at once
        for player_id in player_ids:
            player_team_map[player_id] = {
                'team_id': team_id, 
                'team_name': team_name,
                'team_abbrev': team_abbrev
            }
            
            # Find player in ESPN data using the lookup dictionary
            if player_id in player_lookup:
                player_data = player_lookup[player_id]
                
                # Get player name
                player_name = player_data.get('fullName', f"Player {player_id}")
                
                # Safely access projPts
                proj_pts = None
                if 'projPts' in player_data:
                    try:
                        proj_pts = float(player_data['projPts']) if not pd.isna(player_data['projPts']) else None
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid projection points for {player_name}: {player_data['projPts']}")
                
                player_info = {
                    'id': player_id,
                    'name': player_name,
                    'positions': convert_positions(player_data.get('eligibleSlots', [])),
                    'projPts': proj_pts
                }
                team_rosters[team_id]['players'].append(player_info)
                logger.info(f"Added player: {player_name} to team {team_abbrev}")
            else:
                logger.warning(f"Player ID {player_id} not found in ESPN data")
    
    logger.info(f"Processed {len(player_team_map)} players across {len(team_rosters)} teams")
    return team_rosters, player_team_map
