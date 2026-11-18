# Política de Segurança (`SECURITY.md`)

A segurança criptográfica e a proteção absoluta de dados pessoais (**LGPD — Lei nº 13.709/2018**) são pilares centrais do **VioDigital**. Agradecemos a pesquisadores de segurança e membros da comunidade que reportarem vulnerabilidades de forma responsável.

---

## Versões Suportadas

| Versão | Suporte de Segurança |
| :--- | :--- |
| `0.2.x` (atual) | ✅ Suportada |
| `< 0.2.0` | ❌ Não suportada (atualize para a versão mais recente) |

---

## Como Reportar uma Vulnerabilidade (Divulgação Privada)

**NÃO abra uma Issue pública, Pull Request ou discussão aberta** para reportar falhas de segurança.

Utilize exclusivamente o canal privado do **GitHub Security Advisories**:

* 👉 **[Abrir Security Advisory Privado](https://github.com/Kauerc10/VioDigital/security/advisories/new)**

### O que esperar após o envio
1. **Confirmação inicial:** em até **48 horas** após o recebimento do advisory.
2. **Triagem técnica e plano de correção:** em até **7 dias úteis**, com avaliação de severidade e cronograma de patch.
3. **Divulgação coordenada:** após a publicação da correção e atualização da versão suportada, daremos os créditos ao pesquisador (caso deseje).

### O que incluir no relatório
* Descrição clara da vulnerabilidade e do componente afetado.
* Passos reproduzíveis ou prova de conceito (PoC).
* Impacto potencial (ex.: aceitação de assinatura inválida, contorno de CSP, execução remota, exposição de dados).
* **Somente vetores sintéticos/fictícios:** consulte a regra de privacidade abaixo.

---

## Escopo de Segurança

Estão dentro do escopo prioritário deste projeto:

1. **Motor Criptográfico e Validação de Certificados (`src/viodigital/core/`):**
   * Bypass ou enfraquecimento na verificação de assinaturas digitais assimétricas (**ECDSA**, **RSA** e **JWS ES512** da CIN).
   * Aceitação indevida de envelopes VIO adulterados, certificados inválidos/revogados no catálogo embarcado ou falhas de validação temporal.
   * Vulnerabilidades em parsers binários (compactação 6-bit, 7-bit, BasE91, decodificador **BPG**, TLV ou leitura Multi-QR).
2. **Privacidade, LGPD e Política CSP (`src/viodigital/web/`, `vercel.json`, `sw.js`):**
   * Qualquer regressão que permita exfiltração de dados de documentos a partir do navegador.
   * Relaxamento indevido de `Content-Security-Policy` (como perda de `connect-src 'self'`, introdução de `'unsafe-eval'` ou carregamento de recursos externos).
   * Chamadas HTTP externas durante a validação no cliente WASM (`Pyodide`/`ZXing`) ou no motor Python local.
3. **API REST e Container Self-Hosted (`src/viodigital/api/`, `Dockerfile`):**
   * Contorno de limite de tamanho de upload (`MAX_UPLOAD_SIZE`), negação de serviço (DoS) via PDFs/imagens malformados (ex.: descompressão excessiva / `MAX_PIXELS`), vazamento de informações internas em respostas de erro ou execução privilegiada no container.

---

## Regra Obrigatória de Privacidade (LGPD)

> [!CAUTION]
> **NUNCA envie documentos reais de cidadãos ou terceiros** (PDFs, imagens, capturas de tela, fotos biométricas, CPF, placa, RENAVAM, chassi ou payloads reais de QR Code) ao reportar uma vulnerabilidade.
>
> Utilize exclusivamente **vetores sintéticos e dados fictícios** gerados com chaves de teste (como os exemplos em `tests/`).

---

## Fora de Escopo

* **Situação cadastral em tempo real junto ao DETRAN/SENATRAN:** o VioDigital atesta a autenticidade criptográfica do QR Code no instante de sua emissão; restrições judiciais ou administrativas posteriores (ex.: Renajud, bloqueio ou suspensão) exigem consulta aos sistemas dos órgãos de trânsito, conforme documentado em [`CONTEXT.md`](CONTEXT.md).
* Emissão, rotação ou revogação de chaves públicas oficiais por parte de SERPRO, SENATRAN, ONR ou ICP-Brasil.
* Vulnerabilidades em dependências externas sem impacto explorável no VioDigital (embora relatos com impacto concreto na cadeia de build/runtime sejam bem-vindos).
