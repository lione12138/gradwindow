from __future__ import annotations

import json

import pytest

from gradwindow.programme_adapters.aarhus import AarhusAdapter
from gradwindow.programme_adapters.lancaster import LancasterAdapter
from gradwindow.programme_adapters.lse import LSEAdapter
from gradwindow.programme_adapters.washington import WashingtonAdapter
from gradwindow.programme_adapters.wisconsin import WisconsinAdapter


@pytest.mark.parametrize(
    ("adapter", "document", "expected_name"),
    [
        (
            LSEAdapter(),
            '<a href="https://www.lse.ac.uk/study-at-lse/graduate/msc-data-science">G3U1 MSc Data Science</a>',
            "MSc Data Science",
        ),
        (
            WisconsinAdapter(),
            '<a href="/graduate/data-science/data-science-ms/"><span class="title visual"><h3>Data Science, MS</h3></span></a>',
            "Data Science, MS",
        ),
        (
            LancasterAdapter(),
            "<course-listing></course-listing>"
            "<course-listing :current-entry-year='\"27\\/28\"' "
            ':courses-data=\'[{"title":"Data Science : MSc","slug":"data-science-msc","taught":"1","entryYear":"27/28"}]\'></course-listing>',
            "Data Science MSc",
        ),
    ],
)
def test_official_html_catalogue_parsers(adapter, document, expected_name) -> None:
    adapter.minimum_expected_programmes = 1
    programme = adapter.parse_catalog(document).programmes[0]

    assert programme.name == expected_name
    assert programme.windows == []
    assert programme.parse_status == "no-deadline"
    assert programme.evidence_quality == "official-full-text"


def test_washington_official_api_parser() -> None:
    adapter = WashingtonAdapter()
    adapter.minimum_expected_programmes = 1
    payload = json.dumps(
        [
            {
                "program_name": "Data Science (MS)",
                "degree_level": "Masters",
                "home_page_url": "https://www.washington.edu/data-science",
            },
            {
                "program_name": "Data Science (PhD)",
                "degree_level": "Doctoral",
                "home_page_url": "https://www.washington.edu/data-science-phd",
            },
        ]
    )

    programmes = adapter.parse_catalog(payload).programmes

    assert [programme.name for programme in programmes] == ["Data Science (MS)"]


def test_washington_external_joint_programme_uses_official_directory() -> None:
    adapter = WashingtonAdapter()
    adapter.minimum_expected_programmes = 1
    payload = json.dumps(
        [
            {
                "program_name": "Technology Innovation (MS)",
                "degree_level": "Masters",
                "home_page_url": "https://gixnetwork.org/degree-program/",
            }
        ]
    )

    programme = adapter.parse_catalog(payload).programmes[0]

    assert programme.source_url == (
        "https://grad.uw.edu/programs/find-a-graduate-program/"
    )


def test_aarhus_official_api_parser_keeps_specialisation_context() -> None:
    adapter = AarhusAdapter()
    adapter.minimum_expected_programmes = 1
    payload = json.dumps(
        {
            "Items": [
                {
                    "ID": 1,
                    "Name": "Computer Science",
                    "Uri": "http://masters.au.dk/computer-science",
                    "Parent": 0,
                },
                {
                    "ID": 2,
                    "Name": "Artificial Intelligence",
                    "Uri": "http://masters.au.dk/computer-science#ai",
                    "Parent": 1,
                },
            ]
        }
    )

    programmes = adapter.parse_catalog(payload).programmes

    assert [programme.name for programme in programmes] == [
        "Computer Science",
        "Computer Science: Artificial Intelligence",
    ]
    assert all(programme.source_url.startswith("https://") for programme in programmes)


def test_aarhus_official_xml_api_parser() -> None:
    adapter = AarhusAdapter()
    adapter.minimum_expected_programmes = 1
    payload = """\
<MastersDataList xmlns="http://schemas.datacontract.org/2004/07/WebtoolsAU.Models">
  <Items>
    <MastersDataItem>
      <ID>1</ID><Name>Computer Science</Name><Parent>0</Parent>
      <Uri>http://masters.au.dk/computer-science</Uri>
    </MastersDataItem>
    <MastersDataItem>
      <ID>2</ID><Name>Artificial Intelligence</Name><Parent>1</Parent>
      <Uri>http://masters.au.dk/computer-science</Uri>
    </MastersDataItem>
  </Items>
</MastersDataList>
"""

    programmes = adapter.parse_catalog(payload).programmes

    assert [programme.name for programme in programmes] == [
        "Computer Science",
        "Computer Science: Artificial Intelligence",
    ]
