from __future__ import annotations

from html import escape
from typing import Literal

from pydantic import AnyHttpUrl, Field, TypeAdapter

from .io import read_json
from .models import DataModel
from .paths import ROOT

BUSINESS_SCHOOLS_PATH = ROOT / "data" / "business-schools.json"


class BusinessProgramme(DataModel):
    level: Literal["undergraduate", "masters", "mba"]
    name: str = Field(min_length=1)
    name_zh: str = Field(alias="nameZh", min_length=1)
    url: AnyHttpUrl


class BusinessSchool(DataModel):
    name: str = Field(min_length=1)
    name_zh: str = Field(alias="nameZh", min_length=1)
    location: str = Field(min_length=1)
    location_zh: str = Field(alias="locationZh", min_length=1)
    region: Literal["paris", "france", "other"]
    url: AnyHttpUrl
    programmes: list[BusinessProgramme] = Field(min_length=1)


def render_business_schools() -> str:
    schools = TypeAdapter(list[BusinessSchool]).validate_python(
        read_json(BUSINESS_SCHOOLS_PATH)
    )
    levels = {"undergraduate": "Undergraduate", "masters": "Master’s", "mba": "MBA"}
    cards = []
    for school in schools:
        programmes = []
        for programme in school.programmes:
            level = programme.level
            programmes.append(
                f'<li data-level="{level}">'
                f'<span class="business-programme-level" data-i18n="businessLevel-{level}">'
                f"{levels[level]}</span>"
                f'<a href="{escape(str(programme.url))}" '
                f'data-en="{escape(programme.name)}" data-zh="{escape(programme.name_zh)}">'
                f"{escape(programme.name)}</a></li>"
            )
        cards.append(
            f'<article class="business-school" data-region="{school.region}">'
            f'<h2><a href="{escape(str(school.url))}" '
            f'data-en="{escape(school.name)}" data-zh="{escape(school.name_zh)}">'
            f"{escape(school.name)}</a></h2>"
            f'<p class="business-school-location" data-en="{escape(school.location)}" '
            f'data-zh="{escape(school.location_zh)}">{escape(school.location)}</p>'
            f'<ul class="business-programmes">{"".join(programmes)}</ul></article>'
        )
    return "\n".join(cards)
