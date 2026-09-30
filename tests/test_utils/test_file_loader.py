"""Tests for file loading utilities."""

import json
import os

import pytest

from snyk_jira_reporter.exceptions.exceptions import FileLoadError
from snyk_jira_reporter.utils.file_loader import load_mapping


class TestLoadMapping:
    """Tests for load_mapping function."""

    def test_load_valid_json(self, tmp_path):
        """Test loading a valid JSON file."""
        data = {"key": "value", "nested": {"a": 1}}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data))

        result = load_mapping(str(json_file))
        assert result == data

    def test_file_not_found_raises_error(self):
        """Test that a missing file raises FileLoadError."""
        with pytest.raises(FileLoadError, match="not found"):
            load_mapping("/nonexistent/path/file.json")

    def test_invalid_json_raises_error(self, tmp_path):
        """Test that invalid JSON raises FileLoadError."""
        json_file = tmp_path / "bad.json"
        json_file.write_text("{ invalid json }")

        with pytest.raises(FileLoadError, match="Invalid JSON"):
            load_mapping(str(json_file))

    def test_load_actual_config_files(self):
        """Test loading the actual project config files."""
        # This test verifies the real config files are valid JSON
        config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
        exclude_path = os.path.join(config_dir, "exclude_files.json")
        if os.path.exists(exclude_path):
            result = load_mapping(exclude_path)
            assert isinstance(result, dict)
            assert len(result) > 0
