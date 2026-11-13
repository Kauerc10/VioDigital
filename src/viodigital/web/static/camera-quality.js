/**
 * camera-quality.js - Utilitários de qualidade de imagem para leitura de QR Code via webcam.
 *
 * Executa 100% localmente (zero rede) e é compartilhado entre:
 *  - a página (app.js): mede a nitidez de cada quadro, alimenta o medidor de foco
 *    e escolhe o quadro mais nítido de uma rajada;
 *  - o Web Worker (scanner.worker.js): realça quadros desfocados antes do ZXing.
 *
 * Todas as funções são puras: recebem pixels RGBA (Uint8ClampedArray) e não tocam no DOM.
 */
(function (root) {
  'use strict';

  /** Converte RGBA em luminância (BT.601 em aritmética inteira). */
  function toLuma(rgba, width, height) {
    const total = width * height;
    const luma = new Uint8ClampedArray(total);
    for (let i = 0, p = 0; i < total; i += 1, p += 4) {
      luma[i] = (rgba[p] * 77 + rgba[p + 1] * 150 + rgba[p + 2] * 29) >> 8;
    }
    return luma;
  }

  /**
   * Nitidez pela variância do Laplaciano (métrica clássica de foco).
   * Quanto maior, mais nítido. Valores são comparáveis entre quadros da mesma cena.
   */
  function sharpnessScore(rgba, width, height) {
    if (width < 3 || height < 3) return 0;
    const luma = toLuma(rgba, width, height);
    let sum = 0;
    let sumSq = 0;
    let count = 0;
    for (let y = 1; y < height - 1; y += 1) {
      const row = y * width;
      for (let x = 1; x < width - 1; x += 1) {
        const i = row + x;
        const lap = luma[i - width] + luma[i + width] + luma[i - 1] + luma[i + 1] - 4 * luma[i];
        sum += lap;
        sumSq += lap * lap;
        count += 1;
      }
    }
    const mean = sum / count;
    return sumSq / count - mean * mean;
  }

  /** Limites de contraste pelos percentis (ignora pixels extremos como reflexos e sombras). */
  function contrastBounds(luma, lowFraction, highFraction) {
    const hist = new Uint32Array(256);
    for (let i = 0; i < luma.length; i += 1) hist[luma[i]] += 1;

    const lowTarget = luma.length * lowFraction;
    const highTarget = luma.length * highFraction;
    let low = 0;
    let high = 255;
    let acc = 0;
    for (let v = 0; v < 256; v += 1) {
      acc += hist[v];
      if (acc >= lowTarget) {
        low = v;
        break;
      }
    }
    acc = 0;
    for (let v = 0; v < 256; v += 1) {
      acc += hist[v];
      if (acc >= highTarget) {
        high = v;
        break;
      }
    }
    return { low, high };
  }

  /** Desfoque de caixa 3x3 separável com bordas replicadas (soma bruta, sem divisão). */
  function boxBlurSum3x3(src, width, height) {
    const horizontal = new Uint16Array(src.length);
    for (let y = 0; y < height; y += 1) {
      const row = y * width;
      for (let x = 0; x < width; x += 1) {
        const left = x > 0 ? x - 1 : x;
        const right = x < width - 1 ? x + 1 : x;
        horizontal[row + x] = src[row + left] + src[row + x] + src[row + right];
      }
    }
    const blurred = new Uint16Array(src.length);
    for (let y = 0; y < height; y += 1) {
      const up = (y > 0 ? y - 1 : y) * width;
      const row = y * width;
      const down = (y < height - 1 ? y + 1 : y) * width;
      for (let x = 0; x < width; x += 1) {
        blurred[row + x] = horizontal[up + x] + horizontal[row + x] + horizontal[down + x];
      }
    }
    return blurred;
  }

  /**
   * Realce de quadro de webcam para QR Code:
   *  1. luminância;
   *  2. estiramento de contraste entre os percentis 1% e 99% (corrige imagem lavada e reflexo leve);
   *  3. máscara de nitidez (unsharp mask 3x3) que reforça as bordas dos módulos desfocados.
   * Retorna um novo buffer RGBA em tons de cinza com as mesmas dimensões.
   */
  function enhanceForQr(rgba, width, height, amount = 1.25) {
    const total = width * height;
    const luma = toLuma(rgba, width, height);

    // Imagens quase uniformes (sem QR na cena) não são esticadas para não amplificar ruído.
    const { low, high } = contrastBounds(luma, 0.01, 0.99);
    const range = high - low;
    const lut = new Uint8ClampedArray(256);
    for (let v = 0; v < 256; v += 1) {
      lut[v] = range < 16 ? v : ((v - low) * 255) / range;
    }
    const stretched = new Uint8ClampedArray(total);
    for (let i = 0; i < total; i += 1) stretched[i] = lut[luma[i]];

    const blurSum = boxBlurSum3x3(stretched, width, height);
    const out = new Uint8ClampedArray(total * 4);
    for (let i = 0, p = 0; i < total; i += 1, p += 4) {
      const value = stretched[i];
      const sharpened = value + amount * (value - blurSum[i] / 9);
      out[p] = sharpened;
      out[p + 1] = sharpened;
      out[p + 2] = sharpened;
      out[p + 3] = 255;
    }
    return out;
  }

  root.VioCameraQuality = Object.freeze({
    toLuma,
    sharpnessScore,
    enhanceForQr,
  });
})(typeof self !== 'undefined' ? self : globalThis);
