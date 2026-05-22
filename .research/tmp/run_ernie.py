#!/usr/bin/env python3
"""Submit ERNIE-Image-Turbo workflow to local ComfyUI and retrieve result."""
import json
import time
import urllib.parse
import urllib.request
import uuid
import sys
from pathlib import Path

PROMPT = (
    "Basking in the ethereal glow of golden hour on a sun-drenched coastal terrace, "
    "a tall, statuesque young woman embodies sophisticated leisure. Her dark hair is "
    "sleek in a low ponytail with gentle tendrils, complementing her dewy skin and "
    "natural editorial makeup. She wears a flowing strapless midi dress in soft peach, "
    "featuring a twisted knot detail and a high side slit, showcasing her delicate, "
    "toned silhouette. With an elegant contrapposto stance, she leans casually against "
    "an ornate stone balustrade, holding a woven straw clutch, her gaze softly "
    "off-camera. The vast, calm azure ocean stretches to the horizon with scattered "
    "palms and distant sailboats. Cinematic 85mm photography with a wide aperture "
    "isolates her form, creating creamy bokeh. The warm, side-directional light "
    "sculpts her contours and the delicate chiffon folds. Centered composition with "
    "spacious editorial negative space, captured from a low angle with a slight "
    "upward tilt."
)

WORKFLOW = {
    "1": {"class_type": "UnetLoaderGGUF",
          "inputs": {"unet_name": "ernie-image-turbo-Q8_0.gguf"}},
    "2": {"class_type": "CLIPLoader",
          "inputs": {"clip_name": "ministral-3-3b.safetensors",
                     "type": "flux2", "device": "default"}},
    "3": {"class_type": "VAELoader",
          "inputs": {"vae_name": "flux2-vae.safetensors"}},
    "4": {"class_type": "CLIPTextEncode",
          "inputs": {"clip": ["2", 0], "text": PROMPT}},
    "5": {"class_type": "ConditioningZeroOut",
          "inputs": {"conditioning": ["4", 0]}},
    "6": {"class_type": "EmptyFlux2LatentImage",
          "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
    "7": {"class_type": "KSampler",
          "inputs": {"model": ["1", 0],
                     "positive": ["4", 0],
                     "negative": ["5", 0],
                     "latent_image": ["6", 0],
                     "seed": 42, "steps": 8, "cfg": 1.0,
                     "sampler_name": "euler", "scheduler": "simple",
                     "denoise": 1.0}},
    "8": {"class_type": "VAEDecode",
          "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
    "9": {"class_type": "SaveImage",
          "inputs": {"images": ["8", 0], "filename_prefix": "ernie-test"}},
}

BASE = "http://127.0.0.1:8188"
client_id = str(uuid.uuid4())

def post(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get(path):
    with urllib.request.urlopen(f"{BASE}{path}") as r:
        return json.loads(r.read())

def get_bytes(path):
    with urllib.request.urlopen(f"{BASE}{path}") as r:
        return r.read()

print(f"client_id = {client_id}", flush=True)
print(f"submitting workflow ({len(WORKFLOW)} nodes)...", flush=True)
resp = post("/prompt", {"prompt": WORKFLOW, "client_id": client_id})
prompt_id = resp.get("prompt_id")
print(f"prompt_id = {prompt_id}", flush=True)
if not prompt_id:
    print("FAILED: no prompt_id", resp)
    sys.exit(1)

start = time.time()
while True:
    h = get(f"/history/{prompt_id}")
    if prompt_id in h:
        entry = h[prompt_id]
        status = entry.get("status", {})
        outputs = entry.get("outputs", {})
        if status.get("completed"):
            print(f"completed in {time.time()-start:.1f}s", flush=True)
            print(f"outputs: {json.dumps(outputs, indent=2)[:600]}", flush=True)
            for nid, out in outputs.items():
                for img in out.get("images", []):
                    name = img["filename"]
                    sub = img.get("subfolder", "")
                    typ = img.get("type", "output")
                    qs = urllib.parse.urlencode({"filename": name, "subfolder": sub, "type": typ})
                    data = get_bytes(f"/view?{qs}")
                    out_path = Path("/workspace/.research/tmp") / name
                    out_path.write_bytes(data)
                    print(f"saved: {out_path} ({len(data)/1e6:.2f} MB)", flush=True)
            break
        if status.get("status_str") == "error":
            print(f"ERROR: {status}", flush=True)
            print(f"messages: {entry.get('status', {}).get('messages', [])}", flush=True)
            sys.exit(1)
    elapsed = time.time() - start
    print(f"  waiting... t={elapsed:.0f}s", flush=True)
    time.sleep(20 if elapsed < 60 else 60)
    if elapsed > 3600:
        print("TIMEOUT after 60 min")
        sys.exit(2)
