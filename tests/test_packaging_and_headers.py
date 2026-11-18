from __future__ import annotations

import importlib
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from viodigital import build_static
from viodigital.api import app as api_module
from viodigital.api.app import WEB_DIR, app
from viodigital.build_static import build, build_wheel, compute_core_hash, generate_llms_txt
from viodigital.core.__meta__ import __version__

ROOT_DIR = Path(__file__).resolve().parent.parent
MINIMAL_VIOWEB_SHIMS = frozenset(
    {
        "vioweb/__init__.py",
        "vioweb/__main__.py",
        "vioweb/build_static.py",
        "vioweb/core/__init__.py",
        "vioweb/api/__init__.py",
        "vioweb/api/app.py",
    }
)


def _header_map(rule: Dict[str, Any]) -> Dict[str, str]:
    return {h["key"]: h["value"] for h in rule.get("headers", [])}


def test_vercel_json_cache_rule_ordering_and_directives():
    """Garante ordenação e diretivas de Cache-Control e CSP estrita em vercel.json."""
    config = json.loads((ROOT_DIR / "vercel.json").read_text(encoding="utf-8"))
    rules = config["headers"]
    by_source = {rule["source"]: (idx, _header_map(rule)) for idx, rule in enumerate(rules)}

    for required in ("/(.*)", "/static/(.*)", "/static/vendor/(.*)", "/static/version.json", "/sw.js"):
        assert required in by_source, f"Regra ausente em vercel.json: {required}"

    global_csp = by_source["/(.*)"][1]["Content-Security-Policy"]
    assert "default-src 'self'" in global_csp
    assert "connect-src 'self'" in global_csp
    assert "'wasm-unsafe-eval'" in global_csp
    assert "'unsafe-eval'" not in global_csp

    static_idx, static_headers = by_source["/static/(.*)"]
    static_cc = static_headers["Cache-Control"]
    assert "max-age=0" in static_cc
    assert "must-revalidate" in static_cc
    assert "immutable" not in static_cc

    vendor_idx, vendor_headers = by_source["/static/vendor/(.*)"]
    vendor_cc = vendor_headers["Cache-Control"]
    assert vendor_idx > static_idx, "/static/vendor/(.*) deve vir após /static/(.*) para sobrescrever cache"
    assert "immutable" in vendor_cc
    assert "max-age=31536000" in vendor_cc

    version_idx, version_headers = by_source["/static/version.json"]
    version_cc = version_headers["Cache-Control"]
    assert version_idx > static_idx, "/static/version.json deve vir após /static/(.*)"
    for directive in ("no-cache", "no-store", "must-revalidate"):
        assert directive in version_cc
    assert "immutable" not in version_cc

    sw_cc = by_source["/sw.js"][1]["Cache-Control"]
    for directive in ("no-cache", "no-store", "must-revalidate"):
        assert directive in sw_cc
    assert "immutable" not in sw_cc


def test_api_cache_control_segregation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Garante que o servidor FastAPI segrega Cache-Control entre app/HTML, no-store e vendor imutável."""
    client = TestClient(app)

    for no_store_path in ("/api/version", "/sw.js"):
        res = client.get(no_store_path)
        assert res.status_code == 200, f"Falha ao acessar {no_store_path}"
        cc = res.headers.get("cache-control", "")
        for directive in ("no-cache", "no-store", "must-revalidate"):
            assert directive in cc
        assert "immutable" not in cc

    no_cache_paths = (
        "/",
        "/documentos",
        "/apoiar",
        "/privacidade",
        "/api-comercial",
        "/validar-crlv",
        "/static/app.js",
        "/static/bpgdec8.js",
        "/static/style.css",
        f"/static/wheels/viodigital-{__version__}-py3-none-any.whl",
    )
    for path in no_cache_paths:
        res = client.get(path)
        assert res.status_code == 200, f"Falha ao acessar {path}"
        cc = res.headers.get("cache-control", "")
        assert cc == "no-cache", f"Cache-Control inesperado em {path}: {cc!r}"

    vendor_sample = WEB_DIR / "static" / "vendor" / "pyodide" / "pyodide.js"
    if not vendor_sample.exists():
        static_route = next((r for r in app.routes if getattr(r, "name", None) == "static"), None)
        assert static_route is not None
        fake_static = tmp_path / "static"
        fake_vendor_file = fake_static / "vendor" / "pyodide" / "pyodide.js"
        fake_vendor_file.parent.mkdir(parents=True, exist_ok=True)
        fake_vendor_file.write_text("// deterministic vendor probe", encoding="utf-8")
        monkeypatch.setattr(
            static_route.app,
            "all_directories",
            [*static_route.app.all_directories, str(fake_static)],
        )

    vendor_res = client.get("/static/vendor/pyodide/pyodide.js")
    assert vendor_res.status_code == 200
    vendor_cc = vendor_res.headers.get("cache-control", "")
    assert "immutable" in vendor_cc
    assert "max-age=31536000" in vendor_cc


def test_static_build_csp_precache_sitemap_and_clean_wheel(tmp_path: Path):
    """Valida CSP estrita e offline-first em todos os HTMLs, links de rodapé, SEO e wheel limpa."""
    dist = build(tmp_path / "dist")

    html_files = sorted(dist.rglob("*.html"))
    assert len(html_files) >= 15
    for html_file in html_files:
        html_text = html_file.read_text(encoding="utf-8")
        assert "'unsafe-eval'" not in html_text, f"'unsafe-eval' encontrado em {html_file}"
        assert 'http-equiv="Content-Security-Policy"' in html_text, f"CSP ausente em {html_file}"
        assert "fonts.googleapis.com" not in html_text, f"Fonte externa encontrada em {html_file}"
        assert "fonts.gstatic.com" not in html_text, f"Fonte externa encontrada em {html_file}"

    html_404 = (dist / "404.html").read_text(encoding="utf-8")
    assert "connect-src 'self'" in html_404
    assert "'wasm-unsafe-eval'" in html_404

    for page_name in ("index.html", "documentos.html", "apoiar.html", "privacidade.html", "api.html"):
        page_text = (dist / page_name).read_text(encoding="utf-8")
        footer_start = page_text.index('<footer class="app-footer">')
        footer_end = page_text.index("</footer>", footer_start)
        footer_html = page_text[footer_start:footer_end]
        assert 'href="/api-comercial"' in footer_html, f"Rodapé sem /api-comercial em {page_name}"
        assert 'href="/privacidade"' in footer_html, f"Rodapé sem /privacidade em {page_name}"

    ET.fromstring((dist / "sitemap.xml").read_text(encoding="utf-8"))
    for seo_artifact in ("sitemap.xml", "robots.txt", "llms.txt"):
        artifact_text = (dist / seo_artifact).read_text(encoding="utf-8")
        assert "viodigital.com.br" not in artifact_text
        assert "viodigital.vercel.app" not in artifact_text
    assert "https://vioweb.vercel.app/api-comercial" in (dist / "llms.txt").read_text(encoding="utf-8")

    wheels = list((dist / "static" / "wheels").glob("viodigital-*.whl"))
    assert len(wheels) == 1
    assert wheels[0].name == f"viodigital-{__version__}-py3-none-any.whl"
    with zipfile.ZipFile(wheels[0]) as zf:
        names = set(zf.namelist())

    assert not any(name.startswith("vioweb/web/") for name in names)
    vioweb_entries = {name for name in names if name.startswith("vioweb/")}
    assert vioweb_entries == MINIMAL_VIOWEB_SHIMS
    assert "viodigital/core/checker.py" in names
    assert "viodigital/core/data/templates.json" in names


def test_compute_core_hash_invalidates_on_vioweb_and_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Garante que compute_core_hash invalida quando src/vioweb, pyproject.toml ou core mudam."""
    fake_root = tmp_path / "repo"
    fake_src = fake_root / "src"
    (fake_src / "viodigital" / "core").mkdir(parents=True)
    (fake_src / "vioweb").mkdir(parents=True)

    core_file = fake_src / "viodigital" / "core" / "mod.py"
    init_file = fake_src / "viodigital" / "__init__.py"
    vioweb_file = fake_src / "vioweb" / "__init__.py"
    pyproject_file = fake_root / "pyproject.toml"

    core_file.write_text("X = 1\n", encoding="utf-8")
    init_file.write_text("", encoding="utf-8")
    vioweb_file.write_text("Y = 1\n", encoding="utf-8")
    pyproject_file.write_text('[project]\nversion = "0.2.0"\n', encoding="utf-8")

    monkeypatch.setattr(build_static, "ROOT_DIR", fake_root)
    monkeypatch.setattr(build_static, "SRC_DIR", fake_src)

    h0 = compute_core_hash()
    vioweb_file.write_text("Y = 2\n", encoding="utf-8")
    h1 = compute_core_hash()
    assert h1 != h0

    pyproject_file.write_text('[project]\nversion = "0.2.1"\n', encoding="utf-8")
    h2 = compute_core_hash()
    assert h2 != h1

    core_file.write_text("X = 2\n", encoding="utf-8")
    h3 = compute_core_hash()
    assert h3 != h2


def test_build_wheel_cleans_stale_build_cache_and_old_wheels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Garante limpeza de build/ e wheels antigas ao reconstruir wheel em build_wheel()."""
    stale_marker = ROOT_DIR / "build" / "lib" / "vioweb" / "web" / "stale.html"
    stale_marker.parent.mkdir(parents=True, exist_ok=True)
    stale_marker.write_text("stale", encoding="utf-8")

    wheels_dir = tmp_path / "wheels"
    wheels_dir.mkdir(parents=True)
    old_viodigital = wheels_dir / "viodigital-0.0.1-py3-none-any.whl"
    old_vioweb = wheels_dir / "vioweb-0.0.1-py3-none-any.whl"
    old_viodigital.write_bytes(b"old")
    old_vioweb.write_bytes(b"old")

    monkeypatch.setattr(build_static, "_is_wheel_stale", lambda _d: True)
    built = build_wheel(wheels_dir)

    assert built is not None and built.exists()
    assert not stale_marker.exists()
    assert not old_viodigital.exists()
    assert not old_vioweb.exists()
    assert (wheels_dir / f"viodigital-{__version__}-py3-none-any.whl").exists()
    assert (wheels_dir / f"vioweb-{__version__}-py3-none-any.whl").exists()
    assert (wheels_dir / ".wheel_hash").read_text(encoding="utf-8") == compute_core_hash()

    with zipfile.ZipFile(built) as zf:
        assert not any(name.startswith("vioweb/web/") for name in zf.namelist())


def test_llms_txt_route_and_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Garante que llms.txt e seu fallback incluem a rota comercial B2B."""
    client = TestClient(app)
    res = client.get("/llms.txt")
    assert res.status_code == 200
    assert "https://vioweb.vercel.app/api-comercial" in res.text

    empty_web = tmp_path / "empty_web"
    empty_web.mkdir()
    monkeypatch.setattr(build_static, "WEB_DIR", empty_web)
    monkeypatch.setattr(api_module, "WEB_DIR", empty_web)

    fallback_text = generate_llms_txt()
    assert "https://vioweb.vercel.app/api-comercial" in fallback_text

    fallback_res = client.get("/llms.txt")
    assert fallback_res.status_code == 200
    assert fallback_res.text == fallback_text


def test_readme_uses_canonical_domain():
    """Garante ausência de domínios não adquiridos/legados e adoção de vioweb.vercel.app no README."""
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    assert "viodigital.com.br" not in readme
    assert "viodigital.vercel.app" not in readme
    assert "https://vioweb.vercel.app" in readme
    assert "https://vioweb.vercel.app/privacidade" in readme
    assert "https://vioweb.vercel.app/apoiar" in readme


def test_vioweb_compatibility_shims_and_clean_tree():
    """Garante que os shims mínimos vioweb delegam para viodigital sem resíduos legados na árvore."""
    vioweb_pkg = importlib.import_module("vioweb")
    vioweb_api = importlib.import_module("vioweb.api")
    vioweb_build = importlib.import_module("vioweb.build_static")
    vioweb_main = importlib.import_module("vioweb.__main__")

    viodigital_build = importlib.import_module("viodigital.build_static")
    viodigital_main = importlib.import_module("viodigital.__main__")

    assert vioweb_pkg.__version__ == __version__
    assert vioweb_api is not None
    assert vioweb_build.build is viodigital_build.build
    assert vioweb_build.generate_sitemap_xml is viodigital_build.generate_sitemap_xml
    assert vioweb_main.main is viodigital_main.main

    vioweb_src = ROOT_DIR / "src" / "vioweb"
    assert not (vioweb_src / "web").exists()
    actual_files = {
        f"vioweb/{p.relative_to(vioweb_src).as_posix()}"
        for p in vioweb_src.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }
    assert actual_files == MINIMAL_VIOWEB_SHIMS
