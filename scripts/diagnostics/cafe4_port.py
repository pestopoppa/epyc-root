#!/usr/bin/env python3
"""Materialize the modes port from a pinned repository blob into scratch.

No model load, compilation, or benchmark is performed here. Historical evidence
stays immutable; row builders compile the generated source with the experimental
CAFE4 target snapshot patch and the two headers on their include path.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess

BASE_BLOB = '53035f75429327e82454f7d26f7dd67f65c80c16'
ROOT = Path(__file__).resolve().parents[2]


def materialize(source):
    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError(f'expected exactly one port anchor: {old!r}')
        source = source.replace(old, new)

    replace('#include "mtp_draft_bridge.hpp"',
            '#include "mtp_draft_bridge.hpp"\n#include "cafe4_modes.hpp"')
    replace('const llama_tokens&prompt,int mode)',
            'const llama_tokens&prompt,int mode,int width)')
    replace('cp.n_rs_seq=8;', 'cp.n_rs_seq=std::max(8,width+1);')
    replace('llama_n_rs_seq(ctx.get())<8',
            'llama_n_rs_seq(ctx.get())<cp.n_rs_seq')
    replace('params.speculative.draft.n_max=3;',
            'params.speculative.draft.n_max=width;')
    replace('boundary,prompt,3,o.draft)', 'boundary,prompt,width,o.draft)')
    replace('if(argc!=2||!argv[1][0]){std::fprintf(stderr,"usage: %s model.gguf\\n",argv[0]);return 2;}',
            'cafe4::Options options; if(!cafe4::parse(argc,argv,options)){'
            'std::fprintf(stderr,"usage: %s model.gguf [-ngl N] [--verify-batch d (2..63)] [--fault-injection]\\n",argv[0]);return 2;}')
    replace('mp.n_gpu_layers=0;', 'mp.n_gpu_layers=options.gpu_layers;')
    replace('llama_model_load_from_file(argv[1],mp)',
            'llama_model_load_from_file(options.model.c_str(),mp)')
    replace('trial(model.get(),prompt,0),observe=trial(model.get(),prompt,1),fault=trial(model.get(),prompt,2)',
            'trial(model.get(),prompt,0,options.width),observe=trial(model.get(),prompt,1,options.width),fault=trial(model.get(),prompt,2,options.width)')
    # The last token is a separate post-rollback decode in the subject. Keep
    # that boundary in the cold batched reference too: fusing it with the
    # accepted prefix introduces another batch-shape numerical difference.
    replace('llama_tokens kept(o.prefix.begin()+prompt.size(),o.prefix.end());\n'
            ' if(!decode(batched.get(),kept,prompt.size())||!logits(batched.get(),n,o.batched))return o;',
            'llama_tokens kept(o.prefix.begin()+prompt.size(),o.prefix.end()-1);\n'
            ' if(!decode(batched.get(),kept,prompt.size()))return o;\n'
            ' if(!decode(batched.get(),llama_tokens{o.sampled},keep)||!logits(batched.get(),n,o.batched))return o;')
    # Freeze the already-used width2 gate, rather than recalibrating it using
    # the corrected reference. The measured reference floor stays diagnostic.
    replace('tol=base+1e-5,', 'tol=0.743863867,')
    replace(' std::printf("CAFE4_MTP_ROLLBACK width=',
            ' std::printf("CAFE4_REFERENCE floor=%.9g tolerance=%.9g\\n",base,tol);\n'
            ' std::printf("CAFE4_MTP_ROLLBACK width=')
    replace('std::printf("RESULT PASS nonfault rollback agrees; target snapshot fault demonstrably diverges\\n");model.reset();llama_backend_free();return 0;',
            'const int rc=cafe4::finish(true,true,options.fault_injection);'
            'std::printf("RESULT %s nonfault rollback agrees; target snapshot fault demonstrably diverges\\n",rc==1?"FAIL injected-fault":"PASS");'
            'model.reset();llama_backend_free();return rc;')
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        parser.error('generated source belongs in scratch, outside the lane')
    source = subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', 'blob', BASE_BLOB], text=True)
    generated = materialize(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        stream.write(generated)
    print(f'base_blob={BASE_BLOB} generated_sha256={hashlib.sha256(generated.encode()).hexdigest()}')


if __name__ == '__main__':
    main()
