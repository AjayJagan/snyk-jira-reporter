import re
import requests
import os
import json
from models.models import *


def get_code_analysis_results(
    project_id: str,
    snyk_org_id: str,
    snyk_api_token: str,
    snyk_api_result_limit: str,
    snyk_rest_api_version: str,
):
    results = []
    headers = {
        "authorization": f"token {snyk_api_token}",
        "accept": "application/vnd.api+json",
    }
    rest_api_url = "https://api.snyk.io/rest"
    params = {
        "version": snyk_rest_api_version,
        "limit": snyk_api_result_limit,
        "scan_item.id": project_id,
        "scan_item.type": "project",
        "type": "code",
        "status": "open",
        "ignored": False,
    }
    api_url = rest_api_url + f"/orgs/{snyk_org_id}/issues"
    while True:
        try:
            response = requests.get(api_url, params=params, headers=headers).json()
            if response and response.get("data"):
                results += response.get("data")
            if (
                response
                and response.get("links")
                and "next" in response.get("links").keys()
            ):
                api_url = rest_api_url[:-5] + response.get("links").get("next")
                params = {}
            else:
                break
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)

    return results


def format_code_analysis_results(code_analysis_list, project_id):
    formatted_list = []
    for analysis_result in code_analysis_list:
        for cwe in analysis_result["attributes"]["classes"]:
            cwe_identifiers = []
            cwe_identifiers.append(cwe["id"])
        aggegrate_issue = AggregatedIssue(
            analysis_result["id"],
            analysis_result["attributes"]["type"],
            "",
            "",
            IssueData(
                analysis_result["id"],
                analysis_result["attributes"]["title"],
                analysis_result["attributes"]["effective_severity_level"],
                f"https://app.snyk.io/org/red-hat-openshift-data-science-rhods/project/{project_id}/#issue-{analysis_result['attributes']['key']}",
                "",
                "",
                {"CWE": cwe_identifiers, "CVE": []},
                "",
                "",
                analysis_result["attributes"]["created_at"],
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ),
            "",
            "",
            FixInfo(False, False, False, False, False, False, []),
            "",
            "",
            "",
            "",
        )
        formatted_list.append(aggegrate_issue)
    return formatted_list


def create_labels(vulnerability):
    labels = ["snyk", "security"]
    identifiers = vulnerability.get_identifiers()
    if "CVE" in identifiers and len(identifiers["CVE"]) > 0:
        labels.append("cve")
        labels += vulnerability.get_identifiers().get("CVE")
    if "CWE" in identifiers and len(identifiers["CWE"]) > 0:
        labels.append("cwe")
        labels += vulnerability.get_identifiers().get("CWE")
    if not len(identifiers["CVE"]) and not len(identifiers["CWE"]):
        labels.append("vuln")
    if vulnerability.get_issue_type() == "code":
        labels.append("code-analysis")
    if vulnerability.get_issue_type() == "vuln":
        labels.append("dependency")
    return labels


def get_jira_priority(severity: str) -> {}:
    if severity == "critical":
        return {"name": "Critical"}
    if severity == "high":
        return {"name": "Major"}
    if severity == "medium":
        return {"name": "Normal"}
    if severity == "low":
        return {"name": "Minor"}


def parse_project_name(project_name: str, branch_name: str) -> str:
    return project_name.partition(":")[0].removesuffix(f"({branch_name})")


def parse_file_name(project_name: str) -> str:
    return project_name.partition(":")[2]


def exclude_file(file_name: str, excluded_files: dict) -> bool:
    for file in excluded_files:
        if re.search(file, file_name):
            return True
    return False


def load_mapping(file_path: str) -> {}:
    try:
        root_dir = os.path.abspath(os.curdir)
        rel_file_path = os.path.join(root_dir, file_path)
        os.path.isfile(rel_file_path)
    except SystemError:
        logging.error("the file does not exists")
        sys.exit(1)

    component_maping = {}
    try:
        with open(rel_file_path) as f:
            data = f.read()
            component_maping = json.loads(data)
    except SystemError:
        logging.error("failed to load file")
        sys.exit(1)
    return component_maping
