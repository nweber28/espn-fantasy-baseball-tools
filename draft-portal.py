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
    st.session_state.df = pd.read_csv(file_path)
    st.session_state.df["Drafted"] = False
    st.session_state.df["cleaned_name"] = st.session_state.df["Name"].apply(lambda x: unidecode(str(x)).lower().strip())

# Constants
PICKS_PER_ROUND = len(TEAMS)
TOTAL_ROUNDS = 10
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
    """Calculate total FPTS for a team"""
    return sum(player["FPTS"] for player in team_players)

def search_players(query, df):
    """Search players with fuzzy matching and sort by VORP"""
    if not query:
        return df[~df["Drafted"]].sort_values("VORP", ascending=False)
    
    query = unidecode(query).lower().strip()
    matches = process.extract(query, df["cleaned_name"], limit=None, score_cutoff=60)
    matched_indices = [i[2] for i in matches]
    matched_df = df.iloc[matched_indices]
    return matched_df[~matched_df["Drafted"]].sort_values("VORP", ascending=False)

def assign_players_to_roster(team_players):
    """Assign players to roster positions using a greedy algorithm (sorted by FPTS)."""
    # Initialize empty roster with lists for positions that can have multiple players
    roster = {}
    for pos in ROSTER_POSITIONS:
        if pos in ["P", "BE"]:
            roster[pos] = [{"player": "", "fpts": 0, "vorp": 0} for _ in range(7 if pos == "P" else 3)]
        else:
            roster[pos] = {"player": "", "fpts": 0, "vorp": 0}

    # Sort players by FPTS in descending order (highest first)
    sorted_players = sorted(team_players, key=lambda p: p["FPTS"], reverse=True)

    for player in sorted_players:
        assigned = False
        pos = player["Position"]
        
        # Handle positions that can have multiple players
        if pos in ["P", "BE"]:
            for i, slot in enumerate(roster[pos]):
                if slot["player"] == "":
                    roster[pos][i] = {
                        "player": f"{player['Name']} ({player['Team']})",
                        "fpts": player["FPTS"],
                        "vorp": player["VORP"]
                    }
                    assigned = True
                    break
        # Handle single-player positions
        else:
            if roster[pos]["player"] == "":
                roster[pos] = {
                    "player": f"{player['Name']} ({player['Team']})",
                    "fpts": player["FPTS"],
                    "vorp": player["VORP"]
                }
                assigned = True
        
        # If player wasn't placed in their primary position, try UTIL or Bench
        if not assigned:
            # Try UTIL first
            if roster["UTIL"]["player"] == "":
                roster["UTIL"] = {
                    "player": f"{player['Name']} ({player['Team']})",
                    "fpts": player["FPTS"],
                    "vorp": player["VORP"]
                }
                assigned = True
            # Then try Bench
            else:
                for i, slot in enumerate(roster["BE"]):
                    if slot["player"] == "":
                        roster["BE"][i] = {
                            "player": f"{player['Name']} ({player['Team']})",
                            "fpts": player["FPTS"],
                            "vorp": player["VORP"]
                        }
                        assigned = True
                        break
    
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

    # Create a radio selection for players
    if len(available_players) > 0:
        player_options = available_players.apply(
            lambda x: f"{x['Name']} ({x['Team']}) - {x['Position']} - FPTS: {x['FPTS']:.1f}",
            axis=1
        ).tolist()
        
        selected_player_idx = st.radio(
            "Select a player to draft:",
            range(len(available_players)),
            format_func=lambda x: player_options[x],
            key="player_selection"
        )
    else:
        st.info("No players available matching your search criteria.")
        selected_player_idx = None

    draft_complete = st.session_state.current_pick >= TOTAL_PICKS
    if draft_complete:
        st.warning("🎉 Draft Complete! All rounds have been finished.")
    else:
        if st.button("Draft Selected Player", key="draft_button", disabled=selected_player_idx is None):
            selected_player = available_players.iloc[selected_player_idx]
            player_data = {
                "Name": selected_player["Name"],
                "Team": selected_player["Team"],
                "Position": selected_player["Position"],
                "FPTS": selected_player["FPTS"],
                "VORP": selected_player["VORP"]
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
                if pos in ["P", "BE"]:
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
            "Total FPTS": f"{total_fpts:.1f}",
            "Players Drafted": len(team_players)
        })
    
    # Convert to DataFrame and sort by FPTS
    df_leaderboard = pd.DataFrame(team_stats)
    df_leaderboard["Total FPTS"] = pd.to_numeric(df_leaderboard["Total FPTS"])
    df_leaderboard = df_leaderboard.sort_values("Total FPTS", ascending=False)
    
    # Display leaderboard
    st.dataframe(df_leaderboard, hide_index=True, use_container_width=True)
