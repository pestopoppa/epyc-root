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
    # Split compound native calls so the emitted stage identifies the failed
    # operation. Keep the same short-circuit order and UNKNOWN exit semantics.
    replace('if(!llama_cafe4_target_configure(ctx.get(),mode)||!process(ctx.get(),spec.get(),prompt,0))return o;',
            'if(!llama_cafe4_target_configure(ctx.get(),0))return o;\n'
            ' if(!process(ctx.get(),spec.get(),prompt,0))return o;')
    # The intervention belongs to rollback, not prefill/proposal/verification.
    # Preserve independently produced proposals and all matched-control gates.
    replace('common_speculative_accept(spec.get(),0,(uint16_t)o.accepted);',
            'common_speculative_accept(spec.get(),0,(uint16_t)o.accepted);\n'
            ' if(!llama_cafe4_target_configure(ctx.get(),mode))return o;')
    replace('if(!llama_memory_seq_rm(llama_get_memory(ctx.get()),0,keep,-1)||!llama_memory_seq_rm(llama_get_memory(dft->context()),0,keep,-1))return o;',
            'if(!llama_memory_seq_rm(llama_get_memory(ctx.get()),0,keep,-1))return o;\n'
            ' if(!llama_memory_seq_rm(llama_get_memory(dft->context()),0,keep,-1))return o;')
    replace('if(!cafe4_mtp_draft(spec.get(),0,prompt.size(),boundary,prompt,width,o.draft)||o.draft.size()<2)return o;',
            'if(!cafe4_mtp_draft(spec.get(),0,prompt.size(),boundary,prompt,width,o.draft))return o;\n'
            ' if(o.draft.size()<2)return o;')
    # Witness the actual native tokens before the first rollback mutation.
    # Do not re-sample, add top() calls, or force a matched proposal: a
    # disagreement must retain its original strict-acceptance UNKNOWN.
    replace('int boundary=top(ctx.get(),v,-1);if(boundary<0)return o;',
            'int boundary=top(ctx.get(),v,-1);cafe4::boundary_witness(mode,width,boundary);if(boundary<0)return o;')
    replace(' if(o.draft.size()<2)return o;',
            ' cafe4::proposal_witness(mode,width,o.draft);\n'
            ' if(o.draft.size()<2)return o;')
    replace('int pred=top(ctx.get(),v,i);if(pred<0)return o;',
            'int pred=top(ctx.get(),v,i);cafe4::verification_witness(mode,width,i,o.draft[i],pred);if(pred<0)return o;')
    replace('if(!llama_cafe4_target_counts(ctx.get(),&selected,&faulted)||selected||faulted)return o;',
            'if(!llama_cafe4_target_counts(ctx.get(),&selected,&faulted))return o;\n'
            ' if(selected||faulted)return o;')
    replace('if(!decode(batched.get(),llama_tokens{o.sampled},keep)||!logits(batched.get(),n,o.batched))return o;',
            'if(!decode(batched.get(),llama_tokens{o.sampled},keep))return o;\n'
            ' if(!logits(batched.get(),n,o.batched))return o;')
    replace('if(!off.ok||!observe.ok||!fault.ok||off.prefix!=observe.prefix||off.prefix!=fault.prefix||off.draft!=observe.draft||off.draft!=fault.draft)',
            'if(!cafe4::matched_controls(off,observe,fault))')
    # Record actual hidden inputs and last draft output before target verify.
    # Getters synchronize native buffers; these diagnostics never choose tokens.
    replace('static Observation trial(',
            'static bool cafe4_provenance(llama_context *c,llama_model *m,int mode,int width,bool target,int row=0) {\n'
            ' if(target) {\n'
            '  if(!cafe4::float_witness(mode,width,"target-hidden",llama_get_embeddings_nextn_ith(c,row),llama_model_n_embd_out(m)))return false;\n'
            ' }\n'
            ' return cafe4::float_witness(mode,width,target?"target-logits":"draft-logits",llama_get_logits_ith(c,-1),llama_vocab_n_tokens(llama_model_get_vocab(m)));\n'
            '}\nstatic Observation trial(')
    replace('if(!cafe4_mtp_draft(',
            'if(!cafe4_provenance(ctx.get(),m,mode,width,true,(int)prompt.size()-1))return o;\n'
            ' if(!cafe4_mtp_draft(')
    replace(' cafe4::proposal_witness(mode,width,o.draft);',
            ' cafe4::proposal_witness(mode,width,o.draft);\n'
            ' if(!cafe4_provenance(dft->context(),m,mode,width,false))return o;')
    stages = (
        'target-context-or-capacity', 'draft-context', 'draft-target-alias',
        'speculative-init-or-embedding', 'target-configure', 'prompt-process',
        'boundary-logits', 'target-provenance', 'draft-proposal', 'draft-provenance',
        'draft-too-short', 'draft-rewind',
        'preverify-counts-read', 'preverify-counts-nonzero', 'verify-process',
        'verify-logits', 'strict-partial-acceptance', 'correction-logits',
        'rollback-configure', 'target-suffix-remove', 'draft-suffix-remove', 'correction-process',
        'postreplay-counts-read', 'target-mode-counts', 'replay-logits',
        'oracle-context', 'oracle-decode', 'oracle-logits', 'batched-context',
        'batched-prompt-decode', 'batched-prefix-decode',
        'batched-correction-decode', 'batched-logits',
    )
    start = source.index('static Observation trial(')
    end = source.index('static double error(', start)
    trial = source[start:end]
    # The final successful return is deliberately left unchanged. The pinned
    # blob, exact replacement anchors and count make stage drift fail closed.
    if trial.count('return o;') != len(stages) + 1:
        raise ValueError('trial failure-stage count changed')
    for stage in stages:
        trial = trial.replace('return o;',
                              f'return cafe4::trial_failure(o,mode,width,"{stage}");', 1)
    source = source[:start] + trial + source[end:]
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
