import pytest

from gradwindow.programme_adapters.kfupm import KFUPMAdapter

THESIS_PAGE = """
<p><a href="/program?program_id=142&amp;title=master-of-science-in-computer-science">Master of Science in Computer Science</a></p>
<p><a href="/program?program_id=140&amp;title=doctor-of-philosophy">Doctor of Philosophy in Computer Science</a></p>
"""
PROJECT_PAGE = """
<h2>1. Executive Master of Business Administration (EMBA) 2 YEARS Executive CLOSED</h2>
<h2>2. Master of Science in Data Science &amp; Analytics CLOSED</h2>
<h2>Download Admission Brochure</h2>
"""


def test_kfupm_adapter_combines_thesis_and_project_catalogues() -> None:
    catalog = KFUPMAdapter(minimum_expected_programmes=3).parse_pages(
        THESIS_PAGE, PROJECT_PAGE
    )

    assert [item.name for item in catalog.programmes] == [
        "Executive Master of Business Administration (EMBA)",
        "Master of Science in Computer Science",
        "Master of Science in Data Science & Analytics",
    ]
    assert any(
        item.id == "kfupm-data-science-analytics-ms" for item in catalog.programmes
    )
    assert all(item.windows == [] for item in catalog.programmes)


def test_kfupm_adapter_rejects_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 4"):
        KFUPMAdapter(minimum_expected_programmes=4).parse_pages(
            THESIS_PAGE, PROJECT_PAGE
        )
