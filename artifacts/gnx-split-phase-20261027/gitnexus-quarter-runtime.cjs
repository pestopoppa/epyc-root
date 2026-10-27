'use strict';

module.exports = function capDatabase(lbug) {
  // GitNexus's installed factory passes buffer=0, which chooses host memory.
  // Explicit bounds apply to every DB created through the cached CJS/ESM export.
  function bytes(name) {
    const value = process.env[name];
    if (!/^[1-9][0-9]*$/.test(value || '') || !Number.isSafeInteger(Number(value))) {
      throw new Error(`missing explicit database bound ${name}`);
    }
    return Number(value);
  }
  const bufferCap = bytes('GITNEXUS_LBUG_BUFFER_BYTES');
  const fileCap = bytes('GITNEXUS_LBUG_MAX_DB_SIZE');
  if (bufferCap > 512 * 1024 ** 2 || fileCap > 8 * 1024 ** 3 || bufferCap > fileCap) {
    throw new Error('database bounds exceed reviewed quarter budget');
  }
  function bounded(value, limit) {
    if (value === undefined || value === 0) return limit;
    if (!Number.isSafeInteger(value) || value < 1 || value > limit) {
      throw new Error('database request exceeds explicit quarter bound');
    }
    return value;
  }
  const BaseDatabase = lbug.Database;
  // The native Connection wrapper checks database.constructor.name exactly.
  class Database extends BaseDatabase {
    constructor(databasePath, buffer, compression = true, readOnly = false,
                maxDB, ...rest) {
      super(databasePath, bounded(buffer, bufferCap), compression, readOnly,
            bounded(maxDB, fileCap), ...rest);
    }
  }
  Object.defineProperty(lbug, 'Database', { value: Database, writable: false, configurable: false });
  const BaseConnection = lbug.Connection;
  // Async native init consumes _numThreads; sync init omits that setter.
  // Preserve the name: Ladybug QueryResult asserts constructor.name exactly.
  class Connection extends BaseConnection {
    constructor(database) { super(database, 1); }
    async init() {
      this._numThreads = 1;
      await super.init();
      this._connection.setMaxNumThreadForExec(1);
    }
    initSync() {
      super.initSync();
      this._connection.setMaxNumThreadForExec(1);
    }
    setMaxNumThreadForExec() { return super.setMaxNumThreadForExec(1); }
  }
  // ESM index.mjs delegates to this same cached CJS export. No disk patch.
  Object.defineProperty(lbug, 'Connection', { value: Connection, writable: false, configurable: false });
};
