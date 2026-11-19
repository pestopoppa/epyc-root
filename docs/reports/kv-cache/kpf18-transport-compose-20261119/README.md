# KPF-18 composed bounded transport

The disabled transport successor composes the previously qualified SeedControl
failure-cleanup patch with all three bounded `/slots` calls. Composition exposed
the same cleanup defect in the slots helper: response close failure skipped
connection close, and cleanup could replace the original typed STOP. The new
source-bound patch attempts both closes and preserves the original exception,
recording secondary cleanup failure as an exception note. Cleanup failure on an
otherwise successful request still refuses the request.

The installer verifies the base, six dependencies, both existing patches and the
new slots patch, plus both final module digests. It writes only the two changed
modules and a disabled entry, sealing inherited dependencies by reference rather
than copying the predecessor tree. It refuses an existing destination or one
outside `/mnt/raid0/llm/tmp/kvu`. A failed installation leaves an INCOMPLETE marker;
the entry always returns 78 regardless. This is a transport overlay, not a fully
integrated native driver or an authorized execution entry.

Installed overlay: `/mnt/raid0/llm/tmp/kvu/transport-successor-20261119`.
`inputs.json` pins the final modules; the generated `manifest.json` pins input
and output bytes, including the installed entry. The predecessor is unchanged.
Recreate in a fresh scratch destination:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B \
  docs/reports/kv-cache/kpf18-transport-compose-20261119/install.py \
  /mnt/raid0/llm/tmp/kvu/transport-successor-fresh
```

26 model-free tests passed (1.743 seconds): eight full installed SeedControl
consumer cases with synthetic slots/SSE/native peers; eleven inherited bounded
HTTP cases using real loopback sockets, including stalled headers/body, trickle,
STOP, payload validation and deadline handling; seven cleanup/installation
controls. The full-consumer cases substitute slot observations; the HTTP cases
execute the real bounded transport through SeedControl's initial slot query.
These are complementary controls, not a full real-network native lifecycle test.
No model or benchmark ran.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-transport-compose-20261119 \
  -p test_composed.py -v
```

Actual native cancellation/release, owned server/descendant drain, full driver
integration and scheduled GPU qualification remain required. No row was
published and no layout verdict or production behavior changed. KPF-18.0d
remains open. GitNexus has no indexed repository for this lane; graph blast radius
is unknown. Changes are confined to this isolated report/patch/test package.
