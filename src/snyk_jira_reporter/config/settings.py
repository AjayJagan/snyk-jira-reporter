"""Application settings loaded from environment variables via Pydantic."""

from pydantic_settings import BaseSettings

from snyk_jira_reporter.config.constants import (
    DEFAULT_CATALOG_PROJECTS,
    DEFAULT_EXCLUDE_FILES_PATH,
    DEFAULT_JIRA_LABEL_PREFIX,
    SOFTWARE_CATALOG_PATH,
    SOFTWARE_CATALOG_REF,
    SOFTWARE_CATALOG_REPO,
)


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables.

    All fields map to environment variable names (case-insensitive).
    Required fields will raise a validation error if not set.
    """

    snyk_org_id: str
    snyk_api_token: str
    jira_server: str
    jira_email: str
    jira_api_token: str
    jira_project_id: str
    jira_project_key: str = "RHOAIENG"
    jira_label_prefix: str = DEFAULT_JIRA_LABEL_PREFIX
    dry_run: bool = False
    exclude_files_file_path: str = DEFAULT_EXCLUDE_FILES_PATH

    # Software catalog: single source of truth for repo → Jira component mapping.
    software_catalog_repo: str = SOFTWARE_CATALOG_REPO
    software_catalog_path: str = SOFTWARE_CATALOG_PATH
    software_catalog_ref: str = SOFTWARE_CATALOG_REF
    software_catalog_token: str = ""
    software_catalog_projects: str = DEFAULT_CATALOG_PROJECTS

    model_config = {"env_file": ".env"}
