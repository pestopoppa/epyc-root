"""Bind the fresh scorer testbed to its pinned base before patch application."""
import re


def verify_checkout(container, base_commit):
    if not re.fullmatch(r'[0-9a-f]{40}', base_commit or ''):
        raise ValueError('expected full case base commit')
    prefix = ['git', '-c', 'core.fileMode=false', '-C', '/testbed']

    def command(args):
        result = container.exec_run(prefix + args)
        if result.exit_code:
            raise RuntimeError('checkout guard refused: ' + repr(args) + ': ' + result.output.decode('utf-8', 'replace')[-1000:])
        return result.output

    def entries(revision):
        entries = {}
        for line in command(['ls-tree', '-r', '-z', '--full-tree', revision]).split(b'\0'):
            if not line:
                continue
            meta, path = line.split(b'\t', 1)
            mode, kind, oid = meta.split(b' ')
            if path in entries or not re.fullmatch(rb'[0-9a-f]{40}', oid):
                raise RuntimeError('invalid or duplicate tree entry')
            # SWE-bench's setup commit changes regular-file executable modes.
            # Retain symlink/submodule types exactly; only regular exec mode is ignored.
            normalized = b'100644' if mode in (b'100644', b'100755') else mode
            entries[path] = (normalized, kind, oid)
        if not entries:
            raise RuntimeError('empty tree')
        return entries

    head = command(['rev-parse', '--verify', 'HEAD^{commit}']).decode('ascii').strip()
    tree = command(['rev-parse', '--verify', base_commit + '^{tree}']).decode('ascii').strip()
    if not re.fullmatch(r'[0-9a-f]{40}', head) or not re.fullmatch(r'[0-9a-f]{40}', tree):
        raise RuntimeError('invalid checkout object identity')
    if entries('HEAD') != entries(base_commit):
        raise RuntimeError('image HEAD blob tree differs from pinned case base')
    command(['diff', '--cached', '--quiet', '--no-ext-diff', 'HEAD', '--'])
    command(['diff', '--quiet', '--no-ext-diff', '--'])
    if command(['ls-files', '--others', '--exclude-standard']).strip():
        raise RuntimeError('unexpected untracked testbed files')
    return {'base_commit': base_commit, 'base_tree': tree, 'image_head': head,
            'tracked_content_matches_base': True, 'untracked_nonignored': 0,
            'scope': 'blob trees and clean index/worktree; regular executable mode ignored; ignored image files bound by image digest'}

import subprocess,types,json
class LocalContainer:
 def exec_run(self,cmd):
  p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  return types.SimpleNamespace(exit_code=p.returncode,output=p.stdout)
print(json.dumps(verify_checkout(LocalContainer(),'d16bfe05a744909de4b27f5875fe0d4ed41ce607'),indent=2))
