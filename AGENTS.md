# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

This is the **Snyk to Jira Reporter** - an automated security vulnerability management tool used by the Red Hat OpenShift AI Engineering (RHOAIENG) team. It syncs Snyk security findings with Jira tickets, creating/managing bug reports for high/critical vulnerabilities across monitored repositories.

## Development Commands

### Environment Setup
```bash
# Requires Python 3.9+ (see pyproject.toml)

# Install package in development mode
pip install -e .

# Install with development dependencies (testing, linting, type checking)
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests with coverage report
pytest --cov=snyk_jira_reporter tests/

# Run specific test file with verbose output
pytest tests/test_clients/test_jira_client.py -v

# Run tests matching a pattern
pytest tests/ -k "test_source_file" -v
```

### Code Quality
```bash
# Lint code (checks for errors, style issues)
ruff check src/ tests/

# Format code (auto-formats to project style)
ruff format src/ tests/

# Type checking (strict mode enabled)
mypy src/
```

### Running the Tool
```bash
# ALWAYS test with dry run first
DRY_RUN=true python -m snyk_jira_reporter --disable-dep-analysis

# Production run (creates real Jira issues)
python -m snyk_jira_reporter --disable-dep-analysis

# Filter by severity levels
python -m snyk_jira_reporter --allowed-severity critical,high,medium

# Include dependency scanning (slower, usually disabled)
python -m snyk_jira_reporter --allowed-severity critical

# Resolve existing unmapped issues (automatic during normal runs)
# Note: Unmapped resolution happens automatically in Phase 3 of every execution
```

## Architecture

### Core Components

**Entry Point**: `src/snyk_jira_reporter/__main__.py`
- CLI argument parsing
- Environment variable validation via Pydantic
- Client initialization and orchestration

**API Clients**: `src/snyk_jira_reporter/clients/`
- `snyk_client.py` - Snyk REST API v2024-01-23 integration
- `jira_client.py` - Jira Cloud REST API v3 integration
- `software_catalog_client.py` - Fetches the repo → component mapping from the internal software-catalog repo (single source of truth)

**Core Processing**: `src/snyk_jira_reporter/services/`
- `vulnerability_service.py` - Main business logic for processing Snyk projects
- `component_resolver.py` - Resolves unmapped Jira issues by updating components based on current mappings
- Vulnerability filtering and mapping
- Jira issue lifecycle management (create/update/close)

**Configuration**: `src/snyk_jira_reporter/config/`
- `settings.py` - Pydantic settings loaded from environment variables
- `constants.py` - Named constants and defaults

**Data Models**: `src/snyk_jira_reporter/models/`
- `snyk_models.py` - Snyk API response models
- `vulnerability.py` - VulnerabilityData model for Jira issue creation

**Utilities**: `src/snyk_jira_reporter/utils/`
- `file_loader.py` - JSON configuration file loading utilities
- `labels.py` - Jira label and priority conversion utilities
- `parsing.py` - Project name parsing helpers

### Configuration Files

**Repository-to-Component Mapping**: fetched at runtime from the internal
`opendatahub-io/software-catalog` repo (`.Codex/skills/software-catalog-query/references/repo_mappings.json`)
- Single source of truth; auto-updated by the catalog's own CI. Not maintained in this repo.
- `software_catalog_client.py` fetches it (GitHub contents API) and builds `{org/repo: component}`,
  filtered to the `SOFTWARE_CATALOG_PROJECTS` allowlist. Fails fast if the fetch fails.
- To add/change a repo's component, edit the mapping in the software-catalog repo.

**File Exclusions**: `config/exclude_files.json`
- Regex patterns to exclude files from vulnerability scanning
- Organized by repository

### Environment Variables

Required for operation (all loaded via `AppSettings`):
- `SNYK_ORG_ID`, `SNYK_API_TOKEN` - Snyk API access
- `JIRA_SERVER`, `JIRA_EMAIL`, `JIRA_API_TOKEN` - Jira API access  
- `JIRA_PROJECT_ID` - Target Jira project for issue creation
- `JIRA_PROJECT_KEY` - For JQL queries (defaults to "RHOAIENG")
- `SOFTWARE_CATALOG_TOKEN` - GitHub token with `contents:read` on the internal software-catalog repo
- `SOFTWARE_CATALOG_PROJECTS` - Jira project allowlist (defaults to "RHOAIENG,INFERENG,RHAIENG")
- `DRY_RUN=true` - Safe mode for testing (no real Jira changes)

## Development Workflow

### Making Configuration Changes

**Adding a new repository to component mapping:**
- Component mappings are not maintained here. Add/change the repo's mapping in the internal
  `opendatahub-io/software-catalog` repo's `repo_mappings.json`; it propagates automatically.
- Ensure the repo's Jira project is within `SOFTWARE_CATALOG_PROJECTS` (defaults to
  "RHOAIENG,INFERENG,RHAIENG").

### Testing Guidelines

- **Always use dry run mode first**: `DRY_RUN=true`
- **Verify API access**: Ensure Snyk, Jira, and software-catalog tokens work
- **Run full test suite**: `pytest --cov=snyk_jira_reporter tests/`

### CI Pipeline

**Pull Request Validation** (`.github/workflows/ci.yaml`):
- Linting with ruff
- Type checking with mypy
- Test suite execution with coverage

**Production Run** (`.github/workflows/jira-snyk.yaml`):
- Weekly scheduled execution (Mondays 5 AM UTC)
- Real API tokens from GitHub secrets
- Processes all monitored Snyk projects

## Key Features

**SAST Source File Context**: For Static Application Security Testing findings, the tool provides enhanced Jira issue details including exact source file paths and line numbers, not just project-level information.

**Vulnerability Lifecycle Management**: Automatically creates Jira issues for new vulnerabilities and closes them when resolved in Snyk.

**Component Assignment**: Uses configurable mapping to assign Jira issues to correct component teams based on repository ownership.

**Unmapped Repository Resolution**: Automatically resolves previously unmapped repositories by updating existing Jira issues when the software-catalog mapping gains coverage for them.

## Common Tasks

**Adding a new repository to monitoring:**
1. Ensure repository is monitored in Snyk
2. Add its component mapping in the `opendatahub-io/software-catalog` repo
3. Test with dry run

**Debugging issues:**
- Check logs for API authentication failures (Snyk, Jira, and software-catalog token)
- Verify repository names match exactly (case-sensitive)
- Use dry run mode to test changes safely

**Checking unmapped repositories:**
- Unmapped repos surface as warnings in the run logs and as Jira issues labeled `unmapped-repo`.
- To fix, add the missing repo to the software-catalog mapping; the next run re-components its issues.