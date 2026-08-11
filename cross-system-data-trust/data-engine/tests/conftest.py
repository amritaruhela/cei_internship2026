"""Pytest configuration file — adds data-engine/src to sys.path."""
import sys
from pathlib import Path

# Add data-engine and data-engine/src to sys.path
data_engine_dir = Path(__file__).parent.parent
sys.path.insert(0, str(data_engine_dir))
sys.path.insert(0, str(data_engine_dir / "src"))
