"""Release integrity tests; no network or deployment required."""
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from package_plugin import release_files, archive_bytes


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        files = {
            'plugin/plugin.json': '{"version":"0.1.12"}',
            'plugin/.codex-plugin/plugin.json': '{"version":"0.1.12"}',
            'cloudflare-mcp/package.json': '{"version":"0.1.12"}',
            'd365-email-studio/SKILL.md': 'Rules',
            'plugin/skills/d365-email-studio/SKILL.md': 'Rules',
            'd365-email-studio/references/edit-plan.md': 'Plan format',
            'plugin/skills/d365-email-studio/references/edit-plan.md': 'Plan format',
            'plugin/.app.json': '{"apps":[]}',
        }
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def test_deterministic_archive_contains_references_and_checksums(self):
        version, files = release_files(self.root)
        self.assertEqual(version, '0.1.12')
        first = archive_bytes(files)
        self.assertEqual(first, archive_bytes(dict(reversed(list(files.items())))))
        with ZipFile(BytesIO(first)) as archive:
            self.assertEqual(archive.read('skills/d365-email-studio/references/edit-plan.md'), b'Plan format')
            manifest = json.loads(archive.read('release-manifest.json'))
            self.assertIn('.app.json', manifest['sha256'])

    def test_stale_skill_or_missing_reference_fails(self):
        path = self.root / 'plugin/skills/d365-email-studio/references/edit-plan.md'
        path.write_text('Outdated')
        with self.assertRaisesRegex(ValueError, 'differs'):
            release_files(self.root)
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'differs'):
            release_files(self.root)

    def test_mismatched_versions_fail(self):
        path = self.root / 'cloudflare-mcp/package.json'
        path.write_text('{"version":"0.1.11"}')
        with self.assertRaisesRegex(ValueError, 'versions differ'):
            release_files(self.root)


if __name__ == '__main__':
    unittest.main()
