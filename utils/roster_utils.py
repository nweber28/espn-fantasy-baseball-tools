"""
Roster optimization utilities for fantasy baseball analysis.
"""
from typing import Dict, Any, List, Tuple

def optimize_roster(players: List[Dict[str, Any]], slots: Dict[str, int]) -> Tuple[Dict[str, List[Dict[str, Any]]], float]:
    """
    Optimize a roster by assigning players to positions based on projected points.
    
    Args:
        players: List of player dictionaries with keys:
            - name: Player name
            - positions: List of eligible positions
            - projected_points: Projected fantasy points
            - is_pitcher: Boolean indicating if player is a pitcher
            - is_hitter: Boolean indicating if player is a hitter
        slots: Dictionary of roster slots and counts
        
    Returns:
        Tuple of (position assignments dictionary, total roster strength)
    """
    # Sort players by projected points (highest first)
    sorted_players = sorted(players, key=lambda p: p['projected_points'], reverse=True)
    
    # Initialize assigned slots
    assignments = {position: [] for position in slots.keys()}
    assignments["BN"] = []  # Bench
    
    # Track which players have been assigned
    assigned_players = set()
    total_points = 0
    
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
            total_points += eligible_players[i]['projected_points']
    
    # Assign remaining players to bench
    for player in sorted_players:
        if player['name'] not in assigned_players:
            assignments["BN"].append(player)
            assigned_players.add(player['name'])
    
    return assignments, total_points

def roster_to_dataframe(roster_dict):
    """
    Convert a roster dictionary to a DataFrame for display.
    
    Args:
        roster_dict: Dictionary of position assignments from optimize_roster
        
    Returns:
        DataFrame with columns: Position, Player, Projected Points
    """
    import pandas as pd
    
    rows = []
    # Process starting positions first
    for position, players in roster_dict.items():
        if position != "BN":  # Skip bench for now
            for i, player in enumerate(players):
                rows.append({
                    "Position": f"{position}{i+1}" if len(players) > 1 else position,
                    "Player": player["name"],
                    "Projected Points": player["projected_points"]
                })
    
    # Now add bench players
    for i, player in enumerate(roster_dict.get("BN", [])):
        rows.append({
            "Position": f"BN{i+1}",
            "Player": player["name"],
            "Projected Points": player["projected_points"]
        })
        
    return pd.DataFrame(rows)

def identify_roster_changes(before_df, after_df):
    """
    Identify changes between two roster DataFrames.
    
    Args:
        before_df: DataFrame of roster before changes
        after_df: DataFrame of roster after changes
        
    Returns:
        Tuple of (added players, removed players, position changes)
    """
    # Get players in both rosters
    before_players = set(before_df["Player"])
    after_players = set(after_df["Player"])
    
    # Players added and removed
    added = after_players - before_players
    removed = before_players - after_players
    
    # Players who changed positions
    position_changes = []
    for player in before_players.intersection(after_players):
        before_pos = before_df[before_df["Player"] == player]["Position"].iloc[0]
        after_pos = after_df[after_df["Player"] == player]["Position"].iloc[0]
        
        if before_pos != after_pos:
            position_changes.append({
                "Player": player,
                "Before": before_pos,
                "After": after_pos
            })
    
    return added, removed, position_changes

def prepare_players_for_optimization(df):
    """
    Convert a DataFrame of players to the format needed for roster optimization.
    
    Args:
        df: DataFrame with player information
        
    Returns:
        List of player dictionaries in the format required by optimize_roster
    """
    import pandas as pd
    
    players = []
    for _, player in df.iterrows():
        # Get positions from the Eligible Positions column
        positions = []
        if 'Eligible Positions' in df.columns:
            positions = [pos.strip() for pos in player['Eligible Positions'].split(',') if pos.strip()]
        
        # Determine player type (hitter or pitcher)
        is_pitcher = any(pos in ["SP", "RP", "P"] for pos in positions)
        is_hitter = any(pos in ["C", "1B", "2B", "3B", "SS", "OF", "DH", "UTIL"] for pos in positions)
        
        # Get projected points
        proj_pts = 0
        if 'Projected Points' in df.columns:
            proj_pts = player['Projected Points'] if not pd.isna(player['Projected Points']) else 0
        
        # Get player name
        name = player['Name']
        
        players.append({
            'name': name,
            'positions': positions,
            'projected_points': proj_pts,
            'is_pitcher': is_pitcher,
            'is_hitter': is_hitter
        })
    return players
