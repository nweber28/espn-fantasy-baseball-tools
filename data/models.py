"""
Data models for the fantasy baseball application.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Union
from datetime import datetime

@dataclass
class Player:
    """Player data model representing a baseball player."""
    id: Optional[int] = None
    name: str = ""
    stemmed_name: str = ""
    team: str = ""
    position: str = ""
    projected_points: float = 0.0
    percent_owned: float = 0.0
    eligible_positions: List[str] = None
    
    def __post_init__(self):
        if self.eligible_positions is None:
            self.eligible_positions = []
    
    @property
    def is_pitcher(self) -> bool:
        """Check if player is a pitcher."""
        return any(pos in ["SP", "RP", "P"] for pos in self.eligible_positions)
    
    @property
    def is_hitter(self) -> bool:
        """Check if player is a hitter."""
        return any(pos in ["C", "1B", "2B", "3B", "SS", "OF", "DH"] for pos in self.eligible_positions)

@dataclass
class Team:
    """Team data model representing a fantasy baseball team."""
    id: int
    name: str
    abbreviation: str
    players: List[Player] = None
    
    def __post_init__(self):
        if self.players is None:
            self.players = []

@dataclass
class Game:
    """Game data model representing a baseball game."""
    id: int
    date: datetime
    away_team: str
    home_team: str
    away_pitcher: Optional[Player] = None
    home_pitcher: Optional[Player] = None
    
    @property
    def matchup_string(self) -> str:
        """Get a formatted matchup string."""
        return f"{self.away_team} @ {self.home_team}"
