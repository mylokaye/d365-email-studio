#!/usr/bin/env python3
"""Build or verify a deterministic plugin archive from the canonical skill."""
import argparse
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def release_files(root):
    plugin = root / 'plugin'
    manifest = json.loads((plugin / 'plugin.json').read_text())
    version = manifest['version']
    if json.loads((plugin / '.codex-plugin/plugin.json').read_text())['version'] != version:
        raise ValueError('Plugin manifest versions differ')
    if json.loads((root / 'cloudflare-mcp/package.json').read_text())['version'] != version:
        raise ValueError('Worker and plugin versions differ')
    files = {p.relative_to(plugin).as_posix(): p.read_bytes() for p in plugin.rglob('*')
             if p.is_file() and not any(part in {'__pycache__', '.DS_Store'} for part in p.parts)
             and not p.name.endswith(('.pyc', '.pyo'))}
    skill = root / 'd365-email-studio'
    canonical = {p.relative_to(skill).as_posix(): p.read_bytes() for p in skill.rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('test_')
                 and not p.name.endswith(('.pyc', '.pyo')) and p.name != '.DS_Store'}
    bundled = {name.removeprefix('skills/d365-email-studio/'): value for name, value in files.items()
               if name.startswith('skills/d365-email-studio/')}
    if bundled != canonical:
        raise ValueError('Packaged skill differs from canonical sources; run the builder without --check')
    files['release-manifest.json'] = (json.dumps(dict(version=version, sha256={name: hashlib.sha256(value).hexdigest()
        for name, value in sorted(files.items())}), indent=2) + '\n').encode()
    return version, files


def archive_bytes(files):
    output = io.BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name, value in sorted(files.items()):
            info = ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, value)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        if not args.check:
            target = ROOT / 'plugin/skills/d365-email-studio'
            shutil.rmtree(target)
            shutil.copytree(ROOT / 'd365-email-studio', target,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', 'test_*', '.DS_Store'))
        version, files = release_files(ROOT)
        output = ROOT / f'd365-email-studio-plugin-{version}.zip'
        expected = archive_bytes(files)
        if args.check:
            if not output.exists() or output.read_bytes() != expected:
                raise ValueError('Release archive is missing or stale; rebuild it')
        else:
            output.write_bytes(expected)
        print(f'PASS: {output.name}; canonical sources and {len(files)} archive entries verified')
    except (OSError, ValueError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
