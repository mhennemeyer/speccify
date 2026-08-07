"""Tests für `scripts/sync_docs_to_site.py` (Phase 6, Stage 2)."""

from __future__ import annotations

import sync_docs_to_site as sync


def test_render_mdx_frontmatter_and_banner() -> None:
    markdown = "# Titel — mit Dash\n\nErste Zeile.\nZweite Zeile.\n\nMehr Text.\n"
    rendered = sync.render_mdx(markdown)

    assert rendered.startswith("---\n")
    assert 'title: "Titel — mit Dash"' in rendered
    assert 'description: "Erste Zeile. Zweite Zeile."' in rendered
    assert sync._GENERATED_BANNER in rendered
    # H1 darf nicht doppelt im Body stehen (Starlight rendert Titel aus Frontmatter).
    assert "# Titel — mit Dash" not in rendered


def test_render_mdx_rewrites_relative_links() -> None:
    markdown = "# Playbooks\n\nSee [git](./git-sources.md) and [viewer](./viewer.md#selection).\n"
    rendered = sync.render_mdx(markdown)

    assert "](/git-sources/)" in rendered
    assert "](/viewer/#selection)" in rendered
    assert "./visual-regression.md" not in rendered.split("---", 2)[-1]


def test_render_mdx_keeps_external_links() -> None:
    markdown = "# T\n\nText.\n\n[Extern](https://example.com).\n"
    assert "https://example.com" in sync.render_mdx(markdown)


def test_render_mdx_points_repo_files_at_github() -> None:
    """Ein Link auf eine Repo-Datei ist auf der Site sonst ein 404.

    Der Sync kennt nur die Seiten, die er selbst erzeugt. Alles andere
    Relative zeigt auf eine Datei im Repository — die gibt es unter der
    Doku-URL nicht, und niemandem fällt es auf, weil der Link plausibel
    aussieht.
    """
    markdown = (
        "# T\n\nText.\n\n"
        "[Schema](../schema/playbook.schema.json) "
        "[Nachbar](./local-dev-e2e.md) "
        "[Index](../index/README.md#format).\n"
    )
    rendered = sync.render_mdx(markdown)

    blob = "https://github.com/mhennemeyer/speccify/blob/main"
    assert f"{blob}/schema/playbook.schema.json" in rendered
    # `./x` liegt in docs/, `../x` ist repo-relativ — der Pfad muss das treffen.
    assert f"{blob}/docs/local-dev-e2e.md" in rendered
    # Anker bleiben erhalten.
    assert f"{blob}/index/README.md#format" in rendered
    assert "../schema" not in rendered


def test_check_is_green_after_write() -> None:
    assert sync.run_sync(check=False) == 0
    assert sync.run_sync(check=True) == 0


def test_check_detects_drift_and_write_heals(tmp_path) -> None:
    target = sync.DOC_MAPPINGS[0]
    dest = sync._SITE_DOCS_DIR / target.dest
    original = dest.read_text(encoding="utf-8")
    try:
        dest.write_text(original + "\nDRIFT\n", encoding="utf-8")
        assert sync.run_sync(check=True) == 1
        assert sync.run_sync(check=False) == 0
        assert sync.run_sync(check=True) == 0
    finally:
        sync.run_sync(check=False)
