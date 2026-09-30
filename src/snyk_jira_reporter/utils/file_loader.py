"""Configuration file loading utilities."""

import json
import logging
import os
from typing import Any

from snyk_jira_reporter.exceptions.exceptions import FileLoadError

logger = logging.getLogger(__name__)


def load_mapping(file_path: str) -> dict[str, Any]:
    """Load a JSON mapping file from the given path.

    The path is resolved relative to the current working directory.

    Args:
        file_path: Relative or absolute path to the JSON file.

    Returns:
        Parsed JSON content as a dictionary.

    Raises:
        FileLoadError: If the file does not exist or contains invalid JSON.
    """
    root_dir = os.path.abspath(os.curdir)
    resolved_path = os.path.join(root_dir, file_path)

    if not os.path.isfile(resolved_path):
        raise FileLoadError(f"Configuration file not found: {resolved_path}")

    try:
        with open(resolved_path, encoding="utf-8") as f:
            return json.loads(f.read())  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        raise FileLoadError(f"Invalid JSON in {resolved_path}: {e}") from e
    except OSError as e:
        raise FileLoadError(f"Failed to read {resolved_path}: {e}") from e
