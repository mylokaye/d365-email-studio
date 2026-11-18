import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const input = process.argv[2];
const book = await SpreadsheetFile.importXlsx(await FileBlob.load(input));
book.recalculate();
console.log((await book.inspect({kind:'table',range:'Translations!A6:F12',include:'values,formulas',tableMaxRows:7,tableMaxCols:6,maxChars:3500})).ndjson);
const image = await book.render({sheetName:'Translations',range:'A1:F12',scale:1.5,format:'png'});
await fs.writeFile(new URL('./workbook-preview.png', import.meta.url), new Uint8Array(await image.arrayBuffer()));
