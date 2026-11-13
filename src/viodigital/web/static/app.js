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
  const cameraZoomSelect = document.getElementById('camera-zoom-select');
  const cameraStatusText = document.getElementById('camera-status-text');
  const btnMirrorCamera = document.getElementById('btn-mirror-camera');
  const btnTorchCamera = document.getElementById('btn-torch-camera');
  const cameraFocusDistanceWrap = document.getElementById('camera-focus-distance-wrap');
  const cameraFocusDistance = document.getElementById('camera-focus-distance');
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

  const engineBar = document.getElementById('engine-bar');
  const engineStatusText = document.getElementById('engine-status-text');
  const engineStatusStep = document.getElementById('engine-status-step');
  const engineProgressFill = document.getElementById('engine-progress-fill');
  const enginePercent = document.getElementById('engine-percent');
  const brandSecurityPill = document.getElementById('brand-security-pill');
  const engineReadyActions = document.getElementById('engine-ready-actions');
  const engineBarClose = document.getElementById('engine-bar-close');

  // Detecção de motor em cache na sessão
  const isWarmed = !!sessionStorage.getItem('viodigital_engine_warmed');
  if (isWarmed) {
    if (engineStatusStep) {
      engineStatusStep.textContent = '⚡ CACHE';
      engineStatusStep.style.display = 'inline-block';
      engineStatusStep.classList.add('step-cached');
    }
    if (engineStatusText) {
      engineStatusText.textContent = 'Restaurando motor criptográfico da memória local...';
    }
    if (engineProgressFill) {
      engineProgressFill.style.width = '30%';
    }
    if (enginePercent) {
      enginePercent.textContent = '30%';
    }
  }

  let currentResult = null;
  let mediaStream = null;
  let scanIntervalId = null;
  let isScanningFrame = false;
  let scanAttemptCount = 0;
  let isMirrored = localStorage.getItem('viodigital_camera_mirrored') === '1';
  let desiredCameraZoom = Math.max(1, parseFloat(localStorage.getItem('viodigital_camera_zoom') || '1') || 1);
  let activeDigitalZoom = 1;
  let isTorchOn = false;

  let scannerWorker = null;
  let isEngineReady = false;
  let workerFailed = false;

  function handleEngineReady() {
    isEngineReady = true;
    sessionStorage.setItem('viodigital_engine_warmed', String(Date.now()));
    if (engineBar) {
      engineBar.classList.add('ready');
    }
    if (brandSecurityPill) {
      brandSecurityPill.style.display = 'inline-flex';
    }
    if (engineReadyActions) {
      engineReadyActions.style.display = 'flex';
    }
    if (engineStatusText) {
      if (isWarmed) {
        engineStatusText.textContent = 'Motor restaurado da memória local · 100% offline (0 KB de rede)';
      } else {
        engineStatusText.textContent = 'Motor pronto · Validação criptográfica 100% no navegador';
      }
    }
    if (enginePercent) {
      enginePercent.textContent = '100%';
    }
    if (engineProgressFill) {
      engineProgressFill.style.width = '100%';
    }
  }

  if (engineBarClose && engineBar) {
    engineBarClose.addEventListener('click', () => {
      engineBar.style.display = 'none';
      sessionStorage.setItem('viodigital_engine_bar_dismissed', '1');
    });
  }

  if (sessionStorage.getItem('viodigital_engine_bar_dismissed') === '1' && engineBar && isWarmed) {
    engineBar.style.display = 'none';
    if (brandSecurityPill) {
      brandSecurityPill.style.display = 'inline-flex';
    }
  }

  function initScannerWorker() {
    try {
      const workerUrl = isWarmed ? '/static/scanner.worker.js?warmed=1' : '/static/scanner.worker.js';
      scannerWorker = new Worker(workerUrl);
      scannerWorker.onmessage = (e) => {
        const msg = e.data || {};
        if (msg.type === 'status') {
          if (engineStatusStep && msg.step) {
            engineStatusStep.textContent = msg.step;
            engineStatusStep.style.display = 'inline-block';
            if (isWarmed || msg.step.includes('CACHE')) {
              engineStatusStep.classList.add('step-cached');
            }
          }
          if (engineStatusText && msg.message) {
            engineStatusText.textContent = msg.message;
          }
          if (engineProgressFill && typeof msg.progress === 'number') {
            engineProgressFill.style.width = `${msg.progress}%`;
          }
          if (enginePercent && typeof msg.progress === 'number') {
            enginePercent.textContent = `${msg.progress}%`;
          }
          if (msg.status === 'ready') {
            handleEngineReady();
          }
        } else if (msg.type === 'ready') {
          handleEngineReady();
        } else if (msg.type === 'verify_result') {
          loadingState.style.display = 'none';
          const data = msg.data;
          if (!data || !data.is_parsed) {
            const errDetail =
              (data && data.message) ||
              (data && Array.isArray(data.errors) && data.errors.length
                ? data.errors.join(' | ')
                : 'Falha ao decodificar documento.');
            showError(errDetail);
            dropzone.style.display = 'flex';
            return;
          }
          currentResult = data;
          renderResult(data);
        } else if (msg.type === 'error' || msg.type === 'init_error') {
          console.warn('Motor offline alerta:', msg.error || msg.message);
          workerFailed = true;
          if (engineStatusText) {
            engineStatusText.textContent = 'Validação local pronta · Motor Python local';
          }
          if (engineStatusStep) {
            engineStatusStep.textContent = 'LOCAL';
            engineStatusStep.style.display = 'inline-block';
          }
        }
      };
      scannerWorker.onerror = (err) => {
        console.warn('Erro ao carregar worker local:', err);
        workerFailed = true;
        if (engineStatusText) {
          engineStatusText.textContent = 'Validação local pronta · Motor Python local';
        }
        if (engineStatusStep) {
          engineStatusStep.textContent = 'LOCAL';
          engineStatusStep.style.display = 'inline-block';
        }
      };
    } catch (err) {
      console.warn('Web Workers não disponíveis:', err);
    }
  }

  function checkBrowserCompatibility() {
    const hasWasm = typeof WebAssembly === 'object' && typeof WebAssembly.instantiate === 'function';
    const hasWorker = typeof Worker !== 'undefined';
    if (!hasWasm || !hasWorker) {
      const banner = document.createElement('div');
      banner.className = 'notary-disclaimer';
      banner.style.backgroundColor = 'var(--danger-bg)';
      banner.style.color = 'var(--danger-text)';
      banner.style.borderLeftColor = 'var(--detran-red)';
      banner.style.margin = '1rem 0';
      banner.innerHTML =
        '<strong>Aviso de Compatibilidade:</strong> Seu navegador não suporta WebAssembly ou Web Workers modernos. Atualize para uma versão recente para validar documentos 100% offline no navegador.';
      const main = document.querySelector('.main-content');
      if (main) main.insertBefore(banner, main.firstChild);
      return false;
    }
    return true;
  }

  checkBrowserCompatibility();
  initScannerWorker();

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      const hadController = !!navigator.serviceWorker.controller;
      let refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (!hadController || refreshing) return;
        refreshing = true;
        window.location.reload();
      });

      navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' }).then((reg) => {
        reg.update().catch(() => {});
      }).catch((err) => {
        console.warn('Registro do ServiceWorker:', err);
      });
    });
  }

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

  const modalAudit = document.getElementById('modal-audit');
  const btnOpenAuditModal = document.getElementById('btn-open-audit-modal');
  const btnCloseAuditModal = document.getElementById('btn-close-audit-modal');

  function openModal(modalEl) {
    if (modalEl) modalEl.style.display = 'flex';
  }
  function closeModal(modalEl) {
    if (modalEl) modalEl.style.display = 'none';
  }

  if (btnOpenAuditModal) {
    btnOpenAuditModal.addEventListener('click', () => openModal(modalAudit));
  }
  if (btnCloseAuditModal) {
    btnCloseAuditModal.addEventListener('click', () => closeModal(modalAudit));
  }
  if (modalAudit) {
    modalAudit.addEventListener('click', (e) => {
      if (e.target === modalAudit) closeModal(modalAudit);
    });
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
      if (modalAudit && modalAudit.style.display !== 'none') {
        closeModal(modalAudit);
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
    localStorage.setItem('viodigital_camera_mirrored', isMirrored ? '1' : '0');
    cameraVideo.classList.toggle('mirrored', isMirrored);
    applyCameraVideoTransform();
  });

  if (cameraZoomSelect) {
    cameraZoomSelect.addEventListener('change', () => {
      applyDesiredZoom(cameraZoomSelect.value);
    });
  }

  if (btnTorchCamera) {
    btnTorchCamera.addEventListener('click', async () => {
      const track = getActiveVideoTrack();
      if (!track) return;
      const nextTorch = !isTorchOn;
      const applied = await applyTrackConstraintSafely(track, { torch: nextTorch });
      if (applied) {
        isTorchOn = nextTorch;
        btnTorchCamera.classList.toggle('is-on', isTorchOn);
        btnTorchCamera.textContent = isTorchOn ? 'Luz: ON' : 'Luz';
      }
    });
  }

  if (cameraFocusDistance) {
    cameraFocusDistance.addEventListener('input', () => {
      const track = getActiveVideoTrack();
      if (!track) return;
      const val = Number(cameraFocusDistance.value);
      applyTrackConstraintSafely(track, { focusMode: 'manual', focusDistance: val });
    });
  }

  cameraSelect.addEventListener('change', () => {
    const deviceId = cameraSelect.value;
    if (deviceId) {
      localStorage.setItem('viodigital_camera_id', deviceId);
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
    applyCameraVideoTransform();

    const savedDeviceId = localStorage.getItem('viodigital_camera_id') || '';
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

  function getActiveVideoTrack() {
    if (!mediaStream || typeof mediaStream.getVideoTracks !== 'function') return null;
    const tracks = mediaStream.getVideoTracks();
    return tracks && tracks.length ? tracks[0] : null;
  }

  function applyCameraVideoTransform() {
    if (!cameraVideo) return;
    const parts = [];
    if (isMirrored) parts.push('scaleX(-1)');
    if (activeDigitalZoom > 1.02) parts.push(`scale(${activeDigitalZoom.toFixed(2)})`);
    cameraVideo.style.transform = parts.join(' ');
  }

  async function applyTrackConstraintSafely(track, constraintObj) {
    if (!track || typeof track.applyConstraints !== 'function') return false;
    try {
      await track.applyConstraints({ advanced: [constraintObj] });
      return true;
    } catch (_) {
      try {
        await track.applyConstraints(constraintObj);
        return true;
      } catch (_) {
        return false;
      }
    }
  }

  async function applyDesiredZoom(zoomValue) {
    desiredCameraZoom = Math.max(1, Math.min(3, Number(zoomValue) || 1));
    localStorage.setItem('viodigital_camera_zoom', String(desiredCameraZoom));
    if (cameraZoomSelect) {
      const targetStr = String(desiredCameraZoom);
      if ([...cameraZoomSelect.options].some(opt => opt.value === targetStr)) {
        cameraZoomSelect.value = targetStr;
      }
    }

    const track = getActiveVideoTrack();
    const caps = track && typeof track.getCapabilities === 'function' ? (track.getCapabilities() || {}) : {};
    let hwZoomApplied = 1;

    if (track && caps.zoom && typeof caps.zoom.max === 'number' && caps.zoom.max > 1) {
      const minZ = Math.max(1, caps.zoom.min || 1);
      const maxZ = caps.zoom.max;
      const targetHw = Math.min(maxZ, Math.max(minZ, desiredCameraZoom));
      const ok = await applyTrackConstraintSafely(track, { zoom: targetHw });
      if (ok) {
        hwZoomApplied = targetHw;
      }
    }

    activeDigitalZoom = desiredCameraZoom / hwZoomApplied;
    if (activeDigitalZoom < 1.02) activeDigitalZoom = 1;
    applyCameraVideoTransform();
  }

  async function initCameraHardwareControls() {
    isTorchOn = false;
    if (btnTorchCamera) {
      btnTorchCamera.hidden = true;
      btnTorchCamera.classList.remove('is-on');
      btnTorchCamera.textContent = 'Luz';
    }
    if (cameraFocusDistanceWrap) {
      cameraFocusDistanceWrap.hidden = true;
    }

    const track = getActiveVideoTrack();
    const caps = track && typeof track.getCapabilities === 'function' ? (track.getCapabilities() || {}) : {};
    const modes = Array.isArray(caps.focusMode) ? caps.focusMode : [];

    if (track && modes.includes('continuous')) {
      await applyTrackConstraintSafely(track, { focusMode: 'continuous' });
    } else if (track && modes.includes('single-shot')) {
      await applyTrackConstraintSafely(track, { focusMode: 'single-shot' });
    }

    if (track && caps.torch === true && btnTorchCamera) {
      btnTorchCamera.hidden = false;
    }

    if (
      track &&
      caps.focusDistance &&
      typeof caps.focusDistance.min === 'number' &&
      typeof caps.focusDistance.max === 'number' &&
      caps.focusDistance.max > caps.focusDistance.min &&
      modes.includes('manual') &&
      cameraFocusDistanceWrap &&
      cameraFocusDistance
    ) {
      const fd = caps.focusDistance;
      cameraFocusDistance.min = String(fd.min);
      cameraFocusDistance.max = String(fd.max);
      cameraFocusDistance.step = String(fd.step || ((fd.max - fd.min) / 25));
      const settings = typeof track.getSettings === 'function' ? (track.getSettings() || {}) : {};
      cameraFocusDistance.value = String(
        typeof settings.focusDistance === 'number' ? settings.focusDistance : (fd.min + fd.max) / 2
      );
      cameraFocusDistanceWrap.hidden = false;
    }

    await applyDesiredZoom(desiredCameraZoom);
  }

  function computeTargetCropRect(vw, vh, useCenterCrop) {
    const zoom = Math.max(1, activeDigitalZoom || 1);
    if (useCenterCrop) {
      const baseSide = Math.min(vw, vh) * 0.72;
      const side = Math.max(220, Math.min(Math.min(vw, vh), Math.floor(baseSide / zoom)));
      return {
        sx: Math.floor((vw - side) / 2),
        sy: Math.floor((vh - side) / 2),
        sw: side,
        sh: side,
      };
    }
    const cropW = Math.max(260, Math.min(vw, Math.floor(vw / zoom)));
    const cropH = Math.max(220, Math.min(vh, Math.floor(vh / zoom)));
    return {
      sx: Math.floor((vw - cropW) / 2),
      sy: Math.floor((vh - cropH) / 2),
      sw: cropW,
      sh: cropH,
    };
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

    await initCameraHardwareControls();

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
    isTorchOn = false;
    activeDigitalZoom = 1;
    if (btnTorchCamera) {
      btnTorchCamera.hidden = true;
      btnTorchCamera.classList.remove('is-on');
      btnTorchCamera.textContent = 'Luz';
    }
    if (cameraFocusDistanceWrap) {
      cameraFocusDistanceWrap.hidden = true;
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      mediaStream = null;
    }
    if (cameraVideo) {
      cameraVideo.srcObject = null;
      cameraVideo.style.transform = '';
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
      // Alterna entre recorte central de alta densidade (mira) e quadro completo (respeitando zoom ativo)
      const useCenterCrop = !isManual && (scanAttemptCount % 2 === 1);
      const { sx, sy, sw, sh } = computeTargetCropRect(vw, vh, useCenterCrop);
      captureCanvas.width = sw;
      captureCanvas.height = sh;
      captureCtx.drawImage(cameraVideo, sx, sy, sw, sh, 0, 0, sw, sh);

      if (scannerWorker) {
        const imgData = captureCtx.getImageData(0, 0, captureCanvas.width, captureCanvas.height);
        const reqId = Date.now() + Math.random();
        const pageRes = await new Promise((resolve) => {
          const handler = (e) => {
            const msg = e.data || {};
            if (msg.type === 'verify_imagedata_result' && msg.id === reqId) {
              scannerWorker.removeEventListener('message', handler);
              resolve(msg);
            }
          };
          scannerWorker.addEventListener('message', handler);
          scannerWorker.postMessage({
            type: 'verify_imagedata',
            id: reqId,
            imageData: imgData,
            pageIndex: 1,
            totalPages: 1,
            enhance: true,
          });
        });

        const data = pageRes.data;
        if (data && data.is_parsed) {
          cameraStage.classList.add('scan-success');
          playScanSuccessTone();
          stopCamera();
          currentResult = data;
          renderResult(data);
          showToast('Documento lido com sucesso pela câmera (offline)');
          return;
        }

        if (isManual) {
          cameraStatusText.textContent =
            (data && data.message) ||
            'Ainda não foi possível focar o QR Code. Aproxime ou incline levemente o documento para evitar reflexo.';
        }
        return;
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
  async function processPdfFile(file) {
    if (!window.pdfjsLib) {
      throw new Error('Biblioteca PDF.js não carregada.');
    }
    window.pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/vendor/pdfjs/pdf.worker.min.js';

    const loadingH3 = loadingState.querySelector('h3');
    const loadingP = loadingState.querySelector('p');
    if (loadingH3) loadingH3.textContent = 'Rasterizando PDF no navegador (offline)...';
    if (loadingP) loadingP.textContent = 'Processando páginas em alta resolução (300 DPI) para leitura do QR Code';

    const buffer = await file.arrayBuffer();
    const loadingTask = window.pdfjsLib.getDocument({ data: buffer });
    const pdfDoc = await loadingTask.promise;
    const numPages = pdfDoc.numPages;
    const maxPages = Math.min(numPages, 2);

    if (numPages > 2) {
      showToast(`Documento com ${numPages} páginas: analisando as 2 primeiras.`);
    }

    let lastResult = null;

    for (let p = 1; p <= maxPages; p++) {
      if (loadingP) {
        loadingP.textContent = `Analisando página ${p} de ${maxPages} em alta resolução...`;
      }

      const page = await pdfDoc.getPage(p);
      const viewport = page.getViewport({ scale: 3.5 });
      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = viewport.width;
      pageCanvas.height = viewport.height;
      const pageCtx = pageCanvas.getContext('2d');
      await page.render({ canvasContext: pageCtx, viewport: viewport }).promise;

      const imgData = pageCtx.getImageData(0, 0, viewport.width, viewport.height);

      const pageRes = await new Promise((resolve) => {
        const reqId = Date.now() + Math.random();
        const handler = (e) => {
          const msg = e.data || {};
          if (msg.type === 'verify_imagedata_result' && msg.id === reqId) {
            scannerWorker.removeEventListener('message', handler);
            resolve(msg);
          }
        };
        scannerWorker.addEventListener('message', handler);
        scannerWorker.postMessage({
          type: 'verify_imagedata',
          id: reqId,
          imageData: imgData,
          pageIndex: p,
          totalPages: numPages,
        });
      });

      lastResult = pageRes.data;

      // Se encontrou o QR oficial VIO na página, encerra e exibe com prioridade máxima
      if (pageRes.foundVio && lastResult && lastResult.is_parsed) {
        loadingState.style.display = 'none';
        currentResult = lastResult;
        renderResult(lastResult);
        return;
      }
    }

    loadingState.style.display = 'none';

    if (lastResult && lastResult.is_parsed) {
      currentResult = lastResult;
      renderResult(lastResult);
      return;
    }

    dropzone.style.display = 'flex';
    showError(
      numPages > 2
        ? `Nenhum QR Code oficial detectado nas primeiras 2 páginas (documento possui ${numPages} páginas).`
        : 'Nenhum QR Code foi detectado no arquivo PDF enviado.'
    );
  }

  async function processFile(file) {
    errorBanner.style.display = 'none';
    dropzone.style.display = 'none';
    cameraPanel.style.display = 'none';
    loadingState.style.display = 'flex';
    resultSection.style.display = 'none';

    const isImage = (file.type && file.type.startsWith('image/')) || /\.(png|jpe?g|webp|bmp)$/i.test(file.name || '');
    const isPdf = (file.type === 'application/pdf') || /\.pdf$/i.test(file.name || '');

    // Se for PDF e o motor local estiver disponível, rasteriza e valida localmente
    if (isPdf && scannerWorker && !workerFailed && window.pdfjsLib) {
      try {
        await processPdfFile(file);
      } catch (err) {
        loadingState.style.display = 'none';
        dropzone.style.display = 'flex';
        showError(`Erro ao processar PDF no navegador: ${err.message}`);
      }
      return;
    }

    // Se for imagem e o worker estiver disponível, processa 100% no navegador (sem tráfego de rede)
    if (isImage && scannerWorker && !workerFailed) {
      const loadingH3 = loadingState.querySelector('h3');
      const loadingP = loadingState.querySelector('p');
      if (loadingH3) loadingH3.textContent = 'Validando no seu navegador (offline)...';
      if (loadingP) loadingP.textContent = 'Decodificando envelope binário Serpro/VIO e checando assinatura digital localmente';

      scannerWorker.postMessage({
        type: 'verify_image',
        file: file,
        id: Date.now(),
      });
      return;
    }

    // Fallback: se o worker WebAssembly do navegador não estiver ativo/carregado,
    // valida via backend local (Python nativo) mantendo a premissa de processamento local
    try {
      const loadingH3 = loadingState.querySelector('h3');
      const loadingP = loadingState.querySelector('p');
      if (loadingH3) loadingH3.textContent = 'Validando no motor local...';
      if (loadingP) loadingP.textContent = 'Processando documento via servidor local Python';

      const formData = new FormData();
      formData.append('file', file);
      const resp = await fetch('/api/documents/verify', {
        method: 'POST',
        body: formData,
      });
      const data = await resp.json();
      loadingState.style.display = 'none';
      if (!resp.ok || !data.is_parsed) {
        showError(data.detail || data.message || (data.errors && data.errors.join(' | ')) || 'Erro ao validar documento.');
        dropzone.style.display = 'flex';
        return;
      }
      currentResult = data;
      renderResult(data);
      return;
    } catch (err) {
      loadingState.style.display = 'none';
      dropzone.style.display = 'flex';
      showError(`Erro na validação do documento: ${err.message}`);
      return;
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
      dni: 'DNI — Documento Nacional de Identidade (TSE)',
      rg: 'RG Digital (Gov.br / ICP-Brasil)',
      generic: 'Documento Oficial Serpro/VIO',
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
    } else if (data.document_type === 'cin') {
      renderCinLayout(data, documentContent);
    } else if (data.document_type === 'dni') {
      renderDniLayout(data, documentContent);
    } else if (data.document_type === 'rg') {
      renderRgLayout(data, documentContent);
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
      const photoShowcase = createPhotoShowcase(data.photo_b64, data.photo_format, 'Biometria CNH (Serpro)');
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

    if (data.photo_b64) {
      const photoShowcase = createPhotoShowcase(data.photo_b64, data.photo_format, 'Fotografia do Documento');
      container.appendChild(photoShowcase);
    }

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
      { label: 'Placa Anterior / UF', val: fmt.placa_anterior_uf || f.placa_anterior_uf },
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

    if (data.photo_b64) {
      const photoShowcase = createPhotoShowcase(data.photo_b64, data.photo_format, 'Fotografia do Documento');
      container.appendChild(photoShowcase);
    }

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
    dt_nascimento: 'Data de Nascimento',
    data_emissao: 'Data de Emissão',
    data_validade: 'Data de Validade',
    validade: 'Validade',
    filiacao_mae: 'Filiação (Mãe)',
    filiacao_pai: 'Filiação (Pai)',
    filiacao_1: 'Filiação 1',
    filiacao_2: 'Filiação 2',
    nome_mae: 'Nome da Mãe',
    nome_pai: 'Nome do Pai',
    naturalidade: 'Naturalidade',
    naturalidade_uf: 'UF de Naturalidade',
    uf_naturalidade: 'UF de Naturalidade',
    nacionalidade: 'Nacionalidade',
    orgao_expedidor: 'Órgão Expedidor',
    uf_rg: 'UF do RG',
    emissor_rg: 'Órgão Emissor do RG',
    uf: 'UF',
    municipio: 'Município',
    placa: 'Placa Mercosul / Veículo',
    placa_anterior_uf: 'Placa Anterior / UF',
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
    matricula_siape: 'Matrícula SIAPE',
    cargo: 'Cargo / Função',
    funcao: 'Função',
    lotacao: 'Lotação',
    conselho: 'Conselho / Órgão Emissor',
    titulo_profissional: 'Título Profissional',
    titulacao: 'Titulação',
    titulo_adicional: 'Título Adicional',
    tipo_sanguineo: 'Tipo Sanguíneo',
    tipo_sangue: 'Tipo Sanguíneo',
    fator_rh: 'Fator RH',
    data_admissao: 'Data de Admissão',
    local_expedicao: 'Local de Expedição',
    regime_juridico: 'Regime Jurídico',
    orgao_origem_nome: 'Órgão de Origem',
    orgao_origem_cnpj: 'CNPJ do Órgão de Origem',
    orgao_exercicio_nome: 'Órgão de Exercício',
    orgao_exercicio_cnpj: 'CNPJ do Órgão de Exercício',
    iss: 'Órgão Emissor',
    dvd: 'Data de Validade',
    dns: 'Data de Nascimento',
    uuid: 'Identificador Único (UUID)',
    url_validacao: 'URL de Validação',
    numero_icn: 'Número ICN (Identificação Civil Nacional)',
    matricula_nascimento: 'Matrícula da Certidão de Nascimento',
    certidao: 'Certidão',
    situacao_registro: 'Situação do Registro',
    data_ultima_atualizacao: 'Última Atualização',
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

  function renderCinLayout(data, container) {
    const fmt = data.formatted || {};
    const f = data.fields || {};

    const heroLayout = document.createElement('div');
    heroLayout.className = 'cnh-hero-layout';

    if (data.photo_b64) {
      const photoShowcase = createPhotoShowcase(data.photo_b64, data.photo_format, 'Identidade Nacional (MJSP)');
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
      { label: 'Nome do Titular', val: fmt.nome || f.nome || fmt.nome_completo || f.nome_completo, highlight: true, span: 'span-2' },
      { label: 'CPF (Número Único Nacional)', val: fmt.cpf_formatado || f.cpf, highlight: true },
      { label: 'Data de Nascimento', val: fmt.data_nascimento || f.data_nascimento || fmt.dns || f.dns },
      { label: 'Data de Validade', val: fmt.data_validade || f.data_validade || fmt.dvd || f.dvd },
      { label: 'Órgão Emissor / ISS', val: fmt.orgao_emissor || f.orgao_emissor || fmt.iss || f.iss },
      { label: 'UUID do Documento', val: fmt.uuid || f.uuid, span: 'span-2' },
    ].filter(c => c.val && String(c.val).trim());

    idCards.forEach(c => {
      idGrid.appendChild(createFieldCard(c.label, String(c.val), c.highlight, c.span));
    });
    idSection.appendChild(idGrid);
    heroLayout.appendChild(idSection);
    container.appendChild(heroLayout);

    // Outras claims / metadados Gov.br se existirem
    const extraClaims = [];
    const standardKeys = new Set(['cpf', 'cpf_formatado', 'data_nascimento', 'data_validade', 'orgao_emissor', 'uuid', 'url_validacao', 'nome', 'iss', 'dns', 'dvd']);
    Object.entries(fmt).forEach(([k, v]) => {
      if (!standardKeys.has(k) && v && String(v).trim()) {
        extraClaims.push({ label: humanizeFieldKey(k), val: String(v) });
      }
    });
    if (extraClaims.length > 0) {
      const extraSec = createDocSection('Claims e Metadados Adicionais (ICP-Brasil)');
      const extraGrid = document.createElement('div');
      extraGrid.className = 'fields-grid';
      extraClaims.forEach(c => {
        extraGrid.appendChild(createFieldCard(c.label, c.val, false));
      });
      extraSec.appendChild(extraGrid);
      container.appendChild(extraSec);
    }

    if (fmt.url_validacao || f.url_validacao) {
      const urlVal = fmt.url_validacao || f.url_validacao;
      const urlSec = createDocSection('Validação Oficial Gov.br');
      const urlGrid = document.createElement('div');
      urlGrid.className = 'fields-grid';
      urlGrid.appendChild(createFieldCard('URL de Validação', urlVal, false, 'full-width'));
      urlSec.appendChild(urlGrid);
      container.appendChild(urlSec);
    }

    const legalBox = document.createElement('div');
    legalBox.className = 'notary-disclaimer';
    legalBox.style.marginTop = '1rem';
    legalBox.innerHTML = `<strong>Validade Jurídica Nacional (Decreto nº 10.977/2022):</strong> A Carteira de Identidade Nacional (CIN) adota o CPF como número único de identificação nos bancos de dados públicos federais, estaduais e municipais, com fé pública e validade em todo o território nacional. Criptografia ES512 com chaves ICP-Brasil.`;
    container.appendChild(legalBox);
  }

  function renderDniLayout(data, container) {
    const fmt = data.formatted || {};
    const f = data.fields || {};

    const heroLayout = document.createElement('div');
    heroLayout.className = 'cnh-hero-layout';

    if (data.photo_b64) {
      const photoShowcase = createPhotoShowcase(data.photo_b64, data.photo_format, 'Biometria TSE');
      heroLayout.appendChild(photoShowcase);
    }

    const idSection = document.createElement('div');
    idSection.style.display = 'flex';
    idSection.style.flexDirection = 'column';
    idSection.style.gap = '0.75rem';
    idSection.style.flex = '1';

    const idGrid = document.createElement('div');
    idGrid.className = 'fields-grid';

    const natUf = [fmt.naturalidade || f.naturalidade, fmt.uf || f.uf].filter(Boolean).join(' - ');

    const idCards = [
      { label: 'Nome do Cidadão', val: fmt.nome || f.nome, highlight: true, span: 'span-2' },
      { label: 'CPF', val: fmt.cpf_formatado || f.cpf, highlight: true },
      { label: 'Número ICN (Identificação Civil Nacional)', val: fmt.numero_icn || f.numero_icn, highlight: true },
      { label: 'Data de Nascimento', val: fmt.data_nascimento || f.data_nascimento },
      { label: 'Naturalidade / UF', val: natUf },
      { label: 'Título de Eleitor', val: fmt.titulo_eleitor || f.titulo_eleitor },
      { label: 'Órgão Expedidor', val: fmt.orgao_expedidor || f.orgao_expedidor },
      { label: 'Data de Expedição', val: fmt.data_expedicao || f.data_expedicao },
      { label: 'Situação do Registro', val: fmt.situacao_registro || f.situacao_registro },
    ].filter(c => c.val && String(c.val).trim());

    idCards.forEach(c => {
      idGrid.appendChild(createFieldCard(c.label, String(c.val), c.highlight, c.span));
    });
    idSection.appendChild(idGrid);
    heroLayout.appendChild(idSection);
    container.appendChild(heroLayout);

    const filiacaoCards = [
      { label: 'Filiação (Mãe / Declarada 1)', val: fmt.filiacao_1 || f.filiacao_1, span: 'span-2' },
      { label: 'Filiação (Pai / Declarada 2)', val: fmt.filiacao_2 || f.filiacao_2, span: 'span-2' },
      { label: 'Matrícula da Certidão de Nascimento', val: fmt.matricula_nascimento || f.matricula_nascimento, span: 'span-2' },
    ].filter(c => c.val && String(c.val).trim());

    if (filiacaoCards.length > 0) {
      const filiacaoSection = createDocSection('Filiação Declarada e Registro Civil');
      const filGrid = document.createElement('div');
      filGrid.className = 'fields-grid';
      filiacaoCards.forEach(c => {
        filGrid.appendChild(createFieldCard(c.label, String(c.val), false, c.span));
      });
      filiacaoSection.appendChild(filGrid);
      container.appendChild(filiacaoSection);
    }

    const legalBox = document.createElement('div');
    legalBox.className = 'notary-disclaimer';
    legalBox.style.marginTop = '1rem';
    legalBox.innerHTML = `<strong>Documento Nacional de Identidade (Lei nº 13.444/2017):</strong> Baseado na Identificação Civil Nacional (ICN) gerida pela Justiça Eleitoral (TSE), com validação biométrica e assinatura digital oficial.`;
    container.appendChild(legalBox);
  }

  function renderRgLayout(data, container) {
    const fmt = data.formatted || {};
    const f = data.fields || {};

    const heroLayout = document.createElement('div');
    heroLayout.className = 'cnh-hero-layout';

    if (data.photo_b64) {
      const photoShowcase = createPhotoShowcase(data.photo_b64, data.photo_format, 'Biometria Civil');
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
      { label: 'Nome do Titular', val: fmt.nome || f.nome, highlight: true, span: 'span-2' },
      { label: 'Nome Social', val: fmt.nome_social || f.nome_social, span: 'span-2' },
      { label: 'CPF', val: fmt.cpf_formatado || f.cpf, highlight: true },
      { label: 'Sexo', val: fmt.sexo || f.sexo },
      { label: 'Data de Nascimento', val: fmt.data_nascimento || f.data_nascimento },
      { label: 'Nacionalidade / Naturalidade', val: [fmt.nacionalidade || f.nacionalidade, fmt.naturalidade || f.naturalidade].filter(Boolean).join(' / ') },
      { label: 'Data de Validade', val: fmt.data_validade || f.data_validade },
      { label: 'Órgão Expedidor / UF', val: `${fmt.orgao_expedidor || f.orgao_expedidor || ''} ${fmt.uf || f.uf || ''}`.trim() },
      { label: 'Data de Expedição', val: fmt.data_expedicao || f.data_expedicao },
    ].filter(c => c.val && String(c.val).trim());

    idCards.forEach(c => {
      idGrid.appendChild(createFieldCard(c.label, String(c.val), c.highlight, c.span));
    });
    idSection.appendChild(idGrid);
    heroLayout.appendChild(idSection);
    container.appendChild(heroLayout);

    const filiacaoCards = [
      { label: 'Filiação 1', val: fmt.filiacao_1 || f.filiacao_1, span: 'span-2' },
      { label: 'Filiação 2', val: fmt.filiacao_2 || f.filiacao_2, span: 'span-2' },
      { label: 'Certidão / Matrícula', val: fmt.certidao || f.certidao, span: 'span-2' },
    ].filter(c => c.val && String(c.val).trim());

    if (filiacaoCards.length > 0) {
      const filiacaoSection = createDocSection('Filiação Declarada e Registro Civil');
      const filGrid = document.createElement('div');
      filGrid.className = 'fields-grid';
      filiacaoCards.forEach(c => {
        filGrid.appendChild(createFieldCard(c.label, String(c.val), false, c.span));
      });
      filiacaoSection.appendChild(filGrid);
      container.appendChild(filiacaoSection);
    }
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
      const heroLayout = document.createElement('div');
      heroLayout.className = 'cnh-hero-layout';

      const photoShowcase = createPhotoShowcase(data.photo_b64, data.photo_format, data.document_name || 'Biometria Oficial');
      heroLayout.appendChild(photoShowcase);

      const fieldsCol = document.createElement('div');
      fieldsCol.className = 'cnh-fields-col';
      fieldsCol.style.flex = '1';
      fieldsCol.appendChild(section);

      heroLayout.appendChild(fieldsCol);
      container.appendChild(heroLayout);
    } else {
      container.appendChild(section);
    }
  }

  function createPhotoShowcase(photoB64, photoFormat, badgeText = 'Biometria Oficial') {
    const showcase = document.createElement('div');
    showcase.className = 'photo-showcase';

    const wrapper = document.createElement('div');
    wrapper.className = 'photo-wrapper';

    const fmtLower = String(photoFormat || '').toLowerCase();
    const isBpg = fmtLower === 'bpg' || photoB64.startsWith('data:image/bpg');

    if (isBpg) {
      if (typeof window.BPGDecoder !== 'undefined') {
        const canvas = document.createElement('canvas');
        canvas.id = 'photo-canvas';
        const rendered = decodeBPGToCanvas(photoB64, canvas);
        if (rendered) {
          wrapper.appendChild(canvas);
        } else {
          const placeholder = document.createElement('div');
          placeholder.className = 'photo-placeholder-error';
          placeholder.style.padding = '1rem';
          placeholder.style.color = 'var(--text-muted, #666)';
          placeholder.style.fontSize = '0.85rem';
          placeholder.style.textAlign = 'center';
          placeholder.textContent = 'Não foi possível renderizar a fotografia biométrica BPG';
          wrapper.appendChild(placeholder);
        }
      } else {
        const placeholder = document.createElement('div');
        placeholder.className = 'photo-placeholder-error';
        placeholder.style.padding = '1rem';
        placeholder.style.color = 'var(--text-muted, #666)';
        placeholder.style.fontSize = '0.85rem';
        placeholder.style.textAlign = 'center';
        placeholder.textContent = 'Decodificador BPG em carregamento...';
        wrapper.appendChild(placeholder);
      }
    } else {
      const img = document.createElement('img');
      img.src = photoB64;
      img.alt = badgeText || 'Fotografia Oficial';
      wrapper.appendChild(img);
    }

    showcase.appendChild(wrapper);

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
      if (typeof window.BPGDecoder === 'undefined') {
        return false;
      }
      const base64Data = base64Bpg.replace(/^data:image\/[a-z0-9_-]+;base64,/, '');
      const bin = atob(base64Data);
      const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) {
        u8[i] = bin.charCodeAt(i);
      }

      const ctx = canvas.getContext('2d');
      const dec = new window.BPGDecoder(ctx);

      // 1. Tenta decodificação direta via C API (idêntico ao bpg_converter.js)
      try {
        const img = dec.bpg_decoder_open();
        if (img) {
          const ret = dec.bpg_decoder_decode(img, u8, u8.length);
          if (ret >= 0) {
            const img_info_buf = dec.malloc(20);
            dec.bpg_decoder_get_info(img, img_info_buf);
            const heap8 = (window.Module && window.Module.HEAPU8) || dec.HEAPU8;
            const heap32 = (window.Module && window.Module.HEAPU32) || dec.HEAPU32;
            if (heap8 && heap32) {
              const w = heap32[img_info_buf >> 2];
              const h = heap32[(img_info_buf + 4) >> 2];
              if (w > 0 && h > 0) {
                const w4 = w * 4;
                const rgba_line = dec.malloc(w4);
                if (dec.bpg_decoder_start(img, 1) >= 0) {
                  canvas.width = w;
                  canvas.height = h;
                  const imgData = ctx.createImageData(w, h);
                  const dst = imgData.data;
                  let p0 = 0;
                  for (let y = 0; y < h; y++) {
                    dec.bpg_decoder_get_line(img, rgba_line);
                    for (let i = 0; i < w4; i++) {
                      dst[p0++] = heap8[rgba_line + i];
                    }
                  }
                  ctx.putImageData(imgData, 0, 0);
                  dec.free(rgba_line);
                  dec.free(img_info_buf);
                  dec.bpg_decoder_close(img);
                  return true;
                }
                dec.free(rgba_line);
              }
            }
            dec.free(img_info_buf);
          }
          dec.bpg_decoder_close(img);
        }
      } catch (directErr) {
        console.warn('Falha na decodificação direta BPG, tentando fallback _onload:', directErr);
      }

      // 2. Fallback via dec._onload
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
      }, 'image/png');
    } else if (img) {
      try {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = img.naturalWidth || img.width || 300;
        tempCanvas.height = img.naturalHeight || img.height || 400;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.drawImage(img, 0, 0, tempCanvas.width, tempCanvas.height);
        tempCanvas.toBlob(blob => {
          if (blob && navigator.clipboard && navigator.clipboard.write) {
            navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]).then(() => {
              showToast('Fotografia copiada para a área de transferência');
            }).catch(() => {
              showToast('Clique com o botão direito sobre a foto para copiar');
            });
          }
        }, 'image/png');
      } catch (err) {
        showToast('Clique com o botão direito sobre a foto para salvar');
      }
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
    } else if (data.document_type === 'cin') {
      const lines = [
        `=== DADOS DA CARTEIRA DE IDENTIDADE NACIONAL (CIN / ICP-BRASIL) ===`,
        `AUTENTICIDADE ICP-BRASIL: ${data.is_authentic ? 'AUTÊNTICO / ASSINATURA VÁLIDA' : 'NÃO CONFERE / INVÁLIDO'}`,
        `TITULAR: ${fmt.nome || f.nome || ''}`,
        `CPF: ${fmt.cpf_formatado || f.cpf || ''}`,
        `NASCIMENTO: ${fmt.data_nascimento || f.data_nascimento || ''}`,
        `VALIDADE: ${fmt.data_validade || f.data_validade || ''}`,
        `ÓRGÃO EMISSOR: ${fmt.orgao_emissor || f.orgao_emissor || fmt.iss || ''}`,
        `UUID: ${fmt.uuid || f.uuid || ''}`,
        `URL DE VALIDAÇÃO: ${fmt.url_validacao || f.url_validacao || ''}`,
      ];
      return lines.filter(Boolean).join('\n');
    } else if (data.document_type === 'dni') {
      const lines = [
        `=== DADOS DO DOCUMENTO NACIONAL DE IDENTIDADE (DNI / TSE) ===`,
        `AUTENTICIDADE TSE: ${data.is_authentic ? 'AUTÊNTICO / ASSINATURA VÁLIDA' : 'NÃO CONFERE / INVÁLIDO'}`,
        `CIDADÃO: ${fmt.nome || f.nome || ''}`,
        `CPF: ${fmt.cpf_formatado || f.cpf || ''}`,
        `ICN: ${fmt.numero_icn || f.numero_icn || ''}`,
        `NASCIMENTO: ${fmt.data_nascimento || f.data_nascimento || ''}`,
        `NATURALIDADE/UF: ${fmt.naturalidade || f.naturalidade || ''}/${fmt.uf || f.uf || ''}`,
        `TÍTULO DE ELEITOR: ${fmt.titulo_eleitor || f.titulo_eleitor || ''}`,
        `ÓRGÃO EXPEDIDOR: ${fmt.orgao_expedidor || f.orgao_expedidor || ''} | DATA: ${fmt.data_expedicao || f.data_expedicao || ''}`,
      ];
      if (fmt.filiacao_1 || f.filiacao_1) lines.push(`FILIAÇÃO 1: ${fmt.filiacao_1 || f.filiacao_1}`);
      if (fmt.filiacao_2 || f.filiacao_2) lines.push(`FILIAÇÃO 2: ${fmt.filiacao_2 || f.filiacao_2}`);
      return lines.filter(Boolean).join('\n');
    } else if (data.document_type === 'rg') {
      const lines = [
        `=== DADOS DO RG DIGITAL (GOV.BR / ICP-BRASIL) ===`,
        `AUTENTICIDADE: ${data.is_authentic ? 'AUTÊNTICO / ASSINATURA VÁLIDA' : 'NÃO CONFERE / INVÁLIDO'}`,
        `TITULAR: ${fmt.nome || f.nome || ''}`,
      ];
      if (fmt.nome_social || f.nome_social) lines.push(`NOME SOCIAL: ${fmt.nome_social || f.nome_social}`);
      lines.push(
        `CPF: ${fmt.cpf_formatado || f.cpf || ''}`,
        `NASCIMENTO: ${fmt.data_nascimento || f.data_nascimento || ''} | SEXO: ${fmt.sexo || f.sexo || ''}`,
        `NATURALIDADE: ${fmt.naturalidade || f.naturalidade || ''} - ${fmt.nacionalidade || f.nacionalidade || ''}`,
        `EXPEDIÇÃO: ${fmt.data_expedicao || f.data_expedicao || ''} (${fmt.orgao_expedidor || f.orgao_expedidor || ''} ${fmt.uf || f.uf || ''})`,
        `VALIDADE: ${fmt.data_validade || f.data_validade || ''}`
      );
      if (fmt.filiacao_1 || f.filiacao_1) lines.push(`FILIAÇÃO 1: ${fmt.filiacao_1 || f.filiacao_1}`);
      if (fmt.filiacao_2 || f.filiacao_2) lines.push(`FILIAÇÃO 2: ${fmt.filiacao_2 || f.filiacao_2}`);
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
