"""Tests für das lokale End-to-End-Dogfooding: Lizenz-Badge + `seed_market`.

Deckt zwei Bausteine ab, die das Gesamt-Workflow-Setup ausmacht:

* Die Browse-UI zeigt die Spec-Lizenz (MIT vs. proprietär) als Badge an.
* Das Management-Command `seed_market` publiziert die lokalen Referenz-Specs
  (MIT) und die Commercial-Beispiel-Spec ohne 2FA-Reibung in den Market.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from speccify_registry.api.models import Scope, Spec, SpecVersion

pytestmark = pytest.mark.django_db


def _publish_spec(*, owner: str, scope: str, name: str, license_: str, version: str = "0.1.0") -> None:
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=owner)
    scope_obj, _ = Scope.objects.get_or_create(name=scope, defaults={"owner": user})
    yaml_bytes = (
        f'id: "@{scope}/{name}"\nversion: {version}\nkind: ui-component\n'
        f"title: {name}\nlicense: {license_}\n"
    ).encode()
    spec = Spec.objects.create(scope=scope_obj, name=name)
    SpecVersion.objects.create(
        spec=spec,
        version=version,
        yaml_bytes=yaml_bytes,
        sha256="b" * 64,
        uploader=user,
    )


# --- Lizenz-Badge ------------------------------------------------------


def test_home_shows_license_for_mit_and_commercial() -> None:
    _publish_spec(owner="alice", scope="org", name="button", license_="MIT")
    _publish_spec(owner="alice", scope="acme-pro", name="rating", license_="Commercial")
    body = Client().get("/").content.decode()
    assert "MIT" in body
    assert "Commercial" in body
    # MIT bekommt den Open-Source-Hinweis, Commercial den proprietären.
    assert "Open-Source-Lizenz" in body
    assert "Proprietäre/kommerzielle Lizenz" in body


def test_spec_detail_shows_commercial_license_badge() -> None:
    _publish_spec(owner="alice", scope="acme-pro", name="rating", license_="Commercial")
    body = Client().get("/specs/acme-pro/rating").content.decode()
    assert "License:" in body
    assert "Commercial" in body
    assert "Proprietäre/kommerzielle Lizenz" in body


def test_license_badge_absent_when_field_missing() -> None:
    # yaml_bytes ohne license-Feld → kein Badge, sondern Platzhalter.
    User = get_user_model()
    user = User.objects.create(username="alice")
    scope = Scope.objects.create(name="org", owner=user)
    spec = Spec.objects.create(scope=scope, name="nolic")
    SpecVersion.objects.create(
        spec=spec,
        version="0.1.0",
        yaml_bytes=b'id: "@org/nolic"\nversion: 0.1.0\n',
        sha256="c" * 64,
        uploader=user,
    )
    body = Client().get("/specs/org/nolic").content.decode()
    assert "License:" not in body


# --- seed_market -------------------------------------------------------


def test_seed_market_publishes_mit_and_commercial() -> None:
    out = StringIO()
    call_command("seed_market", stdout=out, stderr=StringIO())

    # Die fünf Phase-0-Referenz-Specs sind MIT-lizenziert ...
    assert Spec.objects.filter(scope__name="org", name="button").exists()
    # ... und mindestens eine Commercial-Spec ist im Market.
    assert Spec.objects.filter(scope__name="acme-pro", name="rating-stars").exists()

    # Browse zeigt beide Lizenz-Typen.
    body = Client().get("/").content.decode()
    assert "MIT" in body
    assert "Commercial" in body
    assert "publiziert" in out.getvalue()


def test_seed_market_is_idempotent() -> None:
    call_command("seed_market", stdout=StringIO(), stderr=StringIO())
    count_after_first = SpecVersion.objects.count()
    second = StringIO()
    call_command("seed_market", stdout=second, stderr=StringIO())
    # Kein Doppel-Publish: identische Bytes werden übersprungen.
    assert SpecVersion.objects.count() == count_after_first
    assert "übersprungen" in second.getvalue()
