# ADR 0001: Validação Criptográfica Offline Local

## Contexto
O cartório precisa validar dezenas de documentos veiculares (CRLV-e) e habilitações (CNH) diariamente.
Atualmente, funcionários usam celulares pessoais com o app oficial VIO para ler os documentos.
Existem APIs de terceiros que oferecem validação cobrando R$ 0,25 por documento ou mensalidades, além da API oficial Serpro que requer contratação institucional por faixas de consumo.
O envio de documentos contendo CPF, placas e fotos para APIs terceiras gera riscos de conformidade com a LGPD.

## Decisão
Implementar a verificação e decodificação do padrão VIO de forma **100% offline e local**, executando no navegador/desktop através de um backend local leve em Python ou biblioteca nativa.
As chaves públicas dos certificados oficiais do Serpro/Senatran serão armazenadas localmente e atualizadas periodicamente conforme divulgado pelo repositório oficial de certificados do governo.

## Consequências
* **Positivas:**
  * Custo zero por documento validado.
  * Privacidade total e conformidade estrita com a LGPD (nenhum dado sai da rede interna do cartório).
  * Independência de conexão externa com a internet para validar a autenticidade dos documentos.
  * Tempo de resposta quase instantâneo (< 100ms por documento).
* **Negativas / Atenções:**
  * O catálogo de certificados do Serpro precisará ser atualizado periodicamente para reconhecer novos lotes emitidos pelo governo.
