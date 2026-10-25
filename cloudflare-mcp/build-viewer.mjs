import { build } from 'esbuild';
import { readFile, writeFile } from 'node:fs/promises';

const result = await build({
  entryPoints: ['src/viewer.js'],
  bundle: true,
  minify: true,
  format: 'iife',
  platform: 'browser',
  write: false,
});
const template = await readFile('src/viewer.html', 'utf8');
const script = result.outputFiles[0].text.replaceAll('</script', '<\\/script');
const html = template.replace('<!-- VIEWER_SCRIPT -->', () => `<script>${script}</script>`);
await writeFile('src/viewer-content.js', `export const viewerHtml = ${JSON.stringify(html)};\n`);
