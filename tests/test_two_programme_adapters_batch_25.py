from __future__ import annotations

import pytest

from gradwindow.programme_adapters.pompeu_fabra import PompeuFabraAdapter
from gradwindow.programme_adapters.umass_chan import UMassChanAdapter


def test_pompeu_fabra_uses_the_official_application_heartbeat() -> None:
    html = """
      <html><head><title>Identificació</title></head><body>
        <p>A SIGMA utilitzem cookies pel correcte funcionament de la web.</p>
        <label>Idioma</label><option>Anglès</option><option>Català</option>
        <h1>Iniciar sessió</h1>
        <a href="/aps/controlPBC/formulario_solicitud_cambio_password_con_DNI">
          No saps o has oblidat la teva contrasenya?
        </a>
      </body></html>
    """

    catalog = PompeuFabraAdapter().parse_catalog(html)

    assert catalog.application_opens_at is None
    assert [row.id for row in catalog.programmes] == ["upf-masters-programmes"]
    assert catalog.programmes[0].evidence_quality == "official-access-limitation"
    assert catalog.programmes[0].source_url == PompeuFabraAdapter.public_catalog_url


def test_pompeu_fabra_rejects_an_unrelated_login_page() -> None:
    with pytest.raises(ValueError, match="heartbeat changed"):
        PompeuFabraAdapter().parse_catalog("<h1>Iniciar sessió</h1>")


def test_umass_chan_uses_its_official_application_heartbeat() -> None:
    html = """
      <html><head><title>Application Management</title></head><body>
        <h1>Umass Med Application Management</h1>
        <h2>Returning users:</h2><p>Log in to continue an application.</p>
        <h2>First-time users:</h2><p>Create an account to start a new application.</p>
        <footer>UMass Chan Medical School</footer>
      </body></html>
    """

    catalog = UMassChanAdapter().parse_catalog(html)

    assert catalog.application_opens_at is None
    assert [row.id for row in catalog.programmes] == ["umass-chan-masters-programmes"]
    assert catalog.programmes[0].application_url == UMassChanAdapter.catalog_url
    assert catalog.programmes[0].evidence_quality == "official-access-limitation"


def test_umass_chan_rejects_a_generic_application_page() -> None:
    with pytest.raises(ValueError, match="heartbeat changed"):
        UMassChanAdapter().parse_catalog("<h1>Application Management</h1>")
