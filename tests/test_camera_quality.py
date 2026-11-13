from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from viodigital.api.app import app

client = TestClient(app)

CAMERA_QUALITY_JS = (
    Path(__file__).resolve().parent.parent / "src" / "viodigital" / "web" / "static" / "camera-quality.js"
)


def test_camera_focus_ui_and_worker_assets_served():
    root = client.get("/")
    assert root.status_code == 200
    html = root.text
    for expected_id in (
        'id="camera-zoom-select"',
        'id="btn-torch-camera"',
        'id="camera-focus-distance"',
    ):
        assert expected_id in html
    assert 'id="camera-focus-badge"' not in html
    assert 'id="btn-refocus-camera"' not in html
    assert 'id="camera-focus-ring"' not in html

    cq_res = client.get("/static/camera-quality.js")
    assert cq_res.status_code == 200
    assert "VioCameraQuality" in cq_res.text

    sw_res = client.get("/sw.js")
    assert sw_res.status_code == 200
    assert "/static/camera-quality.js" in sw_res.text


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js não encontrado no PATH")
def test_camera_quality_js_metrics_and_enhancement():
    script = f"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync({json.dumps(str(CAMERA_QUALITY_JS))}, 'utf8');
const g = {{}};
g.self = g;
g.window = g;
g.globalThis = g;
vm.runInNewContext(code, g);
const cq = g.VioCameraQuality;
if (!cq) throw new Error('VioCameraQuality missing');

const w = 32, h = 32;
const sharp = new Uint8ClampedArray(w * h * 4);
for (let y = 0; y < h; y++) {{
  for (let x = 0; x < w; x++) {{
    const v = (((x >> 2) ^ (y >> 2)) & 1) ? 240 : 20;
    const i = (y * w + x) * 4;
    sharp[i] = v; sharp[i + 1] = v; sharp[i + 2] = v; sharp[i + 3] = 255;
  }}
}}

const blurred = new Uint8ClampedArray(w * h * 4);
for (let y = 0; y < h; y++) {{
  for (let x = 0; x < w; x++) {{
    let sum = 0, c = 0;
    for (let dy = -2; dy <= 2; dy++) {{
      for (let dx = -2; dx <= 2; dx++) {{
        const xx = Math.min(w - 1, Math.max(0, x + dx));
        const yy = Math.min(h - 1, Math.max(0, y + dy));
        sum += sharp[(yy * w + xx) * 4];
        c++;
      }}
    }}
    const v = Math.round(sum / c);
    const i = (y * w + x) * 4;
    blurred[i] = v; blurred[i + 1] = v; blurred[i + 2] = v; blurred[i + 3] = 255;
  }}
}}

const washed = new Uint8ClampedArray(w * h * 4);
for (let y = 0; y < h; y++) {{
  for (let x = 0; x < w; x++) {{
    const v = (((x >> 2) ^ (y >> 2)) & 1) ? 150 : 110;
    const i = (y * w + x) * 4;
    washed[i] = v; washed[i + 1] = v; washed[i + 2] = v; washed[i + 3] = 255;
  }}
}}

const flat = new Uint8ClampedArray(w * h * 4);
for (let i = 0; i < flat.length; i += 4) {{
  flat[i] = 120; flat[i + 1] = 122; flat[i + 2] = 121; flat[i + 3] = 255;
}}

const sharpScore = cq.sharpnessScore(sharp, w, h);
const blurScore = cq.sharpnessScore(blurred, w, h);
const flatScore = cq.sharpnessScore(flat, w, h);
const enh = cq.enhanceForQr(washed, w, h, 1.25);
const enhFlat = cq.enhanceForQr(flat, w, h, 1.25);

let min = 255, max = 0;
for (let i = 0; i < enh.length; i += 4) {{
  if (enh[i] < min) min = enh[i];
  if (enh[i] > max) max = enh[i];
}}

let flatMin = 255, flatMax = 0;
for (let i = 0; i < enhFlat.length; i += 4) {{
  if (enhFlat[i] < flatMin) flatMin = enhFlat[i];
  if (enhFlat[i] > flatMax) flatMax = enhFlat[i];
}}

console.log(JSON.stringify({{
  sharpScore,
  blurScore,
  flatScore,
  min,
  max,
  alpha0: enh[3],
  flatMin,
  flatMax,
  tinyScore: cq.sharpnessScore(new Uint8ClampedArray(16), 2, 2),
}}));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    metrics = json.loads(proc.stdout.strip())
    assert metrics["sharpScore"] > metrics["blurScore"] * 5
    assert metrics["blurScore"] > metrics["flatScore"]
    assert metrics["flatScore"] < 5
    assert metrics["min"] <= 10
    assert metrics["max"] >= 245
    assert metrics["alpha0"] == 255
    assert 118 <= metrics["flatMin"] <= metrics["flatMax"] <= 124
    assert metrics["tinyScore"] == 0
