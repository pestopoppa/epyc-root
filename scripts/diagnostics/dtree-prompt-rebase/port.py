"""Source-bound DTREE winner prompt repair; produces a patch, never edits a tree."""
import argparse
import hashlib
from pathlib import Path
import difflib

COMMIT = '47f08e797c3dca352ebd6f7c5f80260d1e48aa90'
PATH = 'tools/server/server-context.cpp'
SOURCE_SHA256 = '71014850daf569637e012dd9d9a5b3b50994f44e996c2e00f98165a24767beb3'
OLD = '''                slot.spec_draft   = slot.spec_tree_alts[best];
                slot.spec_i_batch = slot.spec_tree_i_batch[best];'''
NEW = '''                // AK-DTREE: handle_last_sampled_token appended the MAIN draft to prompt.tokens.
                // verify_and_accept removes the WINNER's length. Replace the pending suffix now,
                // preserving the committed prefix and anchor even when the winner has another length.
                slot.prompt.tokens.keep_first(slot.prompt.n_tokens() - slot.spec_draft.size());
                slot.prompt.tokens.insert(slot.spec_tree_alts[best]);
                slot.spec_draft   = slot.spec_tree_alts[best];
                slot.spec_i_batch = slot.spec_tree_i_batch[best];'''


def repair(source):
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('source digest mismatch; requires ' + COMMIT + ':' + PATH)
    text = source.decode('utf-8')
    if text.count(OLD) != 1:
        raise ValueError('expected unique winner assignment')
    return text.replace(OLD, NEW).encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('patch', type=Path)
    args = parser.parse_args()
    original = args.source.read_bytes()
    fixed = repair(original)
    patch = ''.join(difflib.unified_diff(original.decode().splitlines(True),
                                       fixed.decode().splitlines(True),
                                       fromfile='a/' + PATH, tofile='b/' + PATH))
    with args.patch.open('x') as out:
        out.write(patch)


if __name__ == '__main__':
    main()
