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
    markdown = (
        "# Conformance\n\nSiehe [VR](./visual-regression.md) und [WS](./workspaces.md#abschnitt).\n"
    )
    rendered = sync.render_mdx(markdown)

    assert "](/conformance/visual-regression/)" in rendered
    assert "](/workspaces/#abschnitt)" in rendered
    assert "./visual-regression.md" not in rendered.split("---", 2)[-1]


def test_render_mdx_keeps_unknown_links() -> None:
    markdown = "# T\n\nText.\n\n[Extern](https://example.com) [X](./unknown.md).\n"
    rendered = sync.render_mdx(markdown)

    assert "https://example.com" in rendered
    assert "./unknown.md" in rendered  # nicht im Mapping → unverändert


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
