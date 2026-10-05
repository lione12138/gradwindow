from gradwindow.programme_adapters.vienna import ViennaAdapter


def test_current_directory_paths_and_plain_names():
    html = """
    <a href="/en/find-you-degree-programme/masters-programmes/physics-masters-programme">Physics</a>
    <a href="https://studieren.univie.ac.at/en/find-your-degree-programme/masters-programmes/chemistry-masters-programme">Chemistry</a>
    <a href="/en/find-you-degree-programme/masters-programmes/physics-masters-programme">Physics</a>
    <a href="/en/find-your-degree-programme/masters-programmes#overview">Overview</a>
    <a href="/en/applying-for-a-programme/international-students/visiting-master">Visiting Master</a>
    <a href="https://example.org/en/find-you-degree-programme/masters-programmes/fake-masters-programme">Fake</a>
    """
    adapter = ViennaAdapter()
    adapter.minimum_expected_programmes = 2
    programmes = adapter.parse_catalog(html).programmes
    assert [p.name for p in programmes] == ["Chemistry", "Physics"]
    assert all(not p.windows for p in programmes)
    assert programmes[1].id == "vienna-physics-master"
