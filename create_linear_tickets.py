#!/usr/bin/env python3
"""
Bulk create Linear tickets from lichess_tickets.json.

This script reads the ticket definitions and creates them in Linear with proper:
- Labels (phase labels, feature labels)
- Dependencies (blocking relationships)
- Priorities
- Descriptions with spec_refs links

Usage:
    python create_linear_tickets.py --dry-run        # Preview what would be created
    python create_linear_tickets.py --phase phase-0  # Create only phase-0 tickets
    python create_linear_tickets.py                  # Create all tickets

Environment:
    LINEAR_API_KEY - Required Linear API key

Assumes linear_utils.py functions are available in the autonomous harness.
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from typing import TypedDict

import httpx

# === Configuration ===

LINEAR_API_URL = "https://api.linear.app/graphql"

# Team UUID for Chess
TEAM_ID = "a26977e4-900b-482c-b52d-d75430ecdf2c"

# Default project (optional - create a Lichess project if desired)
PROJECT_NAME = "Lichess Clone"

# Workflow state for new tickets
DEFAULT_STATE = "Backlog"

# GitHub repo base URL for spec_refs links
GITHUB_SPECS_URL = "https://github.com/dustycyanide/vibefaster/blob/main/django_react_shipfast/lichess_specs"

# Rate limiting - Linear has limits, so we add delays
RATE_LIMIT_DELAY = 0.5  # seconds between requests

# Priority mapping (JSON uses 1=Critical, 2=High, 3=Medium, 4=Low)
# Linear uses: 0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low
PRIORITY_MAP = {
    1: 1,  # Critical -> Urgent
    2: 2,  # High -> High
    3: 3,  # Medium -> Normal
    4: 4,  # Low -> Low
}


class TicketResult(TypedDict):
    json_id: str
    linear_id: str
    identifier: str
    url: str


# === Linear API Functions ===

def _get_api_key() -> str:
    """Get Linear API key from environment."""
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        raise ValueError("LINEAR_API_KEY environment variable not set")
    return api_key


def _graphql_request(query: str, variables: dict | None = None) -> dict:
    """Make a GraphQL request to Linear API."""
    headers = {
        "Authorization": _get_api_key(),
        "Content-Type": "application/json",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = httpx.post(LINEAR_API_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    result = response.json()

    if "errors" in result:
        raise Exception(f"GraphQL errors: {result['errors']}")

    return result.get("data", {})


def get_or_create_labels(team_id: str, label_names: list[str]) -> dict[str, str]:
    """
    Get or create labels in Linear, returning a mapping of name -> ID.

    Args:
        team_id: Team UUID
        label_names: List of label names to ensure exist

    Returns:
        Dict mapping label name to label ID
    """
    # First, fetch existing labels for the team
    query = """
    query GetLabels($teamId: String!) {
        team(id: $teamId) {
            labels {
                nodes {
                    id
                    name
                }
            }
        }
    }
    """
    data = _graphql_request(query, {"teamId": team_id})
    existing = {
        label["name"].lower(): label["id"]
        for label in data.get("team", {}).get("labels", {}).get("nodes", [])
    }

    result = {}
    for name in label_names:
        name_lower = name.lower()
        if name_lower in existing:
            result[name] = existing[name_lower]
        else:
            # Create the label
            label_id = create_label(team_id, name)
            result[name] = label_id
            existing[name_lower] = label_id
            time.sleep(RATE_LIMIT_DELAY)

    return result


def create_label(team_id: str, name: str, color: str | None = None) -> str:
    """
    Create a new label in Linear.

    Args:
        team_id: Team UUID
        name: Label name
        color: Optional hex color

    Returns:
        Created label ID
    """
    mutation = """
    mutation CreateLabel($teamId: String!, $name: String!, $color: String) {
        issueLabelCreate(input: { teamId: $teamId, name: $name, color: $color }) {
            success
            issueLabel {
                id
                name
            }
        }
    }
    """
    variables = {"teamId": team_id, "name": name}
    if color:
        variables["color"] = color

    data = _graphql_request(mutation, variables)
    result = data.get("issueLabelCreate", {})

    if not result.get("success"):
        raise Exception(f"Failed to create label: {name}")

    return result["issueLabel"]["id"]


def get_or_create_project(team_id: str, project_name: str) -> str:
    """
    Get or create a project in Linear.

    Args:
        team_id: Team UUID
        project_name: Project name

    Returns:
        Project ID
    """
    # Search for existing project
    query = """
    query GetProjects($teamId: String!) {
        team(id: $teamId) {
            projects {
                nodes {
                    id
                    name
                }
            }
        }
    }
    """
    data = _graphql_request(query, {"teamId": team_id})
    projects = data.get("team", {}).get("projects", {}).get("nodes", [])

    for project in projects:
        if project["name"].lower() == project_name.lower():
            return project["id"]

    # Create the project
    mutation = """
    mutation CreateProject($teamIds: [String!]!, $name: String!) {
        projectCreate(input: { teamIds: $teamIds, name: $name }) {
            success
            project {
                id
                name
            }
        }
    }
    """
    data = _graphql_request(mutation, {"teamIds": [team_id], "name": project_name})
    result = data.get("projectCreate", {})

    if not result.get("success"):
        raise Exception(f"Failed to create project: {project_name}")

    return result["project"]["id"]


def get_workflow_states(team_id: str) -> dict[str, str]:
    """
    Get workflow states for a team.

    Returns:
        Dict mapping state name to state ID
    """
    query = """
    query GetWorkflowStates($teamId: String!) {
        team(id: $teamId) {
            states {
                nodes {
                    id
                    name
                }
            }
        }
    }
    """
    data = _graphql_request(query, {"teamId": team_id})
    states = data.get("team", {}).get("states", {}).get("nodes", [])
    return {state["name"]: state["id"] for state in states}


def create_issue(
    team_id: str,
    title: str,
    description: str,
    state_id: str | None = None,
    priority: int | None = None,
    label_ids: list[str] | None = None,
    project_id: str | None = None,
) -> dict:
    """
    Create a new issue in Linear.

    Args:
        team_id: Team UUID
        title: Issue title
        description: Issue description (markdown)
        state_id: Workflow state ID
        priority: Priority (0-4)
        label_ids: List of label IDs
        project_id: Project ID

    Returns:
        Created issue data with id, identifier, url
    """
    mutation = """
    mutation CreateIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue {
                id
                identifier
                url
                title
            }
        }
    }
    """

    input_data = {
        "teamId": team_id,
        "title": title,
        "description": description,
    }

    if state_id:
        input_data["stateId"] = state_id
    if priority is not None:
        input_data["priority"] = priority
    if label_ids:
        input_data["labelIds"] = label_ids
    if project_id:
        input_data["projectId"] = project_id

    data = _graphql_request(mutation, {"input": input_data})
    result = data.get("issueCreate", {})

    if not result.get("success"):
        raise Exception(f"Failed to create issue: {title}")

    return result["issue"]


def create_issue_relation(issue_id: str, related_issue_id: str, relation_type: str = "blocks") -> bool:
    """
    Create a relation between two issues.

    Args:
        issue_id: Source issue ID
        related_issue_id: Target issue ID
        relation_type: "blocks" or "related"

    Returns:
        True if successful
    """
    mutation = """
    mutation CreateRelation($issueId: String!, $relatedIssueId: String!, $type: IssueRelationType!) {
        issueRelationCreate(input: { issueId: $issueId, relatedIssueId: $relatedIssueId, type: $type }) {
            success
        }
    }
    """
    data = _graphql_request(mutation, {
        "issueId": issue_id,
        "relatedIssueId": related_issue_id,
        "type": relation_type,
    })
    return data.get("issueRelationCreate", {}).get("success", False)


# === Ticket Processing ===

def format_description(ticket: dict, github_base_url: str) -> str:
    """
    Format ticket description with spec_refs as links.

    Args:
        ticket: Ticket data from JSON
        github_base_url: Base URL for GitHub links

    Returns:
        Formatted markdown description
    """
    parts = []

    # Main description
    parts.append(ticket["description"])
    parts.append("")

    # Spec references
    spec_refs = ticket.get("spec_refs", [])
    if spec_refs:
        parts.append("## Spec References")
        for ref in spec_refs:
            url = f"{github_base_url}/{ref}"
            parts.append(f"- [{ref}]({url})")
        parts.append("")

    # Dependencies
    deps = ticket.get("dependencies", [])
    if deps:
        parts.append("## Dependencies")
        parts.append(f"Blocked by: {', '.join(deps)}")
        parts.append("")

    # Metadata
    parts.append("---")
    parts.append(f"*Phase: {ticket.get('phase', 'unknown')}*")
    parts.append(f"*Source: lichess_tickets.json ({ticket['id']})*")

    return "\n".join(parts)


def load_tickets(json_path: Path) -> tuple[dict, list[dict]]:
    """Load tickets from JSON file."""
    with open(json_path, "r") as f:
        data = json.load(f)
    return data, data.get("tickets", [])


def collect_all_labels(tickets: list[dict]) -> set[str]:
    """Collect all unique labels from tickets."""
    labels = set()
    for ticket in tickets:
        for label in ticket.get("labels", []):
            labels.add(label)
        # Also add phase as a label
        phase = ticket.get("phase", "")
        if phase:
            labels.add(phase)
    return labels


def filter_tickets_by_phase(tickets: list[dict], phase: str | None) -> list[dict]:
    """Filter tickets by phase if specified."""
    if not phase:
        return tickets
    return [t for t in tickets if t.get("phase") == phase]


def create_tickets_batch(
    tickets: list[dict],
    team_id: str,
    label_map: dict[str, str],
    state_id: str,
    project_id: str | None,
    github_base_url: str,
    dry_run: bool = False,
) -> tuple[list[TicketResult], dict[str, str]]:
    """
    Create a batch of tickets in Linear.

    Args:
        tickets: List of ticket dicts from JSON
        team_id: Team UUID
        label_map: Mapping of label name to ID
        state_id: Workflow state ID
        project_id: Optional project ID
        github_base_url: Base URL for spec links
        dry_run: If True, don't actually create

    Returns:
        Tuple of (results list, mapping of JSON ID to Linear ID)
    """
    results = []
    id_map = {}  # Maps "LIC-1" to Linear issue ID

    for i, ticket in enumerate(tickets):
        json_id = ticket["id"]
        title = ticket["title"]
        description = format_description(ticket, github_base_url)
        priority = PRIORITY_MAP.get(ticket.get("priority", 3), 3)

        # Get label IDs (labels + phase)
        ticket_labels = ticket.get("labels", [])
        phase = ticket.get("phase", "")
        if phase:
            ticket_labels = ticket_labels + [phase]

        label_ids = [label_map[l] for l in ticket_labels if l in label_map]

        print(f"[{i+1}/{len(tickets)}] {json_id}: {title[:50]}...")

        if dry_run:
            print(f"  Would create with {len(label_ids)} labels, priority {priority}")
            results.append({
                "json_id": json_id,
                "linear_id": "dry-run",
                "identifier": f"DRY-{i+1}",
                "url": "https://linear.app/dry-run",
            })
            id_map[json_id] = f"dry-run-{json_id}"
        else:
            try:
                issue = create_issue(
                    team_id=team_id,
                    title=title,
                    description=description,
                    state_id=state_id,
                    priority=priority,
                    label_ids=label_ids,
                    project_id=project_id,
                )

                results.append({
                    "json_id": json_id,
                    "linear_id": issue["id"],
                    "identifier": issue["identifier"],
                    "url": issue["url"],
                })
                id_map[json_id] = issue["id"]

                print(f"  Created: {issue['identifier']} - {issue['url']}")
                time.sleep(RATE_LIMIT_DELAY)

            except Exception as e:
                print(f"  ERROR: {e}")
                continue

    return results, id_map


def create_dependency_relations(
    tickets: list[dict],
    id_map: dict[str, str],
    dry_run: bool = False,
) -> int:
    """
    Create blocking relations between tickets based on dependencies.

    Args:
        tickets: List of ticket dicts
        id_map: Mapping of JSON ID to Linear issue ID
        dry_run: If True, don't actually create

    Returns:
        Number of relations created
    """
    count = 0

    for ticket in tickets:
        json_id = ticket["id"]
        deps = ticket.get("dependencies", [])

        if not deps:
            continue

        if json_id not in id_map:
            continue

        issue_id = id_map[json_id]

        for dep_id in deps:
            if dep_id not in id_map:
                print(f"  Warning: Dependency {dep_id} not found for {json_id}")
                continue

            blocking_issue_id = id_map[dep_id]

            if dry_run:
                print(f"  Would create: {dep_id} blocks {json_id}")
            else:
                try:
                    # The blocking issue blocks the current issue
                    create_issue_relation(blocking_issue_id, issue_id, "blocks")
                    print(f"  Created relation: {dep_id} blocks {json_id}")
                    count += 1
                    time.sleep(RATE_LIMIT_DELAY)
                except Exception as e:
                    print(f"  ERROR creating relation {dep_id} -> {json_id}: {e}")

    return count


def save_results(results: list[TicketResult], output_path: Path) -> None:
    """Save creation results to JSON for reference."""
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


# === Main ===

def main():
    parser = argparse.ArgumentParser(
        description="Bulk create Linear tickets from lichess_tickets.json"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without actually creating",
    )
    parser.add_argument(
        "--phase",
        type=str,
        help="Only create tickets for a specific phase (e.g., phase-0)",
    )
    parser.add_argument(
        "--skip-relations",
        action="store_true",
        help="Skip creating dependency relations",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).parent / "lichess_tickets.json",
        help="Path to tickets JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "linear_ticket_mapping.json",
        help="Path to save ID mapping results",
    )
    parser.add_argument(
        "--team-id",
        type=str,
        default=TEAM_ID,
        help="Linear team UUID",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=PROJECT_NAME,
        help="Linear project name (created if doesn't exist)",
    )
    parser.add_argument(
        "--github-url",
        type=str,
        default=GITHUB_SPECS_URL,
        help="Base GitHub URL for spec references",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Linear Ticket Creation Script")
    print("=" * 60)

    if args.dry_run:
        print("DRY RUN MODE - No tickets will be created")

    # Load tickets
    print(f"\nLoading tickets from: {args.input}")
    data, tickets = load_tickets(args.input)
    print(f"Loaded {len(tickets)} tickets")

    # Filter by phase if specified
    if args.phase:
        tickets = filter_tickets_by_phase(tickets, args.phase)
        print(f"Filtered to {len(tickets)} tickets for {args.phase}")

    if not tickets:
        print("No tickets to create!")
        return

    # Collect labels
    all_labels = collect_all_labels(tickets)
    print(f"Found {len(all_labels)} unique labels: {sorted(all_labels)}")

    if not args.dry_run:
        # Get or create labels
        print("\nSetting up labels...")
        label_map = get_or_create_labels(args.team_id, list(all_labels))

        # Get workflow states
        print("Getting workflow states...")
        states = get_workflow_states(args.team_id)
        state_id = states.get(DEFAULT_STATE)
        if not state_id:
            print(f"ERROR: State '{DEFAULT_STATE}' not found. Available: {list(states.keys())}")
            return

        # Get or create project
        print(f"Setting up project: {args.project}...")
        project_id = get_or_create_project(args.team_id, args.project)
    else:
        label_map = {l: f"label-{i}" for i, l in enumerate(all_labels)}
        state_id = "dry-run-state"
        project_id = "dry-run-project"

    # Create tickets
    print(f"\nCreating {len(tickets)} tickets...")
    results, id_map = create_tickets_batch(
        tickets=tickets,
        team_id=args.team_id,
        label_map=label_map,
        state_id=state_id,
        project_id=project_id,
        github_base_url=args.github_url,
        dry_run=args.dry_run,
    )

    print(f"\nCreated {len(results)} tickets")

    # Create dependency relations
    if not args.skip_relations:
        print("\nCreating dependency relations...")
        relation_count = create_dependency_relations(tickets, id_map, args.dry_run)
        print(f"Created {relation_count} blocking relations")

    # Save results
    if not args.dry_run:
        save_results(results, args.output)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
