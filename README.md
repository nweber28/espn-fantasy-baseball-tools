# Fantasy Baseball Analysis Tool

A Streamlit application for fantasy baseball analysis, providing tools for pitcher streaming and waiver wire analysis.

## Features

- **Pitcher Streaming**: Analyze pitcher matchups and find the best streaming options
- **Waiver Wire Analyzer**: Identify valuable players available on the waiver wire
- **Trade Evaluator**: Evaluate potential trades and their impact on your team
- **Player Search**: Search for players and view their projections

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fantasy-baseball-2025.git
cd fantasy-baseball-2025
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run 🏠_Home.py
```

## Project Structure

```
fantasy-baseball-2025/
├── 🏠_Home.py                   # Main entry point
├── config/                      # Configuration files
│   ├── constants.py             # All constants and mappings
│   └── settings.py              # App settings and configuration
├── data/                        # Data models and schemas
│   └── models.py                # Data models using dataclasses
├── services/                    # External API services
│   ├── espn_service.py          # ESPN API interactions
│   ├── fangraphs_service.py     # FanGraphs API interactions
│   └── mlb_service.py           # MLB API interactions
├── utils/                       # Utility functions
│   ├── data_processing.py       # Data transformation functions
│   ├── name_utils.py            # Player name standardization
│   ├── roster_utils.py          # Roster optimization utilities
│   ├── waiver_utils.py          # Waiver wire analysis utilities
│   └── logging_utils.py         # Logging configuration
└── pages/                       # Streamlit pages
    ├── 1_🔍_Player_Search.py    # Player search and analysis
    ├── 2_🔄_Trade_Evaluator.py  # Trade evaluation tool
    ├── 3_📈_Waiver_Wire_Analyzer.py # Waiver wire analysis
    └── 4_🚰_Pitcher_Streaming.py # Pitcher streaming analysis
```

## Usage

1. Enter your ESPN Fantasy Baseball League ID in the sidebar
2. Navigate between different analysis pages using the sidebar
3. Use the Pitcher Streaming page to find the best pitching matchups
4. Use the Waiver Wire Analyzer to find valuable free agents
5. Use the Trade Evaluator to analyze potential trades
6. Use the Player Search to find and compare players

## Performance Optimizations

The application includes several performance optimizations:

- **Vectorized operations** for faster data processing
- **Parallel data fetching** using ThreadPoolExecutor
- **Memory optimization** with appropriate data types
- **Cached name stemming** to avoid redundant calculations
- **Pre-computed lookups** for faster player matching

## Dependencies

- streamlit
- pandas
- numpy
- requests
- nltk
- unidecode
- pytz
- concurrent.futures

## License

MIT
