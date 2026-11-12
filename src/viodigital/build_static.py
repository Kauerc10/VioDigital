"""Script de geração e build estático do VioDigital para deploy e self-host offline.

Gera o diretório estático ``dist/`` contendo:
- Páginas HTML completas (index, documentos, apoiar, privacidade).
- Catálogo de templates embutido diretamente para navegação 100% offline.
- Landing pages SEO (validar-crlv, validar-cnh, validar-atpv, etc.).
- ``robots.txt`` e ``sitemap.xml`` estáticos.
- Cópia de todos os ativos estáticos (CSS, JS, WebAssembly).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

WEB_DIR = Path(__file__).resolve().parent / "web"
STATIC_DIR = WEB_DIR / "static"

from viodigital.core.registry import default_templates

SEO_DOC_PAGES: Dict[str, Dict[str, str]] = {
    "crlv": {
        "title": "Validar QR Code CRLV-e Digital e CRV-e RENAVE no PC (Grátis) — VioDigital",
        "description": "Valide gratuitamente o QR Code VIO do CRLV-e Digital (Templates 10, 12, 62, 70) e CRV-e RENAVE (Template 24) no computador por PDF, Ctrl+V ou Webcam. Extração imediata de Placa, RENAVAM, Chassi e Proprietário.",
        "hero_title": "Validador Oficial de CRLV-e Digital e CRV-e RENAVE",
        "hero_subtitle": "Arraste o PDF do CRLV-e recebido no WhatsApp, cole um print (Ctrl+V) ou aponte o documento impresso para a webcam para validar a assinatura Serpro/SENATRAN e copiar Placa, RENAVAM, Chassi e CPF/CNPJ.",
    },
    "cnh": {
        "title": "Validar QR Code CNH Digital e Física no Computador (Com Foto 3x4) — VioDigital",
        "description": "Leia e valide gratuitamente o QR Code da CNH Digital e Física no PC (Templates VIO 2, 4 e 83). Verifica a assinatura digital SENATRAN e decodifica a fotografia biométrica BPG 3x4 do condutor.",
        "hero_title": "Validador de CNH Digital e Física (Com Fotografia Biométrica)",
        "hero_subtitle": "Confira a autenticidade da Carteira Nacional de Habilitação pelo computador, visualize a fotografia biométrica 3x4 assinada pelo Serpro e copie CPF, Registro, RENACH, Filiação e Validade em 1 clique.",
    },
    "atpv": {
        "title": "Validar QR Code ATPV-e (Intenção de Venda) para Cartório no PC — VioDigital",
        "description": "Valide gratuitamente a ATPV-e (Autorização para Transferência de Propriedade de Veículo — Template VIO 43) no computador. Extrai dados completos do Vendedor, Comprador, Valor da Venda, Hodômetro e CRV para reconhecimento de firma.",
        "hero_title": "Validador Notarial de ATPV-e (Intenção de Venda)",
        "hero_subtitle": "Conferência instantânea de ATPV-e para reconhecimento de firma em cartório: valida o QR Code VIO mesmo em páginas com Selo Digital do TJ e extrai Vendedor, Comprador, Placa, Chassi, Valor e Hodômetro.",
    },
    "cin": {
        "title": "Validar QR Code CIN / Novo RG Nacional (ICP-Brasil) no PC — VioDigital",
        "description": "Verifique gratuitamente o QR Code da Carteira de Identidade Nacional (CIN / Novo RG), RG Digital Estadual e DNI diretamente no computador com validação criptográfica ES512 ICP-Brasil.",
        "hero_title": "Validador de CIN (Carteira de Identidade Nacional / Novo RG)",
        "hero_subtitle": "Verifique a assinatura digital ICP-Brasil (ES512) do QR Code da nova Carteira de Identidade Nacional, RG Digital Estadual e DNI diretamente pelo navegador ou webcam.",
    },
    "tie-marinha": {
        "title": "Validar QR Code TIE (Título de Inscrição de Embarcação) e CHA da Marinha — VioDigital",
        "description": "Valide gratuitamente documentos náuticos da Marinha do Brasil (DPC) com QR Code VIO: TIE (Título de Inscrição de Embarcação PF e PJ — Templates 116 e 118) e CHA (Carteira de Habilitação de Amador e Motonauta).",
        "hero_title": "Validador de TIE (Embarcações) e CHA da Marinha do Brasil",
        "hero_subtitle": "Ideal para cartórios litorâneos e despachantes marítimos: valide a autenticidade do Título de Inscrição de Embarcação (TIE PF/PJ) e Carteira de Arrais/Motonauta (CHA) extraindo todos os 34 campos oficiais.",
    },
}


def render_seo_page(index_html: str, slug: str, meta: Dict[str, str]) -> str:
    canonical_url = f"https://viodigital.com.br/validar-{slug}"
    html = re.sub(r"<title>.*?</title>", f"<title>{meta['title']}</title>", index_html, flags=re.DOTALL)
    html = re.sub(
        r'<meta name="description" content=".*?">',
        f'<meta name="description" content="{meta["description"]}">',
        html,
    )
    html = re.sub(
        r'<link rel="canonical" href=".*?">',
        f'<link rel="canonical" href="{canonical_url}">',
        html,
    )
    html = re.sub(
        r'<meta property="og:title" content=".*?">',
        f'<meta property="og:title" content="{meta["title"]}">',
        html,
    )
    html = re.sub(
        r'<meta property="og:description" content=".*?">',
        f'<meta property="og:description" content="{meta["description"]}">',
        html,
    )
    html = re.sub(
        r'<meta property="og:url" content=".*?">',
        f'<meta property="og:url" content="{canonical_url}">',
        html,
    )
    html = html.replace(
        '<h2 id="hero-title">Validação de Documentos Oficiais</h2>',
        f'<h2 id="hero-title">{meta["hero_title"]}</h2>',
    )
    html = re.sub(
        r'<p class="dropzone-hint" id="hero-subtitle">.*?</p>',
        f'<p class="dropzone-hint" id="hero-subtitle">{meta["hero_subtitle"]}</p>',
        html,
    )
    return html


def get_templates_catalog_data() -> Dict[str, Any]:
    templates_store = default_templates()
    templates_list = []
    by_id = getattr(templates_store, "_by_id", {})
    for tpl_id in sorted(by_id.keys()):
        tpl = by_id[tpl_id]
        templates_list.append({
            "id": tpl.id,
            "name": tpl.name,
            "owner": tpl.owner,
            "fields_count": len(tpl.field_names),
        })

    return {
        "total_templates": len(templates_list),
        "cin_supported": True,
        "templates": templates_list,
    }


def generate_robots_txt() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/documents/\n\n"
        "Sitemap: https://viodigital.com.br/sitemap.xml\n"
    )


def generate_sitemap_xml() -> str:
    urls = [
        ("https://viodigital.com.br/", "1.0"),
        ("https://viodigital.com.br/documentos", "0.9"),
        ("https://viodigital.com.br/privacidade", "0.9"),
        ("https://viodigital.com.br/validar-crlv", "0.9"),
        ("https://viodigital.com.br/validar-cnh", "0.9"),
        ("https://viodigital.com.br/validar-atpv", "0.9"),
        ("https://viodigital.com.br/validar-cin", "0.8"),
        ("https://viodigital.com.br/validar-tie-marinha", "0.8"),
        ("https://viodigital.com.br/apoiar", "0.7"),
    ]
    items = "\n".join(
        f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        for loc, prio in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{items}\n"
        "</urlset>\n"
    )


def _build_wheel_pure_python(wheels_dir: Path) -> Path:
    """Fallback puro Python para gerar a wheel do vioweb sem depender de ferramentas externas."""
    import zipfile

    wheels_dir.mkdir(parents=True, exist_ok=True)
    target_whl = wheels_dir / "viodigital-0.2.0-py3-none-any.whl"
    src_pkg = ROOT_DIR / "src" / "viodigital"
    dist_info = "vioweb-0.2.0.dist-info"

    with zipfile.ZipFile(target_whl, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in src_pkg.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                if "vendor" in p.parts or "wheels" in p.parts:
                    continue
                rel = p.relative_to(src_pkg)
                z.write(p, arcname=f"viodigital/{rel.as_posix()}")

        z.writestr(
            f"{dist_info}/METADATA",
            "Metadata-Version: 2.1\nName: viodigital\nVersion: 0.2.0\nSummary: Verificador Serpro VIO e CIN\n",
        )
        z.writestr(
            f"{dist_info}/WHEEL",
            "Wheel-Version: 1.0\nGenerator: viodigital-internal (0.2.0)\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        z.writestr(f"{dist_info}/top_level.txt", "viodigital\n")

    return target_whl


def build_wheel(wheels_dir: Path) -> Path | None:
    wheels_dir.mkdir(parents=True, exist_ok=True)
    # Reutiliza wheel em cache se já existir e não for a pasta de destino
    default_dist_wheels = ROOT_DIR / "dist" / "static" / "wheels"
    if default_dist_wheels.exists() and wheels_dir != default_dist_wheels:
        cached = list(default_dist_wheels.glob("viodigital-*.whl"))
        if cached:
            target = wheels_dir / cached[0].name
            shutil.copy2(cached[0], target)
            return target

    src_wheels = STATIC_DIR / "wheels"
    if src_wheels.exists() and wheels_dir != src_wheels:
        cached = list(src_wheels.glob("viodigital-*.whl"))
        if cached:
            target = wheels_dir / cached[0].name
            shutil.copy2(cached[0], target)
            return target

    uv_bin = shutil.which("uv")
    commands_to_try = []
    if uv_bin:
        commands_to_try.append([uv_bin, "build", "--wheel", "--out-dir", str(wheels_dir)])
    commands_to_try.append([sys.executable, "-m", "build", "--wheel", "--out-dir", str(wheels_dir)])
    commands_to_try.append([sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(wheels_dir), str(ROOT_DIR)])

    for cmd in commands_to_try:
        try:
            res = subprocess.run(cmd, cwd=ROOT_DIR, check=False, capture_output=True, text=True)
            if res.returncode == 0:
                built = list(wheels_dir.glob("viodigital-*.whl"))
                if built:
                    return built[0]
        except Exception:
            continue

    # Fallback autossuficiente caso nenhum comando de build do sistema tenha sucedido
    try:
        ret = _build_wheel_pure_python(wheels_dir)
    except Exception:
        built = list(wheels_dir.glob("viodigital-*.whl"))
        ret = built[0] if built else None

    if ret:
        legacy_alias = wheels_dir / "vioweb-0.2.0-py3-none-any.whl"
        try:
            shutil.copy2(ret, legacy_alias)
        except Exception:
            pass

    return ret


def _download_file(url: str, dest: Path) -> None:
    import urllib.request

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 VioDigital-Builder"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def ensure_vendor_assets(vendor_dir: Path, download: bool = True) -> None:
    vendor_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = ROOT_DIR / ".vendor_cache"
    pyodide_cache = cache_dir / "pyodide"
    zxing_cache = cache_dir / "zxing"
    pdfjs_cache = cache_dir / "pdfjs"
    pyodide_cache.mkdir(parents=True, exist_ok=True)
    zxing_cache.mkdir(parents=True, exist_ok=True)
    pdfjs_cache.mkdir(parents=True, exist_ok=True)

    pyodide_target = vendor_dir / "pyodide"
    zxing_target = vendor_dir / "zxing"
    pdfjs_target = vendor_dir / "pdfjs"
    pyodide_target.mkdir(parents=True, exist_ok=True)
    zxing_target.mkdir(parents=True, exist_ok=True)
    pdfjs_target.mkdir(parents=True, exist_ok=True)

    pyodide_base = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"
    pyodide_files = [
        "pyodide.js",
        "pyodide.asm.js",
        "pyodide.asm.wasm",
        "python_stdlib.zip",
        "pyodide-lock.json",
        "cryptography-42.0.5-cp312-cp312-pyodide_2024_0_wasm32.whl",
        "cffi-1.16.0-cp312-cp312-pyodide_2024_0_wasm32.whl",
        "pycparser-2.22-py3-none-any.whl",
        "openssl-1.1.1n.zip",
        "six-1.16.0-py2.py3-none-any.whl",
    ]

    for fname in pyodide_files:
        cached_file = pyodide_cache / fname
        if not cached_file.exists() and download:
            try:
                _download_file(pyodide_base + fname, cached_file)
            except Exception as e:
                print(f"Aviso: Não foi possível baixar {fname}: {e}")
        if cached_file.exists():
            shutil.copy2(cached_file, pyodide_target / fname)

    zxing_files = {
        "zxing_reader.js": "https://cdn.jsdelivr.net/npm/zxing-wasm@3.1.6/dist/iife/reader/index.js",
        "zxing_reader.wasm": "https://cdn.jsdelivr.net/npm/zxing-wasm@3.1.6/dist/reader/zxing_reader.wasm",
    }
    for fname, url in zxing_files.items():
        cached_file = zxing_cache / fname
        if not cached_file.exists() and download:
            try:
                _download_file(url, cached_file)
            except Exception as e:
                print(f"Aviso: Não foi possível baixar {fname}: {e}")
        if cached_file.exists():
            shutil.copy2(cached_file, zxing_target / fname)

    pdfjs_files = {
        "pdf.min.js": "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.min.js",
        "pdf.worker.min.js": "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js",
    }
    for fname, url in pdfjs_files.items():
        cached_file = pdfjs_cache / fname
        if not cached_file.exists() and download:
            try:
                _download_file(url, cached_file)
            except Exception as e:
                print(f"Aviso: Não foi possível baixar {fname}: {e}")
        if cached_file.exists():
            shutil.copy2(cached_file, pdfjs_target / fname)


def ensure_runtime_assets(target_web_dir: Path, download: bool = True) -> None:
    """Provisiona todos os ativos necessários para o pipeline de execução 100% no navegador."""
    static_dir = target_web_dir / "static"
    wheels_dir = static_dir / "wheels"
    vendor_dir = static_dir / "vendor"

    # 1. Garante a wheel do vioweb
    has_wheel = wheels_dir.exists() and bool(list(wheels_dir.glob("viodigital-*.whl")))
    if not has_wheel:
        build_wheel(wheels_dir)

    # 2. Garante os ativos de terceiros (ZXing WASM, Pyodide, PDF.js)
    ensure_vendor_assets(vendor_dir, download=download)


def _safe_clean_dir(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return
    import time

    for item in list(path.iterdir()):
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        except Exception:
            time.sleep(0.1)
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
            except Exception:
                pass


def build(output_dir: Path | str = "dist") -> Path:
    out = Path(output_dir).resolve()
    _safe_clean_dir(out)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Copia static
    dist_static = out / "static"
    shutil.copytree(STATIC_DIR, dist_static, dirs_exist_ok=True)

    # 2. Compila wheel do vioweb e disponibiliza em static/wheels/
    wheel_path = build_wheel(dist_static / "wheels")
    if wheel_path and out == ROOT_DIR / "dist":
        src_wheels = STATIC_DIR / "wheels"
        src_wheels.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wheel_path, src_wheels / wheel_path.name)

    # 3. Garante ativos vendor do Pyodide e ZXing WASM em static/vendor/
    ensure_vendor_assets(dist_static / "vendor")
    if out == ROOT_DIR / "dist":
        ensure_vendor_assets(STATIC_DIR / "vendor")

    # 4. Gera templates-data.json
    tpl_data = get_templates_catalog_data()
    tpl_json_path = dist_static / "templates-data.json"
    tpl_json_path.write_text(json.dumps(tpl_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. Páginas HTML principais
    index_file = WEB_DIR / "index.html"
    index_html = index_file.read_text(encoding="utf-8")
    (out / "index.html").write_text(index_html, encoding="utf-8")

    # documentos.html com injeção de templates data embutido
    doc_file = WEB_DIR / "documentos.html"
    if doc_file.exists():
        doc_html = doc_file.read_text(encoding="utf-8")
        inject_script = f'<script>window.__TEMPLATES_DATA__ = {json.dumps(tpl_data["templates"], ensure_ascii=False)};</script>\n</head>'
        doc_html = doc_html.replace("</head>", inject_script, 1)
        (out / "documentos.html").write_text(doc_html, encoding="utf-8")
        # Diretório limpo para /documentos
        doc_dir = out / "documentos"
        doc_dir.mkdir(exist_ok=True)
        (doc_dir / "index.html").write_text(doc_html, encoding="utf-8")

    # apoiar.html
    apoiar_file = WEB_DIR / "apoiar.html"
    if apoiar_file.exists():
        apoiar_html = apoiar_file.read_text(encoding="utf-8")
        (out / "apoiar.html").write_text(apoiar_html, encoding="utf-8")
        apoiar_dir = out / "apoiar"
        apoiar_dir.mkdir(exist_ok=True)
        (apoiar_dir / "index.html").write_text(apoiar_html, encoding="utf-8")

    # api.html se existir
    api_file = WEB_DIR / "api.html"
    if api_file.exists():
        api_html = api_file.read_text(encoding="utf-8")
        (out / "api.html").write_text(api_html, encoding="utf-8")
        api_dir = out / "api-comercial"
        api_dir.mkdir(exist_ok=True)
        (api_dir / "index.html").write_text(api_html, encoding="utf-8")

    # privacidade.html se existir
    priv_file = WEB_DIR / "privacidade.html"
    if priv_file.exists():
        priv_html = priv_file.read_text(encoding="utf-8")
        (out / "privacidade.html").write_text(priv_html, encoding="utf-8")
        priv_dir = out / "privacidade"
        priv_dir.mkdir(exist_ok=True)
        (priv_dir / "index.html").write_text(priv_html, encoding="utf-8")

    # 4. Landing pages SEO (/validar-{slug})
    for slug, meta in SEO_DOC_PAGES.items():
        seo_html = render_seo_page(index_html, slug, meta)
        (out / f"validar-{slug}.html").write_text(seo_html, encoding="utf-8")
        slug_dir = out / f"validar-{slug}"
        slug_dir.mkdir(exist_ok=True)
        (slug_dir / "index.html").write_text(seo_html, encoding="utf-8")

    # 5. PWA e Favicon: sw.js, manifest.json e favicon.ico
    sw_file = WEB_DIR / "sw.js"
    if sw_file.exists():
        (out / "sw.js").write_text(sw_file.read_text(encoding="utf-8"), encoding="utf-8")
    manifest_file = WEB_DIR / "manifest.json"
    if manifest_file.exists():
        (out / "manifest.json").write_text(manifest_file.read_text(encoding="utf-8"), encoding="utf-8")
    favicon_file = WEB_DIR / "favicon.ico"
    if favicon_file.exists():
        shutil.copy2(favicon_file, out / "favicon.ico")

    # 6. robots.txt e sitemap.xml
    (out / "robots.txt").write_text(generate_robots_txt(), encoding="utf-8")
    (out / "sitemap.xml").write_text(generate_sitemap_xml(), encoding="utf-8")

    print(f"Build estático concluído com sucesso em: {out}")
    return out


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "dist"
    build(target)
