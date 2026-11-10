document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const btnBrowse = document.getElementById('btn-browse');
  const loadingState = document.getElementById('loading-state');
  const errorBanner = document.getElementById('error-banner');
  const errorTitle = document.getElementById('error-title');
  const errorMessage = document.getElementById('error-message');
  const btnErrorClose = document.getElementById('btn-error-close');
  const resultSection = document.getElementById('result-section');
  const docTypeBadge = document.getElementById('doc-type-badge');
  const authBadge = document.getElementById('auth-badge');
  const authStatusText = document.getElementById('auth-status-text');
  const fieldsContainer = document.getElementById('fields-container');
  const btnCopyAll = document.getElementById('btn-copy-all');
  const btnNewCheck = document.getElementById('btn-new-check');
  const toast = document.getElementById('toast');

  let currentResult = null;

  // Browse click
  btnBrowse.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropzone.addEventListener('click', () => {
    fileInput.click();
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      processFile(fileInput.files[0]);
    }
  });

  // Drag and drop
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files[0]) {
      processFile(dt.files[0]);
    }
  });

  // Ctrl+V paste listener anywhere on window
  window.addEventListener('paste', (e) => {
    const items = (e.clipboardData || window.clipboardData).items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const blob = items[i].getAsFile();
        if (blob) {
          processFile(blob);
          showToast('Imagem colada da área de transferência!');
          return;
        }
      }
    }
  });

  btnErrorClose.addEventListener('click', () => {
    errorBanner.style.display = 'none';
  });

  btnNewCheck.addEventListener('click', () => {
    resetView();
  });

  btnCopyAll.addEventListener('click', () => {
    if (!currentResult) return;
    const text = formatNotarySummary(currentResult);
    copyToClipboard(text, 'Ficha completa copiada para o sistema notarial!');
  });

  function resetView() {
    resultSection.style.display = 'none';
    errorBanner.style.display = 'none';
    dropzone.style.display = 'flex';
    loadingState.style.display = 'none';
    fileInput.value = '';
    currentResult = null;
  }

  async function processFile(file) {
    errorBanner.style.display = 'none';
    dropzone.style.display = 'none';
    loadingState.style.display = 'flex';
    resultSection.style.display = 'none';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/documents/verify', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      loadingState.style.display = 'none';

      if (!response.ok || !data.is_parsed) {
        showError(data.message || 'Falha ao decodificar documento.');
        dropzone.style.display = 'flex';
        return;
      }

      currentResult = data;
      renderResult(data);
    } catch (err) {
      loadingState.style.display = 'none';
      dropzone.style.display = 'flex';
      showError(`Erro de comunicação com o servidor: ${err.message}`);
    }
  }

  function showError(msg) {
    errorTitle.textContent = 'Atenção na leitura do documento';
    errorMessage.textContent = msg;
    errorBanner.style.display = 'flex';
  }

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2500);
  }

  function copyToClipboard(text, successMsg = 'Copiado!') {
    navigator.clipboard.writeText(text).then(() => {
      showToast(successMsg);
    }).catch(() => {
      const el = document.createElement('textarea');
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      showToast(successMsg);
    });
  }

  function renderResult(data) {
    docTypeBadge.textContent = data.document_name || (data.document_type === 'crlv' ? 'CRLV Digital' : 'CNH Digital');

    if (data.is_authentic) {
      authBadge.className = 'auth-badge authentic';
      authStatusText.textContent = 'Documento Autêntico (Assinatura VIO Válida)';
    } else {
      authBadge.className = 'auth-badge invalid';
      authStatusText.textContent = 'Assinatura Inválida / Não Autêntico';
    }

    fieldsContainer.innerHTML = '';
    const fmt = data.formatted || {};

    if (data.document_type === 'crlv') {
      const crlvCards = [
        { label: 'Placa', val: fmt.placa_formatada || data.fields.placa, highlight: true },
        { label: 'Renavam', val: fmt.renavam_formatado || data.fields.renavam },
        { label: 'Chassi', val: fmt.chassi || data.fields.chassi },
        { label: 'Marca / Modelo', val: fmt.marca_modelo || data.fields.marca_modelo },
        { label: 'Ano Fab / Modelo', val: fmt.ano_fabricacao_modelo || `${data.fields.ano_fabricacao || ''}/${data.fields.ano_modelo || ''}` },
        { label: 'Proprietário', val: fmt.proprietario || data.fields.nome },
        { label: 'CPF / CNPJ', val: fmt.cpf_cnpj_formatado || data.fields.cpf_cnpj },
        { label: 'Exercício', val: fmt.exercicio || data.fields.exercicio },
        { label: 'UF / Município', val: `${fmt.uf || data.fields.uf || ''} - ${fmt.municipio || data.fields.local || ''}` },
        { label: 'Combustível', val: fmt.combustivel || data.fields.combustivel },
        { label: 'Cor Predominante', val: fmt.cor || data.fields.cor },
        { label: 'Categoria', val: fmt.categoria || data.fields.categoria },
      ];

      crlvCards.forEach(c => {
        if (c.val && c.val.trim() && c.val !== ' - ') {
          fieldsContainer.appendChild(createFieldCard(c.label, c.val, c.highlight));
        }
      });
    } else if (data.document_type === 'cnh') {
      const cnhCards = [
        { label: 'Nome do Condutor', val: fmt.nome || data.fields.nome, highlight: true },
        { label: 'CPF', val: fmt.cpf_formatado || data.fields.cpf },
        { label: 'Categoria', val: fmt.categoria || data.fields.categoria },
        { label: 'Registro CNH', val: fmt.numero_registro || data.fields.numero_registro },
        { label: 'Validade', val: fmt.data_validade || data.fields.data_validade },
        { label: 'Emissão', val: fmt.data_emissao || data.fields.data_emissao },
        { label: 'UF / Município', val: `${fmt.uf_emissao || data.fields.uf_emissao || ''} - ${fmt.local_emissao || data.fields.local_emissao || ''}` },
        { label: 'RENACH', val: fmt.numero_renach || data.fields.numero_renach },
      ];

      cnhCards.forEach(c => {
        if (c.val && c.val.trim() && c.val !== ' - ') {
          fieldsContainer.appendChild(createFieldCard(c.label, c.val, c.highlight));
        }
      });
    }

    const photoContainer = document.getElementById('photo-container');
    const photoPreview = document.getElementById('photo-preview');
    if (photoContainer && photoPreview) {
      if (data.photo_b64) {
        photoPreview.innerHTML = `<img src="${data.photo_b64}" alt="Foto" style="max-width: 140px; border-radius: 8px; border: 1px solid var(--border-color); box-shadow: 0 4px 6px rgba(0,0,0,0.3);">`;
        photoContainer.style.display = 'block';
      } else {
        photoContainer.style.display = 'none';
      }
    }

    resultSection.style.display = 'block';
  }

  function createFieldCard(label, value, highlight = false) {
    const card = document.createElement('div');
    card.className = 'field-card';

    const info = document.createElement('div');
    info.className = 'field-info';

    const lbl = document.createElement('span');
    lbl.className = 'field-label';
    lbl.textContent = label;

    const val = document.createElement('span');
    val.className = highlight ? 'field-value highlight-plate' : 'field-value';
    val.textContent = value;

    info.appendChild(lbl);
    info.appendChild(val);

    const btn = document.createElement('button');
    btn.className = 'btn-copy-field';
    btn.title = `Copiar ${label}`;
    btn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
      </svg>
    `;

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      copyToClipboard(value, `${label} copiado!`);
    });

    card.appendChild(info);
    card.appendChild(btn);
    return card;
  }

  function formatNotarySummary(data) {
    const fmt = data.formatted || {};
    const f = data.fields || {};

    if (data.document_type === 'crlv') {
      return [
        `=== DADOS DO VEÍCULO (CRLV-e) ===`,
        `VEÍCULO: ${fmt.marca_modelo || f.marca_modelo || ''} (${fmt.ano_fabricacao_modelo || ''})`,
        `PLACA: ${fmt.placa_formatada || f.placa || ''}`,
        `RENAVAM: ${fmt.renavam_formatado || f.renavam || ''}`,
        `CHASSI: ${fmt.chassi || f.chassi || ''}`,
        `PROPRIETÁRIO: ${fmt.proprietario || f.nome || ''}`,
        `CPF/CNPJ: ${fmt.cpf_cnpj_formatado || f.cpf_cnpj || ''}`,
        `EXERCÍCIO: ${fmt.exercicio || f.exercicio || ''} | UF: ${fmt.uf || f.uf || ''}`,
        `COMBUSTÍVEL: ${fmt.combustivel || f.combustivel || ''} | COR: ${fmt.cor || f.cor || ''}`,
        `AUTENTICIDADE SERPRO/VIO: ${data.is_authentic ? 'AUTÊNTICO / VÁLIDO' : 'NÃO CONFERE'}`,
      ].filter(Boolean).join('\n');
    } else {
      return [
        `=== DADOS DA HABILITAÇÃO (CNH) ===`,
        `CONDUTOR: ${fmt.nome || f.nome || ''}`,
        `CPF: ${fmt.cpf_formatado || f.cpf || ''}`,
        `CATEGORIA: ${fmt.categoria || f.categoria || ''}`,
        `REGISTRO CNH: ${fmt.numero_registro || f.numero_registro || ''}`,
        `VALIDADE: ${fmt.data_validade || f.data_validade || ''}`,
        `EMISSÃO: ${fmt.data_emissao || f.data_emissao || ''} (${fmt.uf_emissao || f.uf_emissao || ''})`,
        `AUTENTICIDADE SERPRO/VIO: ${data.is_authentic ? 'AUTÊNTICO / VÁLIDO' : 'NÃO CONFERE'}`,
      ].filter(Boolean).join('\n');
    }
  }
});
