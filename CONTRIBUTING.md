# Contribuindo com o VioWeb

Muito obrigado pelo interesse em contribuir com o **VioWeb**! Este projeto nasceu dentro de um cartório para oferecer à comunidade brasileira uma alternativa **100% gratuita, aberta e respeitosa à LGPD** para validação e conferência de documentos oficiais baseados no padrão **Serpro/VIO** e **CIN**.

---

## Como você pode ajudar?

1. **Novos Handlers de Documentos (`DocumentHandler`):**
   O catálogo em `src/vioweb/core/data/templates.json` possui **161 templates oficiais** do Serpro (como **TIE da Marinha**, **CRAF / Guia de Tráfego do Exército**, **Placas Mercosul**, **Carteiras do CREA, CRA, CREF, CREFITO, Ministério Público, Defensoria**, etc.). Atualmente, qualquer template sem handler dedicado é lido pelo `GenericHandler`, mas você pode criar um handler tipado em `src/vioweb/core/documents/` para dar formatação e máscaras específicas a uma nova categoria de documento!
2. **Melhorias na Detecção Óptica de QR Code:**
   Aprimoramentos de pré-processamento em `src/vioweb/core/qr.py` para leitura de impressões desgastadas, fotos com reflexo ou câmeras de baixa resolução.
3. **Usabilidade para Cartórios e Despachantes:**
   Atalhos de teclado, modelos de exportação/cópia para sistemas notariais e melhorias de acessibilidade em `src/vioweb/web/`.

---

## Regras de Ouro de Privacidade (LGPD)

* **NUNCA envie documentos reais de terceiros em commits, PRs ou Issues.**
  Se você estiver testando um documento real (PDF ou imagem com CPF, placa, chassi ou foto de uma pessoa real), coloque-o apenas na pasta local `test_samples/` (que é ignorada pelo `.gitignore`).
* **Nos testes automatizados (`tests/`):** utilize sempre vetores sintéticos gerados com dados fictícios e chaves de teste (veja `tests/test_crlv.py` e `tests/test_cnh.py` como referência).
* **Zero dependência de rede na validação:** o motor `src/vioweb/core/` não deve realizar chamadas HTTP externas durante a validação de documentos.

---

## Passo a Passo para Desenvolver

1. Faça um **Fork** do repositório e clone localmente:
   ```bash
   git clone https://github.com/<seu-usuario>/VioWeb.git
   cd VioWeb
   ```
2. Instale em modo editável:
   ```bash
   pip install -e .
   ```
3. Crie uma branch para sua melhoria:
   ```bash
   git checkout -b feat/minha-melhoria
   ```
4. Escreva testes em `tests/` seguindo **TDD** e execute a suíte completa:
   ```bash
   python -m pytest
   ```
5. Abra um **Pull Request** descrevendo o que foi adicionado ou corrigido!
