# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico (SemVer)](https://semver.org/lang/pt-BR/).

## [Unreleased]

## [0.2.0] - 2026-11-18

### Added
- Execução criptográfica e óptica **100% no navegador via WebAssembly** (`Pyodide`, `ZXing-WASM`, `PDF.js` e decodificador `bpgdec8.js` para fotos biométricas BPG) isolada em Web Worker (`scanner.worker.js`), conforme [ADR 0003](docs/adr/0003-browser-wasm-pyodide-validation.md).
- Suporte a **PWA instalável e operação offline** via Service Worker híbrido (`sw.js`) com invalidação determinística de cache por hash de build (`/api/version` e `.wheel_hash`).
- Gerador de site estático (`src/viodigital/build_static.py`) com catálogo de **161 templates VIO** embutido, páginas dedicadas (`/documentos`, `/privacidade`, `/apoiar`, `/api-comercial`), rotas SEO (`/validar-crlv`, `/validar-cnh`, `/validar-atpv`, `/validar-cin`, `/validar-tie-marinha`), `robots.txt`, `sitemap.xml`, `llms.txt` e `404.html`.
- Controles avançados de câmera no leitor óptico via webcam: foco, zoom para foco fixo, rajada nítida e realce óptico (`camera-quality.js`).
- Suíte de testes E2E com Playwright validando tráfego externo zero e bloqueio ativo por CSP (`tests/test_e2e_privacy.py`), além de pipeline CI no GitHub Actions (`.github/workflows/ci.yml`).
- Arquivos de governança comunitária (`CODE_OF_CONDUCT.md`, `SECURITY.md`, templates de issue/PR com alertas LGPD) e empacotamento self-hosted em container (`Dockerfile` multi-stage não-root, `docker-compose.yml` e workflow de publicação no GHCR).

### Changed
- Rebranding completo do projeto de `VioWeb` para **VioDigital** com domínio canônico `https://viodigital.com.br` e shims mínimos de compatibilidade retroativa em `src/vioweb/`.
- Reorganização das dependências opcionais em `pyproject.toml` (`server`, `vision`, `dev`) com desacoplamento claro de `MissingDependencyError`.
- Camada unificada de apresentação de campos (`present()`) compartilhada entre CLI, API REST e WebAssembly.

### Fixed
- Correções na decodificação direta de fotografias BPG em canvas HTML5 e na recuperação de bytes binários do QR Code no worker WASM.
- Ajustes de ordenação de `Cache-Control` na Vercel (`vercel.json`), remoção de resíduos legados e alinhamento de rotas/CSP.

### Security
- Política estrita `Content-Security-Policy` (`default-src 'self'; connect-src 'self'`, `'wasm-unsafe-eval'`), removendo completamente `'unsafe-eval'` e fontes externas do Google Fonts.
- Endurecimento da API FastAPI: CORS sem credenciais, limite máximo de upload de 15 MB (`HTTP 413`), sanitização de respostas `500` e segregação de `Cache-Control`.

## 0.1.0 - 2026-11-10

### Added
- Núcleo criptográfico offline (`DigitalDocumentChecker`) para desempacotamento de envelopes binários VIO (versões 2, 4, 5 e 6 em 6-bit, 7-bit e BasE91) e tokens JWS `ES512` da CIN.
- Handlers dedicados para **CRLV-e** (Templates 10, 12, 62, 70), **CRV-e RENAVE** (Template 24), **CNH** (Templates 2, 4, 83), **ATPV-e** (Template 43) e `GenericHandler` sobre o catálogo oficial de 161 templates Serpro/VIO.
- Pipeline em memória de extração óptica de QR Code para PDFs (300 DPI) e imagens com priorização automática Multi-QR (ignorando selos de TJ e QR Codes PIX).
- Servidor local FastAPI e interface web notarial inicial com arraste de arquivos, colagem via `Ctrl+V` e botões de cópia rápida para sistemas de cartório.
- Documentação inicial de domínio e arquitetura (`CONTEXT.md`, `docs/adr/0001`, `docs/adr/0002`, `docs/vio-reverse-engineering.md`).

[Unreleased]: https://github.com/Kauerc10/VioDigital/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Kauerc10/VioDigital/releases/tag/v0.2.0
