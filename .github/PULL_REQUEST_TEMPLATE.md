## Descrição das Alterações

<!-- Descreva o que foi alterado e por quê. -->

- Issue relacionada: <!-- ex.: Closes #... ou Part of #... -->

## Tipo de Mudança

- [ ] Correção de bug (`fix`)
- [ ] Nova funcionalidade ou Handler VIO (`feat`)
- [ ] Refatoração / Melhoria de desempenho (`refactor` / `perf`)
- [ ] Documentação (`docs`)
- [ ] Infraestrutura / CI / Docker (`ci` / `build`)

## Checklist Obrigatório (Qualidade, Privacidade e Segurança)

- [ ] Executei `ruff check .` localmente e não há erros de lint
- [ ] Executei `pytest` localmente com toda a suíte passando
- [ ] Executei `python src/viodigital/build_static.py` (se aplicável) e `node --check` em scripts JS modificados
- [ ] **LGPD e Vetores Sintéticos:** Nenhuma amostra real de documento (PDF, imagem, CPF, placa, chassi, foto biométrica ou QR Code real) foi adicionada; os testes utilizam exclusivamente vetores sintéticos (`tests/`)
- [ ] **Offline & CSP (`connect-src 'self'`):** Nenhuma chamada de rede externa foi introduzida no motor de validação (`src/viodigital/core/`) nem no frontend web (`connect-src 'self'`, sem `'unsafe-eval'`, sem fontes ou CDNs externos em runtime)
- [ ] Documentação atualizada (`CONTEXT.md`, `docs/adr/`, `CHANGELOG.md`), quando aplicável
