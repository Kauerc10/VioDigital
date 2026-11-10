# VioWeb 🚗📄

> Verificador e decodificador offline de documentos veiculares (CRLV-e, CNH, ATPV-e) baseado no padrão Serpro/Vio para uso em desktop e web.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)

---

## 🎯 O que é o VioWeb?

O **VioWeb** foi criado para resolver um gargalo comum em cartórios e empresas: funcionários que precisam verificar a autenticidade de documentos veiculares (CRLV-e) ou de habilitação (CNH) e acabam recorrendo a celulares pessoais com o app VIO, ou pagando mensalidades para APIs terceirizadas.

Com o **VioWeb**, o usuário simplesmente **arrasta o PDF ou imagem do documento** (ou cola com `Ctrl+V` um print da tela) diretamente no navegador do computador. O sistema:

1. Detecta e lê a matriz do QR Code em alta resolução;
2. Desempacota o payload binário do envelope Serpro/Vio;
3. **Valida criptograficamente a assinatura digital (ECDSA/RSA)** contra os certificados públicos oficiais da SENATRAN/SERPRO de forma **100% offline**;
4. Extrai todos os campos estruturados (Placa, Renavam, Chassi, Ano, Proprietário, Categoria, etc.);
5. Exibe os dados prontos para conferência com botão de cópia rápida para sistemas notariais.

---

## 🔒 Vantagens

* **Custo Zero:** Validação criptográfica local, sem cobrança por consulta.
* **100% Offline:** Não depende de internet nem de APIs externas.
* **Privacidade & LGPD:** Os documentos e dados dos clientes nunca saem da sua máquina ou rede local.
* **Praticidade Notarial:** Sem emuladores pesados e sem necessidade de smartphones.

---

## 📚 Documentação Técnica

* [Glossário do Domínio e Conceitos (`CONTEXT.md`)](CONTEXT.md)
* [Engenharia Reversa e Especificação do Padrão VIO (`docs/vio-reverse-engineering.md`)](docs/vio-reverse-engineering.md)
* [ADR 0001: Validação Criptográfica Offline Local](docs/adr/0001-offline-cryptographic-validation.md)
* [ADR 0002: Arquitetura do Decodificador e Interface Web](docs/adr/0002-crlv-and-cnh-decoding-architecture.md)
* [Diretrizes para Agentes de IA (`AGENTS.md`)](AGENTS.md)
