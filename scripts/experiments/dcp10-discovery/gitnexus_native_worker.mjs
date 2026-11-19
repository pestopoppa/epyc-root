import { readFileSync } from 'node:fs';
import ladybug from '/dcp10/ladybug/index.js';

const { query, seed_paths, max_edges, max_bytes, query_timeout_ms } = JSON.parse(readFileSync(0, 'utf8'));
// Database(path, bufferManagerSize, enableCompression, readOnly, maxDBSize, autoCheckpoint).
const database = new ladybug.Database('/dcp10/index/lbug', 256 * 1024 ** 2, false, true, 0, false);
const connection = new ladybug.Connection(database, 1);
let result;
const encoded = [];
let bytes = 3; // brackets and newline
try {
  connection.setQueryTimeout(query_timeout_ms);
  const statement = await connection.prepare(query);
  if (!statement.isSuccess()) throw new Error(statement.getErrorMessage());
  result = await connection.execute(statement, { seed_paths });
  if (Array.isArray(result) || result.getNumTuples() > max_edges) {
    throw new Error('GitNexus result set or edge count exceeded the capture bound');
  }
  while (result.hasNext()) {
    if (encoded.length >= max_edges) throw new Error('GitNexus edge count exceeded the capture bound');
    const row = await result.getNext();
    for (const field of ['source_id', 'source_path', 'target_id', 'target_path', 'relation']) {
      if (typeof row[field] !== 'string' || Buffer.byteLength(row[field]) > 4096) {
        throw new Error(`GitNexus edge text field is invalid: ${field}`);
      }
    }
    if (typeof row.confidence !== 'number' || !Number.isFinite(row.confidence)) {
      throw new Error('GitNexus confidence was not a finite stored number');
    }
    if (row.depth === 1n) row.depth = 1; // Ladybug may expose the INT64 literal as BigInt.
    const item = JSON.stringify(row);
    bytes += Buffer.byteLength(item) + (encoded.length ? 1 : 0);
    if (bytes > max_bytes) throw new Error('GitNexus output exceeded the capture byte bound');
    encoded.push(item);
  }
} finally {
  if (result && !Array.isArray(result)) result.close();
  await connection.close();
  await database.close();
}
process.stdout.write(`[${encoded.join(',')}]\n`);
