"""Observable round-trip and rejection invariants for the Copilot file workflow."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'copilot/email-translation-workbook/scripts'))
from html_blocks import EmailDocument, language_selection
from translation_workbook import complete, prepare
from openpyxl import load_workbook

spec = importlib.util.spec_from_file_location('package_copilot_skill', ROOT / 'scripts/package_copilot_skill.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)

SOURCE = '\ufeff' + '''<!doctype html>
<html lang="en-GB"><head><title>Protected title</title><style>.x{color:red}</style></head>
<body><h1>Welcome &amp; hello</h1><p>Hello {{Name}}, welcome&nbsp;back.</p>
<p>Explore <strong>our equipment</strong> today.</p><p>Keep [[VALUE]] and ${TOKEN}.</p>
<a href="https://example.com/preferences#_msdynmkt_linkid=xyz" data-id="fixed">Preferences</a>
<img src="https://example.com/image.png" alt="Product image" data-image-file-id="fixed">
<div class="buttonWrapper">
<!--[if mso]><v:roundrect href="https://example.com/info" data-msdyn-tracking-id="button1"><center>Find out more</center></v:roundrect><![endif]-->
<a href="https://example.com/info" data-msdyn-tracking-id="button1">Find out more</a>
</div><p>Repeated</p><p>Repeated</p></body></html>'''.replace('\n', '\r\n')


class RoundTripTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.original = self.folder / 'input.html'
        self.original.write_bytes(SOURCE.encode('utf-8'))
        self.job = self.folder / 'job'
        self.document = EmailDocument(SOURCE)

    def prepare(self, **kwargs):
        return prepare(self.original, 'en-GB', ['de-DE', 'fr-FR'], self.job, **kwargs)

    def filled(self):
        book = load_workbook(self.job / 'translations.xlsx')
        for row, block in enumerate(self.document.blocks, 7):
            for column in [5, 6]:
                cell = book['Translations'].cell(row, column, block.source)
                cell.data_type = 's'
        return book

    def save_and_complete(self, book, output=True):
        path = self.folder / 'returned.xlsx'
        book.save(path)
        book.close()
        return complete(self.job, path, self.folder / 'completed' if output else None)

    def test_no_change_roundtrip_preserves_every_byte_and_entity(self):
        self.prepare(update_lang=False)
        report = self.save_and_complete(self.filled())
        self.assertTrue(report['ok'])
        for target in ['de-DE', 'fr-FR']:
            self.assertEqual((self.folder / f'completed/email-{target}.html').read_bytes(), self.original.read_bytes())

    def test_translated_outputs_patch_only_known_text_and_language(self):
        self.prepare()
        book = self.filled()
        for row, block in enumerate(self.document.blocks, 7):
            if block.source == 'Welcome & hello':
                book['Translations'].cell(row, 5, 'Willkommen & hallo')
                book['Translations'].cell(row, 6, 'Bienvenue & bonjour')
            if block.source == 'Find out more':
                book['Translations'].cell(row, 5, 'Mehr erfahren')
                book['Translations'].cell(row, 6, 'En savoir plus')
        report = self.save_and_complete(book)
        self.assertTrue(report['ok'])
        german = (self.folder / 'completed/email-de-DE.html').read_bytes().decode('utf-8')
        expected = SOURCE.replace('lang="en-GB"', 'lang="de-DE"').replace('Welcome &amp; hello', 'Willkommen &amp; hallo').replace('Find out more', 'Mehr erfahren')
        self.assertEqual(german, expected)
        with ZipFile(self.folder / 'completed/translated-emails.zip') as archive:
            self.assertEqual(archive.read('email-de-DE.html'), german.encode('utf-8'))
            self.assertEqual(set(archive.namelist()), {'email-de-DE.html', 'email-fr-FR.html'})

    def test_outlook_duplicates_share_one_workbook_row(self):
        blocks = [b for b in self.document.blocks if b.source == 'Find out more']
        self.assertEqual(len(blocks), 1)
        self.assertEqual(len(blocks[0].ranges), 2)

    def test_identical_wording_elsewhere_remains_independent(self):
        blocks = [b for b in self.document.blocks if b.source == 'Repeated']
        self.assertEqual(len(blocks), 2)
        values = {b.id: b.source for b in self.document.blocks}
        values[blocks[1].id] = 'Changed only here'
        updated = self.document.render(values, 'en-GB')
        self.assertIn('<p>Repeated</p><p>Changed only here</p>', updated)

    def test_tokens_and_nbsp_never_become_translation_cells(self):
        for block in self.document.blocks:
            self.assertNotIn('{{', block.source)
            self.assertNotIn('[[', block.source)
            self.assertNotIn('${', block.source)
            self.assertNotIn('\xa0', block.source)

    def test_missing_translation_stops_every_output(self):
        self.prepare()
        book = self.filled()
        book['Translations']['F7'] = None
        report = self.save_and_complete(book)
        self.assertFalse(report['ok'])
        self.assertTrue(any(e['language'] == 'fr-FR' and e['cell'] == 'F7' for e in report['errors']))
        self.assertFalse((self.folder / 'completed').exists())

    def test_row_reordering_uses_ids(self):
        self.prepare(update_lang=False)
        book = self.filled()
        sheet = book['Translations']
        values = list(sheet.iter_rows(min_row=7, values_only=True))
        for row, values in enumerate(reversed(values), 7):
            for column, value in enumerate(values, 1):
                sheet.cell(row, column, value)
        report = self.save_and_complete(book)
        self.assertTrue(report['ok'])
        self.assertEqual((self.folder / 'completed/email-de-DE.html').read_bytes(), self.original.read_bytes())

    def test_source_edits_and_duplicate_or_missing_ids_are_rejected(self):
        for mutation, code in [('source', 'source_changed'), ('duplicate', 'duplicate_id'), ('missing', 'missing_id'), ('unknown', 'unknown_id')]:
            with self.subTest(mutation=mutation):
                if not self.job.exists():
                    self.prepare()
                book = self.filled()
                sheet = book['Translations']
                if mutation == 'source':
                    sheet['D7'] = 'Different source'
                elif mutation == 'duplicate':
                    sheet['A8'] = sheet['A7'].value
                elif mutation == 'missing':
                    sheet.delete_rows(7)
                else:
                    sheet['A7'] = 'B999999'
                report = self.save_and_complete(book, output=False)
                self.assertFalse(report['ok'])
                self.assertIn(code, [e['code'] for e in report['errors']])

    def test_changed_language_and_workbook_identity_rejected(self):
        self.prepare()
        book = self.filled()
        book['Translations']['E6'] = 'es-ES'
        self.assertIn('headers', [e['code'] for e in self.save_and_complete(book, False)['errors']])
        book = self.filled()
        for row in book['_EmailStudio']:
            if row[0].value == 'source_sha256':
                row[1].value = json.dumps('wrong')
        self.assertIn('source_mismatch', [e['code'] for e in self.save_and_complete(book, False)['errors']])

    def test_modified_retained_original_cannot_accept_old_workbook(self):
        self.prepare()
        book = self.filled()
        (self.job / 'original.html').write_bytes(SOURCE.replace('Repeated', 'Different').encode('utf-8'))
        with self.assertRaisesRegex(ValueError, 'Saved job'):
            self.save_and_complete(book)

    def test_formula_translation_rejected_but_literal_equals_allowed(self):
        self.prepare()
        book = self.filled()
        book['Translations']['E7'] = '=1+1'
        self.assertIn('formula', [e['code'] for e in self.save_and_complete(book, False)['errors']])
        book = self.filled()
        book['Translations']['E7'] = '=Your literal wording'
        book['Translations']['E7'].data_type = 's'
        self.assertTrue(self.save_and_complete(book, False)['ok'])

    def test_user_markup_is_escaped_and_protected_tokens_cannot_be_inserted(self):
        self.prepare()
        book = self.filled()
        book['Translations']['E7'] = '<b>Hello</b> & "world"'
        self.assertTrue(self.save_and_complete(book)['ok'])
        text = (self.folder / 'completed/email-de-DE.html').read_text(encoding='utf-8')
        self.assertIn('&lt;b&gt;Hello&lt;/b&gt; &amp; &quot;world&quot;', text)
        for replacement in ['{{Injected}}', '[[Injected]]', '${Injected}', 'hidden\u200bword', 'two\nlines']:
            with self.subTest(replacement=replacement):
                book = self.filled()
                book['Translations']['E7'] = replacement
                self.assertFalse(self.save_and_complete(book, False)['ok'])

    def test_unchanged_internal_newlines_survive(self):
        original = SOURCE.replace('Welcome &amp; hello', 'Welcome\r\n &amp; hello')
        document = EmailDocument(original)
        values = {b.id: b.source for b in document.blocks}
        self.assertEqual(document.render(values, 'en-GB', False), original)

    def test_missing_lang_reports_notice_and_never_inserts_attribute(self):
        document = EmailDocument(SOURCE.replace(' lang="en-GB"', ''))
        self.assertTrue(document.notices)
        updated = document.render({b.id: b.source for b in document.blocks}, 'fr-FR')
        self.assertEqual(updated, document.source)

    def test_malformed_encoded_expressions_and_ambiguous_outlook_stop_extraction(self):
        for source in [SOURCE.replace('{{Name}}', '{{Name'), SOURCE.replace('{{Name}}', '&#123;&#123;Name&#125;&#125;'),
                       SOURCE.replace('>Find out more</center>', '>Different</center>'),
                       SOURCE.replace('class="buttonWrapper"', 'class="other"').replace(' data-msdyn-tracking-id="button1"', '')]:
            with self.subTest(source=source[:80]):
                with self.assertRaises(ValueError):
                    EmailDocument(source)

    def test_source_formula_looking_text_is_stored_as_literal(self):
        self.original.write_bytes(SOURCE.replace('Welcome &amp; hello', '=1+1').encode('utf-8'))
        self.prepare()
        book = load_workbook(self.job / 'translations.xlsx')
        self.assertEqual(book['Translations']['D7'].value, '=1+1')
        self.assertEqual(book['Translations']['D7'].data_type, 's')
        self.assertEqual(book['Translations'].freeze_panes, 'E7')
        self.assertTrue(book['Translations'].protection.sheet)
        self.assertFalse(book['Translations']['E7'].protection.locked)
        book.close()

    def test_existing_job_and_outputs_are_never_overwritten(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.prepare()
        self.assertTrue(self.save_and_complete(self.filled())['ok'])
        saved = (self.folder / 'completed/email-de-DE.html').read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.save_and_complete(self.filled())
        self.assertEqual(saved, (self.folder / 'completed/email-de-DE.html').read_bytes())

    def test_language_validation_and_rtl_boundary(self):
        self.assertEqual(language_selection('EN-gb', ['DE-de'])[1], ['de-DE'])
        for targets in [['de-DE', 'DE-de'], ['../escape'], ['ar-SA'], []]:
            with self.subTest(targets=targets):
                with self.assertRaises(ValueError):
                    language_selection('en-GB', targets)

    def test_invalid_attachment_and_extra_columns_fail(self):
        self.prepare()
        book = self.filled()
        book['Translations']['G7'] = 'Unexpected'
        self.assertFalse(self.save_and_complete(book, False)['ok'])
        bad = self.folder / 'bad.xlsx'
        bad.write_bytes(b'not an xlsx')
        process = subprocess.run([sys.executable, str(ROOT / 'copilot/email-translation-workbook/scripts/translation_workbook.py'),
                                  'complete', '--job', str(self.job), '--workbook', str(bad), '--output-dir', str(self.folder / 'bad-output')], capture_output=True, text=True)
        self.assertEqual(process.returncode, 1)
        self.assertFalse(json.loads(process.stdout)['ok'])
        self.assertFalse((self.folder / 'bad-output').exists())

    def test_shipped_emails_roundtrip_and_accept_a_real_replacement(self):
        for path in sorted((ROOT / 'example').glob('*.html')):
            with self.subTest(email=path.name):
                source = path.read_bytes().decode('utf-8')
                document = EmailDocument(source)
                values = {b.id: b.source for b in document.blocks}
                self.assertEqual(document.render(values, 'en-GB', False).encode('utf-8'), path.read_bytes())
                first = document.blocks[0]
                values[first.id] = 'Translated ' + ' '.join(first.source.split())
                updated = document.render(values, 'fr-FR', False)
                self.assertNotEqual(updated, source)
                self.assertIn('Translated ', updated)

    def test_archive_is_deterministic_self_contained_and_runs_outside_repo(self):
        data = packager.package_bytes()
        self.assertEqual(data, packager.package_bytes())
        release = self.folder / 'release'
        with ZipFile(io.BytesIO(data)) as archive:
            self.assertIn('SKILL.md', archive.namelist())
            self.assertEqual(archive.read('scripts/source_guard.py'), (ROOT / 'plugin/skills/d365-email-studio/scripts/validate_email.py').read_bytes())
            archive.extractall(release)
        process = subprocess.run([sys.executable, 'scripts/runtime_check.py', '--output-dir', 'probe'], cwd=release, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        self.assertTrue(json.loads(process.stdout)['ok'])
        returned = subprocess.run([sys.executable, 'scripts/runtime_check.py', '--uploaded', 'probe/runtime-probe.xlsx', '--output-dir', 'uploaded-probe'], cwd=release, capture_output=True, text=True)
        self.assertEqual(returned.returncode, 0, returned.stderr + returned.stdout)
        self.assertTrue(json.loads(returned.stdout)['uploaded_workbook_checked'])


if __name__ == '__main__':
    unittest.main()
