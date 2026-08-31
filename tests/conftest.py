"""Pytest configuration and fixtures."""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        yield repo


@pytest.fixture
def sample_python_repo(temp_repo):
    """Create a sample Python repository."""
    (temp_repo / "main.py").write_text('''
def hello():
    return "world"

class MyClass:
    def method(self):
        return 42
''')
    (temp_repo / "requirements.txt").write_text("requests==2.25.1\n")
    return temp_repo


@pytest.fixture
def sample_js_repo(temp_repo):
    """Create a sample JavaScript repository."""
    (temp_repo / "package.json").write_text('''{
  "name": "test",
  "dependencies": {"express": "^4.18.0"}
}''')
    (temp_repo / "index.js").write_text('const express = require("express");')
    return temp_repo


@pytest.fixture(autouse=True)
def cleanup_cache():
    """Clean up cache after each test."""
    yield
    import shutil
    cache_dirs = ['.cache', '__pycache__', '.pytest_cache']
    for d in cache_dirs:
        p = Path(d)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)