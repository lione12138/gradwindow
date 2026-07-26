from pathlib import Path


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
