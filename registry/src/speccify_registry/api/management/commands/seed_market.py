"""``manage.py seed_market`` — füllt den lokalen Market für End-to-End-Dogfooding.

Der HTTP-Publish-Pfad verlangt einen frischen 2FA-Nachweis (siehe
``ApiToken.last_2fa_verified_at``) — für ein schnelles lokales Hochfahren ist
das zu viel Reibung. Dieses Command ruft daher die wiederverwendbare
Service-Funktion :func:`speccify_registry.api.publish.publish` direkt auf und
umgeht damit Auth/HTTP komplett. Es ist bewusst idempotent: identische Bytes
unter derselben ``id@version`` werden übersprungen.

Standardmäßig werden zwei Spec-Wurzeln publiziert:

* ``registry-fixtures/`` — die fünf Phase-0-Referenz-Specs (alle ``license: MIT``),
* ``example-commercial-specs/`` — mindestens eine ``license: Commercial`` Spec,

sodass der Market direkt MIT *und* proprietär lizenzierte Einträge zeigt.

Beispiel::

    uv run python -m speccify_registry.manage seed_market
    uv run python -m speccify_registry.manage seed_market --user alice
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...publish import PublishError, publish

User = get_user_model()

# settings.BASE_DIR == <repo>/registry; das Repo-Root liegt eine Ebene höher.
_REPO_ROOT = Path(settings.BASE_DIR).parent
_DEFAULT_ROOTS = ("registry-fixtures", "example-commercial-specs")
_SPEC_FILENAME = "spec.speccify.yaml"


def _iter_spec_files(root: Path) -> list[Path]:
    """Sammle alle ``<root>/<scope>/<name>/<version>/spec.speccify.yaml`` deterministisch."""
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob(_SPEC_FILENAME) if p.is_file())


class Command(BaseCommand):
    help = "Publiziert die lokalen Referenz- und Commercial-Specs in den Market (ohne 2FA)."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--user",
            default="marc",
            help="Username des Seed-Uploaders (wird bei Bedarf angelegt). Default: marc.",
        )
        parser.add_argument(
            "--roots",
            nargs="*",
            default=list(_DEFAULT_ROOTS),
            help=(
                "Spec-Wurzeln relativ zum Repo-Root (oder absolute Pfade). "
                f"Default: {' '.join(_DEFAULT_ROOTS)}."
            ),
        )

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        username: str = options["user"]
        roots: list[str] = options["roots"]

        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
            self.stdout.write(f"Seed-User '{username}' angelegt.")

        spec_files: list[Path] = []
        for raw in roots:
            root = Path(raw)
            if not root.is_absolute():
                root = _REPO_ROOT / root
            found = _iter_spec_files(root)
            if not found:
                self.stderr.write(self.style.WARNING(f"Keine Specs unter {root} gefunden."))
            spec_files.extend(found)

        if not spec_files:
            raise CommandError("Keine Spec-Dateien gefunden — nichts zu seeden.")

        published = 0
        skipped = 0
        failed = 0
        for spec_path in spec_files:
            yaml_bytes = spec_path.read_bytes()
            try:
                with transaction.atomic():
                    version, was_created = publish(user=user, yaml_bytes=yaml_bytes)
            except PublishError as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"  ✗ {spec_path}: {exc.code}: {exc.detail}"))
                continue
            if was_created:
                published += 1
                self.stdout.write(f"  ✓ published {version}")
            else:
                skipped += 1
                self.stdout.write(f"  · skipped (exists) {version}")

        summary = (
            f"Seed fertig: {published} publiziert, {skipped} übersprungen, {failed} fehlgeschlagen."
        )
        style = self.style.SUCCESS if failed == 0 else self.style.WARNING
        self.stdout.write(style(summary))
        if failed:
            raise CommandError(f"{failed} Spec(s) konnten nicht publiziert werden.")
