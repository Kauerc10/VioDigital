from __future__ import annotations

import io
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Final

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from viodigital.api.app import app
from viodigital.build_static import SEO_DOC_PAGES, build
from viodigital.core.__meta__ import __version__

ROOT_DIR: Final[Path] = Path(__file__).resolve().parent.parent
CANONICAL_OG_IMAGE_URL: Final[str] = "https://viodigital.com.br/static/og-banner.png"
LEGACY_DOMAINS: Final[tuple[str, ...]] = ("vioweb.vercel.app", "viodigital.vercel.app")
REQUIRED_README_ASSETS: Final[tuple[str, ...]] = (
    "docs/assets/demo-validation.gif",
    "docs/assets/screenshot-result.png",
)
REQUIRED_README_MARKERS: Final[tuple[str, ...]] = (
    "```mermaid",
    "Zero-Network",
    "DevTools",
    "connect-src 'self'",
    "161",
    "docker compose",
    "python -m viodigital",
    "DETRAN",
    "RENAVAM",
)
REQUIRED_COMMUNITY_AND_DIST_FILES: Final[tuple[str, ...]] = (
    ".gitattributes",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "Dockerfile",
    ".dockerignore",
    "docker-compose.yml",
    "docs/launch-playbook.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/release-container.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/new_vio_template.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
)
VISUAL_ASSET_SPECS: Final[tuple[tuple[str, tuple[int, int], str], ...]] = (
    ("src/viodigital/web/static/og-banner.png", (1200, 630), "PNG"),
    ("docs/assets/social-preview.png", (1280, 640), "PNG"),
    ("docs/assets/screenshot-result.png", (960, 560), "PNG"),
    ("docs/assets/demo-validation.gif", (960, 560), "GIF"),
)
MAIN_HTML_PAGES: Final[tuple[str, ...]] = (
    "index.html",
    "documentos.html",
    "apoiar.html",
    "privacidade.html",
    "api.html",
)


def _extract_local_asset_paths(markdown_text: str) -> list[str]:
    """Extrai caminhos locais de assets Markdown/HTML (incluindo ``docs/assets/...``)."""
    paths: list[str] = []
    img_matches = re.findall(r'!\[[^\]]*\]\(([^)]+)\)|<img\b[^>]*\bsrc=["\']([^"\']+)["\']', markdown_text)
    for md_ref, html_ref in img_matches:
        ref = (md_ref or html_ref).strip()
        if ref and not ref.startswith(("http://", "https://", "mailto:", "#")):
            paths.append(ref.split("#", 1)[0].split("?", 1)[0])

    for docs_asset in re.findall(r"docs/assets/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*", markdown_text):
        paths.append(docs_asset)

    return sorted(set(paths))


class _MetaTagParser(HTMLParser):
    """Coleta atributos de todas as tags ``<meta>`` presentes em um documento HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.meta_tags: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "meta":
            self.meta_tags.append({k.lower(): (v or "") for k, v in attrs})


def _assert_opengraph_tags(html_text: str, page_name: str) -> None:
    """Valida que as meta tags ``og:image`` e ``twitter:image`` apontam para a imagem OpenGraph canônica."""
    parser = _MetaTagParser()
    parser.feed(html_text)
    og_images = [m.get("content") for m in parser.meta_tags if m.get("property", "").lower() == "og:image"]
    twitter_images = [m.get("content") for m in parser.meta_tags if m.get("name", "").lower() == "twitter:image"]
    assert CANONICAL_OG_IMAGE_URL in og_images, f"Meta og:image ausente ou incorreta em {page_name}"
    assert CANONICAL_OG_IMAGE_URL in twitter_images, f"Meta twitter:image ausente ou incorreta em {page_name}"


def test_bilingual_readmes_showcase_and_local_assets() -> None:
    """Seam 1: README.md e README.en.md linkam reciprocamente, sem domínios legados e com assets válidos."""
    readme_pt_path: Path = ROOT_DIR / "README.md"
    readme_en_path: Path = ROOT_DIR / "README.en.md"

    assert readme_pt_path.is_file()
    assert readme_en_path.is_file()

    readme_pt: str = readme_pt_path.read_text(encoding="utf-8")
    readme_en: str = readme_en_path.read_text(encoding="utf-8")

    assert "(README.en.md)" in readme_pt
    assert "(README.md)" in readme_en

    for label, content in (("README.md", readme_pt), ("README.en.md", readme_en)):
        for legacy_domain in LEGACY_DOMAINS:
            assert legacy_domain not in content, f"Domínio legado {legacy_domain} encontrado em {label}"

        for required_asset in REQUIRED_README_ASSETS:
            assert required_asset in content, f"Asset obrigatório {required_asset} ausente em {label}"

        for marker in REQUIRED_README_MARKERS:
            assert marker in content, f"Seção/palavra-chave obrigatória '{marker}' ausente em {label}"

        local_assets = _extract_local_asset_paths(content)
        assert local_assets, f"Nenhum asset local extraído em {label}"
        for rel_asset in local_assets:
            asset_path = ROOT_DIR / rel_asset
            assert asset_path.is_file(), f"Asset referenciado em {label} não existe no disco: {rel_asset}"


@pytest.mark.parametrize("rel_path", REQUIRED_COMMUNITY_AND_DIST_FILES)
def test_community_and_distribution_files_exist_and_non_empty(rel_path: str) -> None:
    """Seam 1: Arquivos obrigatórios de comunidade, Linguist, Docker, templates e playbook existem."""
    target: Path = ROOT_DIR / rel_path
    assert target.is_file(), f"Arquivo obrigatório ausente: {rel_path}"
    content: str = target.read_text(encoding="utf-8").strip()
    assert content, f"Arquivo obrigatório está vazio: {rel_path}"


def test_changelog_has_current_package_version() -> None:
    """Seam 1: CHANGELOG.md documenta a versão corrente do pacote em ``__version__``."""
    changelog_path: Path = ROOT_DIR / "CHANGELOG.md"
    changelog_text: str = changelog_path.read_text(encoding="utf-8")
    assert f"[{__version__}]" in changelog_text


@pytest.mark.parametrize(("rel_path", "expected_size", "expected_format"), VISUAL_ASSET_SPECS)
def test_visual_assets_dimensions_and_formats(
    rel_path: str,
    expected_size: tuple[int, int],
    expected_format: str,
) -> None:
    """Seam 1: Assets visuais possuem dimensões exatas e formato esperado via Pillow."""
    asset_path: Path = ROOT_DIR / rel_path
    assert asset_path.is_file(), f"Asset visual ausente: {rel_path}"

    with Image.open(asset_path) as img:
        assert img.format == expected_format, f"Formato inesperado em {rel_path}: {img.format}"
        assert img.size == expected_size, f"Dimensões inesperadas em {rel_path}: {img.size}"


def test_static_build_opengraph_assets_and_meta_tags(tmp_path: Path) -> None:
    """Seam 2: build estático inclui og-banner.png, registra no sw.js e injeta tags OG/Twitter nas HTMLs."""
    dist: Path = build(tmp_path / "dist")

    og_banner_dist: Path = dist / "static" / "og-banner.png"
    assert og_banner_dist.is_file(), "dist/static/og-banner.png não foi gerado"

    sw_text: str = (dist / "sw.js").read_text(encoding="utf-8")
    assert "'/static/og-banner.png'" in sw_text

    seo_pages: tuple[str, ...] = tuple(f"validar-{slug}.html" for slug in SEO_DOC_PAGES)
    built_seo_pages: set[str] = {p.name for p in dist.glob("validar-*.html")}
    assert built_seo_pages == set(seo_pages)

    for page_name in (*MAIN_HTML_PAGES, *seo_pages):
        page_path: Path = dist / page_name
        assert page_path.is_file(), f"Página HTML esperada não gerada no build: {page_name}"
        html_text: str = page_path.read_text(encoding="utf-8")
        _assert_opengraph_tags(html_text, page_name)


def test_api_serves_opengraph_banner_and_page_meta_tags() -> None:
    """Seam 2: FastAPI serve /static/og-banner.png (200, image/png) e inclui tags OpenGraph em / e /validar-crlv."""
    client: TestClient = TestClient(app)

    banner_res = client.get("/static/og-banner.png")
    assert banner_res.status_code == 200
    assert banner_res.headers.get("content-type", "").startswith("image/png")
    with Image.open(io.BytesIO(banner_res.content)) as img:
        assert img.format == "PNG"
        assert img.size == (1200, 630)

    for route in ("/", "/validar-crlv"):
        page_res = client.get(route)
        assert page_res.status_code == 200
        assert CANONICAL_OG_IMAGE_URL in page_res.text
        _assert_opengraph_tags(page_res.text, route)


def test_release_container_workflow_metadata_expressions_valid() -> None:
    """Seam 2: release-container.yml usa expressões GitHub válidas no docker/metadata-action."""
    workflow_path: Path = ROOT_DIR / ".github" / "workflows" / "release-container.yml"
    workflow_text: str = workflow_path.read_text(encoding="utf-8")
    assert "{{is_tag}}" not in workflow_text
    assert "enable=${{ startsWith(github.ref, 'refs/tags/') }}" in workflow_text

