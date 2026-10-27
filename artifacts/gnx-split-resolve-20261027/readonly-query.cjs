'use strict';
// Reusable read-only constructor + filesystem policy, no installed-file edit.
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const crypto = require('node:crypto');
const vm = require('node:vm');
const {createRequire, syncBuiltinESMExports} = require('node:module');
const {pathToFileURL} = require('node:url');
const scripts = '/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase/tool';
const cap = scripts + '/gitnexus-lbug-cap.so';
const runtime = scripts + '/gitnexus-quarter-runtime.cjs';
const native = scripts + '/node_modules/@ladybugdb/core/lbugjs.node';
const cli = scripts + '/dist/cli/index.js';
const pins = {
  [cap]: 'c60e977f9e880f5f64e54c58fbf6a14171b0b408b1fd29601cfd8d4845273a35',
  [runtime]: '19a379dd26f0c112065e20976551348bbf6a9d7c8dbff1315a842ab1113cbe4d',
  [native]: '85b101251f07b052927443a994c69c23621f7c10159687145fa15b06decf7b49',
};
function installConstructors(lbug, expectedDB, runtimeBytes) {
  const BaseDatabase = lbug.Database;
  class Database extends BaseDatabase {
    constructor(databasePath, buffer, compression, _readonly, maximum,
                _checkpoint, ...rest) {
      if (fs.realpathSync(databasePath) !== fs.realpathSync(expectedDB)) {
        throw Error('query opened a foreign database');
      }
      super(databasePath, buffer, compression, true, maximum, false, ...rest);
    }
  }
  Object.defineProperty(lbug, 'Database', {value: Database, writable: true, configurable: true});
  const module = {exports: {}};
  vm.compileFunction(runtimeBytes.toString('utf8'), ['module'], {filename: runtime})(module);
  module.exports(lbug); // Unchanged adopted caps: DB bounds, Connection threads=1.
}
function denyMutations() {
  const denied = () => { throw Error('GNX_READONLY filesystem mutation refused'); };
  for (const name of ['appendFile','chmod','chown','copyFile','cp','link','mkdir','mkdtemp',
    'rename','rm','rmdir','symlink','truncate','unlink','utimes','writeFile','lchmod','lchown','lutimes','fchmod','fchown','futimes','fsync','fdatasync']) {
    for (const suffix of ['', 'Sync']) {
      if (typeof fs[name + suffix] === 'function') {
        Object.defineProperty(fs, name + suffix, {value: denied, writable: false, configurable: false});
      }
    }
    if (typeof fsp[name] === 'function') {
      Object.defineProperty(fsp, name, {value: async () => denied(), writable: false, configurable: false});
    }
  }
  for (const [object, key] of [[fs,'open'],[fs,'openSync'],[fsp,'open']]) {
    const original = object[key];
    Object.defineProperty(object, key, {writable: false, configurable: false,
      value: function(filename, flags, ...args) {
        if (flags !== 'r' && flags !== 'rs' && flags !== fs.constants.O_RDONLY) denied();
        return original.call(object, filename, flags, ...args);
      }});
  }
  const originalWrite = fs.writeSync;
  Object.defineProperty(fs, 'writeSync', {writable: false, configurable: false,
    value: function(fd, ...args) { if (fd !== 1 && fd !== 2) denied(); return originalWrite(fd, ...args); }});
  fs.write = fs.writev = fs.writevSync = fs.ftruncate = fs.ftruncateSync = fs.createWriteStream = denied;
  syncBuiltinESMExports();
}
async function main() {
  const [expectedDB, command, ...args] = process.argv.slice(2);
  if (!expectedDB || !['status','context','impact'].includes(command)) throw Error('read-query argv refused');
  if (process.env.GITNEXUS_HOME !== '/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase/stage1-state/registry' || process.env.HOME !== '/home/node') throw Error('private capsule catalog required');
  for (const [filename, digest] of Object.entries(pins)) {
    if (crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex') !== digest) throw Error('native/runtime source drift');
  }
  if (process.env.LD_PRELOAD !== cap || !fs.readFileSync('/proc/self/maps','utf8').split('\n').some(line=>line.endsWith(' '+cap))) throw Error('native cap is not mapped');
  const runtimeBytes = fs.readFileSync(runtime);
  delete process.env.LD_PRELOAD; // Git descendants do not inherit the native shim.
  denyMutations(); // Refuses JS WAL quarantine, recovery and registry/source edits.
  const lbug = createRequire(cli)('@ladybugdb/core');
  installConstructors(lbug, expectedDB, runtimeBytes);
  fs.writeSync(2, 'GNX_READONLY_READY native_mapped=true readOnly=true autoCheckpoint=false\n');
  process.argv = [process.execPath, cli, command, ...args];
  await import(pathToFileURL(cli).href); // Genuine installed CLI/LocalBackend output.
}
module.exports = {installConstructors, denyMutations};
if (require.main === module) main().catch(error => {console.error(error.stack); process.exitCode=64;});
