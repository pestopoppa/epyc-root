// Private index writer: no stock analyze, registry, AI files, FTS or embeddings.
import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { registerHooks } from 'node:module';
import { createHash } from 'node:crypto';
const { source, base } = JSON.parse(readFileSync(0, 'utf8'));
// Exact source-derived variant: omit unused VECTOR installation and cap native
// memory/threads. Never modify the installed package or swallow diagnostics.
const adapterURL = pathToFileURL(`${source}/dist/core/lbug/lbug-adapter.js`).href;
registerHooks({ load(url, context, nextLoad) {
  const loaded = nextLoad(url, context);
  if (url !== adapterURL) return loaded;
  let text = Buffer.from(loaded.source).toString();
  if (createHash('sha256').update(text).digest('hex') !==
      '36466a35a6fc77fae9329de3506f14e49aa206d5343e08e79371707bb53ad7c2') {
    throw new Error('Adapter source drift');
  }
  for (const [before, after] of [
    ['await loadVectorExtension();', '/* direct-edge-only: no VECTOR */'],
    ['new lbug.Database(dbPath)', 'new lbug.Database(dbPath, 1073741824)'],
    ['new lbug.Connection(db)', 'new lbug.Connection(db, 4)'],
  ]) {
    if (text.split(before).length !== 2) throw new Error('Ambiguous adapter variant');
    text = text.replace(before, after);
  }
  return { ...loaded, source: text };
}});
const load = name => import(pathToFileURL(`${source}/${name}`).href);
const { runPipelineFromRepo } = await load('dist/core/ingestion/pipeline.js');
const { initLbug, loadGraphToLbug, getLbugStats, executeQuery, closeLbug } =
  await load('dist/core/lbug/lbug-adapter.js');
const result = await runPipelineFromRepo(base.root, () => {});
mkdirSync('/dcp10/output/index');
await initLbug('/dcp10/output/index/lbug');
let stats;
try {
  await loadGraphToLbug(result.graph, base.root, '/dcp10/output', () => {});
  stats = await getLbugStats();
  if (stats.nodes !== result.graph.nodeCount || stats.edges !== result.graph.relationshipCount) {
    throw new Error('Database counts differ from the parsed graph');
  }
  const embeddings = await executeQuery('MATCH (e:CodeEmbedding) RETURN count(e) AS cnt');
  if (Number(embeddings[0]?.cnt) !== 0) throw new Error('Unexpected embeddings');
  await executeQuery('CHECKPOINT');
} finally {
  await closeLbug();
}
rmSync('/dcp10/output/csv', { recursive: true, force: true });
writeFileSync('/dcp10/output/index/meta.json', JSON.stringify({
  repoPath: base.root, lastCommit: base.base_commit,
  stats: { files: result.totalFileCount, ...stats, embeddings: 0 }
}) + '\n', { flag: 'wx' });
