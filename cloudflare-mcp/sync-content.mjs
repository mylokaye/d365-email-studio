import { readFile, writeFile } from 'node:fs/promises';
const instructions = await readFile(new URL('../d365-email-studio/SKILL.md', import.meta.url), 'utf8');
const editPlan = await readFile(new URL('../d365-email-studio/references/edit-plan.md', import.meta.url), 'utf8');
const skill = `${instructions}\n\nThe referenced edit-plan document is included below in full; no separate filesystem lookup is needed.\n\n${editPlan}`;
const validator = await readFile(new URL('../d365-email-studio/scripts/validate_email.py', import.meta.url), 'utf8');
await writeFile(new URL('src/content.js', import.meta.url), `// Generated from the repository skill; run node sync-content.mjs to refresh.\nexport const skill = ${JSON.stringify(skill)};\nexport const validator = ${JSON.stringify(validator)};\n`);
