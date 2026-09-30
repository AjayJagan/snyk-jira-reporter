"""Client for fetching the repo → Jira component mapping from software-catalog.

The `opendatahub-io/software-catalog` repo publishes an auto-updated
`repo_mappings.json` that is the single source of truth for which Jira component
owns each repository. The repo is internal, so the file is fetched at runtime via
the authenticated GitHub contents API.
"""

import base64
import binascii
import json
import logging
from collections.abc import Iterable
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from snyk_jira_reporter.config.constants import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    GITHUB_API_BASE_URL,
    HTTP_RETRY_BACKOFF_FACTOR,
    HTTP_RETRY_STATUS_CODES,
    HTTP_RETRY_TOTAL,
)
from snyk_jira_reporter.exceptions.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def _create_session(headers: dict[str, str]) -> requests.Session:
    """Create a requests session with retry logic for transient failures.

    Retries on 429 (rate limited) and 5xx errors with exponential backoff.
    """
    session = requests.Session()
    session.headers.update(headers)
    retry = Retry(
        total=HTTP_RETRY_TOTAL,
        backoff_factor=HTTP_RETRY_BACKOFF_FACTOR,
        status_forcelist=list(HTTP_RETRY_STATUS_CODES),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_repo_mappings(repo: str, path: str, ref: str, token: str) -> dict[str, Any]:
    """Fetch and parse repo_mappings.json from the software-catalog repo.

    Uses the GitHub contents API, which works for internal/private repos when
    given a token with ``contents:read`` on the target repo.

    Args:
        repo: Catalog repo in ``org/name`` form.
        path: Path to the mappings file within the repo.
        ref: Git ref (branch/tag/sha) to read from.
        token: GitHub token with read access to the (internal) catalog repo.

    Returns:
        Parsed JSON payload (expected keys: ``mappings``, ``lifecycle``).

    Raises:
        ConfigurationError: If the token is missing or the fetch/parse fails.
            Fail-fast is deliberate: there is no local fallback, so proceeding
            on an empty mapping would unmap every repository.
    """
    if not token:
        raise ConfigurationError(
            "SOFTWARE_CATALOG_TOKEN is required to read the internal "
            f"'{repo}' repo. Set it in the environment (or .env for dev runs)."
        )

    url = f"{GITHUB_API_BASE_URL}/repos/{repo}/contents/{path}"
    session = _create_session(
        {
            "authorization": f"Bearer {token}",
            "accept": "application/vnd.github+json",
            "x-github-api-version": "2022-11-28",
        }
    )

    try:
        response = session.get(url, params={"ref": ref}, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as e:
        raise ConfigurationError(f"Failed to fetch component mapping from '{repo}/{path}@{ref}': {e}") from e
    except ValueError as e:
        raise ConfigurationError(f"GitHub API returned invalid JSON for '{repo}/{path}': {e}") from e

    try:
        content = base64.b64decode(payload["content"])
        return json.loads(content)  # type: ignore[no-any-return]
    except (KeyError, binascii.Error, ValueError) as e:
        raise ConfigurationError(f"Failed to decode component mapping from '{repo}/{path}': {e}") from e


def build_component_mapping(raw: dict[str, Any], allowed_projects: Iterable[str]) -> dict[str, str]:
    """Build a ``{repo: component}`` mapping from the raw catalog payload.

    Filters to entries whose ``jira_project`` is in ``allowed_projects``. When a
    repo appears under multiple components, the first alphabetically is chosen
    deterministically and the collision is logged (rather than raising) — a few
    catalog repos legitimately span components and must not crash the build.

    Args:
        raw: Parsed catalog payload (from :func:`fetch_repo_mappings`).
        allowed_projects: Jira project keys to include (e.g. RHOAIENG).

    Returns:
        Mapping of ``org/repo`` → Jira component name.

    Raises:
        ConfigurationError: If the payload shape is invalid or no entries match
            the allowlist (an empty mapping would unmap every repository).
    """
    allowed = {p.strip() for p in allowed_projects if p.strip()}

    mappings = raw.get("mappings")
    if not isinstance(mappings, list):
        raise ConfigurationError("Catalog payload missing a 'mappings' list")

    # Collect all candidate components per repo, then resolve deterministically.
    candidates: dict[str, set[str]] = {}
    for entry in mappings:
        if entry.get("jira_project") not in allowed:
            continue
        repo = entry.get("repo")
        component = entry.get("jira_component")
        if not repo or not component:
            continue
        candidates.setdefault(repo, set()).add(component)

    mapping: dict[str, str] = {}
    for repo, components in candidates.items():
        chosen = sorted(components)[0]
        if len(components) > 1:
            logger.warning(
                "Repo '%s' maps to multiple components %s; using '%s'",
                repo,
                sorted(components),
                chosen,
            )
        mapping[repo] = chosen

    if not mapping:
        raise ConfigurationError(
            f"No catalog entries matched the project allowlist {sorted(allowed)}; "
            "refusing to run with an empty component mapping."
        )

    logger.info("Loaded %d repo → component mappings from software-catalog", len(mapping))
    return mapping
