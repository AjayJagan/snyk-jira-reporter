"""Configuration loading and validation for snyk-jira-reporter."""

from typing import Any

from pydantic import ValidationError

from snyk_jira_reporter.clients.software_catalog_client import build_component_mapping, fetch_repo_mappings
from snyk_jira_reporter.config.settings import AppSettings
from snyk_jira_reporter.exceptions.exceptions import ConfigurationError
from snyk_jira_reporter.utils.file_loader import load_mapping


def load_configuration() -> AppSettings:
    """Load application settings from environment variables.

    Returns:
        Validated application settings.

    Raises:
        ConfigurationError: If required settings are missing or invalid.
    """
    try:
        return AppSettings()  # type: ignore[call-arg]
    except ValidationError as e:
        error_details = []
        for error in e.errors():
            field = error["loc"][0] if error["loc"] else "unknown"
            msg = error["msg"]
            error_details.append(f"  - {field}: {msg}")

        error_msg = "Missing or invalid required environment variables:\n"
        error_msg += "\n".join(error_details)
        raise ConfigurationError(error_msg) from e


def load_configuration_files(settings: AppSettings) -> tuple[dict[str, str], dict[str, Any]]:
    """Load and validate configuration files.

    The component mapping is fetched at runtime from the software-catalog repo
    (single source of truth); the exclude-files mapping is still a local file.

    Args:
        settings: Application settings containing catalog config and file paths.

    Returns:
        Tuple of (component_mapping, exclude_files_mapping).

    Raises:
        ConfigurationError: If the catalog fetch fails or files are invalid.
    """
    raw_mappings = fetch_repo_mappings(
        repo=settings.software_catalog_repo,
        path=settings.software_catalog_path,
        ref=settings.software_catalog_ref,
        token=settings.software_catalog_token,
    )
    components_mapping = build_component_mapping(
        raw_mappings,
        settings.software_catalog_projects.split(","),
    )

    try:
        exclude_files_mapping = load_mapping(settings.exclude_files_file_path)
    except Exception as e:
        raise ConfigurationError(f"Configuration file error: {e}") from e

    return components_mapping, exclude_files_mapping
