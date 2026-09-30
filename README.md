# Snyk to Jira Reporter

Automated tool that scans Snyk for security vulnerabilities and creates/manages Jira tickets. Runs as a GitHub Actions workflow on a weekly schedule to keep your Jira project synchronized with your Snyk security findings.

##What This Tool Does

1. **Scans Snyk Projects**: Fetches all monitored projects from your Snyk organization
2. **Finds Vulnerabilities**: Discovers SAST (code analysis) and dependency vulnerabilities
3. **Creates Jira Issues**: Automatically creates Jira bug tickets for new high/critical vulnerabilities
4. **Manages Issue Lifecycle**: Closes Jira tickets when vulnerabilities are resolved in Snyk
5. **Maps to Components**: Assigns Jira issues to the correct component team using configurable mappings
6. **Provides Detailed Context**: For SAST issues, shows exact source file and line number information

##Quick Start

### Prerequisites

- Python 3.10+
- Snyk API token with org access
- Jira Cloud API token with project access
- Access to RHOAIENG Jira project

### Installation

```bash
# Install the package
pip install -e .

# For development
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Run with dry-run (recommended first time)
DRY_RUN=true python -m snyk_jira_reporter --disable-dep-analysis

# Run for real (creates actual Jira issues)
python -m snyk_jira_reporter --disable-dep-analysis
```

##Step-by-Step Setup

### 1. Get Required API Tokens

**Snyk API Token:**
1. Go to [Snyk Account Settings](https://app.snyk.io/account)
2. Generate a new API token
3. Note your organization ID from the URL: `https://app.snyk.io/org/{ORG_ID}`

**Jira API Token:**
1. Go to [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Create a new API token
3. Note your email address for authentication

### 2. Configure Environment Variables

Create a `.env` file (ignored by git):

```bash
# Snyk Configuration
SNYK_ORG_ID=your-snyk-org-id-here
SNYK_API_TOKEN=your-snyk-token-here

# Jira Configuration
JIRA_SERVER=https://redhat.atlassian.net
JIRA_EMAIL=your-email@redhat.com
JIRA_API_TOKEN=your-jira-token-here
JIRA_PROJECT_ID=your-jira-project-id
JIRA_PROJECT_KEY=RHOAIENG

# Software catalog (component mapping source of truth)
# Requires read access to the internal opendatahub-io/software-catalog repo.
SOFTWARE_CATALOG_TOKEN=your-github-token-here
SOFTWARE_CATALOG_PROJECTS=RHOAIENG,INFERENG,RHAIENG

# Optional Configuration
DRY_RUN=true
JIRA_LABEL_PREFIX=snyk-jira-integration:
EXCLUDE_FILES_FILE_PATH=./config/exclude_files.json
```

### 3. Test Your Configuration

```bash
# Test with dry-run to validate setup
DRY_RUN=true python -m snyk_jira_reporter --allowed-severity critical --disable-dep-analysis
```

Look for output like:
```
INFO:root:DRY_RUN is enabled
INFO:root:Processing project: red-hat-data-services/your-repo(main)
INFO:snyk_jira_reporter.clients.jira_client:DRY RUN: X issue(s) would be created
```

##Configuration Guide

### Component Mappings

Repository → Jira component mappings are **no longer maintained in this repo**. They are
fetched at runtime from the internal
[`opendatahub-io/software-catalog`](https://github.com/opendatahub-io/software-catalog) repo
(`.claude/skills/software-catalog-query/references/repo_mappings.json`), which is the single
source of truth and auto-updates.

**To add or change a repository's component**, update the mapping in the software-catalog repo.
The change propagates automatically on the next run — no change is needed here.

Only entries whose `jira_project` is in `SOFTWARE_CATALOG_PROJECTS` (default
`RHOAIENG,INFERENG,RHAIENG`) are used. Fetching requires `SOFTWARE_CATALOG_TOKEN` with
`contents:read` on the (internal) catalog repo; the run fails fast if the fetch fails, rather
than proceeding with an empty mapping.

### File Exclusions

To exclude specific files from vulnerability scanning, edit `config/exclude_files.json`:

```json
{
    "red-hat-data-services/your-repo": [
        "^vendor/",
        "^node_modules/",
        "^tests/",
        "\\.test\\.",
        "\\.spec\\."
    ]
}
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `-s, --allowed-severity` | Severities to include (critical,high,medium,low) | `critical,high` |
| `-l, --limit` | Snyk API results per page | `100` |
| `-v, --version` | Snyk REST API version | `2024-01-23` |
| `--disable-dep-analysis` | Skip dependency scanning (SAST only) | `false` |

**Examples:**

```bash
# Only critical vulnerabilities
python -m snyk_jira_reporter --allowed-severity critical

# Include medium severity
python -m snyk_jira_reporter --allowed-severity critical,high,medium

# SAST only (recommended for faster runs)
python -m snyk_jira_reporter --disable-dep-analysis
```

##Understanding SAST Source File Feature

For Static Application Security Testing (SAST) issues, this tool provides enhanced context:

**Jira Issue Title:**
```
Snyk - [CWE-23] - [high] - [main] - red-hat-data-services/odh-dashboard - packages/gen-ai/bff/internal/api/openapi_handler.go - Path Traversal
```
↑ Shows actual source file, not just project file

**Jira Issue Description:**
```
Found vulnerability in red-hat-data-services/odh-dashboard project, in file ,

Source file: packages/gen-ai/bff/internal/api/openapi_handler.go (line 42)

in branch main.
```
↑ Includes exact file path and line number

This helps developers:
- Quickly identify which file contains the vulnerability
- Jump directly to the problematic code location
- Understand the context and severity of the security issue

##Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SNYK_ORG_ID` | Yes | - | Snyk organization ID (UUID) |
| `SNYK_API_TOKEN` | Yes | - | Snyk API authentication token |
| `JIRA_SERVER` | Yes | - | Jira server URL (e.g., https://redhat.atlassian.net) |
| `JIRA_EMAIL` | Yes | - | Your email for Jira authentication |
| `JIRA_API_TOKEN` | Yes | - | Jira API token from Atlassian |
| `JIRA_PROJECT_ID` | Yes | - | Jira project ID for issue creation |
| `JIRA_PROJECT_KEY` | No | `RHOAIENG` | Jira project key for JQL queries |
| `JIRA_LABEL_PREFIX` | No | `snyk-jira-integration:` | Prefix for tracking labels |
| `DRY_RUN` | No | `false` | If `true`, shows what would happen without creating issues |
| `SOFTWARE_CATALOG_TOKEN` | Yes | - | GitHub token with `contents:read` on the internal software-catalog repo |
| `SOFTWARE_CATALOG_PROJECTS` | No | `RHOAIENG,INFERENG,RHAIENG` | Jira project keys to include from the catalog |
| `EXCLUDE_FILES_FILE_PATH` | No | `./config/exclude_files.json` | File exclusion config |

##Development Guide

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=snyk_jira_reporter tests/

# Run specific test file
pytest tests/test_clients/test_jira_client.py -v

# Run tests matching pattern
pytest tests/ -k "test_source_file" -v
```

### Code Quality

```bash
# Lint code
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Type checking
mypy src/
```

### Testing Your Changes

1. **Use dry-run mode**: Always test with `DRY_RUN=true` first
2. **Test with a small subset**: Filter to specific repos during development
3. **Check the logs**: Verify your changes work as expected
4. **Run the test suite**: Ensure you haven't broken existing functionality

```bash
# Test your changes
DRY_RUN=true python -m snyk_jira_reporter --allowed-severity critical
```

##Troubleshooting

### Common Issues

**"No component mapping found for repo 'org/repo'"**
- Add the repository to the mapping in the internal `opendatahub-io/software-catalog` repo
- Verify the repository name format matches exactly (`org/repo`, case-sensitive)

**"Authentication failed - check JIRA_EMAIL and JIRA_API_TOKEN"**
- Verify your Jira email address is correct
- Regenerate your Jira API token
- Check that you have access to the RHOAIENG project

**"Reached max page limit (100) for JQL query"**
- This is normal for large projects with many existing issues
- The tool handles this automatically and continues processing

**"Could not extract UID from Jira issue"**
- This indicates an existing Jira issue wasn't created by this tool
- These issues are safely ignored

### Getting Help

1. **Check the logs**: The tool provides detailed logging about what it's doing
2. **Use dry-run mode**: Test changes safely with `DRY_RUN=true`
3. **Validate your config**: Ensure all required environment variables are set
4. **Test API access**: Verify you can access both Snyk and Jira manually

### Debug Mode

For more detailed logging:

```bash
# Enable debug logging
PYTHONPATH=src python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from snyk_jira_reporter.__main__ import main
main()
" --disable-dep-analysis
```

##Project Structure

```
src/snyk_jira_reporter/
├── __main__.py               # CLI entry point
├── config/
│   ├── settings.py          # Pydantic settings (environment variables)
│   └── constants.py         # Named constants and defaults
├── models/
│   ├── vulnerability.py     # VulnerabilityData model (Jira issue creation)
│   └── snyk_models.py       # Snyk API response models
├── clients/
│   ├── snyk_client.py       # Snyk REST API client
│   └── jira_client.py       # Jira Cloud v3 API client
├── services/
│   └── vulnerability_service.py  # Core processing logic
├── utils/
│   ├── labels.py            # Jira label/priority utilities
│   ├── parsing.py           # Project name parsing helpers
│   └── file_loader.py       # JSON config file loading
└── exceptions/
    └── exceptions.py        # Custom exception hierarchy

config/
└── exclude_files.json           # File exclusion patterns
                                 # (component mapping is fetched from software-catalog)

.github/workflows/
├── jira-snyk.yaml               # Weekly scheduled run
└── ci.yaml                      # Pull request validation
```

##GitHub Actions

### Weekly Scheduled Run (`.github/workflows/jira-snyk.yaml`)

- **When**: Every Monday at 5 AM UTC
- **What**: Scans all monitored Snyk projects and updates Jira
- **Environment**: Production environment with real API tokens
- **Notifications**: GitHub will notify on failures

### CI Pipeline (`.github/workflows/ci.yaml`)

- **When**: Every push and pull request
- **What**: Runs linting, type checking, and tests
- **Purpose**: Ensures code quality and prevents regressions

##API Compatibility

This tool uses:
- **Jira Cloud REST API v3** (latest, fully compatible with Jira Cloud)
- **Snyk REST API v2024-01-23** (current stable version)

All endpoints are current and supported as of 2024. The tool includes backward compatibility for existing Jira issues created with previous versions.

---

##Example Workflow: Adding a New Repository

Repository → component mappings live in the internal
[`opendatahub-io/software-catalog`](https://github.com/opendatahub-io/software-catalog) repo,
not here. To onboard a new repository:

1. **Ensure it is monitored in Snyk** (part of the RHOAI Snyk org).
2. **Add its component mapping** in the software-catalog repo's `repo_mappings.json`.
3. **Confirm its Jira project** is in `SOFTWARE_CATALOG_PROJECTS` (default `RHOAIENG,INFERENG,RHAIENG`).
4. That's it — the mapping propagates automatically on the next scheduled run.

Until a repository has a mapping in the catalog, its issues are created without a component and
labeled `unmapped-repo`; they are re-componented automatically once the mapping appears.

Need help? Check the troubleshooting section above or reach out to the team!

