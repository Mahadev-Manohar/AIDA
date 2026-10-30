import pandas as pd
from typing import Optional
import os

# Global variables to store the loaded DataFrame and file information
df: Optional[pd.DataFrame] = None
file_path: Optional[str] = None

# Directory where generated charts will be saved
CHARTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "charts"))

def init_charts_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)
