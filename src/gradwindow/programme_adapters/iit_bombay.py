from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://acad.iitb.ac.in/admissions/masters/divisions"
APPLICATION_URL = "https://acad.iitb.ac.in/admissions/masters"
DEGREE_TYPES = (
    "M.Tech",
    "M.Des",
    "MBA",
    "EMBA",
    "MA+PhD",
    "MA.Res",
    "MPP",
    "MSc",
    "MSc+PhD",
    "MDP",
)
CODE_RE = re.compile(r"^\([A-Z0-9]+\)\s*")

# The current Drupal page flattened the tables into paragraphs. Match explicit
# headings, not their positions, so a missing section cannot shift degree types.
SECTION_HEADINGS = (
    "Master of Technology/(Dual Degree) Master of Technology + Doctor of Philosophy",
    "Master of Design (M.Des.) and Master of Design by Research (M.Des. by Research)",
    "Master of Business Administration",
    "Master of Business Administration (Executive)",
    "MA+Ph.D. (Dual Degree) in Philosophy",
    "Master of Arts by Research (MA.Res.)",
    "Master in Public Policy",
    "Master of Science",
    "(Dual Degree) Master of Science + Doctor of Philosophy",
    "Master in Development Practice (MDP)",
)
# Uncoded rows have no remaining HTML distinction between a programme and its
# department (Chemistry and Physics even repeat). Validate the reviewed row
# grammar verbatim; never guess alternation or publish department names.
UNCODED_ROWS = {
    "MA+PhD": (
        ("MA+Ph.D. (Dual Degree) in Philosophy", "Humanities and Social Sciences"),
    ),
    "MA.Res": (
        ("Master of Arts by Research (MA.Res.)", "Humanities and Social Sciences"),
    ),
    "MPP": (("Public Policy", "Centre for Policy Studies"),),
    "MSc": (
        ("Applied Geology", "Applied Geophysics", "Earth Sciences"),
        ("Applied Statistics & Informatics", "Mathematics"),
        ("Biotechnology", "Biosciences & Bioengineering"),
        ("Chemistry", "Chemistry"),
        ("Operations Research", "Industrial Engineering and Operations Research"),
        ("Physics", "Physics"),
    ),
    "MSc+PhD": (
        ("Environmental Science", "Department of Environmental Science & Engineering"),
        ("Energy", "Energy Science and Engineering"),
    ),
    "MDP": (
        (
            "Master in Development Practice",
            "Centre for Technology Alternatives for Rural Areas (CTARA)",
        ),
    ),
}


class IITBombayAdapter(OfficialCatalogAdapter):
    university_id = "indian-institute-of-technology-bombay-iitb"
    school_prefix = "iitb"
    institution_name = "Indian Institute of Technology Bombay"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 40
    retrieval_method = "official-master-academic-divisions"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        if not soup.select("table"):
            return self._paragraph_entries(soup)
        entries: list[CatalogEntry] = []
        for table_index, table in enumerate(soup.select("table")):
            if table_index >= len(DEGREE_TYPES):
                break
            degree_type = DEGREE_TYPES[table_index]
            for row in table.select("tr"):
                cells = row.select("td")
                if len(cells) < 2:
                    continue
                department_link = cells[1].select_one("a[href]")
                source_url = (
                    str(department_link["href"]) if department_link else CATALOG_URL
                )
                names = [
                    normalise(node.get_text(" ", strip=True))
                    for node in cells[0].select(":scope > p")
                ]
                if not names:
                    names = [normalise(cells[0].get_text(" ", strip=True))]
                for value in names:
                    name = CODE_RE.sub("", value).strip()
                    if not name or name.casefold() == "degree/specialization":
                        continue
                    if (
                        degree_type == "EMBA"
                        and name == "Master of Business Administration"
                    ):
                        name = "Executive Master of Business Administration"
                    entries.append(
                        entry(
                            name=name,
                            degree_type=degree_type,
                            source_url=source_url,
                            base_url=CATALOG_URL,
                        )
                    )
        return entries

    def _paragraph_entries(self, soup: BeautifulSoup) -> list[CatalogEntry]:
        body = soup.select_one(".field--name-body")
        if body is None:
            raise ValueError("IIT Bombay catalogue body missing")
        paragraphs = [
            value
            for node in body.select("p")
            if (value := normalise(node.get_text(" ", strip=True)))
        ]
        markers = [
            index
            for index, value in enumerate(paragraphs)
            if value == "Degree/Specialization"
        ]
        sections: dict[str, list[str]] = {}
        for position, index in enumerate(markers):
            if index == 0 or paragraphs[index - 1] not in SECTION_HEADINGS:
                raise ValueError("IIT Bombay unrecognised degree section")
            heading = paragraphs[index - 1]
            degree = DEGREE_TYPES[SECTION_HEADINGS.index(heading)]
            if degree in sections or paragraphs[index + 1 : index + 2] != [
                "Department"
            ]:
                raise ValueError("IIT Bombay duplicate or malformed degree section")
            end = (
                markers[position + 1] - 1
                if position + 1 < len(markers)
                else len(paragraphs)
            )
            sections[degree] = paragraphs[index + 2 : end]
        if set(sections) != set(DEGREE_TYPES):
            raise ValueError("IIT Bombay catalogue is missing degree sections")
        entries: list[CatalogEntry] = []
        for degree, values in sections.items():
            if degree in UNCODED_ROWS:
                rows = UNCODED_ROWS[degree]
                if values != [value for row in rows for value in row]:
                    raise ValueError(
                        f"IIT Bombay {degree} uncoded rows changed; review required"
                    )
                names = [value for row in rows for value in row[:-1]]
            else:
                names = [
                    CODE_RE.sub("", value).strip()
                    for value in values
                    if CODE_RE.match(value)
                ]
                if not names or any(not name for name in names):
                    raise ValueError(f"IIT Bombay {degree} has no coded programmes")
            for name in names:
                if degree == "EMBA" and name == "Master of Business Administration":
                    name = "Executive Master of Business Administration"
                entries.append(
                    entry(
                        name=name,
                        degree_type=degree,
                        source_url=CATALOG_URL,
                        base_url=CATALOG_URL,
                    )
                )
        return entries
