# Spec 0001: VioWeb Core - Verificador e Decodificador Notarial de CRLV-e e CNH

## Problem Statement
O cartório e seus colaboradores enfrentam perda de tempo e atrito diário na conferência de documentos veiculares (CRLV-e) e habilitações (CNH) de clientes. Como não há versão oficial nativa do Serpro VIO para computadores desktop, os funcionários precisam recorrer aos seus telefones celulares para escanear QR Codes físicos ou na tela do computador e, em seguida, redigitar manualmente os dados do condutor e do veículo para dentro do sistema notarial. Soluções de API pagas de terceiros trazem custos recorrentes por documento e geram graves riscos de conformidade com a LGPD ao trafegar dados de clientes por servidores externos.

## Solution
O VioWeb oferece uma aplicação desktop/web local, gratuita e 100% offline para os computadores do cartório. O funcionário simplesmente arrasta o PDF do CRLV-e/CNH recebido por e-mail ou WhatsApp Web, ou cola um print da tela com `Ctrl+V`. O sistema renderiza o PDF em alta resolução, isola o QR Code, desempacota o payload binário do envelope Serpro/Vio, verifica a assinatura digital contra as chaves públicas oficiais da SENATRAN/SERPRO e exibe instantaneamente os dados do documento com selo de autenticidade e botões de cópia direta para o sistema notarial.

## User Stories
1. As a notary clerk, I want to drag and drop a CRLV-e PDF file into the web application, so that I don't need to print it or use my smartphone camera to scan it.
2. As a notary clerk, I want to paste a screenshot directly from my clipboard using `Ctrl+V`, so that I can quickly verify documents already open in another window.
3. As a notary clerk, I want to upload image files (PNG, JPG) of scanned documents, so that I can verify documents that arrived as image scans.
4. As a notary clerk, I want the system to automatically detect and extract the VIO QR Code from the document, so that I don't have to manually crop or point a camera.
5. As a notary clerk, I want the system to cryptographically verify the digital signature using official public certificates, so that I have mathematical certainty that the document was issued by the government and was not tampered with.
6. As a notary clerk, I want to see a clear visual badge indicating whether the cryptographic signature is valid, invalid, or unverifiable, so that I can make an immediate notary decision.
7. As a notary clerk, I want to see formatted vehicle data (Placa, Renavam, Chassi, Ano de Fabricação, Ano do Modelo, Marca/Modelo, Proprietário, CPF/CNPJ, Motor, Exercício) clearly organized in cards, so that I can cross-check it against transaction documents.
8. As a notary clerk, I want to click a single button to copy individual fields or all vehicle data formatted to my clipboard, so that I can paste them into notary management software without typing errors.
9. As a notary clerk, I want to verify driver's licenses (CNH) as well as vehicle documents (CRLV-e), so that I can use the same desktop tool for both vehicle and identity verification.
10. As a notary clerk, I want the system to work 100% offline without sending document data to external cloud services, so that our office maintains strict compliance with the Brazilian General Data Protection Law (LGPD).
11. As a notary office manager, I want the verification tool to be completely free of per-document fees, so that we can verify high volumes of documents without operational cost increases.
12. As a notary clerk, I want to see a clear legal disclaimer reminding me that QR Code validity proves document authenticity at issuance time, but does not substitute real-time Detran lien or encumbrance queries.
13. As a notary clerk, I want clear error feedback when an uploaded file does not contain a recognizable QR Code or contains a non-VIO QR code, so that I immediately understand why verification could not proceed.
14. As an office administrator, I want to run VioWeb locally on individual workstations or host it on a local office server, so that all staff members can access it via local network browser.

## Implementation Decisions
- **Architectural Seam:** The primary seam is a high-level Python verification orchestrator `VioDocumentChecker` that accepts document inputs (PDF file, image file, raw bytes, or base64) and returns a structured `DocumentResult`.
- **Backend Service:** A lightweight local FastAPI HTTP server exposing endpoints for document verification (`POST /api/verify`) and health check (`GET /api/health`).
- **Web Frontend:** A modern, responsive web interface with drag-and-drop zones, clipboard paste listener, real-time feedback, authentic badge indicator, and organized field cards with copy-to-clipboard actions.
- **QR Code Detection Pipeline:** Uses high-resolution rasterization (300 DPI) for PDFs via PyMuPDF (`fitz`), followed by computer-vision adaptive binarization and QR decoding to reliably extract high-density VIO QR codes.
- **VIO Envelope & Multiblock Parser:** Implements the Serpro VIO specification for version 2 (legacy CNH) and multiblock versions 4, 5, and 6 (CRLV-e, modern CNH, Mercosul plates), decoding 6-bit, 7-bit, and BasE91 packed textual fields.
- **Cryptographic Verification:** Verifies ECDSA (P-256 with SHA-256) and RSA digital signatures over the normalized signed byte payloads against a local catalogue of official public certificates.
- **Document Handlers:** Dedicated `CRLVHandler` covering templates 10, 12, 62, and 70 with standardized field names and formatted helpers, alongside `CNHHandler` for templates 2, 4, and 83.
- **Data Privacy by Design:** In-memory processing; uploaded files and rendered page images are discarded immediately after QR code extraction and never stored on disk or transmitted across the network.

## Testing Decisions
- **Boundary Testing:** All tests will execute against the public orchestrator seam `VioDocumentChecker.check(...)` and the HTTP verification endpoint, asserting strictly on observable outputs (`is_authentic`, `document_type`, extracted fields, errors, and warnings) rather than internal byte packing logic.
- **Test Fixtures & Vectors:** Create synthetic and sanitized test vectors representing CRLV-e multiblock payloads and CNH payloads to verify:
  1. Successful extraction and signature verification with matching public keys.
  2. Detection of forged or tampered payloads (signature mismatch).
  3. Proper field mapping for all CRLV templates (10, 12, 62, 70).
  4. Behavior on corrupt or truncated QR codes.
- **No Network in Tests:** All unit and integration tests must run without external network access, asserting that offline verification is complete and self-contained.

## Out of Scope
- Real-time online queries against Detran/Senatran databases for current vehicle liens, judicial blocks, or active license suspensions.
- Generation or digital signing of new documents (the system is strictly a reader/verifier, not an issuer).
- User authentication, multi-tenant billing, or external cloud deployment.

## Further Notes
- The local public certificate store should be easy to update with new certificate releases published by Serpro/Senatran.
