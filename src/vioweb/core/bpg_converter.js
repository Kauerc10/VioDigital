// src/vioweb/core/bpg_converter.js
// Converte imagens BPG para buffer RGBA puro via bpgdec8.js (Emscripten / libbpg)
const fs = require('fs');
const path = require('path');

process.argv[1] = process.argv[1] || 'bpg';
global.window = global;

const bpgdecPath = path.resolve(__dirname, '..', 'web', 'static', 'bpgdec8.js');
require(bpgdecPath);

try {
  const inputBuffer = fs.readFileSync(0);
  if (!inputBuffer || inputBuffer.length === 0) {
    process.exit(1);
  }
  const u8 = new Uint8Array(inputBuffer);

  const dec = new global.BPGDecoder(null);
  const img = dec.bpg_decoder_open();
  if (dec.bpg_decoder_decode(img, u8, u8.length) < 0) {
    process.exit(2);
  }

  const img_info_buf = dec.malloc(20);
  dec.bpg_decoder_get_info(img, img_info_buf);
  const heap8 = global.Module["HEAPU8"];
  const heap32 = global.Module["HEAPU32"];
  const w = heap32[img_info_buf >> 2];
  const h = heap32[(img_info_buf + 4) >> 2];

  const w4 = w * 4;
  const rgba_line = dec.malloc(w4);
  if (dec.bpg_decoder_start(img, 1) < 0) {
    dec.free(img_info_buf);
    dec.bpg_decoder_close(img);
    process.exit(3);
  }

  const header = Buffer.alloc(8);
  header.writeUInt32BE(w, 0);
  header.writeUInt32BE(h, 4);
  process.stdout.write(header);

  for (let y = 0; y < h; y++) {
    dec.bpg_decoder_get_line(img, rgba_line);
    const lineBuf = Buffer.from(heap8.buffer, heap8.byteOffset + rgba_line, w4);
    process.stdout.write(lineBuf);
  }

  dec.free(rgba_line);
  dec.free(img_info_buf);
  dec.bpg_decoder_close(img);
} catch (err) {
  process.exit(4);
}
