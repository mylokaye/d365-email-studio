import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtemp, writeFile, rm, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

test('MCP-distributed artifacts include the plan format and run independently', async () => {
  execFileSync(process.execPath,['sync-content.mjs']);
  const {skill,validator} = await import('../src/content.js');
  const reference = await readFile('../d365-email-studio/references/edit-plan.md','utf8');
  assert.ok(skill.includes(reference));
  const dir = await mkdtemp(join(tmpdir(),'email-mcp-artifacts-'));
  try {
    await writeFile(join(dir,'validate_email.py'),validator);
    await writeFile(join(dir,'original.html'),'<html><body><p>Hello</p></body></html>');
    const inventory = JSON.parse(execFileSync('python3',['validate_email.py','original.html','--inventory'],{cwd:dir}));
    const field = inventory.fields.find(f=>f.before==='Hello');
    const plan = {version:1,source_sha256:inventory.source_sha256,mode:'translation',request:'Translate Hello to French',
      edits:[{id:field.id,before:'Hello',after:'Bonjour',reason:'Requested greeting translation'}]};
    await writeFile(join(dir,'edits.json'),JSON.stringify(plan));
    execFileSync('python3',['validate_email.py','original.html','--apply-plan','edits.json','--output','updated.html'],{cwd:dir});
    execFileSync('python3',['validate_email.py','original.html','updated.html','--plan','edits.json'],{cwd:dir});
    assert.equal(await readFile(join(dir,'updated.html'),'utf8'),'<html><body><p>Bonjour</p></body></html>');
  } finally { await rm(dir,{recursive:true,force:true}); }
});
