# JIRA SNYK AUTOMATION SCRIPTS IN GITHUB ACTIONS

## Motivation
Snyk is a security tool which scans the code, finds the vulnerabilities and posts the result. In our team, we use JIRA to track all issues to tackle. Snyk doesnot provide out-of-the-box support of automatically creating JIRAs. So the purpose of this repository is to provide the capability to automatically generate JIRAs from the scan results.
## How to use it?
This is a GitHub Actions workflow that runs on all Snyk projects. It runs on a schedule(cron job) so that the scan results are periodically converted to JIRAs.

### Required Environment Variables

The following environment variables need to be configured for the script to work:

#### Secrets (configure in GitHub Actions or locally):
  * `SNYK_API_TOKEN` - Your Snyk API token for authentication
  * `JIRA_API_TOKEN` - Your Jira API token (generate at https://id.atlassian.com/manage-profile/security/api-tokens)
  * `JIRA_EMAIL` - Your Atlassian account email address (required for Jira Cloud authentication)

#### Jira Configuration:
  * `JIRA_SERVER` - Your Jira server URL (e.g., `https://uat-1-1-redhat.atlassian.net`)
  * `JIRA_PROJECT_ID` - Your Jira project key (e.g., `RHOAIENG`)
  * `JIRA_LABEL_PREFIX` - (Optional) Label prefix for tracking issues (default: `snyk-jira-integration:`)

#### Snyk Configuration:
  * `SNYK_ORG_ID` - Your Snyk organization ID

#### Other:
  * `DRY_RUN` - Set to `true` to test without creating actual Jira issues (default: `false`)
  * `COMPONENT_MAPPING_FILE_PATH` - (Optional) Path to component mapping file (default: `./config/jira_components_mapping.json`)
  * `EXCLUDE_FILES_FILE_PATH` - (Optional) Path to exclude files config (default: `./config/exclude_files.json`)

### Local Development

Create a `.env` file in the project root:
```bash
SNYK_API_TOKEN=your_snyk_token_here
JIRA_API_TOKEN=your_jira_api_token_here
JIRA_EMAIL=your.email@example.com
JIRA_SERVER=https://uat-1-1-redhat.atlassian.net
JIRA_PROJECT_ID=RHOAIENG
SNYK_ORG_ID=ed870ef2-8f76-4ea1-ad4b-dacfa225eb69
DRY_RUN=true
```

### Excluding Files

In case you need to exclude folders, insert regex in `exclude_files.json` in format:
```json
{
    "opendatahub/opendatahub-operator": ["^modules/.*/vendor"],
    "repo_name": ["Array", "of", "path_regex_to_ignore"]
}
```

