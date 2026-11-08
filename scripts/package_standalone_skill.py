#!/usr/bin/env python3
"""Build/check the self-contained local skill from the canonical editing rules."""
import argparse
import sys
from pathlib import Path
from package_plugin import archive_bytes

ROOT = Path(__file__).resolve().parents[1]
NAME = 'd365-email-studio-local'


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Canonical workflow changed; review the standalone adaptation before building')
    return source.replace(old, new, 1)


def standalone_files(root):
    canonical = root / 'd365-email-studio'
    source = (canonical / 'SKILL.md').read_text(encoding='utf-8')
    prefix, workflow = source.split('## Work and verification\n', 1)
    prefix = replace_once(prefix, 'name: d365-email-studio\n', f'name: {NAME}\n')
    prefix = replace_once(prefix, '# Dynamics 365 Email Studio\n', '# Dynamics 365 Email Studio — Local\n')
    prefix = replace_once(prefix, 'description: Edit or translate existing', 'description: Locally edit or translate existing')
    # Share the actual editing steps and guard unchanged, adapting only delivery.
    workflow = '1. Read the source' + workflow.split('\n1. Read the source', 1)[1]
    workflow = workflow.split('\n6. After validation and review,', 1)[0]
    workflow = replace_once(workflow,
        'The inline plugin preview is the only preview step here; recommend a separate Dynamics preview/test-send when rendering needs confirmation.',
        'Rendering is not verified by this workflow; recommend a separate Dynamics preview/test-send when rendering needs confirmation.')
    delivery = '''
6. After validation and meaning review, return a link or attachment to the complete updated HTML file, a brief summary of requested changes, and the actual validation result. If the host cannot attach files, provide the absolute local output path. Keep the original, inventory and edit plan local. Never substitute a shortened HTML example for the complete file, claim Dynamics acceptance/rendering from a guard pass, or publish/send an email.
'''
    requirements = '''## Local execution

This skill runs with local files and Python 3.9 or later using only the standard library. It needs no MCP server, connector, Node.js, tenant connection or preview app. Use the bundled validator and edit-plan reference directly; do not retrieve tools or guides from a remote service. If local execution is unavailable, explain that validation cannot run and stop before presenting an output as validated. Content supplied to your AI host remains subject to that host's processing and account settings.

## Work and verification

'''
    return {
        'SKILL.md': (prefix + requirements + workflow + delivery).encode('utf-8'),
        'scripts/validate_email.py': (canonical / 'scripts/validate_email.py').read_bytes(),
        'references/edit-plan.md': (canonical / 'references/edit-plan.md').read_bytes(),
        'agents/openai.yaml': b'interface:\n  display_name: "Dynamics 365 Email Studio Local"\n  short_description: "Edit D365 email HTML with local validation"\n',
        'LICENSE': (root / 'LICENSE').read_bytes(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        files = standalone_files(ROOT)
        folder = ROOT / 'standalone' / NAME
        output = ROOT / f'{NAME}.zip'
        archive = archive_bytes({f'{NAME}/{path}': data for path, data in files.items()})
        if args.check:
            actual = {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*')
                      if p.is_file() and '__pycache__' not in p.parts and p.name != '.DS_Store'}
            if actual != files or not output.exists() or output.read_bytes() != archive:
                raise ValueError('Standalone skill or archive is stale; rebuild it')
        else:
            for relative, data in files.items():
                path = folder / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            output.write_bytes(archive)
        print(f'PASS: {NAME}; {len(files)} self-contained files and reproducible archive verified')
    except (OSError, ValueError, IndexError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
