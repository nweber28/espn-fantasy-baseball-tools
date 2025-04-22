# Fantasy Baseball Analysis Tool

A Streamlit application for fantasy baseball analysis, providing tools for pitcher streaming and waiver wire analysis.

## Features

- **Pitcher Streaming**: Analyze pitcher matchups and find the best streaming options
- **Waiver Wire Analyzer**: Identify valuable players available on the waiver wire

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
streamlit run Home.py
```

## Project Structure

```
fantasy-baseball-2025/
├── Home.py                      # Main entry point
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
│   └── logging_utils.py         # Logging configuration
└── pages/                       # Streamlit pages
    ├── 🚰_Pitcher_Streaming.py  # Pitcher streaming analysis
    └── 📈_Waiver_Wire_Analyzer.py # Waiver wire analysis
```

## Usage

1. Enter your ESPN Fantasy Baseball League ID in the sidebar
2. Navigate between different analysis pages using the sidebar
3. Use the Pitcher Streaming page to find the best pitching matchups
4. Use the Waiver Wire Analyzer to find valuable free agents

## Dependencies

- streamlit
- pandas
- requests
- nltk
- unidecode
- pytz

## License

MIT
