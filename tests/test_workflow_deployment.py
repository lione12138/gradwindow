import re
from pathlib import Path


def _concurrency_group(workflow: str) -> str:
    match = re.search(r"(?m)^concurrency:\s*\n\s+group:\s*(\S+)", workflow)
    assert match is not None
    return match.group(1)


def test_monitor_status_workflow_deploys_the_status_it_publishes() -> None:
    workflow = Path(".github/workflows/publish-monitor-status.yml").read_text(
        encoding="utf-8"
    )

    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "gradwindow build-site" in workflow
    assert "actions/upload-pages-artifact@v5" in workflow
    assert "actions/deploy-pages@v5" in workflow
    assert "gh workflow run tests.yml" not in workflow


def test_adapter_health_issue_is_updated_before_data_pr_cleans_worktree() -> None:
    workflow = Path(".github/workflows/update-data.yml").read_text(encoding="utf-8")

    health_issue_step = workflow.index("- name: Maintain one adapter-health issue")
    data_pr_step = workflow.index(
        "- name: Open or update automated data publication pull request"
    )

    assert health_issue_step < data_pr_step


def test_data_writing_workflows_share_one_concurrency_lock() -> None:
    update_workflow = Path(".github/workflows/update-data.yml").read_text(
        encoding="utf-8"
    )
    monitor_workflow = Path(".github/workflows/publish-monitor-status.yml").read_text(
        encoding="utf-8"
    )

    assert _concurrency_group(update_workflow) == "application-data-state-writes"
    assert _concurrency_group(monitor_workflow) == "application-data-state-writes"
    assert "cancel-in-progress: false" in update_workflow
    assert "cancel-in-progress: false" in monitor_workflow
    assert "git pull --rebase origin main" in monitor_workflow


def test_data_workflows_maintain_failure_issues_without_comment_spam() -> None:
    update_workflow = Path(".github/workflows/update-data.yml").read_text(
        encoding="utf-8"
    )
    monitor_workflow = Path(".github/workflows/publish-monitor-status.yml").read_text(
        encoding="utf-8"
    )

    assert "Maintain update workflow failure issue" in update_workflow
    assert 'title="Application-data refresh failed"' in update_workflow
    assert "Maintain monitoring workflow failure issue" in monitor_workflow
    assert 'title="Monitoring-status publication failed"' in monitor_workflow
    assert "gh issue comment" not in monitor_workflow
