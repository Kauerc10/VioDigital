from __future__ import annotations

import json
from pathlib import Path

from viodigital.build_static import SEO_DOC_PAGES, build


def test_build_static_generates_all_assets(tmp_path: Path):
    dist = build(tmp_path / "test_dist")

    assert (dist / "index.html").exists()
    assert (dist / "documentos.html").exists()
    assert (dist / "apoiar.html").exists()
    assert (dist / "privacidade.html").exists()
    assert (dist / "sw.js").exists()
    assert (dist / "manifest.json").exists()
    assert (dist / "robots.txt").exists()
    assert (dist / "sitemap.xml").exists()
    assert (dist / "llms.txt").exists()
    assert (dist / "404.html").exists()
    assert (dist / "static" / "style.css").exists()
    assert (dist / "static" / "app.js").exists()
    assert (dist / "static" / "camera-quality.js").exists()
    assert (dist / "static" / "scanner.worker.js").exists()
    assert (dist / "static" / "wheels").exists()
    assert any((dist / "static" / "wheels").glob("viodigital-*.whl"))
    assert any((dist / "static" / "wheels").glob("vioweb-*.whl"))
    assert (dist / "static" / "vendor" / "pyodide" / "pyodide.js").exists()
    assert (dist / "static" / "vendor" / "zxing" / "zxing_reader.js").exists()
    assert (dist / "static" / "vendor" / "pdfjs" / "pdf.min.js").exists()

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

    # Verifica version.json e injeção de hash no sw.js
    version_file = dist / "static" / "version.json"
    assert version_file.exists()
    ver_data = json.loads(version_file.read_text(encoding="utf-8"))
    assert "build_hash" in ver_data
    assert len(ver_data["build_hash"]) == 12
    sw_text = (dist / "sw.js").read_text(encoding="utf-8")
    assert "__BUILD_HASH__" not in sw_text
    assert ver_data["build_hash"] in sw_text


def test_wheel_staleness_detection(tmp_path: Path):
    from viodigital.build_static import _is_wheel_stale, build_wheel

    wheels_dir = tmp_path / "wheels"
    assert _is_wheel_stale(wheels_dir) is True

    build_wheel(wheels_dir)
    assert _is_wheel_stale(wheels_dir) is False

    # Simula alteração no código-fonte alterando o hash salvo
    (wheels_dir / ".wheel_hash").write_text("oldstalehash", encoding="utf-8")
    assert _is_wheel_stale(wheels_dir) is True
