"""Tests for the software-catalog client."""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from snyk_jira_reporter.clients.software_catalog_client import (
    build_component_mapping,
    fetch_repo_mappings,
)
from snyk_jira_reporter.exceptions.exceptions import ConfigurationError


def _encode(payload: dict) -> dict:
    """Wrap a payload the way the GitHub contents API returns it."""
    content = base64.b64encode(json.dumps(payload).encode()).decode()
    return {"content": content, "encoding": "base64"}


class TestFetchRepoMappings:
    """Tests for fetch_repo_mappings."""

    def test_missing_token_raises(self):
        """A missing token fails fast rather than making an unauthenticated call."""
        with pytest.raises(ConfigurationError, match="SOFTWARE_CATALOG_TOKEN is required"):
            fetch_repo_mappings("org/repo", "path.json", "main", token="")

    def test_fetches_and_decodes(self):
        """A successful response is base64-decoded and JSON-parsed."""
        payload = {"mappings": [{"repo": "org/repo", "jira_project": "RHOAIENG"}]}
        mock_response = MagicMock()
        mock_response.json.return_value = _encode(payload)
        mock_response.raise_for_status.return_value = None

        with patch("snyk_jira_reporter.clients.software_catalog_client._create_session") as mock_create:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response
            mock_create.return_value = mock_session

            result = fetch_repo_mappings("org/repo", "path.json", "main", token="tok")

        assert result == payload

    def test_http_error_raises_configuration_error(self):
        """A transport error is wrapped as ConfigurationError (fail-fast)."""
        with patch("snyk_jira_reporter.clients.software_catalog_client._create_session") as mock_create:
            mock_session = MagicMock()
            mock_session.get.side_effect = requests.exceptions.RequestException("boom")
            mock_create.return_value = mock_session

            with pytest.raises(ConfigurationError, match="Failed to fetch component mapping"):
                fetch_repo_mappings("org/repo", "path.json", "main", token="tok")

    def test_invalid_base64_raises(self):
        """Undecodable content raises ConfigurationError."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "!!!not-base64!!!"}
        mock_response.raise_for_status.return_value = None

        with patch("snyk_jira_reporter.clients.software_catalog_client._create_session") as mock_create:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response
            mock_create.return_value = mock_session

            with pytest.raises(ConfigurationError, match="Failed to decode"):
                fetch_repo_mappings("org/repo", "path.json", "main", token="tok")


class TestBuildComponentMapping:
    """Tests for build_component_mapping."""

    def test_filters_to_allowlist_and_builds_repo_to_component(self):
        """Only entries in the allowlist are kept, keyed by repo."""
        raw = {
            "mappings": [
                {"repo": "org/a", "jira_project": "RHOAIENG", "jira_component": "Model Serving"},
                {"repo": "org/b", "jira_project": "INFERENG", "jira_component": "llm-d"},
                {"repo": "org/c", "jira_project": "OTHER", "jira_component": "Ignored"},
            ]
        }
        result = build_component_mapping(raw, ["RHOAIENG", "INFERENG"])
        assert result == {"org/a": "Model Serving", "org/b": "llm-d"}

    def test_multi_component_repo_is_deduped_deterministically(self, caplog):
        """A repo with multiple components picks the first alphabetically and logs it."""
        raw = {
            "mappings": [
                {"repo": "org/multi", "jira_project": "RHOAIENG", "jira_component": "Zeta"},
                {"repo": "org/multi", "jira_project": "RHOAIENG", "jira_component": "Alpha"},
            ]
        }
        result = build_component_mapping(raw, ["RHOAIENG"])
        assert result == {"org/multi": "Alpha"}
        assert "multiple components" in caplog.text

    def test_skips_entries_missing_repo_or_component(self):
        """Entries without a repo or component are ignored."""
        raw = {
            "mappings": [
                {"repo": "org/a", "jira_project": "RHOAIENG", "jira_component": "Good"},
                {"jira_project": "RHOAIENG", "jira_component": "NoRepo"},
                {"repo": "org/b", "jira_project": "RHOAIENG"},
            ]
        }
        result = build_component_mapping(raw, ["RHOAIENG"])
        assert result == {"org/a": "Good"}

    def test_allowlist_entries_are_stripped(self):
        """Whitespace around allowlist entries is tolerated (comma-split input)."""
        raw = {"mappings": [{"repo": "org/a", "jira_project": "RHOAIENG", "jira_component": "C"}]}
        result = build_component_mapping(raw, [" RHOAIENG ", ""])
        assert result == {"org/a": "C"}

    def test_missing_mappings_key_raises(self):
        """A payload without a 'mappings' list is invalid."""
        with pytest.raises(ConfigurationError, match="missing a 'mappings' list"):
            build_component_mapping({"lifecycle": {}}, ["RHOAIENG"])

    def test_empty_result_raises(self):
        """An empty mapping (nothing matched the allowlist) fails fast."""
        raw = {"mappings": [{"repo": "org/a", "jira_project": "OTHER", "jira_component": "C"}]}
        with pytest.raises(ConfigurationError, match="refusing to run with an empty component mapping"):
            build_component_mapping(raw, ["RHOAIENG"])
