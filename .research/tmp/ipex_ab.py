#!/usr/bin/env python3
"""IPEX A/B harness against ERNIE-Image-Turbo on the sidecar (port 8189).

Builds two workflows — baseline and IPEX-injected — and submits one of
them. Run twice with --variant baseline / --variant ipex. Same prompt,
same seed, same dimensions, same steps. Reports server-side
"Prompt executed in N seconds".
"""
import argparse, json, time, urllib.request, uuid, sys

PROMPT = "a fluffy red panda eating bamboo, watercolor"
SEED = 42
WIDTH = 512
HEIGHT = 512
STEPS = 4
BASE = "http://127.0.0.1:8189"


def base_workflow():
    return {
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
              "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1}},
        "7": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0],
                         "positive": ["4", 0],
                         "negative": ["5", 0],
                         "latent_image": ["6", 0],
                         "seed": SEED, "steps": STEPS, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple",
                         "denoise": 1.0}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": "ipex-ab"}},
    }


def ipex_workflow():
    wf = base_workflow()
    # Insert IPEX node between loader (1) and sampler (7).
    wf["10"] = {"class_type": "ApplyIpexOptimize",
                "inputs": {"model": ["1", 0]}}
    wf["7"]["inputs"]["model"] = ["10", 0]
    return wf


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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variant", choices=["baseline", "ipex"], required=True)
    args = p.parse_args()

    wf = ipex_workflow() if args.variant == "ipex" else base_workflow()
    client_id = str(uuid.uuid4())
    print(f"variant={args.variant}, nodes={len(wf)}, client_id={client_id}", flush=True)
    submitted = time.monotonic()
    resp = post("/prompt", {"prompt": wf, "client_id": client_id})
    prompt_id = resp.get("prompt_id")
    print(f"prompt_id={prompt_id}", flush=True)

    while True:
        time.sleep(5)
        h = get(f"/history/{prompt_id}")
        if prompt_id in h:
            entry = h[prompt_id]
            status = entry.get("status", {})
            if status.get("completed"):
                wall = time.monotonic() - submitted
                print(f"WALL_CLOCK_SEC={wall:.2f}", flush=True)
                outs = entry.get("outputs", {})
                for nid, out in outs.items():
                    for img in out.get("images", []):
                        print(f"image: {img}", flush=True)
                return 0
            if status.get("status_str") == "error":
                print(f"ERROR: {status}", flush=True)
                return 1


if __name__ == "__main__":
    raise SystemExit(main())
