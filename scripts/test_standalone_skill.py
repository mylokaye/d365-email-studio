"""Verify a standalone extraction works using only Python and bundled resources."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from package_standalone_skill import ROOT, NAME, standalone_files
from package_plugin import archive_bytes


class StandaloneTests(unittest.TestCase):
    def test_complete_reproducible_archive_has_no_connector_manifests(self):
        files = standalone_files(ROOT)
        expected = archive_bytes({f'{NAME}/{path}': data for path, data in files.items()})
        self.assertEqual((ROOT / f'{NAME}.zip').read_bytes(), expected)
        self.assertEqual(files['scripts/validate_email.py'], (ROOT / 'd365-email-studio/scripts/validate_email.py').read_bytes())
        with ZipFile(ROOT / f'{NAME}.zip') as archive:
            self.assertEqual(set(archive.namelist()), {f'{NAME}/{path}' for path in files})
            self.assertFalse(any(Path(name).name in {'mcp.json', '.mcp.json', '.app.json', 'plugin.json'} for name in archive.namelist()))

    def test_extracted_skill_translates_and_rejects_unrequested_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with ZipFile(ROOT / f'{NAME}.zip') as archive:
                archive.extractall(root)
            skill = root / NAME
            # The temporary workspace has no repository, packages, MCP config or app.
            source = '\ufeff<html lang="en-US"><body><p>Hello {{Name}} welcome</p>\r\n<!--[if mso]><v:roundrect href="https://example.com/a" data-msdyn-tracking-id="cta"><center>Buy</center></v:roundrect><![endif]--><a href="https://example.com/a" data-msdyn-tracking-id="cta">Buy</a></body></html>'
            original = root / 'original.html'
            original.write_bytes(source.encode('utf-8'))
            def run(*args):
                return subprocess.run([sys.executable, '-I', str(skill / 'scripts/validate_email.py'), str(original), *map(str, args)],
                                      cwd=root, capture_output=True, text=True)
            inventory = run('--inventory')
            self.assertEqual(inventory.returncode, 0, inventory.stderr)
            inventory = json.loads(inventory.stdout)
            replacements = {'Hello {{Name}} welcome': 'Bonjour {{Name}} bienvenue', 'Buy': 'Acheter', 'en-US': 'fr-FR'}
            plan = dict(version=1, source_sha256=inventory['source_sha256'], mode='translation',
                        request='Translate the greeting and both button copies into French, preserving links and tokens.',
                        edits=[dict(id=field['id'], before=field['before'], after=replacements[field['before']], reason='Requested translation occurrence.')
                               for field in inventory['fields'] if field['before'] in replacements])
            self.assertEqual(len(plan['edits']), 4)
            (root / 'edits.json').write_text(json.dumps(plan), encoding='utf-8')
            applied = run('--apply-plan', 'edits.json', '--output', 'updated.html')
            self.assertEqual(applied.returncode, 0, applied.stderr)
            expected = source
            for before, after in replacements.items():
                expected = expected.replace(before, after)
            self.assertEqual((root / 'updated.html').read_bytes(), expected.encode('utf-8'))
            self.assertEqual(original.read_bytes(), source.encode('utf-8'))
            result = run('updated.html', '--plan', 'edits.json')
            self.assertEqual(result.returncode, 0, result.stderr)
            (root / 'updated.html').write_bytes(expected.replace('https://example.com/a', 'https://other.example/b').encode('utf-8'))
            self.assertNotEqual(run('updated.html', '--plan', 'edits.json').returncode, 0)

    def test_bundled_workflow_resources_are_resolvable(self):
        files = standalone_files(ROOT)
        instructions = files['SKILL.md'].decode()
        self.assertIn('(references/edit-plan.md)', instructions)
        self.assertIn('references/edit-plan.md', files)
        self.assertNotIn('show_completed_email', instructions)
        self.assertNotIn('dependencies:', files['agents/openai.yaml'].decode())


if __name__ == '__main__':
    unittest.main()
