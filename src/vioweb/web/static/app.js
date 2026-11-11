document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const btnBrowse = document.getElementById('btn-browse');
  const btnOpenCamera = document.getElementById('btn-open-camera');
  const btnHeaderUpload = document.getElementById('btn-header-upload');
  const btnHeaderCamera = document.getElementById('btn-header-camera');
  const btnResultCamera = document.getElementById('btn-result-camera');

  const cameraPanel = document.getElementById('camera-panel');
  const cameraStage = document.getElementById('camera-stage');
  const cameraVideo = document.getElementById('camera-video');
  const cameraSelect = document.getElementById('camera-select');
  const cameraStatusText = document.getElementById('camera-status-text');
  const btnMirrorCamera = document.getElementById('btn-mirror-camera');
  const btnCloseCamera = document.getElementById('btn-close-camera');
  const btnCaptureNow = document.getElementById('btn-capture-now');

  const loadingState = document.getElementById('loading-state');
  const errorBanner = document.getElementById('error-banner');
  const errorTitle = document.getElementById('error-title');
  const errorMessage = document.getElementById('error-message');
  const btnErrorClose = document.getElementById('btn-error-close');
  const resultSection = document.getElementById('result-section');
  const docTypeBadge = document.getElementById('doc-type-badge');
  const authBadge = document.getElementById('auth-badge');
  const authIcon = document.getElementById('auth-icon');
  const authStatusText = document.getElementById('auth-status-text');
  const documentContent = document.getElementById('document-content');
  const btnCopyAll = document.getElementById('btn-copy-all');
  const btnNewCheck = document.getElementById('btn-new-check');
  const toast = document.getElementById('toast');

  let currentResult = null;
  let mediaStream = null;
  let scanIntervalId = null;
  let isScanningFrame = false;
  let scanAttemptCount = 0;
  let isMirrored = localStorage.getItem('vioweb_camera_mirrored') === '1';

  const captureCanvas = document.createElement('canvas');
  const captureCtx = captureCanvas.getContext('2d', { willReadFrequently: true });

  // Browse click
  btnBrowse.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  btnOpenCamera.addEventListener('click', (e) => {
    e.stopPropagation();
    openCameraScanner();
  });

  if (btnHeaderUpload) {
    btnHeaderUpload.addEventListener('click', () => {
      stopCamera();
      resetView();
      fileInput.click();
    });
  }

  if (btnHeaderCamera) {
    btnHeaderCamera.addEventListener('click', () => {
      openCameraScanner();
    });
  }

  if (btnResultCamera) {
    btnResultCamera.addEventListener('click', () => {
      openCameraScanner();
    });
  }

  dropzone.addEventListener('click', (e) => {
    if (e.target.closest('button')) return;
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
          stopCamera();
          processFile(blob);
          showToast('Imagem colada da área de transferência');
          return;
        }
      }
    }
  });

  // Keyboard shortcuts for camera mode and modals
  const modalPix = document.getElementById('modal-pix');
  const modalApi = document.getElementById('modal-api');
  const btnHeaderPix = document.getElementById('btn-header-pix');
  const btnOpenPixModal = document.getElementById('btn-open-pix-modal');
  const btnFooterPix = document.getElementById('btn-footer-pix');
  const btnClosePixModal = document.getElementById('btn-close-pix-modal');
  const btnCopyPix = document.getElementById('btn-copy-pix');
  const pixKeyValue = document.getElementById('pix-key-value');

  const btnHeaderApi = document.getElementById('btn-header-api');
  const btnOpenApiModal = document.getElementById('btn-open-api-modal');
  const btnFooterApi = document.getElementById('btn-footer-api');
  const btnCloseApiModal = document.getElementById('btn-close-api-modal');

  function openModal(modalEl) {
    if (modalEl) modalEl.style.display = 'flex';
  }
  function closeModal(modalEl) {
    if (modalEl) modalEl.style.display = 'none';
  }

  [btnHeaderPix, btnOpenPixModal, btnFooterPix].forEach(btn => {
    if (btn) btn.addEventListener('click', () => openModal(modalPix));
  });
  if (btnClosePixModal) btnClosePixModal.addEventListener('click', () => closeModal(modalPix));
  if (modalPix) {
    modalPix.addEventListener('click', (e) => {
      if (e.target === modalPix) closeModal(modalPix);
    });
  }
  if (btnCopyPix && pixKeyValue) {
    btnCopyPix.addEventListener('click', () => {
      copyToClipboard(pixKeyValue.textContent.trim(), 'Chave PIX copiada para a área de transferência');
    });
  }

  [btnHeaderApi, btnOpenApiModal, btnFooterApi].forEach(btn => {
    if (btn) btn.addEventListener('click', () => openModal(modalApi));
  });
  if (btnCloseApiModal) btnCloseApiModal.addEventListener('click', () => closeModal(modalApi));
  if (modalApi) {
    modalApi.addEventListener('click', (e) => {
      if (e.target === modalApi) closeModal(modalApi);
    });
  }

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (modalPix && modalPix.style.display !== 'none') {
        closeModal(modalPix);
        return;
      }
      if (modalApi && modalApi.style.display !== 'none') {
        closeModal(modalApi);
        return;
      }
    }
    if (cameraPanel.style.display !== 'none') {
      if (e.key === 'Escape') {
        e.preventDefault();
        stopCamera();
        resetView();
      } else if (e.code === 'Space' && document.activeElement !== cameraSelect) {
        e.preventDefault();
        captureCameraFrame(true);
      }
    }
  });

  btnErrorClose.addEventListener('click', () => {
    errorBanner.style.display = 'none';
  });

  btnNewCheck.addEventListener('click', () => {
    stopCamera();
    resetView();
  });

  btnCopyAll.addEventListener('click', () => {
    if (!currentResult) return;
    const text = formatNotarySummary(currentResult);
    copyToClipboard(text, 'Ficha completa copiada para o sistema notarial');
  });

  // Camera controls
  btnCloseCamera.addEventListener('click', () => {
    stopCamera();
    resetView();
  });

  btnMirrorCamera.addEventListener('click', () => {
    isMirrored = !isMirrored;
    localStorage.setItem('vioweb_camera_mirrored', isMirrored ? '1' : '0');
    cameraVideo.classList.toggle('mirrored', isMirrored);
  });

  cameraSelect.addEventListener('change', () => {
    const deviceId = cameraSelect.value;
    if (deviceId) {
      localStorage.setItem('vioweb_camera_id', deviceId);
      startCameraStream(deviceId);
    }
  });

  btnCaptureNow.addEventListener('click', () => {
    captureCameraFrame(true);
  });

  function resetView() {
    resultSection.style.display = 'none';
    errorBanner.style.display = 'none';
    cameraPanel.style.display = 'none';
    dropzone.style.display = 'flex';
    loadingState.style.display = 'none';
    fileInput.value = '';
    currentResult = null;
  }

  // ------------------------------------------------------------------ //
  // Webcam Scanner Logic
  // ------------------------------------------------------------------ //
  async function openCameraScanner() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showError('O navegador atual não suporta acesso à câmera ou a página não está em contexto seguro (HTTPS / localhost).');
      return;
    }

    errorBanner.style.display = 'none';
    resultSection.style.display = 'none';
    dropzone.style.display = 'none';
    loadingState.style.display = 'none';
    cameraPanel.style.display = 'flex';
    cameraStage.classList.remove('scan-success');
    cameraVideo.classList.toggle('mirrored', isMirrored);

    const savedDeviceId = localStorage.getItem('vioweb_camera_id') || '';
    await startCameraStream(savedDeviceId);
    await populateCameraDevices();
  }

  async function populateCameraDevices() {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(d => d.kind === 'videoinput');
      cameraSelect.innerHTML = '';

      videoDevices.forEach((dev, idx) => {
        const opt = document.createElement('option');
        opt.value = dev.deviceId;
        opt.textContent = dev.label || `Câmera ${idx + 1}`;
        cameraSelect.appendChild(opt);
      });

      const currentTrack = mediaStream && mediaStream.getVideoTracks()[0];
      const activeDeviceId = currentTrack && currentTrack.getSettings ? currentTrack.getSettings().deviceId : '';
      if (activeDeviceId) {
        cameraSelect.value = activeDeviceId;
      }
      cameraSelect.style.display = videoDevices.length > 1 ? 'inline-block' : 'none';
    } catch (err) {
      console.warn('Não foi possível listar dispositivos de vídeo:', err);
    }
  }

  async function startCameraStream(preferredDeviceId = '') {
    stopCameraStreamOnly();

    const videoConstraints = {
      width: { ideal: 1920 },
      height: { ideal: 1080 },
    };
    if (preferredDeviceId) {
      videoConstraints.deviceId = { exact: preferredDeviceId };
    } else {
      videoConstraints.facingMode = { ideal: 'environment' };
    }

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        video: videoConstraints,
        audio: false,
      });
    } catch (firstErr) {
      try {
        // Fallback sem restrições estritas caso a webcam do PC rejeite 1080p ou exact deviceId
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
      } catch (err) {
        stopCamera();
        resetView();
        showError(`Não foi possível acessar a webcam: ${err.message || 'Permissão negada pelo navegador.'}`);
        return;
      }
    }

    cameraVideo.srcObject = mediaStream;
    try {
      await cameraVideo.play();
    } catch (_) {}

    scanAttemptCount = 0;
    cameraStatusText.textContent = 'Posicione o QR Code do documento físico ou tela dentro da área de leitura';

    if (scanIntervalId) clearInterval(scanIntervalId);
    scanIntervalId = setInterval(() => {
      captureCameraFrame(false);
    }, 550);
  }

  function stopCameraStreamOnly() {
    if (scanIntervalId) {
      clearInterval(scanIntervalId);
      scanIntervalId = null;
    }
    isScanningFrame = false;
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      mediaStream = null;
    }
    if (cameraVideo) {
      cameraVideo.srcObject = null;
    }
  }

  function stopCamera() {
    stopCameraStreamOnly();
    if (cameraPanel) {
      cameraPanel.style.display = 'none';
    }
  }

  async function captureCameraFrame(isManual) {
    if (!mediaStream || !cameraVideo || cameraVideo.readyState < 2) return;
    if (isScanningFrame && !isManual) return;

    const vw = cameraVideo.videoWidth;
    const vh = cameraVideo.videoHeight;
    if (!vw || !vh) return;

    isScanningFrame = true;
    scanAttemptCount += 1;

    try {
      // Alterna entre recorte central de alta densidade (mira) e quadro completo
      const useCenterCrop = !isManual && (scanAttemptCount % 2 === 1);
      if (useCenterCrop) {
        const side = Math.floor(Math.min(vw, vh) * 0.72);
        const sx = Math.floor((vw - side) / 2);
        const sy = Math.floor((vh - side) / 2);
        captureCanvas.width = side;
        captureCanvas.height = side;
        captureCtx.drawImage(cameraVideo, sx, sy, side, side, 0, 0, side, side);
      } else {
        captureCanvas.width = vw;
        captureCanvas.height = vh;
        captureCtx.drawImage(cameraVideo, 0, 0, vw, vh);
      }

      const blob = await new Promise(resolve => captureCanvas.toBlob(resolve, 'image/jpeg', 0.92));
      if (!blob || !mediaStream) {
        isScanningFrame = false;
        return;
      }

      const formData = new FormData();
      formData.append('file', blob, 'webcam-frame.jpg');

      const response = await fetch('/api/documents/verify', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.is_parsed) {
        cameraStage.classList.add('scan-success');
        playScanSuccessTone();
        stopCamera();
        currentResult = data;
        renderResult(data);
        showToast('Documento lido com sucesso pela câmera');
        return;
      }

      if (isManual) {
        cameraStatusText.textContent = data.message || 'Ainda não foi possível focar o QR Code. Aproxime ou incline levemente o documento para evitar reflexo.';
      }
    } catch (_) {
      // Ignora erros transitórios durante o loop de vídeo
    } finally {
      isScanningFrame = false;
    }
  }

  function playScanSuccessTone() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.setValueAtTime(1174.66, ctx.currentTime + 0.07);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.18);
    } catch (_) {}
  }

  // ------------------------------------------------------------------ //
  // Upload & Document Verification
  // ------------------------------------------------------------------ //
  async function processFile(file) {
    errorBanner.style.display = 'none';
    dropzone.style.display = 'none';
    cameraPanel.style.display = 'none';
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
        const errDetail = data.message || (Array.isArray(data.errors) && data.errors.length ? data.errors.join(' | ') : 'Falha ao decodificar documento.');
        showError(errDetail);
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

  function copyToClipboard(text, successMsg = 'Copiado') {
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
    const typeLabels = {
      crlv: 'CRLV-e Digital',
      cnh: 'CNH Digital',
      atpv: 'ATPV-e (Intenção de Venda)',
      cin: 'Carteira de Identidade Nacional (CIN)',
      external_qr: 'QR Code Externo',
    };
    docTypeBadge.textContent = data.document_name || typeLabels[data.document_type] || 'Documento Digital';

    if (data.document_type === 'external_qr') {
      authBadge.className = 'auth-badge invalid';
      if (authIcon) authIcon.textContent = '!';
      authStatusText.textContent = 'QR Code Externo (Sem Assinatura VIO)';
    } else if (data.is_authentic) {
      authBadge.className = 'auth-badge authentic';
      if (authIcon) authIcon.textContent = '✓';
      authStatusText.textContent = 'Documento Autêntico (Assinatura VIO Válida)';
    } else {
      authBadge.className = 'auth-badge invalid';
      if (authIcon) authIcon.textContent = '✕';
      authStatusText.textContent = 'Assinatura Inválida / Não Autêntico';
    }

    documentContent.innerHTML = '';

    // Exibir avisos/alertas diagnósticos se houver
    const diagnostics = [
      ...(Array.isArray(data.warnings) ? data.warnings : []),
      ...(!data.is_authentic && Array.isArray(data.errors) ? data.errors : []),
    ];
    if (diagnostics.length > 0) {
      const diagBox = document.createElement('div');
      diagBox.className = 'notary-disclaimer';
      diagBox.style.borderLeftColor = 'var(--detran-red)';
      diagBox.style.backgroundColor = 'var(--danger-bg)';
      diagBox.style.color = 'var(--danger-text)';
      diagBox.innerHTML = `<strong>Diagnóstico da Leitura:</strong> ${diagnostics.join(' • ')}`;
      documentContent.appendChild(diagBox);
    }

    if (data.document_type === 'cnh') {
      renderCnhLayout(data, documentContent);
    } else if (data.document_type === 'crlv') {
      renderCrlvLayout(data, documentContent);
    } else if (data.document_type === 'atpv') {
      renderAtpvLayout(data, documentContent);
    } else if (data.document_type === 'external_qr') {
      renderExternalQrLayout(data, documentContent);
    } else {
      renderGenericLayout(data, documentContent);
    }

    renderRawAccordion(data, documentContent);
    resultSection.style.display = 'block';
  }

  function renderCnhLayout(data, container) {
    const fmt = data.formatted || {};
    const f = data.fields || {};

    const heroLayout = document.createElement('div');
    heroLayout.className = 'cnh-hero-layout';

    if (data.photo_b64) {
      const photoShowcase = createPhotoShowcase(data.photo_b64, data.photo_format);
      heroLayout.appendChild(photoShowcase);
    }

    const idSection = document.createElement('div');
    idSection.style.display = 'flex';
    idSection.style.flexDirection = 'column';
    idSection.style.gap = '0.75rem';
    idSection.style.flex = '1';

    const idGrid = document.createElement('div');
    idGrid.className = 'fields-grid';

    const idCards = [
      { label: 'Nome do Condutor', val: fmt.nome || f.nome, highlight: true, span: 'span-2' },
      { label: 'Nome Civil / Social', val: fmt.nome_civil || f.nome_civil, span: 'span-2' },
      { label: 'CPF', val: fmt.cpf_formatado || f.cpf },
      { label: 'RG / Documento de Identidade', val: fmt.identidade || f.identidade },
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

    const filiacaoCards = [
      { label: 'Filiação Materna (Mãe)', val: fmt.filiacao_mae || f.filiacao_mae, span: 'span-2' },
      { label: 'Filiação Paterna (Pai)', val: fmt.filiacao_pai || f.filiacao_pai, span: 'span-2' },
    ].filter(c => c.val && c.val.trim());

    if (filiacaoCards.length > 0) {
      const filiacaoSection = createDocSection('Filiação Declarada');
      const filiacaoGrid = document.createElement('div');
      filiacaoGrid.className = 'fields-grid';
      filiacaoCards.forEach(c => {
        filiacaoGrid.appendChild(createFieldCard(c.label, c.val, false, c.span));
      });
      filiacaoSection.appendChild(filiacaoGrid);
      container.appendChild(filiacaoSection);
    }

    const habCards = [
      { label: 'Número de Registro CNH', val: fmt.numero_registro || f.numero_registro, highlight: true },
      { label: 'Validade do Exame / CNH', val: fmt.data_validade || f.data_validade, highlight: true },
      { label: 'Data da 1ª Habilitação', val: fmt.data_primeira_habilitacao || f.data_primeira_habilitacao },
      { label: 'Data de Emissão', val: fmt.data_emissao || f.data_emissao },
      { label: 'UF / Município de Emissão', val: `${fmt.uf_emissao || f.uf_emissao || ''} - ${fmt.local_emissao || f.local_emissao || ''}` },
      { label: 'Formulário RENACH', val: fmt.numero_renach || f.numero_renach },
      { label: 'Código de Segurança / Validação', val: fmt.numero_validacao_cnh || f.numero_validacao_cnh },
      { label: 'Permissão', val: fmt.permissao || f.permissao },
      { label: 'ACC (Ciclomotor)', val: fmt.acc || f.acc },
    ].filter(c => c.val && c.val.trim() && c.val !== ' - ');

    const habSection = createDocSection('Dados da Habilitação, Emissão e Prazos');
    const habGrid = document.createElement('div');
    habGrid.className = 'fields-grid';
    habCards.forEach(c => {
      habGrid.appendChild(createFieldCard(c.label, c.val, c.highlight, c.span));
    });
    habSection.appendChild(habGrid);
    container.appendChild(habSection);

    const obsVal = fmt.observacoes || f.observacoes;
    if (obsVal && obsVal.trim()) {
      const obsSection = createDocSection('Observações e Restrições Médicas / Profissionais');
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

    const veicSection = createDocSection('Identificação Oficial do Veículo');
    const veicGrid = document.createElement('div');
    veicGrid.className = 'fields-grid';

    const veicCards = [
      { label: 'Placa do Veículo', val: fmt.placa_formatada || f.placa, highlight: true },
      { label: 'Código Renavam', val: fmt.renavam_formatado || f.renavam, highlight: true },
      { label: 'Chassi', val: fmt.chassi || f.chassi },
      { label: 'Marca / Modelo / Versão', val: fmt.marca_modelo || f.marca_modelo, span: 'span-2' },
      { label: 'Ano Fabricação / Modelo', val: fmt.ano_fabricacao_modelo || `${f.ano_fabricacao || ''}/${f.ano_modelo || ''}` },
      { label: 'Cor Predominante', val: fmt.cor || f.cor },
      { label: 'Combustível', val: fmt.combustivel || f.combustivel },
      { label: 'Categoria', val: fmt.categoria || f.categoria },
      { label: 'Espécie / Tipo / Carroceria', val: [fmt.especie || f.especie, fmt.tipo || f.tipo, fmt.carroceria || f.carroceria].filter(Boolean).join(' / ') },
    ];

    veicCards.forEach(c => {
      if (c.val && c.val.trim() && c.val !== '/') {
        veicGrid.appendChild(createFieldCard(c.label, c.val, c.highlight, c.span));
      }
    });
    veicSection.appendChild(veicGrid);
    container.appendChild(veicSection);

    const propSection = createDocSection('Proprietário Atual e Licenciamento');
    const propGrid = document.createElement('div');
    propGrid.className = 'fields-grid';

    const propCards = [
      { label: 'Nome do Proprietário', val: fmt.proprietario || f.nome, highlight: true, span: 'span-2' },
      { label: 'CPF / CNPJ', val: fmt.cpf_cnpj_formatado || f.cpf_cnpj, highlight: true },
      { label: 'Exercício Licenciado', val: fmt.exercicio || f.exercicio, highlight: true },
      { label: 'Município / UF de Jurisdição', val: `${fmt.uf || f.uf || ''} - ${fmt.municipio || f.local || ''}` },
      { label: 'Data de Emissão', val: fmt.data_emissao || f.data },
    ];

    propCards.forEach(c => {
      if (c.val && c.val.trim() && c.val !== ' - ') {
        propGrid.appendChild(createFieldCard(c.label, c.val, c.highlight, c.span));
      }
    });
    propSection.appendChild(propGrid);
    container.appendChild(propSection);

    const tecCards = [
      { label: 'Potência / Cilindradas', val: `${fmt.potencia || f.potencia || ''} cv / ${fmt.cilindradas || f.cilindradas || ''} cc` },
      { label: 'Número do Motor', val: fmt.motor || f.motor },
      { label: 'Capacidade Máx. de Carga', val: fmt.capacidade_maxima_carga || f.capacidade_maxima_carga },
      { label: 'Peso Bruto Total (PBT)', val: fmt.pbt || f.pbt },
      { label: 'Cap. Máx. Tração (CMT)', val: fmt.cmt || f.cmt },
      { label: 'Lotação / Eixos', val: `${fmt.lotacao || f.lotacao || ''} pass. / ${fmt.eixos || f.eixos || ''} eixos` },
      { label: 'RNTRC', val: fmt.rntrc || f.rntrc },
      { label: 'Código de Segurança CLA', val: fmt.codigo_seguranca_cla || f.codigo_seguranca_cla },
      { label: 'Número do CRV', val: fmt.numero_crv || f.numero_crv },
    ].filter(c => c.val && c.val.trim() && c.val !== ' cv /  cc' && c.val !== ' pass. /  eixos');

    if (tecCards.length > 0) {
      const tecSection = createDocSection('Especificações Técnicas e Numeração do CRV/CLA');
      const tecGrid = document.createElement('div');
      tecGrid.className = 'fields-grid';
      tecCards.forEach(c => {
        tecGrid.appendChild(createFieldCard(c.label, c.val, false, c.span));
      });
      tecSection.appendChild(tecGrid);
      container.appendChild(tecSection);
    }

    const obsVal = fmt.observacoes || f.observacoes;
    if (obsVal && obsVal.trim()) {
      const obsSection = createDocSection('Observações, Gravames e Restrições');
      const obsGrid = document.createElement('div');
      obsGrid.className = 'fields-grid';
      obsGrid.appendChild(createFieldCard('Observações Registradas no CRLV-e', obsVal, false, 'full-width', true));
      obsSection.appendChild(obsGrid);
      container.appendChild(obsSection);
    }
  }

  function renderAtpvLayout(data, container) {
    const fmt = data.formatted || {};
    const f = data.fields || {};

    const veicSection = createDocSection('Identificação do Veículo e ATPV-e');
    const veicGrid = document.createElement('div');
    veicGrid.className = 'fields-grid';

    const veicCards = [
      { label: 'Placa do Veículo', val: fmt.placa_formatada || f.placa, highlight: true },
      { label: 'Código Renavam', val: fmt.renavam_formatado || f.renavam, highlight: true },
      { label: 'Chassi do Veículo', val: fmt.chassi || f.chassi },
      { label: 'Marca / Modelo / Versão', val: fmt.marca_modelo || f.marca_modelo, span: 'span-2' },
      { label: 'Ano Fabricação / Modelo', val: fmt.ano_fabricacao_modelo || `${f.ano_fabricacao || ''}/${f.ano_modelo || ''}` },
      { label: 'Cor Predominante', val: fmt.cor || f.cor },
      { label: 'Número da ATPV-e', val: fmt.numero_atpv || f.numero_atpv, highlight: true },
      { label: 'Código de Segurança CRV / CLA', val: fmt.codigo_seguranca_crv || f.codigo_seguranca_crv },
      { label: 'Número do CRV', val: fmt.numero_crv || f.numero_crv },
      { label: 'UF / Emissão do CRV', val: `${fmt.uf_emissao_crv || f.uf_emissao_crv || ''} - ${fmt.data_emissao_crv || f.data_emissao_crv || ''}` },
    ];

    veicCards.forEach(c => {
      if (c.val && String(c.val).trim() && c.val !== '/' && c.val !== ' - ') {
        veicGrid.appendChild(createFieldCard(c.label, String(c.val), c.highlight, c.span));
      }
    });
    veicSection.appendChild(veicGrid);
    container.appendChild(veicSection);

    const vendaSection = createDocSection('Dados da Transação, Local e Hodômetro');
    const vendaGrid = document.createElement('div');
    vendaGrid.className = 'fields-grid';

    const vendaCards = [
      { label: 'Valor Declarado da Venda', val: fmt.valor_venda || f.valor_venda, highlight: true },
      { label: 'Data da Venda', val: fmt.data_venda || f.data_venda, highlight: true },
      { label: 'Local / Município da Venda', val: fmt.local_venda || f.local_venda },
      { label: 'Quilometragem / Hodômetro (km)', val: fmt.kilometragem_hodometro || f.kilometragem_hodometro },
    ];

    vendaCards.forEach(c => {
      if (c.val && String(c.val).trim() && c.val !== ' - ') {
        vendaGrid.appendChild(createFieldCard(c.label, String(c.val), c.highlight, c.span));
      }
    });
    vendaSection.appendChild(vendaGrid);
    container.appendChild(vendaSection);

    const vendSection = createDocSection('Vendedor / Proprietário Anterior (Transmitente)');
    const vendGrid = document.createElement('div');
    vendGrid.className = 'fields-grid';

    const vendCards = [
      { label: 'Nome do Vendedor', val: fmt.nome_vendedor || f.nome_vendedor, highlight: true, span: 'span-2' },
      { label: 'CPF / CNPJ do Vendedor', val: fmt.documento_vendedor_formatado || f.documento_vendedor, highlight: true },
      { label: 'E-mail do Vendedor', val: fmt.email_vendedor || f.email_vendedor },
      { label: 'Município / UF do Vendedor', val: `${fmt.uf_vendedor || f.uf_vendedor || ''} - ${fmt.municipio_vendedor || f.municipio_vendedor || ''}` },
    ];

    vendCards.forEach(c => {
      if (c.val && String(c.val).trim() && c.val !== ' - ') {
        vendGrid.appendChild(createFieldCard(c.label, String(c.val), c.highlight, c.span));
      }
    });
    vendSection.appendChild(vendGrid);
    container.appendChild(vendSection);

    const compSection = createDocSection('Comprador / Adquirente');
    const compGrid = document.createElement('div');
    compGrid.className = 'fields-grid';

    const compCards = [
      { label: 'Nome do Comprador', val: fmt.nome_comprador || f.nome_comprador, highlight: true, span: 'span-2' },
      { label: 'CPF / CNPJ do Comprador', val: fmt.documento_comprador_formatado || f.documento_comprador, highlight: true },
      { label: 'E-mail do Comprador', val: fmt.email_comprador || f.email_comprador },
      { label: 'Município / UF do Comprador', val: `${fmt.uf_comprador || f.uf_comprador || ''} - ${fmt.municipio_comprador || f.municipio_comprador || ''}` },
    ];

    compCards.forEach(c => {
      if (c.val && String(c.val).trim() && c.val !== ' - ') {
        compGrid.appendChild(createFieldCard(c.label, String(c.val), c.highlight, c.span));
      }
    });
    compSection.appendChild(compGrid);
    container.appendChild(compSection);
  }

  function renderExternalQrLayout(data, container) {
    const f = data.fields || {};
    const section = createDocSection('Conteúdo do QR Code Externo (Não-VIO)');
    const grid = document.createElement('div');
    grid.className = 'fields-grid';

    if (f.tipo_qr_detectado) {
      grid.appendChild(createFieldCard('Padrão Detectado', f.tipo_qr_detectado, true, 'span-2'));
    }
    if (f.dominio) {
      grid.appendChild(createFieldCard('Domínio / Emissor', f.dominio));
    }
    if (f.url_verificacao) {
      grid.appendChild(createFieldCard('URL Completa do QR Code', f.url_verificacao, false, 'full-width'));
    } else if (f.conteudo_qr) {
      grid.appendChild(createFieldCard('Conteúdo Bruto do QR Code', f.conteudo_qr, false, 'full-width'));
    }

    Object.entries(f).forEach(([key, val]) => {
      if (['tipo_qr_detectado', 'dominio', 'url_verificacao', 'conteudo_qr'].includes(key)) return;
      if (val && String(val).trim()) {
        const label = key.replace(/_/g, ' ').toUpperCase();
        grid.appendChild(createFieldCard(label, String(val)));
      }
    });

    section.appendChild(grid);
    container.appendChild(section);
  }

  const GENERIC_FIELD_LABELS = {
    nome: 'Nome / Titular',
    nome_civil: 'Nome Civil',
    nome_social: 'Nome Social',
    cpf: 'CPF',
    cnpj: 'CNPJ',
    cpf_cnpj: 'CPF / CNPJ',
    rg: 'RG / Identidade',
    identidade: 'Documento de Identidade',
    data_nascimento: 'Data de Nascimento',
    dn: 'Data de Nascimento',
    data_emissao: 'Data de Emissão',
    data_validade: 'Data de Validade',
    validade: 'Validade',
    filiacao_mae: 'Filiação (Mãe)',
    filiacao_pai: 'Filiação (Pai)',
    naturalidade: 'Naturalidade',
    nacionalidade: 'Nacionalidade',
    orgao_expedidor: 'Órgão Expedidor',
    uf: 'UF',
    municipio: 'Município',
    placa: 'Placa Mercosul / Veículo',
    renavam: 'Código RENAVAM',
    chassi: 'Chassi',
    nome_embarcacao: 'Nome da Embarcação',
    numero_inscricao: 'Nº de Inscrição (Marinha / TIE)',
    capitania: 'Capitania / Delegacia / Agência',
    tipo_embarcacao: 'Tipo de Embarcação',
    area_navegacao: 'Área de Navegação',
    arqueacao_bruta: 'Arqueação Bruta (AB)',
    registro_profissional: 'Registro Profissional',
    numero_registro: 'Número de Registro',
    inscricao: 'Número de Inscrição',
    matricula: 'Matrícula Funcional',
    cargo: 'Cargo / Função',
    funcao: 'Função',
    lotacao: 'Lotação',
    conselho: 'Conselho / Órgão Emissor',
    titulo_profissional: 'Título Profissional',
    sigma: 'Nº SIGMA (Exército)',
    especie_arma: 'Espécie da Arma',
    marca_arma: 'Marca da Arma',
    calibre: 'Calibre',
    numero_serie: 'Número de Série',
  };

  function humanizeFieldKey(key) {
    const k = String(key || '').toLowerCase();
    if (GENERIC_FIELD_LABELS[k]) return GENERIC_FIELD_LABELS[k];
    return String(key || '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, ch => ch.toUpperCase());
  }

  function renderGenericLayout(data, container) {
    const f = (data.formatted && Object.keys(data.formatted).length) ? data.formatted : (data.fields || {});
    const docTitle = data.document_name || data.template_name || 'Documento Oficial VIO';
    const section = createDocSection(`Dados Extraídos — ${docTitle}`);
    const grid = document.createElement('div');
    grid.className = 'fields-grid';

    const highlightKeys = new Set([
      'nome', 'cpf', 'cnpj', 'cpf_cnpj', 'placa', 'renavam',
      'numero_inscricao', 'nome_embarcacao', 'registro_profissional',
      'numero_registro', 'matricula', 'sigma',
    ]);

    Object.entries(f).forEach(([key, val]) => {
      if (key === '_extras') return;
      if (val && String(val).trim()) {
        const label = humanizeFieldKey(key);
        const isHighlight = highlightKeys.has(key.toLowerCase());
        const span = (key.toLowerCase().includes('nome') || String(val).length > 36) ? 'span-2' : '';
        grid.appendChild(createFieldCard(label, String(val), isHighlight, span));
      }
    });

    section.appendChild(grid);

    if (data.photo_b64) {
      const mainLayout = document.createElement('div');
      mainLayout.className = 'cnh-main-layout';

      const fieldsCol = document.createElement('div');
      fieldsCol.className = 'cnh-fields-col';
      fieldsCol.appendChild(section);

      const photoCol = document.createElement('div');
      photoCol.className = 'cnh-photo-col';
      photoCol.appendChild(createPhotoShowcase(data.photo_b64, data.photo_format));

      mainLayout.appendChild(fieldsCol);
      mainLayout.appendChild(photoCol);
      container.appendChild(mainLayout);
    } else {
      container.appendChild(section);
    }
  }

  function createPhotoShowcase(photoB64, photoFormat) {
    const showcase = document.createElement('div');
    showcase.className = 'photo-showcase';

    const wrapper = document.createElement('div');
    wrapper.className = 'photo-wrapper';

    const isBpg = photoB64.startsWith('data:image/bpg');

    if (isBpg && typeof window.BPGDecoder !== 'undefined') {
      const canvas = document.createElement('canvas');
      canvas.id = 'photo-canvas';
      const rendered = decodeBPGToCanvas(photoB64, canvas);
      if (rendered) {
        wrapper.appendChild(canvas);
      } else {
        const img = document.createElement('img');
        img.src = photoB64;
        img.alt = 'Fotografia CNH';
        wrapper.appendChild(img);
      }
    } else {
      const img = document.createElement('img');
      img.src = photoB64;
      img.alt = 'Fotografia CNH';
      wrapper.appendChild(img);
    }

    showcase.appendChild(wrapper);

    const badge = document.createElement('div');
    badge.className = 'photo-badge';
    badge.textContent = 'Biometria Serpro';
    showcase.appendChild(badge);

    const actions = document.createElement('div');
    actions.className = 'photo-actions';

    const btnCopyImg = document.createElement('button');
    btnCopyImg.type = 'button';
    btnCopyImg.className = 'btn btn-secondary btn-sm';
    btnCopyImg.textContent = 'Copiar Foto';
    btnCopyImg.title = 'Copiar fotografia para a área de transferência';
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
      let ok = false;
      dec.onload = function () {
        const imageData = this.imageData || (this.frames && this.frames[0] && this.frames[0].img);
        if (imageData) {
          canvas.width = imageData.width;
          canvas.height = imageData.height;
          ctx.putImageData(imageData, 0, 0);
          ok = true;
        }
      };
      if (typeof dec._onload === 'function') {
        dec._onload({ response: u8.buffer }, null);
      } else {
        dec.load(base64Bpg);
        ok = true;
      }
      return ok;
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
            showToast('Fotografia copiada para a área de transferência');
          }).catch(() => {
            showToast('Não foi possível copiar a imagem diretamente');
          });
        }
      });
    } else if (img && img.src.startsWith('data:image/png')) {
      fetch(img.src).then(res => res.blob()).then(blob => {
        if (blob && navigator.clipboard && navigator.clipboard.write) {
          navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]).then(() => {
            showToast('Fotografia copiada para a área de transferência');
          });
        }
      }).catch(() => {
        showToast('Clique com o botão direito sobre a foto para salvar');
      });
    } else {
      showToast('Imagem pronta para uso notarial');
    }
  }

  function createDocSection(title) {
    const sec = document.createElement('section');
    sec.className = 'doc-section';

    const hdr = document.createElement('div');
    hdr.className = 'section-header';

    const ttl = document.createElement('h3');
    ttl.className = 'section-title';
    ttl.textContent = title;

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
    btn.type = 'button';
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
      copyToClipboard(value, `${label} copiado`);
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
        <span>Dicionário Técnico de Campos e Metadados (Auditoria VIO)</span>
        <span class="raw-count-badge">${entries.length} campos</span>
      </div>
      <div class="raw-accordion-chevron">▼</div>
    `;

    header.addEventListener('click', () => {
      accordion.classList.toggle('open');
    });

    const body = document.createElement('div');
    body.className = 'raw-accordion-body';

    const searchBox = document.createElement('div');
    searchBox.style.marginBottom = '0.75rem';
    searchBox.innerHTML = `
      <input type="text" placeholder="Filtrar campo por chave ou valor..." class="search-input" style="width: 100%; padding: 0.5rem 0.75rem; background: var(--bg-subtle); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-main); font-size: 0.78rem; font-family: var(--font-mono);">
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
            <button type="button" class="btn-copy-field" title="Copiar ${k}">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </td>
        `;

        tr.querySelector('.btn-copy-field').addEventListener('click', (e) => {
          e.stopPropagation();
          copyToClipboard(valStr, `${k} copiado`);
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
    } else if (data.document_type === 'atpv') {
      const lines = [
        `=== DADOS OFICIAIS DA ATPV-e (INTENÇÃO DE VENDA / VIO) ===`,
        `AUTENTICIDADE SERPRO/VIO: ${data.is_authentic ? 'AUTÊNTICO / ASSINATURA VÁLIDA' : 'NÃO CONFERE / INVÁLIDO'}`,
        `Nº ATPV-e: ${fmt.numero_atpv || f.numero_atpv || ''} | CÓD. SEGURANÇA CRV: ${fmt.codigo_seguranca_crv || f.codigo_seguranca_crv || ''} | Nº CRV: ${fmt.numero_crv || f.numero_crv || ''}`,
        `PLACA: ${fmt.placa_formatada || f.placa || ''} | RENAVAM: ${fmt.renavam_formatado || f.renavam || ''} | CHASSI: ${fmt.chassi || f.chassi || ''}`,
        `MARCA/MODELO: ${fmt.marca_modelo || f.marca_modelo || ''} (${fmt.ano_fabricacao_modelo || `${f.ano_fabricacao || ''}/${f.ano_modelo || ''}`})`,
        `COR: ${fmt.cor || f.cor || ''} | UF/EMISSÃO CRV: ${fmt.uf_emissao_crv || f.uf_emissao_crv || ''} - ${fmt.data_emissao_crv || f.data_emissao_crv || ''}`,
        `VALOR DA VENDA: ${fmt.valor_venda || f.valor_venda || ''} | DATA VENDA: ${fmt.data_venda || f.data_venda || ''} | LOCAL VENDA: ${fmt.local_venda || f.local_venda || ''}`,
        `HODÔMETRO: ${fmt.kilometragem_hodometro || f.kilometragem_hodometro || ''} km`,
        `--- VENDEDOR (TRANSMITENTE) ---`,
        `NOME VENDEDOR: ${fmt.nome_vendedor || f.nome_vendedor || ''}`,
        `CPF/CNPJ VENDEDOR: ${fmt.documento_vendedor_formatado || f.documento_vendedor || ''} | E-MAIL: ${fmt.email_vendedor || f.email_vendedor || ''} | MUNICÍPIO/UF: ${fmt.municipio_vendedor || f.municipio_vendedor || ''}/${fmt.uf_vendedor || f.uf_vendedor || ''}`,
        `--- COMPRADOR (ADQUIRENTE) ---`,
        `NOME COMPRADOR: ${fmt.nome_comprador || f.nome_comprador || ''}`,
        `CPF/CNPJ COMPRADOR: ${fmt.documento_comprador_formatado || f.documento_comprador || ''} | E-MAIL: ${fmt.email_comprador || f.email_comprador || ''} | MUNICÍPIO/UF: ${fmt.municipio_comprador || f.municipio_comprador || ''}/${fmt.uf_comprador || f.uf_comprador || ''}`,
      ];
      return lines.filter(Boolean).join('\n');
    } else if (data.document_type === 'cnh') {
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
    } else {
      const sourceFields = (fmt && Object.keys(fmt).length) ? fmt : f;
      const lines = [
        `=== DADOS OFICIAIS DO DOCUMENTO (${data.document_name || data.template_name || data.document_type || 'VIO'}) ===`,
        `AUTENTICIDADE SERPRO/VIO: ${data.is_authentic ? 'AUTÊNTICO / ASSINATURA VÁLIDA' : 'SEM ASSINATURA VIO / EXTERNO'}`,
      ];
      Object.entries(sourceFields).forEach(([k, v]) => {
        if (k === '_extras') return;
        if (v && String(v).trim()) {
          lines.push(`${humanizeFieldKey(k).toUpperCase()}: ${v}`);
        }
      });
      return lines.join('\n');
    }
  }
});
