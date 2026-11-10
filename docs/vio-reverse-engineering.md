# Engenharia Reversa e Especificação Técnica do Padrão VIO (Serpro / Senatran)

Este documento sintetiza a arquitetura, o fluxo criptográfico, a estrutura de empacotamento binário e os dicionários de modelos (*templates*) utilizados pelo aplicativo **Vio: QR Seguro** (pacote `br.gov.serpro.lince`, desenvolvido pelo SERPRO para o Governo Federal do Brasil).

---

## 1. Visão Geral da Tecnologia

O sistema **Vio** é projetado para atestar a autenticidade de documentos físicos e digitais emitidos pelo governo brasileiro (CNH, CRLV-e, ATPV-e, Placas Mercosul e Carteiras Funcionais) sem depender de conexão com a internet.

### Princípio Criptográfico:
* **Na emissão (Serpro/Senatran):** O órgão condensa as informações textuais do documento e a fotografia biométrica em um envelope binário enxuto. Em seguida, gera uma assinatura digital assimétrica utilizando sua **chave privada** (ECDSA/RSA protegida em HSM).
* **No QR Code:** A matriz do QR Code armazena os dados comprimidos, os identificadores de template, o timestamp de emissão e a assinatura criptográfica de 256 bytes.
* **Na conferência (Aplicativo/Leitor):** O validador não consulta um banco de dados central. Ele utiliza o par público correspondente (**chaves públicas** de certificados oficiais embutidos na aplicação) para verificar a assinatura digital.
  * Se a assinatura conferir: **O documento é genuíno e não sofreu nenhuma alteração**.
  * Se a assinatura falhar: **Houve adulteração, erro de leitura ou falsificação**.

---

## 2. Estrutura do Envelope e Cabeçalho

Todo QR Code do padrão VIO inicia com um envelope de metadados:

### Cabeçalho Hexadecimal (10 bytes ASCII) ou Binário (5 bytes)
* **Hexadecimal (10 bytes):**
  * Bytes `[0:8]`: Timestamp UNIX em hexadecimal (8 caracteres = 4 bytes `uint32_be`).
  * Bytes `[8:10]`: Versão do formato do documento em hexadecimal (2 caracteres = 1 byte).
* **Binário (5 bytes - fallback):**
  * Bytes `[0:4]`: Timestamp UNIX em `uint32` (big-endian).
  * Byte `[4]`: Versão do formato.

Após o cabeçalho, inicia o `payload` do documento.

---

## 3. Formatos de Versão e Layout do Payload

### Versão 2 (CNH clássica)
Utilizado nas primeiras gerações de CNH com QR Code (`n2.c` no APK):
* `payload[0:2]`: `template_id` (big-endian `uint16`).
* `payload[2:4]`: `fields_len` (tamanho dos campos de texto, big-endian `uint16`).
* `payload[4 : 4 + fields_len]`: Campos de texto empacotados em **alfabeto de 6 bits por caractere**, separados pelo caractere separador `^`.
* `payload[4 + fields_len : 4 + fields_len + 256]`: Bloco de **assinatura digital (256 bytes)**.
* `payload[4 + fields_len + 256 :]`: Fotografia em formato **BPG** (*Better Portable Graphics*), armazenada sem o cabeçalho de magic bytes `BPG` (o leitor deve reinserir `b"BPG"` antes da renderização).

**Dado Assinado na v2:**
$$\text{signed\_data} = \text{header}_{10} + \text{payload}[0 : 4 + \text{fields\_len}] + \text{payload}[4 + \text{fields\_len} + 256 :]$$

---

### Versões 4, 5 e 6 (Multibloco - CRLV-e, CNH Moderna, ATPV-e)
Formato modular empregado nos documentos veiculares e CNH recente (`p4.f` / `p4.h` / `p4.j` no APK). O payload é fatiado em blocos prefixados com comprimentos de 2 bytes (`uint16_be`):

1. **Bloco 0:** `template_id` (2 bytes)
2. **Bloco 1:** Tamanho da assinatura `len1` (2 bytes)
3. **Bloco 2:** Bloco da Assinatura Digital (`len1` bytes)
4. **Bloco 3:** Tamanho da foto `len2` (2 bytes)
5. **Bloco 4:** Fotografia BPG (`len2` bytes, sem o magic `BPG`)
6. **Bloco 5:** Tamanho dos campos de texto `len3` (2 bytes)
7. **Bloco 6:** Campos de dados comprimidos (`len3` bytes):
   * **Versão 4:** Decodificação com alfabeto de **7 bits**.
   * **Versão 5:** Decodificação com alfabeto de **6 bits**.
   * **Versão 6:** Decodificação via **BasE91** lido como ISO-8859-1 (Latin-1).
8. **Bloco 7:** Bytes adicionais / extras até o fim do payload.

**Dado Assinado no Formato Multibloco:**
$$\text{signed\_data} = \text{timestamp}[4:8] + \text{versão}(1\text{ byte}) + \text{Bloco}_0 + \text{Bloco}_3 + \text{Bloco}_4 + \text{Bloco}_5 + \text{Bloco}_6$$

A assinatura presente no Bloco 2 é validada diretamente sobre o hash SHA-256 desse buffer consolidado.

---

## 4. Dicionário de Templates de Documentos Oficiais

Cada documento possui um `template_id` registrado no catálogo oficial do Serpro (`templates.json`). Quando o texto decodificado (delimitado por `^`) é fatiado, a ordem dos valores obedece rigidamente à ordem dos campos cadastrados no template.

### CRLV Digital (Certificado de Registro e Licenciamento de Veículo)
Identificadores: **Templates 10, 12, 62 e 70** (Emissor: `SENATRAN`).

**Ordem dos Campos do CRLV-e:**
1. `codigo_seguranca_cla` (Código de Segurança do CLA)
2. `numero_crv` (Número do CRV)
3. `uf` (Unidade Federativa)
4. `renavam` (Código RENAVAM)
5. `rntrc` (Registro Nacional de Transportadores Rodoviários de Cargas)
6. `exercicio` (Ano de Exercício do Licenciamento)
7. `nome` (Nome do Proprietário)
8. `cpf_cnpj` (CPF ou CNPJ do Proprietário)
9. `placa` (Placa do Veículo)
10. `chassi` (Número do Chassi)
11. `especie` (Espécie)
12. `tipo` (Tipo do Veículo)
13. `carroceria` (Tipo de Carroceria)
14. `combustivel` (Tipo de Combustível)
15. `ano_fabricacao` (Ano de Fabricação)
16. `ano_modelo` (Ano do Modelo)
17. `marca_modelo` (Marca / Modelo)
18. `lotacao` (Capacidade de Lotação)
19. `potencia` (Potência em cv)
20. `cilindradas` (Cilindradas em cc)
21. `categoria` (Categoria do Veículo)
22. `cor` (Cor Predominante)
23. `motor` (Número de Identificação do Motor)
24. `capacidade_maxima_carga` (Carga Máxima)
25. `pbt` (Peso Bruto Total)
26. `cmt` (Capacidade Máxima de Tração)
27. `eixos` (Quantidade de Eixos)
28. `local` (Município / Localidade de Emissão)
29. `data` (Data de Emissão do Documento)
30. `observacoes` (Observações adicionais do documento)

### CNH (Carteira Nacional de Habilitação)
Identificadores: **Templates 2, 4 e 83** (Emissor: `SENATRAN`).
* Campos: `nome`, `nome_civil`, `identidade`, `cpf`, `data_nascimento`, `filiacao_pai`, `filiacao_mae`, `permissao`, `acc`, `categoria`, `numero_registro`, `data_validade`, `data_primeira_habilitacao`, `observacoes`, `local_emissao`, `uf_emissao`, `data_emissao`, `numero_validacao_cnh`, `numero_renach`.

### Placas Veiculares (Padrão Mercosul)
Identificadores: **Templates 11 e 17**.

---

## 5. Chaves Criptográficas e Atualização

* O Serpro distribui periodicamente os certificados atualizados através da API pública:
  `https://vio.serpro.gov.br/api/v2/`
* As chaves públicas confiáveis são mapeadas por `certificate_group` e `id` no catálogo `certificates.json`.
* A verificação utiliza curvas elípticas padrão (SECP256r1 / NIST P-256) com algoritmo ECDSA ou chaves RSA com padding PKCS#1 v1.5 / PSS e hash SHA-256.

---

## 6. Pipeline de Leitura a partir de Documentos Reais (PDF / Imagem)

Para extrair e decodificar no computador:
1. **Entrada de Arquivo:** O usuário fornece um PDF original (ou captura de tela/scanner).
2. **Renderização de Alta Fidelidade:** O PDF é rasterizado com resolução mínima de **300 DPI** utilizando `PyMuPDF` (`fitz`), garantindo contraste nítido nos módulos do QR Code.
3. **Localização e Binarização:** OpenCV ou bibliotecas de visão computacional aplicam binarização adaptativa para isolar o QR Code.
4. **Extração dos Bytes Brutos:** Decodificador de QR (ex.: `pyzbar` ou decodificador nativo OpenCV) recupera os bytes binários brutos (sem forçar conversão antecipada para UTF-8).
5. **Desempacotamento e Verificação:** A rotina de envelope extrai os blocos, valida o hash criptográfico com a chave pública e estrutura o JSON para apresentação ao usuário.
