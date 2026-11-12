# Context & Glossário do Domínio: VioDigital

Este documento estabelece o modelo de domínio, a terminologia e as premissas operacionais do **VioDigital**, sistema de conferência e validação de documentos oficiais (CRLV-e, CNH, ATPV-e) para cartórios e ambientes corporativos.

---

## 1. Glossário de Termos

### Entidades do Domínio

* **CRLV-e (Certificado de Registro e Licenciamento de Veículo Eletrônico):** Documento veicular obrigatório anual emitido pela SENATRAN/Detran, contendo dados do veículo (placa, renavam, chassi) e do proprietário (Templates VIO 10, 12, 62 e 70, além do CRV-e RENAVE Template 24).
* **CNH (Carteira Nacional de Habilitação):** Documento de habilitação do condutor emitido pela SENATRAN contendo dados biográficos, foto biométrica BPG e categorias de condução (Templates VIO 2, 4 e 83).
* **ATPV-e (Autorização para Transferência de Propriedade de Veículo):** Documento eletrônico utilizado para intenção de venda e transferência veicular com reconhecimento de firma em cartório (Template VIO 43).
* **CIN (Carteira de Identidade Nacional / Novo RG):** Documento nacional de identificação civil cujo QR Code armazena um token compacto JWS assinado com algoritmo ES512 pelas chaves públicas oficiais da ONR/ICP-Brasil.
* **Catálogo de Templates VIO (`templates.json`):** Dicionário embarcado com 161 modelos oficiais de documentos governamentais brasileiros (incluindo TIE da Marinha, CRAF/Guia de Tráfego do Exército, Placas Mercosul, DNI, RG Digital e Carteiras de Conselhos Profissionais como CREA, CRA, CREF e CREFITO).
* **QR Code VIO:** Código bidimensional de alta densidade impresso nos documentos oficiais brasileiros contendo um payload binário compactado e assinado digitalmente pelo SERPRO.
* **QR Code Externo (Não-VIO):** Códigos bidimensionais presentes no mesmo documento ou folha (como Selo Digital de Fiscalização do TJ/Cartório, link do e-Notariado ou QR Code PIX de taxa estadual) que apontam para URLs ou pagamentos em vez de conterem um envelope criptográfico VIO.
* **Assinatura Digital VIO:** Assinatura criptográfica assimétrica gerada pelo SERPRO que comprova matematicamente que os dados gravados no QR Code foram emitidos pelo órgão governamental e não foram alterados.
* **Validação Criptográfica Offline:** Processo de verificação da integridade do documento realizado localmente na máquina, conferindo a assinatura digital contra as chaves públicas oficiais do governo, sem necessidade de internet nem chamadas de API.
* **Conferência Notarial:** Procedimento executado pelo escrevente ou funcionário do cartório para confrontar os dados do documento apresentado pelo cliente com os registros do ato notarial (reconhecimento de firma, escritura, procuração).

---

## 2. Distinção Notarial Fundamental

Ao processar documentos no ambiente de cartório, o sistema deve deixar explicitamente clara a distinção entre:

1. **Autenticidade do Documento (Garantida pelo Vio):**
   * Atesta que o PDF ou papel apresentado foi legitimamente gerado pelo SERPRO/SENATRAN e que seus dados textuais e foto são genuínos e inalterados em relação ao momento de sua emissão.
2. **Situação Cadastral em Tempo Real (Exige Consulta DETRAN/RENAVAM):**
   * O QR Code reflete o estado do veículo/habilitação **no instante da emissão**. Restrições judiciais supervenientes (ex.: Renajud, alienação fiduciária nova, comunicação de venda, suspensão de CNH) inseridas após a emissão do documento não constam no QR Code e continuam exigindo consulta online nas bases do Detran quando exigido pelo ato notarial.

---

## 3. Requisitos Operacionais no Cartório

* **Zero Custo por Consulta:** Não utilizar intermediários pagos que cobrem por documento validado.
* **Privacidade e LGPD:** Dados de clientes (CPF, placa, endereço, foto) não podem ser trafegados nem armazenados em servidores de terceiros ou nuvens não autorizadas.
* **Praticidade no Desktop:** O escrevente não deve precisar usar celular. As entradas devem suportar:
  * Arraste de arquivo PDF recebido por WhatsApp Web ou e-mail.
  * Colar captura de tela direto da área de transferência (`Ctrl+V`).
  * Upload de imagens escaneadas (PNG, JPEG).
* **Agilidade de Preenchimento:** Botões de "Copiar dados" organizados para facilitar a colagem nos sistemas de gestão notarial (ex.: E-Cartório, E-Notariado, sistemas locais de notas).
