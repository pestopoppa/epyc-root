// Private index writer: no stock analyze, registry, AI files, FTS or embeddings.
import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
const { source, base } = JSON.parse(readFileSync(0, 'utf8'));
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
