import pytest

from gradwindow.programme_adapters.lund import LundAdapter

PAGE = """
<div class="hits-list-result">
  <li class="hit hit--educations">
    <h3><a href="https://www.lunduniversity.lu.se/study/machine-learning-systems-and-control-masters-programme-TAMSR">Machine Learning, Systems and Control - Master's Programme</a></h3>
    <span class="education-course-points">Master's programme • 2 year • 120 credits</span>
  </li>
  <li class="hit hit--educations">
    <h3><a href="https://www.lunduniversity.lu.se/study/economy-and-society-bachelors-programme-EGESO">Economy and Society - Bachelor's Programme</a></h3>
    <span class="education-course-points">Bachelor's programme • 3 year • 180 credits</span>
  </li>
  <li class="hit hit--educations">
    <h3><a href="https://www.lunduniversity.lu.se/study/public-health-masters-programme-VAPHE">Public Health - Master's Programme</a></h3>
    <span class="education-course-points">Master's programme • 2 year • 120 credits</span>
  </li>
</div>
"""


def test_lund_adapter_keeps_only_masters_and_reuses_existing_id() -> None:
    catalog = LundAdapter(minimum_expected_programmes=2).parse_pages([PAGE])

    assert [item.name for item in catalog.programmes] == [
        "Machine Learning, Systems and Control - Master's Programme",
        "Public Health - Master's Programme",
    ]
    assert catalog.programmes[0].id == "lund-machine-learning-systems-control-msc"
    assert all(item.windows == [] for item in catalog.programmes)


def test_lund_adapter_rejects_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        LundAdapter(minimum_expected_programmes=3).parse_pages([PAGE])
