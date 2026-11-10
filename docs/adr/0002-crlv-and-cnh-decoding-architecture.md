# ADR 0002: Arquitetura do Decodificador e Interface Web

## Contexto
O escrevente de cartório recebe documentos principalmente em PDF via e-mail ou WhatsApp Web, ou como impressões físicas apresentadas no balcão. O processo precisa de uma interface simples para Windows/Web que elimine atritos de digitação manual.

## Decisão
Adotar uma arquitetura dividida em três camadas desacopladas:
1. **Extrator de Imagem/QR:**
   * Utilizar `PyMuPDF` para converter páginas de PDF em imagem de alta resolução (300 DPI) em memória.
   * Utilizar decodificador de QR Code (OpenCV / ZBar) com binarização adaptativa para localizar o QR Code nos cantos do documento.
2. **Motor de Parsing e Validação Criptográfica:**
   * Extrair o envelope binário do Vio.
   * Processar os formatos v2, v4, v5 e v6 com decodificadores específicos (6-bit, 7-bit, BasE91).
   * Validar assinatura ECDSA/RSA sobre o bloco assinado com certificados do catálogo.
   * Mapear os campos aos esquemas dos templates oficiais (Templates 10, 12, 62, 70 para CRLV; 2, 4, 83 para CNH).
3. **Interface de Usuário (VioWeb):**
   * Interface web moderna e responsiva (HTML5 / CSS / Vanilla JS ou React leve), servida localmente por FastAPI.
   * Suporte nativo a arraste de PDF/imagem, seleção de arquivo e evento de colagem do clipboard (`Ctrl+V`).
   * Visualização organizada dos campos com indicação de autenticidade (selo verde) e botão de cópia de dados.

## Consequências
* O escrevente não precisa instalar emuladores pesados de Android no Windows.
* Funciona em qualquer navegador moderno acessando o serviço local.
* Pode ser executado em uma única máquina ou disponibilizado em rede local para todos os computadores do cartório.
