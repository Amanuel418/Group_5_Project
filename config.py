"""
Configuration module for Library Management System
Provides shared database path that works regardless of execution directory
"""
import os
from pathlib import Path

# Get the directory where this config file is located
BASE_DIR = Path(__file__).parent.absolute()

# Database path - always relative to this module's location
DB_PATH = str(BASE_DIR / "library.db")

