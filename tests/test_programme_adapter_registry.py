from __future__ import annotations

import json
from pathlib import Path

from gradwindow.assisted_discovery import AssistedCatalogAdapter
from gradwindow.programme_adapters.base import BaseProgrammeAdapter, ProgrammeAdapter
from gradwindow.changed_adapters import adapter_keys_for_paths
from gradwindow.programme_adapters.registry import PROGRAMME_ADAPTERS


def test_registry_is_the_complete_unique_source_of_dedicated_adapters() -> None:
    assert set(PROGRAMME_ADAPTERS) >= {
        "adelaide",
        "anu",
        "auckland",
        "berkeley",
        "birmingham",
        "bristol",
        "caltech",
        "columbia",
        "cornell",
        "epfl",
        "fudan",
        "heidelberg",
        "ip-paris",
        "jhu",
        "kfupm",
        "korea",
        "ku-leuven",
        "kyoto",
        "lmu",
        "lund",
        "manchester",
        "mcgill",
        "northwestern",
        "nottingham",
        "ntu",
        "ntu-taiwan",
        "nus",
        "peking",
        "penn-state",
        "polimi",
        "pompeu-fabra",
        "princeton",
        "psl",
        "sjtu",
        "sheffield",
        "snu",
        "southampton",
        "sorbonne",
        "toronto",
        "tsinghua",
        "tum",
        "ubc",
        "uchicago",
        "ucl",
        "ucla",
        "ucsd",
        "uiuc",
        "unsw",
        "upenn",
        "utokyo",
        "uts",
        "uwa",
        "warwick",
        "yale",
        "yonsei",
        "zju",
        "aarhus",
        "lancaster",
        "lse",
        "washington",
        "wisconsin",
        "copenhagen",
        "ghent",
        "st-andrews",
        "stockholm",
        "tu-wien",
        "aalto",
        "basel",
        "bath",
        "boston",
        "dtu",
        "exeter",
        "fu-berlin",
        "groningen",
        "helsinki",
        "leiden",
        "liverpool",
        "newcastle",
        "oslo",
        "rice",
        "rmit",
        "uzh",
        "vienna",
        "wageningen",
        "waterloo",
        "york",
        "geneva",
        "kyushu",
        "nagoya",
        "nthu",
        "queens-ontario",
        "khalifa",
        "nanjing",
        "osaka",
        "tohoku",
        "tongji",
        "emory",
        "qatar",
        "tamu",
        "ucsb",
        "unc",
        "cmu",
        "michigan",
        "nyu",
        "trinity",
        "uba",
        "hokkaido",
        "qmul",
        "reading",
        "rwth",
        "sapienza",
        "skku",
        "upm",
        "usm",
        "uow",
        "postech",
        "grenoble-alpes",
        "hunan",
        "mainz",
        "umass-amherst",
        "umass-chan",
        "uestc",
        "chongqing",
        "goethe-frankfurt",
        "padua",
        "rutgers-nb",
        "scut",
        "aix-marseille",
        "montpellier",
        "milan",
        "lshtm",
        "normale-superiore",
        "pumc",
        "qut",
        "soochow-china",
        "utsw",
        "virginia",
        "zhengzhou",
    }
    university_ids = [factory.university_id for factory in PROGRAMME_ADAPTERS.values()]
    assert len(university_ids) == len(set(university_ids))
    public_university_ids = {
        university["id"]
        for university in json.loads(
            Path("data/universities.json").read_text(encoding="utf-8")
        )["universities"]
    }
    assert len(PROGRAMME_ADAPTERS) == len(public_university_ids)
    assert set(university_ids) == public_university_ids


def test_manual_discovery_workflow_delegates_adapter_validation_to_registry() -> None:
    workflow = Path(".github/workflows/discover-programmes.yml").read_text(
        encoding="utf-8"
    )
    university_input = workflow.split("university:", 1)[1].split("permissions:", 1)[0]

    assert "type: string" in university_input
    assert "options:" not in university_input


def test_manual_discovery_workflow_passes_browser_rendering_secrets() -> None:
    workflow = Path(".github/workflows/discover-programmes.yml").read_text(
        encoding="utf-8"
    )
    selected_adapter_step = workflow.split("- name: Run selected programme adapter", 1)[
        1
    ].split("- name: Validate discovery outputs", 1)[0]

    assert "CLOUDFLARE_ACCOUNT_ID" in selected_adapter_step
    assert "CLOUDFLARE_BROWSER_API_TOKEN" in selected_adapter_step
    assert "inputs.university != 'oxford'" not in selected_adapter_step
    assert "discover-assisted --university university-of-oxford" not in workflow


def test_post_merge_smoke_runs_changed_adapters_with_production_secrets() -> None:
    workflow = Path(".github/workflows/post-merge-adapter-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert "branches: [main]" in workflow
    assert "adapter-smoke-${{ github.sha }}" in workflow
    assert "CLOUDFLARE_ACCOUNT_ID" in workflow
    assert "CLOUDFLARE_BROWSER_API_TOKEN" in workflow
    assert (
        'discover-programmes --university "${{ matrix.adapter }}" --dry-run' in workflow
    )


def test_changed_adapter_keys_are_derived_from_the_registry() -> None:
    assert adapter_keys_for_paths(
        [
            "src/gradwindow/programme_adapters/oxford.py",
            "docs/notes.md",
        ]
    ) == ["oxford"]


def test_every_registered_adapter_satisfies_the_discovery_contract() -> None:
    for name, factory in PROGRAMME_ADAPTERS.items():
        adapter = factory()
        assert isinstance(adapter, ProgrammeAdapter), name
        assert adapter.application_opens_at_basis in {
            "official",
            "missing",
            "inferred-cycle-default",
        }
        assert isinstance(adapter.replace_pending_candidates, bool)


def test_assisted_adapter_uses_the_same_discovery_defaults() -> None:
    assert issubclass(AssistedCatalogAdapter, BaseProgrammeAdapter)


def test_enabled_generic_overlaps_are_explicit_fallbacks() -> None:
    config_path = Path("data/ops/generic-programme-discovery.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    dedicated_ids = {factory().university_id for factory in PROGRAMME_ADAPTERS.values()}
    overlaps = [
        school
        for school in config["schools"]
        if school.get("enabled", True) and school["universityId"] in dedicated_ids
    ]

    assert overlaps
    assert all(school.get("discoveryRole") == "fallback" for school in overlaps)
