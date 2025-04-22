"""
Constants used throughout the fantasy baseball application.
"""
from typing import Dict, Any

# Team mappings
TEAM_MAP: Dict[str, str] = {
    'CWS': 'CHW', 'SF': 'SFG', 'SD': 'SDP', 'WSH': 'WSN', 'WAS': 'WSN', 'TB': 'TBR',
    'KC': 'KCR', 'ANA': 'LAA', 'FLA': 'MIA', 'NYN': 'NYM', 'SLN': 'STL', 'LAN': 'LAD', 
    'SFN': 'SFG', 'AZ': 'ARI'
}

TEAM_IDS: Dict[str, int] = {
    'LAA': 1, 'BAL': 2, 'BOS': 3, 'CHW': 4, 'CLE': 5, 'DET': 6, 'KCR': 7, 'MIN': 8,
    'NYY': 9, 'ATH': 10, 'SEA': 11, 'TBR': 12, 'TEX': 13, 'TOR': 14, 'ARI': 15,
    'ATL': 16, 'CHC': 17, 'CIN': 18, 'COL': 19, 'MIA': 20, 'HOU': 21, 'LAD': 22,
    'MIL': 23, 'WSN': 24, 'NYM': 25, 'PHI': 26, 'PIT': 27, 'STL': 28, 'SDP': 29,
    'SFG': 30
}

POSITION_MAP: Dict[int, str] = {
    0: "C", 1: "1B", 2: "2B", 3: "3B", 4: "SS", 5: "OF", 6: "MI", 7: "CI", 8: "LF",
    9: "CF", 10: "RF", 11: "DH", 12: "UTIL", 13: "P", 14: "SP", 15: "RP", 16: "BN",
    17: "IL", 18: "NA", 19: "IF"
}

# Fantasy baseball constants
AVG_STARTER_IP: float = 5.5
AVG_PA_PER_INNING: float = 4.2
DEFAULT_PITCHER_PTS: float = 6.0

# API request headers
API_HEADERS: Dict[str, str] = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json, text/plain, */*'
}
