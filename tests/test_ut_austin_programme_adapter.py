from gradwindow.programme_adapters.ut_austin import UTAustinAdapter

HTML = """<h2>College of Natural Sciences</h2><table><tr><th>Program</th><th>A</th><th>B</th><th>C</th><th>Degrees</th><th>Deadline</th></tr><tr><td><a href="https://cs.utexas.edu/graduate">Computer Science</a></td><td></td><td></td><td></td><td>MS, Ph.D.</td><td>Dec. 15</td></tr><tr><td>Statistics</td><td></td><td></td><td></td><td>MA</td><td>Jan. 10</td></tr></table>"""


def test_ut_austin_splits_master_degrees_and_ignores_phd() -> None:
    catalog = UTAustinAdapter(minimum_expected_programmes=2).parse_catalog(HTML)
    assert {item.id for item in catalog.programmes} == {
        "ut-austin-computer-science-ms",
        "ut-austin-statistics-ma",
    }
    assert all("Ph" not in item.degree_type for item in catalog.programmes)
