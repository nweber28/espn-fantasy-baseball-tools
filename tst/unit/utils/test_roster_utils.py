"""
Unit tests for roster optimization utilities.
"""
import unittest
import pandas as pd
import numpy as np
from utils.roster_utils import optimize_roster, roster_to_dataframe, identify_roster_changes, prepare_players_for_optimization

class TestOptimizeRoster(unittest.TestCase):
    def setUp(self):
        # Create sample players for testing
        self.test_players = [
            {
                'name': 'Player 1',
                'positions': ['1B', 'OF'],
                'projected_points': 100,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 2',
                'positions': ['2B', 'SS'],
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
                'positions': ['SP'],
                'projected_points': 70,
                'is_pitcher': True,
                'is_hitter': False,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 5',
                'positions': ['RP'],
                'projected_points': 60,
                'is_pitcher': True,
                'is_hitter': False,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 6',
                'positions': ['C'],
                'projected_points': 50,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 7',
                'positions': ['3B'],
                'projected_points': 40,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 8',
                'positions': ['OF'],
                'projected_points': 30,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Bench Player 1',
                'positions': ['1B'],
                'projected_points': 20,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Bench Player 2',
                'positions': ['OF'],
                'projected_points': 10,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'IL Player',
                'positions': ['SP'],
                'projected_points': 85,
                'is_pitcher': True,
                'is_hitter': False,
                'injury_status': 'TEN_DAY_DL'
            }
        ]
        
        # Define roster slots
        self.test_slots = {
            'C': 1,
            '1B': 1,
            '2B': 1,
            '3B': 1,
            'SS': 1,
            'OF': 3,
            'UTIL': 1,
            'SP': 1,
            'RP': 1,
            'P': 1,
            'BN': 2
        }

    def test_optimize_roster_assigns_all_positions(self):
        """Test that optimize_roster assigns all required positions."""
        optimized_roster, _ = optimize_roster(self.test_players, self.test_slots)
        
        # Check that all required positions have the correct number of players
        for position, count in self.test_slots.items():
            if position != 'BN':  # Bench might not be fully filled
                self.assertEqual(len(optimized_roster[position]), count, 
                                f"Position {position} should have {count} players")
    
    def test_optimize_roster_handles_bench_correctly(self):
        """Test that optimize_roster correctly assigns bench players."""
        optimized_roster, _ = optimize_roster(self.test_players, self.test_slots)
        
        # Check that bench exists in the result
        self.assertIn('BN', optimized_roster, "Bench should be included in optimized roster")
        
        # Check that bench has players (up to the limit)
        self.assertLessEqual(len(optimized_roster['BN']), self.test_slots['BN'], 
                           "Bench should not exceed the specified limit")
    
    def test_optimize_roster_handles_il_correctly(self):
        """Test that optimize_roster correctly handles IL players."""
        optimized_roster, _ = optimize_roster(self.test_players, self.test_slots)
        
        # Check that IL exists in the result
        self.assertIn('IL', optimized_roster, "IL should be included in optimized roster")
        
        # Check that IL players are correctly assigned
        il_players = [p for p in self.test_players if p.get('injury_status') in ['TEN_DAY_DL', 'SUSPENSION', 'SIXTY_DAY_DL', 'OUT', 'FIFTEEN_DAY_DL']]
        self.assertEqual(len(optimized_roster['IL']), len(il_players), 
                       "All IL-eligible players should be assigned to IL")
        
        # Check that IL players are not assigned to other positions
        il_names = [p['name'] for p in il_players]
        for position, players in optimized_roster.items():
            if position != 'IL':
                for player in players:
                    self.assertNotIn(player['name'], il_names, 
                                   f"IL player {player['name']} should not be assigned to {position}")
    
    def test_optimize_roster_maximizes_points(self):
        """Test that optimize_roster maximizes projected points."""
        # Create a simple test case with clear optimal solution
        simple_players = [
            {'name': 'Best OF', 'positions': ['OF'], 'projected_points': 100, 'is_pitcher': False, 'is_hitter': True},
            {'name': 'Worst OF', 'positions': ['OF'], 'projected_points': 50, 'is_pitcher': False, 'is_hitter': True}
        ]
        simple_slots = {'OF': 1, 'BN': 1}
        
        optimized_roster, _ = optimize_roster(simple_players, simple_slots)
        
        # Check that the best player is assigned to the starting position
        self.assertEqual(optimized_roster['OF'][0]['name'], 'Best OF', 
                       "Player with highest projected points should be assigned to starting position")
        
        # Check that the worst player is assigned to bench
        self.assertEqual(optimized_roster['BN'][0]['name'], 'Worst OF', 
                       "Player with lower projected points should be assigned to bench")


class TestRosterToDataframe(unittest.TestCase):
    def test_roster_to_dataframe_includes_bench(self):
        """Test that roster_to_dataframe correctly includes bench players."""
        # Create a sample roster dictionary with bench players
        roster_dict = {
            'C': [{'name': 'Catcher', 'projected_points': 50, 'positions': ['C']}],
            '1B': [{'name': 'First Base', 'projected_points': 60, 'positions': ['1B']}],
            'BN': [
                {'name': 'Bench Player 1', 'projected_points': 40, 'positions': ['OF']},
                {'name': 'Bench Player 2', 'projected_points': 30, 'positions': ['2B']}
            ]
        }
        
        # Convert to dataframe
        df = roster_to_dataframe(roster_dict)
        
        # Check that bench players are included
        bench_rows = df[df['Position'].str.startswith('BN')]
        self.assertEqual(len(bench_rows), 2, "Dataframe should include 2 bench players")
        
        # Check bench player names
        bench_names = set(bench_rows['Player'])
        expected_names = {'Bench Player 1', 'Bench Player 2'}
        self.assertEqual(bench_names, expected_names, "Bench player names should match")
    
    def test_roster_to_dataframe_handles_empty_bench(self):
        """Test that roster_to_dataframe correctly handles empty bench."""
        # Create a sample roster dictionary with no bench players
        roster_dict = {
            'C': [{'name': 'Catcher', 'projected_points': 50, 'positions': ['C']}],
            '1B': [{'name': 'First Base', 'projected_points': 60, 'positions': ['1B']}],
            'BN': []  # Empty bench
        }
        
        # Convert to dataframe
        df = roster_to_dataframe(roster_dict)
        
        # Check that no bench players are included
        bench_rows = df[df['Position'].str.startswith('BN')]
        self.assertEqual(len(bench_rows), 0, "Dataframe should not include any bench players")
    
    def test_roster_to_dataframe_handles_missing_bench(self):
        """Test that roster_to_dataframe correctly handles missing bench key."""
        # Create a sample roster dictionary with no bench key
        roster_dict = {
            'C': [{'name': 'Catcher', 'projected_points': 50, 'positions': ['C']}],
            '1B': [{'name': 'First Base', 'projected_points': 60, 'positions': ['1B']}]
            # No 'BN' key
        }
        
        # Convert to dataframe
        df = roster_to_dataframe(roster_dict)
        
        # Check that no bench players are included
        bench_rows = df[df['Position'].str.startswith('BN')]
        self.assertEqual(len(bench_rows), 0, "Dataframe should not include any bench players")


class TestPreparePlayersForOptimization(unittest.TestCase):
    def test_prepare_players_from_dataframe(self):
        """Test that prepare_players_for_optimization correctly converts DataFrame to player list."""
        # Create a sample DataFrame
        df = pd.DataFrame({
            'Name': ['Player 1', 'Player 2'],
            'Eligible Positions': ['1B, OF', 'SS, 2B'],
            'Projected Points': [100, 90],
            'Injury Status': ['ACTIVE', 'ACTIVE']
        })
        
        # Convert to player list
        players = prepare_players_for_optimization(df)
        
        # Check that the conversion is correct
        self.assertEqual(len(players), 2, "Should have 2 players")
        
        # Check first player
        self.assertEqual(players[0]['name'], 'Player 1', "First player name should match")
        self.assertEqual(players[0]['positions'], ['1B', 'OF'], "First player positions should match")
        self.assertEqual(players[0]['projected_points'], 100, "First player points should match")
        self.assertTrue(players[0]['is_hitter'], "First player should be a hitter")
        self.assertFalse(players[0]['is_pitcher'], "First player should not be a pitcher")
        
        # Check second player
        self.assertEqual(players[1]['name'], 'Player 2', "Second player name should match")
        self.assertEqual(players[1]['positions'], ['SS', '2B'], "Second player positions should match")
        self.assertEqual(players[1]['projected_points'], 90, "Second player points should match")
        self.assertTrue(players[1]['is_hitter'], "Second player should be a hitter")
        self.assertFalse(players[1]['is_pitcher'], "Second player should not be a pitcher")
    
    def test_prepare_players_handles_missing_values(self):
        """Test that prepare_players_for_optimization correctly handles missing values."""
        # Create a sample DataFrame with missing values
        df = pd.DataFrame({
            'Name': ['Player 1', 'Player 2'],
            'Eligible Positions': ['1B, OF', None],
            'Projected Points': [100, None],
            # No Injury Status column
        })
        
        # Convert to player list
        players = prepare_players_for_optimization(df)
        
        # Check that the conversion is correct
        self.assertEqual(len(players), 2, "Should have 2 players")
        
        # Check first player
        self.assertEqual(players[0]['name'], 'Player 1', "First player name should match")
        self.assertEqual(players[0]['positions'], ['1B', 'OF'], "First player positions should match")
        self.assertEqual(players[0]['projected_points'], 100, "First player points should match")
        
        # Check second player
        self.assertEqual(players[1]['name'], 'Player 2', "Second player name should match")
        self.assertEqual(players[1]['positions'], [], "Second player positions should be empty")
        self.assertEqual(players[1]['projected_points'], 0, "Second player points should be 0")
        self.assertIsNone(players[1]['injury_status'], "Second player injury status should be None")


if __name__ == '__main__':
    unittest.main()
