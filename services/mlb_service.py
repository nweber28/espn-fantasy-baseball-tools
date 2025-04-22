"""
Service for interacting with MLB Stats API.
"""
import requests
import logging
import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class MLBService:
    """Service for interacting with MLB Stats API."""
    
    BASE_URL = "https://statsapi.mlb.com/api/v1"
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def fetch_schedule(date: str) -> Optional[Dict[str, Any]]:
        """
        Fetch MLB schedule for a specific date.
        
        Args:
            date: Date string in YYYY-MM-DD format
            
        Returns:
            Dictionary of schedule data or None if request fails
        """
        url = f"{MLBService.BASE_URL}/schedule"
        
        params = {
            "sportId": 1,
            "date": date,
            "leagueId": "103,104",
            "hydrate": "team,linescore,flags,liveLookin,review",
            "useLatestGames": False,
            "language": "en"
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json, text/plain, */*'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code != 200:
                logger.error(f"Request failed {response.status_code}: {url}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Request exception: {e}")
            return None
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def fetch_game_feed(game_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed game feed for a specific game.
        
        Args:
            game_id: MLB game ID
            
        Returns:
            Dictionary of game feed data or None if request fails
        """
        url = f"{MLBService.BASE_URL}.1/game/{game_id}/feed/live"
        
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json, text/plain, */*'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"Request failed {response.status_code}: {url}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Request exception: {e}")
            return None
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def fetch_team_lineup(team_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch recent lineup for a specific team.
        
        Args:
            team_id: MLB team ID
            
        Returns:
            List of lineup data or None if request fails
        """
        url = f"https://www.fangraphs.com/api/depth-charts/past-lineups"
        
        params = {
            "teamid": team_id,
            "loaddate": int(datetime.now().timestamp())
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json, text/plain, */*'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code != 200:
                logger.error(f"Request failed {response.status_code}: {url}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Request exception: {e}")
            return None
