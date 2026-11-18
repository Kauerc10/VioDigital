from __future__ import annotations

import importlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from viodigital.api.app import WEB_DIR, app
from viodigital.build_static import build

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


def _header_map(rule: dict) -> dict[str, str]:
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


def test_api_cache_control_segregation():
    """Garante que o servidor FastAPI segrega Cache-Control entre app e vendor imutável."""
    client = TestClient(app)

    ver = client.get("/api/version")
    assert ver.status_code == 200
    ver_cc = ver.headers.get("cache-control", "")
    for directive in ("no-cache", "no-store", "must-revalidate"):
        assert directive in ver_cc

    for path in ("/", "/static/app.js", "/static/wheels/viodigital-0.2.0-py3-none-any.whl"):
        res = client.get(path)
        assert res.status_code == 200, f"Falha ao acessar {path}"
        cc = res.headers.get("cache-control", "")
        assert "no-cache" in cc
        assert "immutable" not in cc

    vendor_sample = WEB_DIR / "static" / "vendor" / "pyodide" / "pyodide.js"
    if vendor_sample.exists():
        vendor_res = client.get("/static/vendor/pyodide/pyodide.js")
        assert vendor_res.status_code == 200
        vendor_cc = vendor_res.headers.get("cache-control", "")
        assert "immutable" in vendor_cc
        assert "max-age=31536000" in vendor_cc


def test_static_build_csp_precache_sitemap_and_clean_wheel(tmp_path: Path):
    """Valida CSP estrita em todos os HTMLs, /api-comercial em sitemap/sw e wheel sem legado vioweb/web."""
    dist = build(tmp_path / "dist")

    html_files = sorted(dist.rglob("*.html"))
    assert len(html_files) >= 15
    assert (dist / "404.html") in html_files
    assert (dist / "api-comercial" / "index.html") in html_files
    for html_file in html_files:
        html_text = html_file.read_text(encoding="utf-8")
        assert "'unsafe-eval'" not in html_text, f"'unsafe-eval' encontrado em {html_file}"

    sitemap_root = ET.fromstring((dist / "sitemap.xml").read_text(encoding="utf-8"))
    locs = {el.text for el in sitemap_root.iter() if el.tag.endswith("loc") and el.text}
    assert "https://viodigital.com.br/api-comercial" in locs
    for seo_artifact in ("sitemap.xml", "robots.txt", "llms.txt"):
        assert "viodigital.vercel.app" not in (dist / seo_artifact).read_text(encoding="utf-8")

    sw_text = (dist / "sw.js").read_text(encoding="utf-8")
    precache_match = re.search(r"const\s+PRECACHE_ASSETS\s*=\s*\[(.*?)\];", sw_text, flags=re.DOTALL)
    assert precache_match is not None, "PRECACHE_ASSETS não encontrado em dist/sw.js"
    precache_entries = re.findall(r"['\"]([^'\"]+)['\"]", precache_match.group(1))
    assert "/api-comercial" in precache_entries

    wheels = list((dist / "static" / "wheels").glob("viodigital-*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as zf:
        names = set(zf.namelist())

    assert not any(name.startswith("vioweb/web/") for name in names)
    vioweb_entries = {name for name in names if name.startswith("vioweb/")}
    assert vioweb_entries == MINIMAL_VIOWEB_SHIMS
    assert "viodigital/core/checker.py" in names
    assert "viodigital/core/data/templates.json" in names


def test_readme_uses_canonical_domain():
    """Garante ausência de links legados viodigital.vercel.app e adoção de viodigital.com.br no README."""
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    assert "viodigital.vercel.app" not in readme
    assert "https://viodigital.com.br" in readme
    assert "https://viodigital.com.br/privacidade" in readme
    assert "https://viodigital.com.br/apoiar" in readme


def test_vioweb_compatibility_shims_and_clean_tree():
    """Garante que os shims mínimos vioweb delegam para viodigital sem resíduos legados na árvore."""
    vioweb_pkg = importlib.import_module("vioweb")
    vioweb_core = importlib.import_module("vioweb.core")
    vioweb_api = importlib.import_module("vioweb.api")
    vioweb_app = importlib.import_module("vioweb.api.app")
    vioweb_build = importlib.import_module("vioweb.build_static")
    vioweb_main = importlib.import_module("vioweb.__main__")

    viodigital_core = importlib.import_module("viodigital.core")
    viodigital_app = importlib.import_module("viodigital.api.app")
    viodigital_build = importlib.import_module("viodigital.build_static")
    viodigital_main = importlib.import_module("viodigital.__main__")
    viodigital_meta = importlib.import_module("viodigital.core.__meta__")

    assert vioweb_pkg.__version__ == viodigital_meta.__version__
    assert vioweb_api is not None
    assert vioweb_core.DigitalDocumentChecker is viodigital_core.DigitalDocumentChecker
    assert vioweb_app.app is viodigital_app.app
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
