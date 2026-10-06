import pytest

from gradwindow.programme_adapters.eduhk import EdUHKAdapter, _programmes

CATALOGUE = """
<div><h4 id="tpp-gs">Taught Postgraduate Programmes</h4>
<details class="programme-section"><summary><strong>Graduate School</strong></summary>
<div class="section-body">
<a href="https://gs.eduhk.hk/med/">Master of Education [MEd]<br>教育碩士</a>
<a href="https://gs.eduhk.hk/new/">Master of New Studies # *<br>待批准</a>
<a href="https://example.org/course">Master of Fake</a>
</div></details></div>
<div><h4 id="tpp-reg">Taught Postgraduate Programmes</h4>
<details class="programme-section"><summary><strong>Humanities</strong></summary>
<div class="section-body">
<a href="https://www.eduhk.hk/ma/">Master of Arts / Medium of Instruction: Chinese #<br>文學碩士</a>
<a href="https://www.eduhk.hk/pgcert/">Postgraduate Certificate</a>
</div></details></div>
"""
SCHEDULE = """2027/28 September 2027 Intake
5 Oct 2026 (Mon) Open for Applications
10 May 2027 (Mon) Application Deadline for Non-local Applicants
31 May 2027 (Mon) Application Deadline for Local Applicants
not applicable to PhD, MPhil, EdD, EdD(Chinese), MSocSc(EP) and PGDE
"""


def test_new_catalogue_and_general_schedule_keep_scope_separate():
    adapter = EdUHKAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        catalogue_fetcher=lambda _: CATALOGUE,
        schedule_fetcher=lambda _: SCHEDULE,
    )
    rows = adapter.parse_catalog_from_fetcher(lambda _: "").programmes
    courses = [p for p in rows if not p.windows]
    assert [p.name for p in courses] == [
        "Master of Arts / Medium of Instruction: Chinese",
        "Master of Education [MEd]",
    ]
    assert courses[0].faculty == "Humanities"
    groups = [p for p in rows if p.windows]
    assert len(groups) == 2
    assert all(p.windows[0].opens_at == "2026-10-05" for p in groups)
    assert all(p.windows[0].opens_at_basis == "official" for p in groups)
    assert {p.windows[0].closes_at for p in groups} == {"2027-05-10", "2027-05-31"}
    assert all("MSocSc(EP)" in p.deadline_text for p in groups)


@pytest.mark.parametrize(
    "original,replacement",
    [
        ("5 Oct 2026", "October 2026"),
        ("September 2027", "September 2028"),
        ("MSocSc(EP)", "Changed scope"),
    ],
)
def test_changed_schedule_is_not_assumed(original, replacement):
    adapter = EdUHKAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        catalogue_fetcher=lambda _: CATALOGUE,
        schedule_fetcher=lambda _: SCHEDULE.replace(original, replacement),
    )
    with pytest.raises(ValueError, match="dates or scope changed"):
        adapter.parse_catalog_from_fetcher(lambda _: "")


def test_missing_registry_section_is_rejected():
    with pytest.raises(ValueError, match="administering section"):
        _programmes(CATALOGUE.replace('id="tpp-reg"', 'id="unknown"'))
