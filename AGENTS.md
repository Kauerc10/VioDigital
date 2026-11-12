# VioDigital: Diretrizes de Desenvolvimento e Contexto do Repositório

Bem-vindo ao repositório do **VioDigital**, o verificador e decodificador offline de documentos oficiais brasileiros (CRLV-e, CNH, ATPV-e, Placas Mercosul) baseado na tecnologia Serpro/Vio, projetado para uso em computadores e navegadores em ambientes de cartório e corporativos.

---

## Agent skills

### Issue tracker

Issues e especificações deste repositório vivem no GitHub Issues e são operados via CLI `gh`. Veja `docs/agents/issue-tracker.md`.

### Triage labels

Vocabulário de cinco papéis canônicos de triagem (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). Veja `docs/agents/triage-labels.md`.

### Domain docs

Estrutura de contexto único (`CONTEXT.md` na raiz e `docs/adr/` para decisões arquiteturais). Veja `docs/agents/domain.md`.

---

## 1. Visão Geral do Projeto

O objetivo do VioDigital é permitir que colaboradores de cartórios e empresas confiram a autenticidade e extraiam automaticamente os dados de documentos veiculares (CRLV-e) e habilitações (CNH) diretamente em seus computadores:
* **Entradas:** Arraste de arquivos PDF, imagens escaneadas ou colagem de captura de tela (`Ctrl+V`).
* **Processamento:** Extração do QR Code em alta resolução (300 DPI), desempacotamento do envelope binário VIO, decodificação dos campos (6-bit, 7-bit, BasE91) e verificação criptográfica offline da assinatura digital (ECDSA/RSA) contra certificados oficiais do SERPRO/SENATRAN.
* **Saída:** Interface web elegante e instantânea com selo de autenticidade, campos formatados (Placa, Renavam, Chassi, Proprietário, Categoria, Validade) e botões de cópia rápida para o sistema notarial.

---

## 2. Leitura Obrigatória para Agentes

Antes de propor alterações ou implementar funcionalidades, consulte:
1. **`CONTEXT.md`**: Glossário de termos do domínio (CRLV-e, CNH, ATPV-e, verificação notarial, distinção de autenticidade vs. base do DETRAN).
2. **`docs/vio-reverse-engineering.md`**: Especificação técnica aprofundada da estrutura binária do QR Code VIO, formatos de envelope (v2, v4, v5, v6), algoritmos criptográficos e schemas de templates.
3. **`docs/adr/`**: Registros de decisões de arquitetura (ADR 0001 sobre validação offline local, ADR 0002 sobre arquitetura do motor e interface web).

---

## 3. Padrões de Código e Arquitetura

* **Linguagem Principal:** Python 3.12+ no backend com tipagem estática rigorosa (`typing`, `dataclasses`, `pydantic`).
* **Arquitetura Modular:** Cada documento possui seu próprio `DocumentHandler` isolado (ex.: `CRLVHandler`, `CNHHandler`), com mapeamento explícito de campos e propriedades formatadas (`placa_formatada`, `cpf_cnpj_formatado`, etc.).
* **Zero Network Dependency para Validação:** O processo de verificação de autenticidade e parsing deve ser estritamente **offline**, dependendo apenas do repositório local de certificados e templates.
* **Privacidade Absoluta (LGPD):** Nenhum documento, dado pessoal, foto ou payload pode ser transmitido para serviços externos.

---

## 4. Testes e TDD

* Sempre adote o fluxo de **Test-Driven Development (TDD)** ao implementar novos handlers ou decodificadores.
* Testes devem cobrir:
  * Extração de envelopes com cabeçalhos hexadecimais e binários.
  * Decodificação de texto compactado em alfabetos de 6-bit, 7-bit e BasE91.
  * Validação de assinaturas digitais válidas e rejeição de payloads adulterados.
  * Parsing completo de templates de CRLV Digital (10, 12, 62, 70) e CNH (2, 4, 83).
