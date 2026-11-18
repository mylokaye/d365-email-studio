#!/usr/bin/env python3
"""Build the standalone Copilot workbook skill, including the unchanged HTML guard."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]


def package_bytes(root=ROOT):
    skill = root / 'copilot/email-translation-workbook'
    files = {p.relative_to(skill).as_posix(): p.read_bytes() for p in skill.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.pyo'} and not p.name.startswith('.')}
    files['scripts/source_guard.py'] = (root / 'plugin/skills/d365-email-studio/scripts/validate_email.py').read_bytes()
    files['LICENSE'] = (root / 'LICENSE').read_bytes()
    manifest = dict(version='0.1.0', guard_source='plugin/skills/d365-email-studio/scripts/validate_email.py',
                    sha256={name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())})
    files['package-manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode('utf-8')
    output = io.BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/copilot-workbook/email-translation-workbook.zip')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(package_bytes())
    print(args.output)


if __name__ == '__main__':
    main()
