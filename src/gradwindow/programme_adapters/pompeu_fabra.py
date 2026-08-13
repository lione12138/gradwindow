from __future__ import annotations

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise

APPLICATION_HEARTBEAT_URL = (
    "https://secretariavirtual.upf.edu/cosmos/Controlador/"
    "?apl=Uninavs&gu=a&idNav=inicio&NuevaSesionUsuario=true"
    "&NombreUsuarioAlumno=ALUMNO&responsive=S"
)
PUBLIC_CATALOG_URL = "https://www.upf.edu/en/web/masters/masters-universitaris"
APPLICATION_INFORMATION_URL = "https://www.upf.edu/en/web/masters/2_preinscripcio"


class PompeuFabraAdapter(BaseProgrammeAdapter):
    university_id = "pompeu-fabra-university"
    catalog_url = APPLICATION_HEARTBEAT_URL
    public_catalog_url = PUBLIC_CATALOG_URL
    application_url = APPLICATION_INFORMATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_HEARTBEAT_URL,)
    catalogue_status = "blocked"
    retrieval_method = "official-application-system-access-monitor"
    catalogue_limitation_reason = (
        "Pompeu Fabra University's official master's directory and admissions "
        "calendar return a Cloudflare challenge to unattended clients. The official "
        "SIGMA application system is monitored as a first-party availability "
        "heartbeat; programme names and dates are not copied from search snippets."
    )

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        text = normalise(soup.get_text(" ", strip=True)).casefold()
        links = {str(link.get("href", "")) for link in soup.select("a[href]")}
        if not all(
            marker in text
            for marker in (
                "identificació",
                "sigma",
                "iniciar sessió",
                "català",
            )
        ) or not any("controlpbc" in link.casefold() for link in links):
            raise ValueError("Pompeu Fabra's official application heartbeat changed")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="upf-masters-programmes",
                    name="Official master's degree programmes",
                    degree_type="Master",
                    faculty="Pompeu Fabra University",
                    department="Graduate Admissions",
                    source_url=PUBLIC_CATALOG_URL,
                    application_url=APPLICATION_INFORMATION_URL,
                    windows=[],
                    deadline_text=(
                        "UPF's official catalogue and calendar currently block "
                        "unattended retrieval. This monitor preserves the official "
                        "catalogue and admissions links without inferring dates."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-access-limitation",
                )
            ],
        )
