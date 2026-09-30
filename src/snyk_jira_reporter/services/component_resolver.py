"""Component resolution service for unmapped Jira issues."""

import logging
import re
import time
from typing import Any

from snyk_jira_reporter.clients.jira_client import JiraClient
from snyk_jira_reporter.config.constants import (
    JIRA_COMMENT_DELAY_SECONDS,
    UID_REGEX,
)
from snyk_jira_reporter.exceptions.exceptions import JiraClientError
from snyk_jira_reporter.utils.adf_parser import extract_text_from_adf

logger = logging.getLogger(__name__)


def _extract_uid_from_description(description: str | dict[str, Any] | None) -> str | None:
    """Extract UID from Jira issue description.

    Args:
        description: Jira issue description text or ADF dict.

    Returns:
        UID string if found, None otherwise.
    """
    if not description:
        return None

    # Handle both string and ADF dict format
    description_text = ""
    if isinstance(description, dict):
        # Extract text from ADF format (same logic as JiraClient)
        description_text = extract_text_from_adf(description)
    elif isinstance(description, str):
        description_text = description
    else:
        description_text = str(description) if description else ""

    # Look for UID pattern in description
    match = re.search(UID_REGEX, description_text)
    return match.group(1) if match else None


def _extract_project_from_uid(uid: str) -> str | None:
    """Extract project name from UID.

    Args:
        uid: UID in format 'prefix:project:file:branch:id'

    Returns:
        Project name if found, None otherwise.
    """
    # UID format: prefix:project:file:branch:id
    parts = uid.split(":")
    if len(parts) >= 2:
        return parts[1]  # project name is second part
    return None


def resolve_unmapped_issues(jira_client: JiraClient) -> int:
    """Resolve unmapped-repo issues by updating components based on current mappings.

    Args:
        jira_client: JiraClient instance with component mapping.

    Returns:
        Number of issues resolved.

    Raises:
        JiraClientError: If API operations fail.
    """
    logger.info("Starting unmapped issue resolution")

    # Find all unmapped-repo issues
    try:
        unmapped_issues = jira_client.search_issues_by_label("unmapped-repo")
    except JiraClientError as e:
        logger.error("Failed to search for unmapped issues: %s", e)
        raise

    if not unmapped_issues:
        logger.info("No unmapped issues found")
        return 0

    logger.info("Found %d unmapped issues to process", len(unmapped_issues))

    resolved_count = 0
    failed_count = 0

    for issue in unmapped_issues:
        issue_key = issue["key"]
        description = issue["fields"].get("description", "")

        logger.debug("Processing unmapped issue: %s", issue_key)

        # Extract project from issue description UID
        uid = _extract_uid_from_description(description)
        if not uid:
            logger.warning("Could not extract UID from issue %s, skipping", issue_key)
            failed_count += 1
            continue

        project_name = _extract_project_from_uid(uid)
        if not project_name:
            logger.warning("Could not extract project from UID in issue %s, skipping", issue_key)
            failed_count += 1
            continue

        # Look up component mapping for this project
        component = jira_client.component_mapping.get(project_name)
        if not component:
            logger.debug("No component mapping found for project '%s' in issue %s", project_name, issue_key)
            continue

        # Update the issue: add component and remove unmapped-repo label
        try:
            # Update component
            jira_client.update_issue_component(issue_key, component)

            # Rate limiting between operations
            time.sleep(JIRA_COMMENT_DELAY_SECONDS)

            # Update labels: remove unmapped-repo
            jira_client.update_issue_labels(issue_key, [], ["unmapped-repo"])

            # Rate limiting between issues
            time.sleep(JIRA_COMMENT_DELAY_SECONDS)

            resolved_count += 1
            logger.info("✓ Resolved issue %s: assigned to component '%s'", issue_key, component)

        except JiraClientError as e:
            logger.error("Failed to update issue %s: %s", issue_key, e)
            failed_count += 1
            continue

    logger.info("Unmapped issue resolution completed: %d resolved, %d failed", resolved_count, failed_count)
    return resolved_count
