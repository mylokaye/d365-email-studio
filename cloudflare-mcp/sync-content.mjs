import { readFile, writeFile } from 'node:fs/promises';
const skill = await readFile(new URL('../d365-email-studio/SKILL.md', import.meta.url), 'utf8');
const validator = await readFile(new URL('../d365-email-studio/scripts/validate_email.py', import.meta.url), 'utf8');
await writeFile(new URL('src/content.js', import.meta.url), `// Generated from the repository skill; run node sync-content.mjs to refresh.\nexport const skill = ${JSON.stringify(skill)};\nexport const validator = ${JSON.stringify(validator)};\n`);
