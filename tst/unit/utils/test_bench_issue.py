"""
Unit test to debug the "No bench players available" issue.
"""
import unittest
import pandas as pd
import numpy as np
from utils.roster_utils import optimize_roster

class TestBenchIssue(unittest.TestCase):
    def test_bench_players_assignment(self):
        """Test that optimize_roster correctly assigns bench players."""
        # Create a test roster with more players than starting positions
        test_players = [
            {
                'name': 'Player 1',
                'positions': ['1B'],
                'projected_points': 100,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 2',
                'positions': ['1B'],
                'projected_points': 90,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 3',
                'positions': ['OF'],
                'projected_points': 80,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 4',
                'positions': ['OF'],
                'projected_points': 70,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            }
        ]
        
        # Define roster slots with fewer positions than players
        test_slots = {
            '1B': 1,
            'OF': 1,
            'BN': 2  # Explicitly define bench slots
        }
        
        # Run the optimization
        optimized_roster, _ = optimize_roster(test_players, test_slots)
        
        # Check that bench exists in the result
        self.assertIn('BN', optimized_roster, "Bench should be included in optimized roster")
        
        # Check that bench has the expected number of players
        self.assertEqual(len(optimized_roster['BN']), 2, 
                       "Bench should have 2 players")
        
        # Check that the bench has the lower-projected players
        bench_names = [player['name'] for player in optimized_roster['BN']]
        self.assertIn('Player 2', bench_names, "Player 2 should be on the bench")
        self.assertIn('Player 4', bench_names, "Player 4 should be on the bench")
        
        # Print the optimized roster for debugging
        print("Optimized Roster:")
        for position, players in optimized_roster.items():
            print(f"{position}: {[player['name'] for player in players]}")
    
    def test_bench_players_with_default_slots(self):
        """Test bench players assignment with default roster slots."""
        # Create a test roster with more players than starting positions
        test_players = [
            {
                'name': 'Player 1',
                'positions': ['1B'],
                'projected_points': 100,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 2',
                'positions': ['1B'],
                'projected_points': 90,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 3',
                'positions': ['OF'],
                'projected_points': 80,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 4',
                'positions': ['OF'],
                'projected_points': 70,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            }
        ]
        
        # Define roster slots with fewer positions than players but no explicit BN
        test_slots = {
            '1B': 1,
            'OF': 1
            # No explicit BN key
        }
        
        # Run the optimization
        optimized_roster, _ = optimize_roster(test_players, test_slots)
        
        # Check that bench exists in the result
        self.assertIn('BN', optimized_roster, "Bench should be included in optimized roster even without explicit BN key")
        
        # Print the optimized roster for debugging
        print("Optimized Roster (Default Slots):")
        for position, players in optimized_roster.items():
            print(f"{position}: {[player['name'] for player in players]}")

if __name__ == '__main__':
    unittest.main()
