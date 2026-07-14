import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import pytest
from core.state import init_db


@pytest.fixture(autouse=True)
def setup_db():
    """Ensure SQLite tables exist for every test."""
    init_db()
    yield
    # Clean up the db file after tests so tests are isolated
    db_path = "db/taskpilot.db"
    if os.path.exists(db_path):
        os.remove(db_path)
