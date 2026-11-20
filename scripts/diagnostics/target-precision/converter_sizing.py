"""Content-bound v10/Qwen3.8 text conversion storage audit; no weight access."""
import hashlib
import json
import math
from pathlib import Path
import re

from plan_weights import GIB, _require, tensor_storage_plan

REVISION = '37561816e66b5b9153b1b64c10968c18c1e6f4a0'
CONVERTER = 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
# Audited source contents, not a directory/version-string freshness assumption.
AUDITED_FILES = {
    'convert_hf_to_gguf.py': '8f1bed9466221e57e434caa7ee720abe1569deb6bc2fe5a65da950ea66c8e737',
    'conversion/__init__.py': 'b323927760f90d1bee8ed06b1165df12f28510b8241318bd08c7d46be8516951',
    'conversion/base.py': 'b54106d70b21ff6af4d8fcc68bc98a59b436ac5933d2c552e9eea55c32e48db9',
    'conversion/qwen.py': '7da4c1dca81de0e5e05abf6bb31055d3cffa8be16415980b23c4f6a53d0ab28f',
    'ggml/src/ggml-common.h': '3e7a03c2deb30a27c04aaad631ccd38a7c0403b923fdda3dc34356673f1a7a5f',
    'src/llama-quant.cpp': '94f80fa5b8734b6d6228e039ec21a06159350ea7bce176722014b3212e693180',
    'gguf-py/gguf/gguf_writer.py': 'b959644737bec534cbe563bac9473af01d6d16255d701cf347da0ff021ff6eb5',
}


def bind_source(source_root):
    root = Path(source_root)
    for name, digest in AUDITED_FILES.items():
        _require(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest,
                 'audited source content mismatch: ' + name)
    return dict(AUDITED_FILES)


# Shape-preserving paths only. Fused QKVZ/expert paths are deliberately refused.
MATRICES = {
    'mlp.down_proj.weight': (5120, 17408),
    'mlp.gate_proj.weight': (17408, 5120),
    'mlp.up_proj.weight': (17408, 5120),
    'self_attn.k_proj.weight': (1024, 5120),
    'self_attn.v_proj.weight': (1024, 5120),
    'self_attn.q_proj.weight': (12288, 5120),
    'self_attn.o_proj.weight': (5120, 6144),
    'linear_attn.in_proj_a.weight': (48, 5120),
    'linear_attn.in_proj_b.weight': (48, 5120),
    'linear_attn.in_proj_qkv.weight': (10240, 5120),
    'linear_attn.in_proj_z.weight': (6144, 5120),
    'linear_attn.out_proj.weight': (5120, 6144),
}
F32 = {
    'input_layernorm.weight': (5120,),
    'post_attention_layernorm.weight': (5120,),
    'self_attn.k_norm.weight': (256,),
    'self_attn.q_norm.weight': (256,),
    'linear_attn.norm.weight': (128,),
    'linear_attn.A_log': (48,),
    'linear_attn.dt_bias': (48,),
    'linear_attn.conv1d.weight': (10240, 1, 4),
}


def tensor_caps(name, shape):
    """Return payload caps, retaining default MTP and excluding vision tensors.

    Quantized matrices use a Q8_0 ceiling for BOTH Q8_0 and mixed Q4_K_M:
    Q4/Q5/Q6 and their 32-column fallbacks fit below 34 bytes per 32 values.
    Unusual rows conservatively reserve F16. This is not an exact Q4 recipe.
    """
    shape = tuple(shape)
    if name.startswith('model.visual.'):
        return None
    norm = name.replace('model.language_model.', 'model.')
    special = {
        'model.embed_tokens.weight': (248320, 5120),
        'lm_head.weight': (248320, 5120),
        'model.norm.weight': (5120,),
        'mtp.fc.weight': (5120, 10240),
        'mtp.norm.weight': (5120,),
        'mtp.pre_fc_norm_embedding.weight': (5120,),
        'mtp.pre_fc_norm_hidden.weight': (5120,),
    }
    if norm in special:
        _require(shape == special[norm], 'unaudited tensor shape: ' + name)
        f32 = len(shape) == 1
    else:
        match = re.fullmatch(r'(model|mtp)\.layers\.(\d+)\.(.+)', norm)
        _require(match is not None, 'unaudited tensor: ' + name)
        family, layer, suffix = match.groups()
        _require(int(layer) < (64 if family == 'model' else 1), 'unaudited layer')
        expected = {**MATRICES, **F32}.get(suffix)
        _require(expected is not None and shape == expected, 'unaudited tensor shape: ' + name)
        f32 = suffix in F32
    elements = math.prod(shape)
    bf16 = elements * (4 if f32 else 2)
    quant = (bf16 if f32 else
             elements // 32 * 34 if shape[-1] % 32 == 0 else elements * 2)
    return {'elements': elements, 'BF16': bf16, 'Q8_0': quant, 'Q4_K_M': quant,
            'f32': f32}


def converter_storage_plan(plan, index_bytes, headers, config_bytes, source_root, available_bytes):
    """Refuse unreviewed source/config, then derive serial default-command caps.

    The metadata reserve is an enforced proposed cap, not a size proven by source.
    No executor is supplied here and a fitting budget never admits execution.
    """
    _require(plan['base'] == {'repo': 'Qwen/Qwen3.8-27B', 'revision': REVISION}
             and plan['converter_commit'] == CONVERTER, 'unaudited source revision')
    expected_steps = [
        ['python3', 'convert_hf_to_gguf.py', 'source', '--outtype', 'bf16', '--outfile', 'target-BF16.gguf'],
        ['llama-quantize', 'target-BF16.gguf', 'target-Q8_0.gguf', 'Q8_0'],
        ['llama-quantize', 'target-BF16.gguf', 'target-Q4_K_M.gguf', 'Q4_K_M'],
    ]
    _require(plan['steps'] == expected_steps, 'unaudited command policy')
    source = bind_source(source_root)
    sized = tensor_storage_plan(plan, index_bytes, headers, available_bytes)
    cfg_source = next(s for s in plan['sources'] if s['path'] == 'config.json')
    blob = hashlib.sha1(b'blob ' + str(len(config_bytes)).encode() + b'\0' + config_bytes).hexdigest()
    _require(blob == cfg_source.get('git_blob_sha1') and len(config_bytes) == cfg_source['size'],
             'config identity mismatch')
    cfg = json.loads(config_bytes)
    _require(cfg.get('architectures') == ['Qwen3_5ForConditionalGeneration']
             and cfg.get('tie_word_embeddings') is False
             and cfg.get('text_config', {}).get('tie_word_embeddings') is False
             and cfg['text_config'].get('mtp_num_hidden_layers') == 1
             and not cfg.get('quantization_config') and not cfg['text_config'].get('quantization_config'),
             'unaudited conversion configuration')
    arms = {q: 0 for q in ('BF16', 'Q8_0', 'Q4_K_M')}
    retained = dropped = max_elements = retained_elements = f32_elements = 0
    for raw in headers.values():
        for name, tensor in json.loads(raw[8:]).items():
            if name == '__metadata__':
                continue
            _require(tensor['dtype'] == 'BF16', 'unaudited source dtype')
            caps = tensor_caps(name, tensor['shape'])
            if caps is None:
                dropped += 1
                continue
            retained += 1
            retained_elements += caps['elements']
            f32_elements += caps['elements'] if caps['f32'] else 0
            max_elements = max(max_elements, caps['elements'])
            for arm in arms:
                arms[arm] += caps[arm]
    reserve = GIB + retained * 32
    outputs = {arm: payload + reserve for arm, payload in arms.items()}
    # Default lazy conversion writes directly: no --use-temp-file spool, no
    # split, no eager materialization, no projector, no expert fusion/overrides.
    peak = plan['storage']['source_bytes'] + sum(outputs.values())
    floor = sized['disk_floor_bytes']
    return dict(schema='epyc.target-precision.converter-sizing.v1',
                base=plan['base'], converter_commit=CONVERTER, audited_source_sha256=source,
                config_git_blob_sha1=blob, headers=sized['headers'], steps=plan['steps'],
                retained_tensor_count=retained, dropped_vision_tensor_count=dropped,
                retained_elements=retained_elements, retained_f32_elements=f32_elements,
                payload_cap_bytes=arms, metadata_alignment_reserve_per_arm_bytes=reserve,
                output_cap_bytes=outputs, source_bytes=plan['storage']['source_bytes'],
                peak_additional_bytes=peak, disk_floor_bytes=floor,
                required_free_bytes=floor + peak, available_bytes=available_bytes,
                disk_envelope_fits=available_bytes >= floor + peak,
                workspace=dict(extra_disk_bytes=0, largest_retained_tensor_elements=max_elements,
                               quantizer_two_buffer_logical_bytes=8 * max_elements,
                               quantizer_reallocation_logical_bytes=12 * max_elements,
                               converter_total_rss_bound_bytes=None, quantizer_total_rss_bound_bytes=None),
                execution_admitted=False,
                limitations=['headers/config are metadata, not verified weight payloads',
                             'Q4_K_M cap uses Q8 ceiling, not exact mixed-type recipe',
                             'reserve must be enforced; metadata/tokenizer size not proven',
                             'workspace logical sizes exclude vector spare capacity, allocator/interpreter/thread stacks and mapped/page-cache residency',
                             'no total RAM admission; measure or enforce process memory separately',
                             'default serial commands only; temp/eager/split/overrides require a new audit',
                             'bind tool builds, verify tensor/tokenizer/drafter correspondence and recheck floors'])
