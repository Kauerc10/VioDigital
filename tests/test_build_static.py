from __future__ import annotations

import json
from pathlib import Path

from vioweb.build_static import SEO_DOC_PAGES, build


def test_build_static_generates_all_assets(tmp_path: Path):
    dist = build(tmp_path / "test_dist")

    assert (dist / "index.html").exists()
    assert (dist / "documentos.html").exists()
    assert (dist / "apoiar.html").exists()
    assert (dist / "robots.txt").exists()
    assert (dist / "sitemap.xml").exists()
    assert (dist / "static" / "style.css").exists()
    assert (dist / "static" / "app.js").exists()

    # Verifica templates-data.json
    tpl_json = dist / "static" / "templates-data.json"
    assert tpl_json.exists()
    data = json.loads(tpl_json.read_text(encoding="utf-8"))
    assert "templates" in data
    assert data["total_templates"] >= 160

    # Verifica injeção direta no documentos.html
    doc_html = (dist / "documentos.html").read_text(encoding="utf-8")
    assert "window.__TEMPLATES_DATA__ =" in doc_html

    # Verifica landing pages SEO
    for slug in SEO_DOC_PAGES:
        assert (dist / f"validar-{slug}.html").exists()
        assert (dist / f"validar-{slug}" / "index.html").exists()
        slug_html = (dist / f"validar-{slug}.html").read_text(encoding="utf-8")
        assert f"validar-{slug}" in slug_html
        assert SEO_DOC_PAGES[slug]["title"] in slug_html

    # Verifica robots e sitemap
    robots_text = (dist / "robots.txt").read_text(encoding="utf-8")
    assert "sitemap.xml" in robots_text
    sitemap_text = (dist / "sitemap.xml").read_text(encoding="utf-8")
    assert "<urlset" in sitemap_text
