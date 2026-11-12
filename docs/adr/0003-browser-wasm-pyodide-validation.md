# ADR 0003: Validação Criptográfica 100% no Navegador via Pyodide/WebAssembly

## Contexto
O VioWeb se apresentava como um validador offline, mas no ambiente de hospedagem web pública (`vioweb.vercel.app`), cada documento — PDF, imagem ou print colado via `Ctrl+V` — era transmitido via requisição HTTP `POST` para processamento no servidor backend.
Para o usuário comum ou escrevente de cartório utilizando a versão pública, isso representava um risco de exposição de dados pessoais e veiculares (LGPD).
Além disso, manter um backend serverless processando decodificações de imagens e computação criptográfica gerava custos operacionais, riscos de indisponibilidade e contradição com o posicionamento open source de "zero dados enviados a servidores".

Reescrever todo o motor criptográfico e os parsers de 161 templates de Python para JavaScript exigiria manter duas bases de código divergentes e aumentaria o risco de falhas de compatibilidade.

## Decisão
1. **Motor Único em Python via Pyodide (WebAssembly):**
   * O mesmo código do núcleo (`vioweb.core`) roda tanto no servidor Python nativo quanto diretamente dentro do navegador através do runtime WebAssembly **Pyodide**.
   * A biblioteca `cryptography` é carregada a partir dos binários pré-compilados oficiais do Pyodide (`wasm32`), garantindo verificações de assinatura digital RSA e ECDSA com aceleração nativa.
   * A wheel pura do `vioweb` é gerada durante o build estático e instalada diretamente no ambiente virtual em memória do Pyodide.

2. **Isolamento em Web Worker e Zero Network:**
   * Toda a execução óptica (decodificação de QR via ZXing C++ compilado para WASM) e criptográfica ocorre em segundo plano em um Web Worker dedicado (`scanner.worker.js`), mantendo a interface fluida sem bloqueio da thread principal.
   * A rasterização de PDFs ocorre localmente no navegador via `PDF.js` a ~300 DPI, limitando a análise inicial às duas primeiras páginas para proteção de memória.
   * O site público é servido como arquivos estáticos (`dist/`) com política estrita de segurança (CSP `connect-src 'self'`), impedindo tecnicamente que qualquer script tente enviar dados para fora da máquina.
   * Adotou-se o modelo Progressive Web App (PWA) com Service Worker (`sw.js`), permitindo que após o primeiro acesso a ferramenta funcione plenamente sem conexão à internet.

3. **Papel Preservado do FastAPI:**
   * O servidor FastAPI permanece no repositório exclusivamente para cenários de **self-hosting em rede local/intranet de cartórios** e para automações headless via API HTTP interna.

## Consequências
* **Positivas:**
  * **Conformidade Absoluta com a LGPD:** Nenhum dado pessoal, documento, placa ou fotografia sai do computador do usuário no site público.
  * **Auditabilidade e Prova Técnica:** O usuário e auditores de segurança podem verificar a ausência de tráfego na aba Network do DevTools e validar o bloqueio imposto pelo CSP `connect-src 'self'`.
  * **Custo Zero de Infraestrutura:** O site público pode ser hospedado como ativos estáticos puros (GitHub Pages, Vercel estático, Cloudflare Pages, Nginx), eliminando limites de função serverless e custos computacionais.
  * **Manutenibilidade:** Existe apenas um único motor de validação em Python (`vioweb.core`), testado unitariamente e compartilhado entre navegador e servidor.
  * **Resiliência:** Operação garantida mesmo durante quedas de conexão ou instabilidades de rede interna.
* **Negativas / Atenções:**
  * **Carga Inicial:** O primeiro download do runtime Pyodide e das bibliotecas de criptografia consome aproximadamente 19 MB. Esse custo é mitigado pelo pré-carregamento em segundo plano, indicador de progresso e cache permanente via Service Worker.
