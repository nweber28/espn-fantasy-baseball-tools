import streamlit as st
import pandas as pd
from rapidfuzz import process
from unidecode import unidecode

# Define team names and your team
TEAMS = [
    "Shoehei's Interpreter",
    "C Team",
    "James's Finest Team",
    "The Destroyers🔥⚾️",
    "MD Madness",
    "Mr Met",
    "Mark's Monstrous Team",
    "Breggy Bombs",
    "Chris's Cool Team",
    "Matt's Pent Team"
]
YOUR_TEAM = "Shoehei's Interpreter"  # Change this to your team name

# Define fixed roster positions
ROSTER_POSITIONS = ["C", "1B", "2B", "3B", "SS", "OF", "OF", "OF", "UTIL", "BE", "BE", "BE",
                    "P", "P", "P", "P", "P", "P", "P"]

# Initialize session state
if 'current_pick' not in st.session_state:
    st.session_state.current_pick = 0
if 'team_picks' not in st.session_state:
    st.session_state.team_picks = {team: [] for team in TEAMS}  # Store full player details
if 'df' not in st.session_state:
    file_path = "data/generated/all-positions-fpts.csv"
    raw_df = pd.read_csv(file_path)
    
    # Create a dictionary to store player data with multiple positions
    player_data = {}
    for _, row in raw_df.iterrows():
        player_key = f"{row['Name']}_{row['Team']}"
        if player_key not in player_data:
            player_data[player_key] = {
                "Name": row["Name"],
                "Team": row["Team"],
                "FPTS": row["FPTS"],
                "Positions": {},
                "Max VORP": 0  # Initialize max VORP
            }
        player_data[player_key]["Positions"][row["Position"]] = row["VORP"]
        # Update max VORP if this position's VORP is higher
        player_data[player_key]["Max VORP"] = max(player_data[player_key]["Max VORP"], row["VORP"])
    
    # Convert to DataFrame for display and searching
    st.session_state.df = pd.DataFrame.from_dict(player_data, orient='index')
    st.session_state.df["Drafted"] = False
    st.session_state.df["cleaned_name"] = st.session_state.df["Name"].apply(lambda x: unidecode(str(x)).lower().strip())

# Constants
PICKS_PER_ROUND = len(TEAMS)
TOTAL_ROUNDS = 19
TOTAL_PICKS = PICKS_PER_ROUND * TOTAL_ROUNDS

def get_round_number(pick_number):
    """Get the round number (1-based) for a given absolute pick number"""
    return (pick_number // PICKS_PER_ROUND) + 1

def get_pick_in_round(pick_number):
    """Get the pick number within the round (1-based) for a given absolute pick number"""
    return (pick_number % PICKS_PER_ROUND) + 1

def get_team_index(pick_number):
    """Get the index of the team that should pick at this position in a snake draft"""
    round_num = get_round_number(pick_number)
    pick_in_round = get_pick_in_round(pick_number)
    
    # In even rounds, reverse the order
    if round_num % 2 == 0:
        return PICKS_PER_ROUND - pick_in_round
    return pick_in_round - 1

def get_current_team(pick_number):
    """Get the team picking at the current pick number"""
    return TEAMS[get_team_index(pick_number)]

def calculate_team_fpts(team_players):
    """Calculate total FPTS for a team, with bench players weighted at 50%"""
    roster = assign_players_to_roster(team_players)
    total_fpts = 0
    
    # Add full FPTS for all non-bench positions
    for pos, data in roster.items():
        if pos == "BE":
            # Add 50% of FPTS for bench players
            for slot in data:
                total_fpts += slot["fpts"] * 0.5
        elif pos in ["P", "OF"]:
            # Add full FPTS for pitchers and outfielders
            for slot in data:
                total_fpts += slot["fpts"]
        else:
            # Add full FPTS for all other positions
            total_fpts += data["fpts"]
    
    return total_fpts

def search_players(query, df):
    """Search players with fuzzy matching and sort by highest VORP across all positions"""
    if not query:
        return df[~df["Drafted"]].sort_values("Max VORP", ascending=False)
    
    query = unidecode(query).lower().strip()
    matches = process.extract(query, df["cleaned_name"], limit=None, score_cutoff=60)
    matched_indices = [i[2] for i in matches]
    matched_df = df.loc[matched_indices]
    return matched_df[~matched_df["Drafted"]].sort_values("Max VORP", ascending=False)

def assign_players_to_roster(team_players):
    """Assign players to roster positions using a greedy algorithm (sorted by FPTS)."""
    # Initialize empty roster with lists for positions that can have multiple players
    roster = {}
    for pos in ROSTER_POSITIONS:
        if pos in ["P", "BE", "OF"]:
            roster[pos] = [{"player": "", "fpts": 0, "vorp": 0} for _ in range(7 if pos == "P" else (3 if pos == "BE" else 3))]
        else:
            roster[pos] = {"player": "", "fpts": 0, "vorp": 0}

    # Sort players by FPTS in descending order (highest first)
    sorted_players = sorted(team_players, key=lambda p: p["FPTS"], reverse=True)

    # First pass: Try to fill all regular positions
    for player in sorted_players:
        assigned = False
        # Get all eligible positions for this player
        eligible_positions = list(player["Positions"].keys())
        
        # Try to assign player to their best position first (highest VORP)
        best_position = max(eligible_positions, key=lambda pos: player["Positions"][pos])
        
        # Map DH to UTIL
        if best_position == "DH":
            best_position = "UTIL"
        
        # Handle positions that can have multiple players
        if best_position in ["P", "BE", "OF"]:
            for i, slot in enumerate(roster[best_position]):
                if slot["player"] == "":
                    roster[best_position][i] = {
                        "player": f"{player['Name']} ({player['Team']})",
                        "fpts": player["FPTS"],
                        "vorp": player["Positions"][best_position if best_position != "UTIL" else "DH"]
                    }
                    assigned = True
                    break
        # Handle single-player positions
        else:
            if roster[best_position]["player"] == "":
                roster[best_position] = {
                    "player": f"{player['Name']} ({player['Team']})",
                    "fpts": player["FPTS"],
                    "vorp": player["Positions"][best_position if best_position != "UTIL" else "DH"]
                }
                assigned = True
        
        # If player wasn't placed in their best position, try other eligible positions
        if not assigned:
            for pos in eligible_positions:
                if pos == best_position:
                    continue
                
                # Map DH to UTIL for other positions too
                target_pos = "UTIL" if pos == "DH" else pos
                    
                if target_pos in ["P", "BE", "OF"]:
                    for i, slot in enumerate(roster[target_pos]):
                        if slot["player"] == "":
                            roster[target_pos][i] = {
                                "player": f"{player['Name']} ({player['Team']})",
                                "fpts": player["FPTS"],
                                "vorp": player["Positions"][pos]
                            }
                            assigned = True
                            break
                else:
                    if roster[target_pos]["player"] == "":
                        roster[target_pos] = {
                            "player": f"{player['Name']} ({player['Team']})",
                            "fpts": player["FPTS"],
                            "vorp": player["Positions"][pos]
                        }
                        assigned = True
                        break
        
        # Mark player as assigned if they were placed anywhere
        if assigned:
            player["assigned"] = True
        else:
            player["assigned"] = False

    # Second pass: Fill UTIL with best remaining hitter
    if roster["UTIL"]["player"] == "":
        remaining_hitters = [p for p in sorted_players if not p["assigned"] and "P" not in p["Positions"]]
        if remaining_hitters:
            best_hitter = max(remaining_hitters, key=lambda p: p["FPTS"])
            roster["UTIL"] = {
                "player": f"{best_hitter['Name']} ({best_hitter['Team']})",
                "fpts": best_hitter["FPTS"],
                "vorp": max(best_hitter["Positions"].values())
            }
            best_hitter["assigned"] = True

    # Third pass: Fill bench spots with remaining players
    remaining_players = [p for p in sorted_players if not p["assigned"]]
    for player in remaining_players:
        assigned = False
        for i, slot in enumerate(roster["BE"]):
            if slot["player"] == "":
                roster["BE"][i] = {
                    "player": f"{player['Name']} ({player['Team']})",
                    "fpts": player["FPTS"],
                    "vorp": max(player["Positions"].values())
                }
                assigned = True
                break
        if assigned:
            player["assigned"] = True
    
    return roster

# UI Layout
st.title("⚾️ Fantasy Baseball Draft Tracker")

# Create tabs
tab_draft, tab_rosters, tab_leaderboard = st.tabs(["📝 Draft Board", "👥 Team Rosters", "🏆 Leaderboard"])

with tab_draft:
    round_num = get_round_number(st.session_state.current_pick)
    pick_in_round = get_pick_in_round(st.session_state.current_pick)
    current_team = get_current_team(st.session_state.current_pick)

    st.header(f"Round {round_num}, Pick {pick_in_round} (Overall: {st.session_state.current_pick + 1})")

    selected_team = st.selectbox("Select Team to Draft For:", TEAMS, index=TEAMS.index(current_team))
    st.subheader(f"Current Pick: {selected_team}")

    st.divider()
    search_query = st.text_input("Search Players:", key="player_search")

    available_players = search_players(search_query, st.session_state.df)
    
    # Create a display DataFrame with position-specific VORP values
    display_data = []
    for idx, row in available_players.iterrows():
        player_info = {
            "Name": row["Name"],
            "Team": row["Team"],
            "FPTS": row["FPTS"],
            "VORP": f"{row['Max VORP']:.1f}",
            "Positions": ", ".join(f"{pos} ({vorp:.1f})" for pos, vorp in row["Positions"].items())
        }
        display_data.append(player_info)
    
    display_df = pd.DataFrame(display_data)
    
    # Use dataframe with row selection
    event = st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    draft_complete = st.session_state.current_pick >= TOTAL_PICKS
    if draft_complete:
        st.warning("🎉 Draft Complete! All rounds have been finished.")
    else:
        if st.button("Draft Selected Player", key="draft_button") and event.selection.rows:
            # Get the selected player from the dataframe
            selected_idx = event.selection.rows[0]
            selected_player = available_players.iloc[selected_idx]
            
            player_data = {
                "Name": selected_player["Name"],
                "Team": selected_player["Team"],
                "FPTS": selected_player["FPTS"],
                "Positions": selected_player["Positions"]
            }
            
            st.session_state.df.loc[selected_player.name, "Drafted"] = True
            st.session_state.team_picks[selected_team].append(player_data)
            st.session_state.current_pick += 1
            st.rerun()

with tab_rosters:
    st.header("Team Rosters")
    
    team_tabs = st.tabs(TEAMS)
    
    for idx, team_tab in enumerate(team_tabs):
        with team_tab:
            team_name = TEAMS[idx]
            team_players = st.session_state.team_picks[team_name]

            roster = assign_players_to_roster(team_players)

            # Convert roster to DataFrame for display
            roster_data = []
            for pos, data in roster.items():
                if pos in ["P", "BE", "OF"]:
                    for i, slot in enumerate(data):
                        roster_data.append({
                            "Position": f"{pos}{i+1}",
                            "Player": slot["player"],
                            "FPTS": f"{slot['fpts']:.1f}",
                            "VORP": f"{slot['vorp']:.1f}"
                        })
                else:
                    roster_data.append({
                        "Position": pos,
                        "Player": data["player"],
                        "FPTS": f"{data['fpts']:.1f}",
                        "VORP": f"{data['vorp']:.1f}"
                    })
            df_roster = pd.DataFrame(roster_data)

            st.markdown(f"### {team_name} Roster")
            st.dataframe(df_roster, hide_index=True, use_container_width=True)

with tab_leaderboard:
    st.header("🏆 Draft Leaderboard")
    
    # Calculate team stats
    team_stats = []
    for team_name in TEAMS:
        team_players = st.session_state.team_picks[team_name]
        total_fpts = calculate_team_fpts(team_players)
        team_stats.append({
            "Team": team_name,
            "Total FPTS": total_fpts,
            "Players Drafted": len(team_players)
        })
    
    # Convert to DataFrame and sort by FPTS
    df_leaderboard = pd.DataFrame(team_stats)
    
    # Calculate relative strength
    league_avg = df_leaderboard["Total FPTS"].mean()
    df_leaderboard["Relative Strength (%)"] = ((df_leaderboard["Total FPTS"] - league_avg) / league_avg * 100).round(1)
    
    # Format Total FPTS for display
    df_leaderboard["Total FPTS"] = df_leaderboard["Total FPTS"].round(1)
    
    # Sort by FPTS
    df_leaderboard = df_leaderboard.sort_values("Total FPTS", ascending=False)
    
    # Display leaderboard
    st.dataframe(df_leaderboard, hide_index=True, use_container_width=True)
    
    # Add a note about the relative strength calculation
    st.markdown("""
    ---
    *Note: Relative Strength shows percentage above/below league average. A positive number means your team is that much better than average.*
    """)
