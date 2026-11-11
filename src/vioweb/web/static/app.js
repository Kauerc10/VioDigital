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
  const documentContent = document.getElementById('document-content');
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

    documentContent.innerHTML = '';

    if (data.document_type === 'cnh') {
      renderCnhLayout(data, documentContent);
    } else if (data.document_type === 'crlv') {
      renderCrlvLayout(data, documentContent);
    } else {
      renderGenericLayout(data, documentContent);
    }

    renderRawAccordion(data, documentContent);
    resultSection.style.display = 'block';
  }

  function renderCnhLayout(data, container) {
    const fmt = data.formatted || {};
    const f = data.fields || {};

    // 1. Hero: Foto + Identificação Principal
    const heroLayout = document.createElement('div');
    heroLayout.className = 'cnh-hero-layout';

    // Foto Biométrica (se presente)
    if (data.photo_b64) {
      const photoShowcase = createPhotoShowcase(data.photo_b64, data.photo_format);
      heroLayout.appendChild(photoShowcase);
    }

    // Identificação do Condutor
    const idSection = document.createElement('div');
    idSection.style.display = 'flex';
    idSection.style.flexDirection = 'column';
    idSection.style.gap = '0.85rem';
    idSection.style.flex = '1';

    const idGrid = document.createElement('div');
    idGrid.className = 'fields-grid';

    const idCards = [
      { label: 'Nome do Condutor', val: fmt.nome || f.nome, highlight: true, span: 'span-2' },
      { label: 'Nome Civil / Social', val: fmt.nome_civil || f.nome_civil, span: 'span-2' },
      { label: 'CPF', val: fmt.cpf_formatado || f.cpf },
      { label: 'RG / Identidade', val: fmt.identidade || f.identidade },
      { label: 'Data de Nascimento', val: fmt.data_nascimento || f.data_nascimento },
      { label: 'Categoria CNH', val: fmt.categoria || f.categoria, highlight: true },
    ];

    idCards.forEach(c => {
      if (c.val && c.val.trim()) {
        idGrid.appendChild(createFieldCard(c.label, c.val, c.highlight, c.span));
      }
    });

    idSection.appendChild(idGrid);
    heroLayout.appendChild(idSection);
    container.appendChild(heroLayout);

    // 2. Seção Filiação (se mãe ou pai preenchidos)
    const filiacaoCards = [
      { label: 'Nome da Mãe', val: fmt.filiacao_mae || f.filiacao_mae, span: 'span-2' },
      { label: 'Nome do Pai', val: fmt.filiacao_pai || f.filiacao_pai, span: 'span-2' },
    ].filter(c => c.val && c.val.trim());

    if (filiacaoCards.length > 0) {
      const filiacaoSection = createDocSection('Filiação Declarada', '👥');
      const filiacaoGrid = document.createElement('div');
      filiacaoGrid.className = 'fields-grid';
      filiacaoCards.forEach(c => {
        filiacaoGrid.appendChild(createFieldCard(c.label, c.val, false, c.span));
      });
      filiacaoSection.appendChild(filiacaoGrid);
      container.appendChild(filiacaoSection);
    }

    // 3. Seção Habilitação e Validades
    const habCards = [
      { label: 'Registro CNH', val: fmt.numero_registro || f.numero_registro },
      { label: 'Validade CNH', val: fmt.data_validade || f.data_validade, highlight: true },
      { label: '1ª Habilitação', val: fmt.data_primeira_habilitacao || f.data_primeira_habilitacao },
      { label: 'Data de Emissão', val: fmt.data_emissao || f.data_emissao },
      { label: 'UF / Município', val: `${fmt.uf_emissao || f.uf_emissao || ''} - ${fmt.local_emissao || f.local_emissao || ''}` },
      { label: 'Formulário RENACH', val: fmt.numero_renach || f.numero_renach },
      { label: 'Código Segurança / Validação', val: fmt.numero_validacao_cnh || f.numero_validacao_cnh },
      { label: 'Permissão para Dirigir', val: fmt.permissao || f.permissao },
      { label: 'ACC (Ciclomotor)', val: fmt.acc || f.acc },
    ].filter(c => c.val && c.val.trim() && c.val !== ' - ');

    const habSection = createDocSection('Habilitação, Emissão e Prazos', '🚗');
    const habGrid = document.createElement('div');
    habGrid.className = 'fields-grid';
    habCards.forEach(c => {
      habGrid.appendChild(createFieldCard(c.label, c.val, c.highlight, c.span));
    });
    habSection.appendChild(habGrid);
    container.appendChild(habSection);

    // 4. Observações e Restrições (se houver)
    const obsVal = fmt.observacoes || f.observacoes;
    if (obsVal && obsVal.trim()) {
      const obsSection = createDocSection('Observações e Restrições Médicas / Profissionais', '📝');
      const obsGrid = document.createElement('div');
      obsGrid.className = 'fields-grid';
      obsGrid.appendChild(createFieldCard('Observações Registradas', obsVal, false, 'full-width', true));
      obsSection.appendChild(obsGrid);
      container.appendChild(obsSection);
    }
  }

  function renderCrlvLayout(data, container) {
    const fmt = data.formatted || {};
    const f = data.fields || {};

    // 1. Identificação do Veículo
    const veicSection = createDocSection('Identificação Oficial do Veículo', '🚗');
    const veicGrid = document.createElement('div');
    veicGrid.className = 'fields-grid';

    const veicCards = [
      { label: 'Placa do Veículo', val: fmt.placa_formatada || f.placa, highlight: true },
      { label: 'Código Renavam', val: fmt.renavam_formatado || f.renavam, highlight: true },
      { label: 'Chassi do Veículo', val: fmt.chassi || f.chassi },
      { label: 'Marca / Modelo / Versão', val: fmt.marca_modelo || f.marca_modelo, span: 'span-2' },
      { label: 'Ano Fabricação / Modelo', val: fmt.ano_fabricacao_modelo || `${f.ano_fabricacao || ''}/${f.ano_modelo || ''}` },
      { label: 'Cor Predominante', val: fmt.cor || f.cor },
      { label: 'Combustível', val: fmt.combustivel || f.combustivel },
      { label: 'Categoria', val: fmt.categoria || f.categoria },
      { label: 'Espécie / Tipo / Carroceria', val: [fmt.especie || f.especie, fmt.tipo || f.tipo, fmt.carroceria || f.carroceria].filter(Boolean).join(' / ') },
    ];

    veicCards.forEach(c => {
      if (c.val && c.val.trim()) {
        veicGrid.appendChild(createFieldCard(c.label, c.val, c.highlight, c.span));
      }
    });
    veicSection.appendChild(veicGrid);
    container.appendChild(veicSection);

    // 2. Proprietário e Registro
    const propSection = createDocSection('Proprietário Atual e Jurisdição', '👤');
    const propGrid = document.createElement('div');
    propGrid.className = 'fields-grid';

    const propCards = [
      { label: 'Proprietário Atual', val: fmt.proprietario || f.nome, highlight: true, span: 'span-2' },
      { label: 'CPF / CNPJ', val: fmt.cpf_cnpj_formatado || f.cpf_cnpj },
      { label: 'Exercício Licenciado', val: fmt.exercicio || f.exercicio, highlight: true },
      { label: 'Município / UF Registro', val: `${fmt.uf || f.uf || ''} - ${fmt.municipio || f.local || ''}` },
      { label: 'Data de Emissão / Licenciamento', val: fmt.data_emissao || f.data },
    ];

    propCards.forEach(c => {
      if (c.val && c.val.trim() && c.val !== ' - ') {
        propGrid.appendChild(createFieldCard(c.label, c.val, c.highlight, c.span));
      }
    });
    propSection.appendChild(propGrid);
    container.appendChild(propSection);

    // 3. Especificações Técnicas e Carga
    const tecCards = [
      { label: 'Potência / Cilindradas', val: `${fmt.potencia || f.potencia || ''} cv / ${fmt.cilindradas || f.cilindradas || ''} cc` },
      { label: 'Número do Motor', val: fmt.motor || f.motor },
      { label: 'Capacidade Máx. de Carga', val: fmt.capacidade_maxima_carga || f.capacidade_maxima_carga },
      { label: 'PBT (Peso Bruto Total)', val: fmt.pbt || f.pbt },
      { label: 'CMT (Capacidade Tração)', val: fmt.cmt || f.cmt },
      { label: 'Lotação / Eixos', val: `${fmt.lotacao || f.lotacao || ''} pass. / ${fmt.eixos || f.eixos || ''} eixos` },
      { label: 'RNTRC (ANTT)', val: fmt.rntrc || f.rntrc },
      { label: 'Código Segurança CLA', val: fmt.codigo_seguranca_cla || f.codigo_seguranca_cla },
      { label: 'Número do CRV', val: fmt.numero_crv || f.numero_crv },
    ].filter(c => c.val && c.val.trim() && c.val !== ' cv /  cc' && c.val !== ' pass. /  eixos');

    if (tecCards.length > 0) {
      const tecSection = createDocSection('Especificações Técnicas e Carga', '⚙️');
      const tecGrid = document.createElement('div');
      tecGrid.className = 'fields-grid';
      tecCards.forEach(c => {
        tecGrid.appendChild(createFieldCard(c.label, c.val, false, c.span));
      });
      tecSection.appendChild(tecGrid);
      container.appendChild(tecSection);
    }

    // 4. Observações e Gravames
    const obsVal = fmt.observacoes || f.observacoes;
    if (obsVal && obsVal.trim()) {
      const obsSection = createDocSection('Observações, Gravames e Restrições', '🔒');
      const obsGrid = document.createElement('div');
      obsGrid.className = 'fields-grid';
      obsGrid.appendChild(createFieldCard('Observações Registradas no CRLV', obsVal, false, 'full-width', true));
      obsSection.appendChild(obsGrid);
      container.appendChild(obsSection);
    }
  }

  function renderGenericLayout(data, container) {
    const f = data.fields || {};
    const section = createDocSection('Campos do Documento', '📋');
    const grid = document.createElement('div');
    grid.className = 'fields-grid';

    Object.entries(f).forEach(([key, val]) => {
      if (val && String(val).trim()) {
        const label = key.replace(/_/g, ' ').toUpperCase();
        grid.appendChild(createFieldCard(label, String(val)));
      }
    });

    section.appendChild(grid);
    container.appendChild(section);
  }

  function createPhotoShowcase(photoB64, photoFormat) {
    const showcase = document.createElement('div');
    showcase.className = 'photo-showcase';

    const wrapper = document.createElement('div');
    wrapper.className = 'photo-wrapper';

    const isBpg = (photoFormat && photoFormat.toLowerCase() === 'bpg') || photoB64.startsWith('data:image/bpg');

    if (isBpg && typeof window.BPGDecoder !== 'undefined' && window.Module) {
      const canvas = document.createElement('canvas');
      canvas.id = 'photo-canvas';
      const rendered = decodeBPGToCanvas(photoB64, canvas);
      if (rendered) {
        wrapper.appendChild(canvas);
      } else {
        const img = document.createElement('img');
        img.src = photoB64;
        img.alt = 'Foto CNH';
        wrapper.appendChild(img);
      }
    } else {
      const img = document.createElement('img');
      img.src = photoB64;
      img.alt = 'Foto CNH';
      wrapper.appendChild(img);
    }

    showcase.appendChild(wrapper);

    const badge = document.createElement('div');
    badge.className = 'photo-badge';
    badge.innerHTML = `<span>✓</span> Foto Serpro`;
    showcase.appendChild(badge);

    const actions = document.createElement('div');
    actions.className = 'photo-actions';

    const btnCopyImg = document.createElement('button');
    btnCopyImg.className = 'btn btn-secondary btn-sm';
    btnCopyImg.textContent = 'Copiar Foto';
    btnCopyImg.title = 'Copiar foto para área de transferência';
    btnCopyImg.addEventListener('click', () => {
      copyImageToClipboard(wrapper);
    });

    actions.appendChild(btnCopyImg);
    showcase.appendChild(actions);

    return showcase;
  }

  function decodeBPGToCanvas(base64Bpg, canvas) {
    try {
      const base64Data = base64Bpg.replace(/^data:image\/[a-z0-9_-]+;base64,/, '');
      const bin = atob(base64Data);
      const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) {
        u8[i] = bin.charCodeAt(i);
      }

      const ctx = canvas.getContext('2d');
      const dec = new window.BPGDecoder(ctx);
      const img = dec.bpg_decoder_open();
      if (dec.bpg_decoder_decode(img, u8, u8.length) < 0) return false;

      const img_info_buf = dec.malloc(20);
      dec.bpg_decoder_get_info(img, img_info_buf);
      const heap8 = window.Module["HEAPU8"];
      const heap32 = window.Module["HEAPU32"];
      const w = heap32[img_info_buf >> 2];
      const h = heap32[(img_info_buf + 4) >> 2];
      canvas.width = w;
      canvas.height = h;

      const w4 = w * 4;
      const rgba_line = dec.malloc(w4);
      if (dec.bpg_decoder_start(img, 1) >= 0) {
        const cimg = ctx.createImageData(w, h);
        const dst = cimg.data;
        let p0 = 0;
        for (let y = 0; y < h; y++) {
          dec.bpg_decoder_get_line(img, rgba_line);
          for (let i = 0; i < w4; i++) {
            dst[p0++] = heap8[rgba_line + i];
          }
        }
        ctx.putImageData(cimg, 0, 0);
      }
      dec.free(rgba_line);
      dec.free(img_info_buf);
      dec.bpg_decoder_close(img);
      return true;
    } catch (err) {
      console.warn('Erro ao decodificar BPG no canvas:', err);
      return false;
    }
  }

  function copyImageToClipboard(wrapper) {
    const canvas = wrapper.querySelector('canvas');
    const img = wrapper.querySelector('img');

    if (canvas) {
      canvas.toBlob(blob => {
        if (blob && navigator.clipboard && navigator.clipboard.write) {
          navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]).then(() => {
            showToast('Foto copiada para a área de transferência!');
          }).catch(() => {
            showToast('Não foi possível copiar a imagem diretamente.');
          });
        }
      });
    } else if (img && img.src.startsWith('data:image/png')) {
      fetch(img.src).then(res => res.blob()).then(blob => {
        if (blob && navigator.clipboard && navigator.clipboard.write) {
          navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]).then(() => {
            showToast('Foto copiada para a área de transferência!');
          });
        }
      }).catch(() => {
        showToast('Abra a imagem com o botão direito para salvar.');
      });
    } else {
      showToast('Imagem pronta para uso notarial.');
    }
  }

  function createDocSection(title, icon) {
    const sec = document.createElement('section');
    sec.className = 'doc-section';

    const hdr = document.createElement('div');
    hdr.className = 'section-header';

    const ttl = document.createElement('h3');
    ttl.className = 'section-title';
    ttl.innerHTML = `<span>${icon}</span> ${title}`;

    hdr.appendChild(ttl);
    sec.appendChild(hdr);
    return sec;
  }

  function createFieldCard(label, value, highlight = false, spanClass = '', isAlert = false) {
    const card = document.createElement('div');
    card.className = 'field-card' + (spanClass ? ` ${spanClass}` : '') + (isAlert ? ' alert-card' : '');

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

  function renderRawAccordion(data, container) {
    const fields = data.fields || {};
    const entries = Object.entries(fields);

    const accordion = document.createElement('div');
    accordion.className = 'raw-accordion';

    const header = document.createElement('div');
    header.className = 'raw-accordion-header';
    header.innerHTML = `
      <div class="raw-accordion-title">
        <span>🔍 Dicionário Completo de Campos e Metadados (VIO Raw / Auditoria)</span>
        <span class="raw-count-badge">${entries.length} campos decodificados</span>
      </div>
      <div class="raw-accordion-chevron">▼</div>
    `;

    header.addEventListener('click', () => {
      accordion.classList.toggle('open');
    });

    const body = document.createElement('div');
    body.className = 'raw-accordion-body';

    // Campo de busca rápida
    const searchBox = document.createElement('div');
    searchBox.style.marginBottom = '0.75rem';
    searchBox.innerHTML = `
      <input type="text" placeholder="Filtrar campo por chave ou valor..." class="search-input" style="width: 100%; padding: 0.5rem 0.75rem; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-main); font-size: 0.8rem; font-family: var(--font-mono);">
    `;

    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'raw-table-wrapper';

    const table = document.createElement('table');
    table.className = 'raw-table';
    table.innerHTML = `
      <thead>
        <tr>
          <th>Campo / Chave Serpro</th>
          <th>Valor Decodificado</th>
          <th style="width: 40px;"></th>
        </tr>
      </thead>
      <tbody></tbody>
    `;

    const tbody = table.querySelector('tbody');

    // Metadados adicionais do envelope
    const metaRows = [
      ['__envelope_tipo', data.document_type || '—'],
      ['__envelope_template_id', String(data.template_id || '—')],
      ['__envelope_template_nome', data.template_name || '—'],
      ['__cripto_algoritmo', data.signature_algorithm || '—'],
      ['__data_emissao_timestamp', data.issued_at || '—'],
    ];

    const allRows = [...metaRows, ...entries];

    function populateTable(filter = '') {
      tbody.innerHTML = '';
      const filterLower = filter.toLowerCase().trim();

      allRows.forEach(([k, v]) => {
        const valStr = String(v ?? '');
        if (filterLower && !k.toLowerCase().includes(filterLower) && !valStr.toLowerCase().includes(filterLower)) {
          return;
        }

        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="col-key">${k}</td>
          <td class="col-val">${valStr || '<span style="color: var(--text-muted); font-style: italic;">(vazio)</span>'}</td>
          <td class="col-act">
            <button class="btn-copy-field" title="Copiar ${k}">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </td>
        `;

        tr.querySelector('.btn-copy-field').addEventListener('click', (e) => {
          e.stopPropagation();
          copyToClipboard(valStr, `${k} copiado!`);
        });

        tbody.appendChild(tr);
      });
    }

    populateTable();

    searchBox.querySelector('input').addEventListener('input', (e) => {
      populateTable(e.target.value);
    });

    body.appendChild(searchBox);
    tableWrapper.appendChild(table);
    body.appendChild(tableWrapper);

    accordion.appendChild(header);
    accordion.appendChild(body);
    container.appendChild(accordion);
  }

  function formatNotarySummary(data) {
    const fmt = data.formatted || {};
    const f = data.fields || {};

    if (data.document_type === 'crlv') {
      const lines = [
        `=== DADOS OFICIAIS DO VEÍCULO (CRLV-e / VIO) ===`,
        `AUTENTICIDADE SERPRO/VIO: ${data.is_authentic ? 'AUTÊNTICO / ASSINATURA VÁLIDA' : 'NÃO CONFERE / INVÁLIDO'}`,
        `PLACA: ${fmt.placa_formatada || f.placa || ''}`,
        `RENAVAM: ${fmt.renavam_formatado || f.renavam || ''}`,
        `CHASSI: ${fmt.chassi || f.chassi || ''}`,
        `MARCA/MODELO: ${fmt.marca_modelo || f.marca_modelo || ''}`,
        `ANO FAB/MODELO: ${fmt.ano_fabricacao_modelo || `${f.ano_fabricacao || ''}/${f.ano_modelo || ''}`}`,
        `COR: ${fmt.cor || f.cor || ''} | COMBUSTÍVEL: ${fmt.combustivel || f.combustivel || ''}`,
        `CATEGORIA: ${fmt.categoria || f.categoria || ''} | ESPÉCIE/TIPO: ${[fmt.especie || f.especie, fmt.tipo || f.tipo].filter(Boolean).join(' / ')}`,
        `PROPRIETÁRIO: ${fmt.proprietario || f.nome || ''}`,
        `CPF/CNPJ: ${fmt.cpf_cnpj_formatado || f.cpf_cnpj || ''}`,
        `MUNICÍPIO/UF: ${fmt.uf || f.uf || ''} - ${fmt.municipio || f.local || ''}`,
        `EXERCÍCIO: ${fmt.exercicio || f.exercicio || ''} | DATA EMISSÃO: ${fmt.data_emissao || f.data || ''}`,
        `CÓD. SEGURANÇA CLA: ${fmt.codigo_seguranca_cla || f.codigo_seguranca_cla || ''} | Nº CRV: ${fmt.numero_crv || f.numero_crv || ''}`,
        `MOTOR: ${fmt.motor || f.motor || ''} | POTÊNCIA/CILINDRADAS: ${fmt.potencia || f.potencia || ''} cv / ${fmt.cilindradas || f.cilindradas || ''} cc`,
      ];
      if (fmt.observacoes || f.observacoes) {
        lines.push(`GRAVAMES/OBSERVAÇÕES: ${fmt.observacoes || f.observacoes}`);
      }
      return lines.filter(Boolean).join('\n');
    } else {
      const lines = [
        `=== DADOS OFICIAIS DA HABILITAÇÃO (CNH / VIO) ===`,
        `AUTENTICIDADE SERPRO/VIO: ${data.is_authentic ? 'AUTÊNTICO / ASSINATURA VÁLIDA' : 'NÃO CONFERE / INVÁLIDO'}`,
        `CONDUTOR: ${fmt.nome || f.nome || ''}`,
      ];
      if (fmt.nome_civil || f.nome_civil) {
        lines.push(`NOME CIVIL/SOCIAL: ${fmt.nome_civil || f.nome_civil}`);
      }
      lines.push(
        `CPF: ${fmt.cpf_formatado || f.cpf || ''}`,
        `RG / IDENTIDADE: ${fmt.identidade || f.identidade || ''}`,
        `DATA DE NASCIMENTO: ${fmt.data_nascimento || f.data_nascimento || ''}`,
        `CATEGORIA: ${fmt.categoria || f.categoria || ''}`,
        `REGISTRO CNH: ${fmt.numero_registro || f.numero_registro || ''}`,
        `VALIDADE: ${fmt.data_validade || f.data_validade || ''}`,
        `1ª HABILITAÇÃO: ${fmt.data_primeira_habilitacao || f.data_primeira_habilitacao || ''}`,
        `DATA DE EMISSÃO: ${fmt.data_emissao || f.data_emissao || ''} (${fmt.uf_emissao || f.uf_emissao || ''} - ${fmt.local_emissao || f.local_emissao || ''})`,
        `RENACH: ${fmt.numero_renach || f.numero_renach || ''} | CÓD. VALIDAÇÃO: ${fmt.numero_validacao_cnh || f.numero_validacao_cnh || ''}`
      );
      if (fmt.filiacao_mae || f.filiacao_mae) lines.push(`MÃE: ${fmt.filiacao_mae || f.filiacao_mae}`);
      if (fmt.filiacao_pai || f.filiacao_pai) lines.push(`PAI: ${fmt.filiacao_pai || f.filiacao_pai}`);
      if (fmt.observacoes || f.observacoes) lines.push(`OBSERVAÇÕES/RESTRIÇÕES: ${fmt.observacoes || f.observacoes}`);
      return lines.filter(Boolean).join('\n');
    }
  }
});
