import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createHash,randomUUID} from 'node:crypto';
const root=fileURLToPath(new URL('../',import.meta.url));
const python='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const script='scripts/derive-strict-trends-without-channel14.py';
const hash=relative=>createHash('sha256').update(fs.readFileSync(path.join(root,relative))).digest('hex');
const protectedFiles=['scripts/derive-strict-trends-without-channel14-2026-10-09.py','data/strict-party-trends-without-channel14.json',
  ...fs.readdirSync(path.join(root,'artifacts/channel14-default-2026-10-09/strict-without14'))
    .filter(name=>fs.statSync(path.join(root,'artifacts/channel14-default-2026-10-09/strict-without14',name)).isFile())
    .map(name=>'artifacts/channel14-default-2026-10-09/strict-without14/'+name)];
const before=new Map(protectedFiles.map(relative=>[relative,hash(relative)]));
const command=(...args)=>spawnSync(python,['-X','utf8',script,...args],{cwd:root,encoding:'utf8'});

test('read-only preflight derives the current counts without computing or rewriting dated evidence',()=>{
  const run=command('--as-of','2026-10-09','--check');
  assert.equal(run.status,0,run.stderr);
  const result=JSON.parse(run.stdout);
  assert.equal(result.status,'PASS');assert.equal(result.readOnly,true);
  assert.equal(result.polls,32);assert.equal(result.series,7);assert.equal(result.deltas,25);
  assert.equal(result.partyTests,17);assert.equal(result.individualTests,119);assert.equal(result.signPatterns,128);
  assert.equal(result.exactPermutations,'7166361600000');
  assert.equal(result.channel14ExcludedPollCount,7);assert.equal(result.unverifiedExcludedPollCount,4);
  assert.ok(result.output.includes('/2026-10-09/'));
  if(!result.reusesExistingValidatedRun)assert.equal(fs.existsSync(path.join(root,result.output)),false);
});

test('the requested date must match all canonical reviewed dates before computation',()=>{
  const run=command('--as-of','2026-10-10','--check');
  assert.notEqual(run.status,0);assert.match(run.stderr,/must match the reviewed/);
  for(const date of ['2026-13-10','20261009','2026-10-9']){
    const invalid=command('--as-of',date,'--check');assert.notEqual(invalid.status,0);assert.match(invalid.stderr,/YYYY-MM-DD/);
  }
});

test('output paths and frozen evidence cannot be overridden, and unsafe run ids reject',()=>{
  for(const args of [
    ['--output-root','../outside-evidence'],
    ['--output-root','artifacts/channel14-default-2026-10-09/strict-without14'],
    ['--run-id','../overwrite'],
  ]){
    const run=command('--as-of','2026-10-09','--check',...args);
    assert.notEqual(run.status,0);assert.match(run.stderr,/inside this project|frozen 9 October|run-id/);
  }
});

test('an existing dated directory with changed source hashes is immutable',()=>{
  // Keep this tiny fixture as inspectable guard evidence; no recursive cleanup.
  const fixtureRoot='artifacts/regeneration-policy-tests-2026-10-09/'+randomUUID();
  const target=path.resolve(root,fixtureRoot,'2026-10-09','reviewed');
  assert.ok(target.startsWith(path.resolve(root,'artifacts')+path.sep));
  fs.mkdirSync(target,{recursive:true});
  const fixtureFile=path.join(target,'inputs-manifest.json');
  const fixtureBytes=JSON.stringify({schemaVersion:1,asOf:'2026-10-09',sourceHashes:{history:'changed'}},null,2)+'\n';
  fs.writeFileSync(fixtureFile,fixtureBytes);
  const run=command('--as-of','2026-10-09','--check','--output-root',fixtureRoot);
  assert.notEqual(run.status,0);assert.match(run.stderr,/source hashes differ; refusing to overwrite/);
  assert.equal(fs.readFileSync(fixtureFile,'utf8'),fixtureBytes);
  assert.deepEqual(fs.readdirSync(target),['inputs-manifest.json']);
});

test('an existing empty dated directory is a reserved run and must not be overwritten',()=>{
  const fixtureRoot='artifacts/regeneration-policy-tests-2026-10-09/'+randomUUID();
  const target=path.resolve(root,fixtureRoot,'2026-10-09','reviewed');
  assert.ok(target.startsWith(path.resolve(root,'artifacts')+path.sep));
  fs.mkdirSync(target,{recursive:true});
  const run=command('--as-of','2026-10-09','--check','--output-root',fixtureRoot);
  assert.notEqual(run.status,0);assert.match(run.stderr,/already exists or is empty; refusing to overwrite/);
  assert.deepEqual(fs.readdirSync(target),[]);
});

test('wrapper validation preserves the frozen script, current site snapshot and every 9 October audit output',()=>{
  for(const [relative,expected] of before)assert.equal(hash(relative),expected,relative);
});
