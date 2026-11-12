/**
 * scanner.worker.js - Web Worker para decodificação óptica e validação criptográfica 100% no navegador.
 *
 * Arquitetura de Privacidade e Zero Network:
 * 1. ZXing C++ compilado para WebAssembly (zxing-wasm): decodifica o QR Code em nível de bits/bytes.
 * 2. Pyodide (Python 3.12 WebAssembly): executa o motor vioweb.core e a biblioteca cryptography.
 * 3. vioweb.core.checker.DigitalDocumentChecker + vioweb.core.presentation.present:
 *    valida assinatura digital e formata os dados diretamente na memória do navegador.
 *
 * Nenhum dado, documento, imagem ou QR Code é transmitido para servidores externos ou backend.
 */

/* global importScripts, ZXingWASM, loadPyodide */

self.pyodide = null;
self.zxingReady = false;
self.engineReady = false;
self.initPromise = null;

function postStatus(status, progress, message, step) {
  self.postMessage({ type: 'status', status, progress, message, step });
}

function resolveAssetUrl(relPath) {
  return new URL(relPath, self.location.href).href;
}

async function initEngine() {
  if (self.engineReady) return;
  if (self.initPromise) return self.initPromise;

  self.initPromise = (async () => {
    try {
      // 1. ZXing WASM
      postStatus('loading_zxing', 25, 'Decodificador óptico (WASM)...', '1/4');
      const zxingLocalJs = resolveAssetUrl('vendor/zxing/zxing_reader.js');
      const zxingLocalWasm = resolveAssetUrl('vendor/zxing/zxing_reader.wasm');

      let zxingLoaded = false;
      try {
        importScripts(zxingLocalJs);
        if (typeof ZXingWASM !== 'undefined') {
          ZXingWASM.setZXingModuleOverrides({
            locateFile: () => zxingLocalWasm,
          });
          await ZXingWASM.getZXingModule();
          zxingLoaded = true;
        }
      } catch (err) {
        console.warn('ZXing local indisponível, tentando fallback CDN:', err);
      }

      if (!zxingLoaded && typeof ZXingWASM === 'undefined') {
        const cdnJs = 'https://cdn.jsdelivr.net/npm/zxing-wasm@3.1.6/dist/iife/reader/index.js';
        const cdnWasm = 'https://cdn.jsdelivr.net/npm/zxing-wasm@3.1.6/dist/reader/zxing_reader.wasm';
        importScripts(cdnJs);
        ZXingWASM.setZXingModuleOverrides({
          locateFile: () => cdnWasm,
        });
        await ZXingWASM.getZXingModule();
      }
      self.zxingReady = true;

      // 2. Pyodide
      postStatus('loading_pyodide', 50, 'Ambiente Python WebAssembly...', '2/4');
      const pyodideLocalJs = resolveAssetUrl('vendor/pyodide/pyodide.js');
      const pyodideLocalIndex = resolveAssetUrl('vendor/pyodide/');

      let pyodideLoaded = false;
      try {
        importScripts(pyodideLocalJs);
        if (typeof loadPyodide !== 'undefined') {
          self.pyodide = await loadPyodide({ indexURL: pyodideLocalIndex });
          pyodideLoaded = true;
        }
      } catch (err) {
        console.warn('Pyodide local indisponível, tentando fallback CDN:', err);
      }

      if (!pyodideLoaded && typeof loadPyodide === 'undefined') {
        const cdnPyodideJs = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js';
        const cdnPyodideIndex = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/';
        importScripts(cdnPyodideJs);
        self.pyodide = await loadPyodide({ indexURL: cdnPyodideIndex });
      }

      // 3. Cryptography
      postStatus('loading_crypto', 75, 'Biblioteca de criptografia (ECDSA/RSA)...', '3/4');
      await self.pyodide.loadPackage('cryptography');

      // 4. VioWeb Wheel
      postStatus('loading_vioweb', 90, 'Motor VioWeb e base de 161 templates...', '4/4');
      const wheelUrl = resolveAssetUrl('wheels/vioweb-0.2.0-py3-none-any.whl');
      const wheelResp = await fetch(wheelUrl);
      if (!wheelResp.ok) {
        throw new Error(`Falha ao obter wheel do VioWeb (${wheelResp.status})`);
      }
      const wheelBuf = await wheelResp.arrayBuffer();
      self.pyodide.FS.writeFile('/tmp/vioweb.whl', new Uint8Array(wheelBuf));

      await self.pyodide.runPythonAsync(`
import sys
import zipfile
import json

# Extrai a wheel pura diretamente para site-packages do Pyodide
with zipfile.ZipFile('/tmp/vioweb.whl', 'r') as z:
    z.extractall('/lib/python3.12/site-packages')

import vioweb
from vioweb.core import DigitalDocumentChecker, present
from vioweb.core.formats.envelope import is_vio_or_cin_qr, looks_like_external_qr
from vioweb.core.exceptions import DigitalDocumentError, ParseError

_checker = DigitalDocumentChecker()

def _py_validate_bytes(raw_bytes_py):
    if hasattr(raw_bytes_py, "to_py"):
        raw_bytes = bytes(raw_bytes_py.to_py())
    elif isinstance(raw_bytes_py, (bytes, bytearray)):
        raw_bytes = bytes(raw_bytes_py)
    else:
        raw_bytes = bytes(raw_bytes_py)

    try:
        doc = _checker.parse_bytes(raw_bytes)
        res = present(doc)
    except Exception as exc:
        res = {
            "is_parsed": False,
            "is_authentic": False,
            "is_valid": False,
            "is_expired": False,
            "document_type": "unknown",
            "document_name": "Documento não reconhecido",
            "errors": [str(exc)],
            "warnings": [],
            "message": f"Falha na validação do documento: {exc}",
        }
    return json.dumps(res, ensure_ascii=False)

def _py_is_vio(raw_bytes_py):
    if hasattr(raw_bytes_py, "to_py"):
        raw_bytes = bytes(raw_bytes_py.to_py())
    elif isinstance(raw_bytes_py, (bytes, bytearray)):
        raw_bytes = bytes(raw_bytes_py)
    else:
        raw_bytes = bytes(raw_bytes_py)
    return is_vio_or_cin_qr(raw_bytes)
      `);

      self.engineReady = true;
      postStatus('ready', 100, 'Motor pronto · 100% offline no navegador', '✓');
      self.postMessage({ type: 'ready' });
    } catch (err) {
      console.error('Erro na inicialização do motor offline:', err);
      self.postMessage({ type: 'init_error', error: err.message || String(err) });
      throw err;
    }
  })();

  return self.initPromise;
}

// Inicia o carregamento imediatamente ao criar o worker
initEngine().catch(() => {});

// Leitura de códigos QR em imagem (ImageData / Bitmap)
async function decodeBarcodesFromImageData(imageData) {
  if (!self.zxingReady) {
    await initEngine();
  }
  return await ZXingWASM.readBarcodes(imageData, {
    formats: ['QRCode'],
    tryHarder: true,
    tryRotate: true,
    tryInvert: true,
    tryDownscale: true,
  });
}

// Processa arquivo de imagem
async function processImageFile(file) {
  await initEngine();

  const bitmap = await createImageBitmap(file);
  const w = bitmap.width;
  const h = bitmap.height;

  const canvas = new OffscreenCanvas(w, h);
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(bitmap, 0, 0);
  let imageData = ctx.getImageData(0, 0, w, h);

  let barcodes = await decodeBarcodesFromImageData(imageData);

  // Escalonamento de resolução progressivo se nada for encontrado (conforme vioweb.core.qr)
  if (barcodes.length === 0 && (w < 1600 || h < 1600)) {
    for (const scale of [2, 3]) {
      const upW = w * scale;
      const upH = h * scale;
      if (upW * upH > 25000000) break;
      const upCanvas = new OffscreenCanvas(upW, upH);
      const upCtx = upCanvas.getContext('2d', { willReadFrequently: true });
      upCtx.imageSmoothingEnabled = false;
      upCtx.drawImage(bitmap, 0, 0, upW, upH);
      const upData = upCtx.getImageData(0, 0, upW, upH);
      barcodes = await decodeBarcodesFromImageData(upData);
      if (barcodes.length > 0) break;
    }
  }

  if (barcodes.length === 0) {
    return {
      is_parsed: false,
      is_authentic: false,
      is_valid: false,
      is_expired: false,
      document_type: 'unknown',
      document_name: 'Nenhum QR Code detectado',
      errors: ['Nenhum QR Code foi detectado na imagem enviada.'],
      warnings: [],
      message: 'Nenhum QR Code foi detectado no arquivo enviado.',
    };
  }

  // Priorização Multi-QR: seleciona o QR oficial VIO/CIN se presente
  const pyIsVio = self.pyodide.globals.get('_py_is_vio');
  let selected = null;
  for (const b of barcodes) {
    if (b.bytes && b.bytes.length > 0) {
      const isVio = pyIsVio(b.bytes);
      if (isVio) {
        selected = b;
        break;
      }
    }
  }
  if (!selected) {
    selected = barcodes[0];
  }

  // Validação criptográfica no Pyodide
  const pyValidate = self.pyodide.globals.get('_py_validate_bytes');
  const resJson = pyValidate(selected.bytes);
  return JSON.parse(resJson);
}

// Processa bytes brutos de um QR Code
async function processRawBytes(rawBytes) {
  await initEngine();
  const pyValidate = self.pyodide.globals.get('_py_validate_bytes');
  const resJson = pyValidate(rawBytes);
  return JSON.parse(resJson);
}

// Processa ImageData (usado na rasterização de PDFs e quadros de câmera)
async function processImageData(imageData) {
  await initEngine();

  let barcodes = await decodeBarcodesFromImageData(imageData);

  if (barcodes.length === 0) {
    return {
      foundVio: false,
      result: {
        is_parsed: false,
        is_authentic: false,
        is_valid: false,
        is_expired: false,
        document_type: 'unknown',
        document_name: 'Nenhum QR Code detectado',
        errors: ['Nenhum QR Code foi detectado nesta página do documento.'],
        warnings: [],
        message: 'Nenhum QR Code foi detectado nesta página do documento.',
      },
    };
  }

  // Priorização Multi-QR: seleciona o QR oficial VIO/CIN se presente
  const pyIsVio = self.pyodide.globals.get('_py_is_vio');
  let selected = null;
  let isVioFound = false;

  for (const b of barcodes) {
    if (b.bytes && b.bytes.length > 0) {
      if (pyIsVio(b.bytes)) {
        selected = b;
        isVioFound = true;
        break;
      }
    }
  }

  if (!selected) {
    selected = barcodes[0];
  }

  const pyValidate = self.pyodide.globals.get('_py_validate_bytes');
  const resJson = pyValidate(selected.bytes);
  return {
    foundVio: isVioFound,
    result: JSON.parse(resJson),
  };
}

self.onmessage = async (e) => {
  const msg = e.data || {};
  const { type, id } = msg;

  if (type === 'init') {
    try {
      await initEngine();
      self.postMessage({ type: 'ready', id });
    } catch (err) {
      self.postMessage({ type: 'error', id, message: err.message });
    }
    return;
  }

  if (type === 'verify_image') {
    try {
      const result = await processImageFile(msg.file);
      self.postMessage({ type: 'verify_result', id, data: result });
    } catch (err) {
      console.error('Erro no processamento da imagem:', err);
      self.postMessage({
        type: 'verify_result',
        id,
        data: {
          is_parsed: false,
          is_authentic: false,
          is_valid: false,
          is_expired: false,
          document_type: 'unknown',
          document_name: 'Erro ao processar imagem',
          errors: [err.message || String(err)],
          warnings: [],
          message: `Erro ao processar imagem no navegador: ${err.message || err}`,
        },
      });
    }
    return;
  }

  if (type === 'verify_bytes') {
    try {
      const result = await processRawBytes(msg.bytes);
      self.postMessage({ type: 'verify_result', id, data: result });
    } catch (err) {
      self.postMessage({
        type: 'verify_result',
        id,
        data: {
          is_parsed: false,
          is_authentic: false,
          is_valid: false,
          is_expired: false,
          document_type: 'unknown',
          document_name: 'Erro ao processar dados',
          errors: [err.message || String(err)],
          warnings: [],
          message: `Erro ao processar dados no navegador: ${err.message || err}`,
        },
      });
    }
    return;
  }

  if (type === 'verify_imagedata') {
    try {
      const { foundVio, result } = await processImageData(msg.imageData);
      self.postMessage({
        type: 'verify_imagedata_result',
        id,
        pageIndex: msg.pageIndex,
        totalPages: msg.totalPages,
        foundVio,
        data: result,
      });
    } catch (err) {
      self.postMessage({
        type: 'verify_imagedata_result',
        id,
        pageIndex: msg.pageIndex,
        totalPages: msg.totalPages,
        foundVio: false,
        data: {
          is_parsed: false,
          is_authentic: false,
          is_valid: false,
          is_expired: false,
          document_type: 'unknown',
          document_name: 'Erro ao processar página',
          errors: [err.message || String(err)],
          warnings: [],
          message: `Erro ao processar página do documento: ${err.message || err}`,
        },
      });
    }
    return;
  }
};
