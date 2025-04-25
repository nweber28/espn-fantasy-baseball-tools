"""
Roster optimization utilities for fantasy baseball analysis.
"""
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
import logging
import pulp

logger = logging.getLogger(__name__)

# Define injury statuses that make a player eligible for IL
IL_ELIGIBLE_STATUSES = ["TEN_DAY_DL", "SUSPENSION", "SIXTY_DAY_DL", "OUT", "FIFTEEN_DAY_DL"]

def optimize_roster(players: List[Dict[str, Any]], slots: Dict[str, int]) -> Tuple[Dict[str, List[Dict[str, Any]]], float]:
    """
    Optimize a roster by assigning players to positions based on projected points using Integer Linear Programming.
    This approach finds the globally optimal solution by considering all valid position combinations.
    
    Args:
        players: List of player dictionaries with keys:
            - name: Player name
            - positions: List of eligible positions
            - projected_points: Projected fantasy points
            - is_pitcher: Boolean indicating if player is a pitcher
            - is_hitter: Boolean indicating if player is a hitter
            - injury_status: Player's injury status (optional)
        slots: Dictionary of roster slots and counts
        
    Returns:
        Tuple of (position assignments dictionary, total roster strength)
    """
    # First, handle IL-eligible players separately
    il_eligible_players = [p for p in players if p.get('injury_status') in IL_ELIGIBLE_STATUSES]
    il_limit = 3  # ESPN Fantasy allows 3 IL slots
    
    # Sort IL players by projected points and take the top ones up to the limit
    il_eligible_players.sort(key=lambda p: p.get('projected_points', 0), reverse=True)
    il_assigned_players = il_eligible_players[:min(il_limit, len(il_eligible_players))]
    il_assigned_names = {p['name'] for p in il_assigned_players}
    
    # Filter out IL-assigned players from the main optimization
    active_players = [p for p in players if p['name'] not in il_assigned_names]
    
    # Create the ILP problem
    prob = pulp.LpProblem("RosterOptimization", pulp.LpMaximize)
    
    # Create decision variables: x[i,j] = 1 if player i is assigned to position j, 0 otherwise
    x = {}
    for i, player in enumerate(active_players):
        for position in slots.keys():
            # Check if player is eligible for this position
            is_eligible = False
            if position == "UTIL" and player.get('is_hitter', False):
                is_eligible = True
            elif position == "P" and player.get('is_pitcher', False):
                is_eligible = True
            elif position in player.get('positions', []):
                is_eligible = True
            
            if is_eligible and position != "BN":  # We'll handle bench separately
                x[i, position] = pulp.LpVariable(f"x_{i}_{position}", cat='Binary')
    
    # Create bench assignment variables
    bench_vars = {}
    for i, _ in enumerate(active_players):
        bench_vars[i] = pulp.LpVariable(f"bench_{i}", cat='Binary')
    
    # Objective function: maximize total projected points
    prob += pulp.lpSum([active_players[i]['projected_points'] * x[i, pos] 
                       for i, player in enumerate(active_players) 
                       for pos in slots.keys() 
                       if (i, pos) in x])
    
    # Constraint 1: Each player can be assigned to at most one position (including bench)
    for i, _ in enumerate(active_players):
        prob += pulp.lpSum([x[i, pos] for pos in slots.keys() if (i, pos) in x]) + bench_vars[i] <= 1
    
    # Constraint 2: Each position needs exactly the required number of players
    for position, count in slots.items():
        if position != "BN":  # Handle bench separately
            prob += pulp.lpSum([x[i, position] for i in range(len(active_players)) if (i, position) in x]) == count
    
    # Constraint 3: Bench limit
    bench_limit = slots.get("BN", 3)  # Default to 3 bench spots if not specified
    prob += pulp.lpSum([bench_vars[i] for i in range(len(active_players))]) <= bench_limit
    
    # Solve the problem
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    # Check if a solution was found
    if pulp.LpStatus[prob.status] != 'Optimal':
        logger.warning(f"No optimal solution found. Status: {pulp.LpStatus[prob.status]}")
        # Return empty assignments if no solution found
        return {position: [] for position in slots.keys()}, 0
    
    # Extract the solution
    assignments = {position: [] for position in slots.keys()}
    assignments["IL"] = []  # Add IL list
    total_points = 0
    
    # First add IL players
    for player in il_assigned_players:
        assignments["IL"].append(player)
    
    # Then add active players based on the ILP solution
    for i, player in enumerate(active_players):
        assigned = False
        for position in slots.keys():
            if (i, position) in x and x[i, position].value() > 0.5:  # Variable is 1 (assigned)
                assignments[position].append(player)
                total_points += player['projected_points']
                assigned = True
                break
        
        # Check if player is assigned to bench
        if not assigned and bench_vars[i].value() > 0.5:
            assignments["BN"].append(player)
    
    # Sort players within each position by projected points (highest first)
    for position in assignments:
        assignments[position].sort(key=lambda p: p.get('projected_points', 0), reverse=True)
    
    return assignments, total_points
def roster_to_dataframe(roster_dict):
    """
    Convert a roster dictionary to a DataFrame for display.
    
    Args:
        roster_dict: Dictionary of position assignments from optimize_roster
        
    Returns:
        DataFrame with columns: Position, Player, Projected Points
    """
    # Create lists for each column for vectorized DataFrame creation
    positions = []
    players = []
    projected_points = []
    player_positions = []
    injury_statuses = []
    
    # Process starting positions first
    for position, player_list in roster_dict.items():
        if position != "BN" and position != "IL":  # Skip bench and IL for now
            for i, player in enumerate(player_list):
                positions.append(f"{position}{i+1}" if len(player_list) > 1 else position)
                players.append(player["name"])
                projected_points.append(player["projected_points"])
                player_positions.append(player.get("positions", ""))
                injury_statuses.append(player.get("injury_status", "ACTIVE"))
    
    # Now add bench players
    for i, player in enumerate(roster_dict.get("BN", [])):
        positions.append(f"BN{i+1}")
        players.append(player["name"])
        projected_points.append(player["projected_points"])
        player_positions.append(player.get("positions", ""))
        injury_statuses.append(player.get("injury_status", "ACTIVE"))
    
    # Now add IL players
    for i, player in enumerate(roster_dict.get("IL", [])):
        positions.append(f"IL{i+1}")
        players.append(player["name"])
        projected_points.append(player["projected_points"])
        player_positions.append(player.get("positions", ""))
        injury_statuses.append(player.get("injury_status", "ACTIVE"))
    
    # Create DataFrame in one operation
    return pd.DataFrame({
        "Position": positions,
        "Player": players,
        "Eligible Positions": player_positions,
        "Projected Points": projected_points,
        "Injury Status": injury_statuses
    })
def identify_roster_changes(before_df, after_df):
    """
    Identify changes between two roster DataFrames using vectorized operations.
    
    Args:
        before_df: DataFrame of roster before changes
        after_df: DataFrame of roster after changes
        
    Returns:
        Tuple of (added players, removed players, position changes)
    """
    # Get players in both rosters using set operations
    before_players = set(before_df["Player"])
    after_players = set(after_df["Player"])
    
    # Players added and removed
    added = after_players - before_players
    removed = before_players - after_players
    
    # Players who changed positions - use merge for vectorized comparison
    common_players = before_players.intersection(after_players)
    
    # Filter DataFrames to only include common players
    before_common = before_df[before_df["Player"].isin(common_players)]
    after_common = after_df[after_df["Player"].isin(common_players)]
    
    # Merge on Player to compare positions
    merged = pd.merge(
        before_common[["Player", "Position"]], 
        after_common[["Player", "Position"]], 
        on="Player", 
        suffixes=('_before', '_after')
    )
    
    # Find position changes
    position_changes = merged[merged["Position_before"] != merged["Position_after"]]
    
    # Convert to list of dictionaries
    position_changes_list = [
        {"Player": row["Player"], "Before": row["Position_before"], "After": row["Position_after"]}
        for _, row in position_changes.iterrows()
    ]
    
    return added, removed, position_changes_list
def prepare_players_for_optimization(df):
    """
    Convert a DataFrame of players to the format needed for roster optimization.
    Uses vectorized operations for better performance.
    
    Args:
        df: DataFrame with player information
        
    Returns:
        List of player dictionaries in the format required by optimize_roster
    """
    # Create empty lists for each field
    players = []
    
    # Define position lists for faster checking
    pitcher_positions = ["SP", "RP", "P"]
    hitter_positions = ["C", "1B", "2B", "3B", "SS", "OF", "DH", "UTIL"]
    
    # Process each row
    for _, player in df.iterrows():
        # Get positions from the Eligible Positions column
        positions = []
        if 'Eligible Positions' in df.columns:
            positions = [pos.strip() for pos in player['Eligible Positions'].split(',') if pos.strip()]
        
        # Determine player type (hitter or pitcher)
        is_pitcher = any(pos in pitcher_positions for pos in positions)
        is_hitter = any(pos in hitter_positions for pos in positions)
        
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
            'is_hitter': is_hitter,
            'injury_status': player.get('Injury Status')  # Add injury status
        })
    return players

def optimize_dataframe_memory(df):
    """
    Reduce memory usage of dataframe by setting appropriate data types.
    
    Args:
        df: DataFrame to optimize
        
    Returns:
        Optimized DataFrame
    """
    for col in df.columns:
        # Skip columns with unhashable types like dictionaries or lists
        try:
            if df[col].dtype == 'float64':
                df[col] = pd.to_numeric(df[col], downcast='float')
            elif df[col].dtype == 'int64':
                df[col] = pd.to_numeric(df[col], downcast='integer')
            elif df[col].dtype == 'object':
                # Check if the column contains only hashable types
                sample_value = df[col].iloc[0] if not df[col].empty else None
                if sample_value is not None and isinstance(sample_value, (str, int, float, bool)):
                    # For string columns, consider using categorical for repeated values
                    if df[col].nunique() < len(df) * 0.5:  # If less than 50% unique values
                        df[col] = df[col].astype('category')
        except (TypeError, ValueError):
            # Skip columns that cause errors (likely containing unhashable types)
            continue
    return df
