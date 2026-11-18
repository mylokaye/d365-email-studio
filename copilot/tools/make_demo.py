#!/usr/bin/env python3
"""Generate a fictional blank workbook, completed example and translated HTML."""
from pathlib import Path
import sys

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'copilot/email-translation-workbook/scripts'))
from html_blocks import EmailDocument
from translation_workbook import complete, new_directory, prepare

SOURCE = '''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><title>Example email</title></head>
<body><h1>Meet the new collection</h1><p>Hello {{FirstName}},</p>
<p>Explore equipment designed for everyday performance.</p>
<a href="https://example.com/collection#_msdynmkt_linkid=demo">Explore the collection</a>
<p>Thank you for choosing Example Company.</p></body></html>'''

TRANSLATIONS = {
    'Meet the new collection': ['Entdecken Sie die neue Kollektion', 'Découvrez la nouvelle collection'],
    'Hello': ['Hallo', 'Bonjour'],
    ',': [',', ','],
    'Explore equipment designed for everyday performance.': ['Entdecken Sie Geräte für zuverlässige Leistung im Alltag.', 'Découvrez des équipements conçus pour être performants au quotidien.'],
    'Explore the collection': ['Kollektion entdecken', 'Découvrir la collection'],
    'Thank you for choosing Example Company.': ['Vielen Dank, dass Sie sich für Example Company entschieden haben.', 'Merci d’avoir choisi Example Company.'],
}


def main():
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'outputs/copilot-workbook/example'
    with new_directory(destination) as folder:
        original = folder / 'example-original.html'
        original.write_bytes(SOURCE.encode('utf-8'))
        result = prepare(original, 'en-GB', ['de-DE', 'fr-FR'], folder / 'job')
        document = EmailDocument(SOURCE)
        book = load_workbook(folder / 'job/translations.xlsx')
        for row, block in enumerate(document.blocks, 7):
            for column, value in enumerate(TRANSLATIONS[block.source], 5):
                book['Translations'].cell(row, column, value)
        book.save(folder / 'example-completed.xlsx')
        book.close()
        report = complete(folder / 'job', folder / 'example-completed.xlsx', folder / 'translated')
        if not report['ok']:
            raise ValueError(report)
        print(f"Example: {result['blocks']} blocks x {result['languages']} languages = {result['translations_required']} translations")
    print(destination)


if __name__ == '__main__':
    main()
