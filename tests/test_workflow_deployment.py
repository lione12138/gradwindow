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


def test_daily_refresh_waits_for_tests_and_pages_deployment() -> None:
    update_workflow = Path(".github/workflows/update-data.yml").read_text(
        encoding="utf-8"
    )
    pages_workflow = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")

    assert "Test and deploy refreshed production site" in update_workflow
    assert 'gh run watch "$tests_run_id"' in update_workflow
    assert "gh workflow run pages.yml" in update_workflow
    assert 'gh run watch "$pages_run_id"' in update_workflow
    assert "workflow_dispatch:" in pages_workflow
    assert "tests_run_id:" in pages_workflow
    assert "github.event.workflow_run.id || inputs.tests_run_id" in pages_workflow


def test_adapter_health_issue_is_updated_before_data_pr_cleans_worktree() -> None:
    workflow = Path(".github/workflows/update-data.yml").read_text(encoding="utf-8")

    health_issue_step = workflow.index("- name: Maintain one adapter-health issue")
    data_pr_step = workflow.index(
        "- name: Open or update automated data publication pull request"
    )

    assert health_issue_step < data_pr_step
    assert "notification_due=" in workflow
    assert "notification_reason=" in workflow
    assert 'if [ "$NOTIFICATION_DUE" = "true" ]; then' in workflow
    assert "Weekly consolidated adapter-maintenance reminder" in workflow


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

    pull_position = monitor_workflow.index("git pull --ff-only origin main")
    scan_position = monitor_workflow.index("gradwindow monitor --workers 16")
    commit_position = monitor_workflow.index(
        'git commit -m "chore: publish daily monitoring status"'
    )
    assert pull_position < scan_position < commit_position
    assert "git pull --rebase origin main" not in monitor_workflow


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
