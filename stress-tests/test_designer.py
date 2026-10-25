"""Regression checks against the shipped designer source."""
import importlib.util
import re
from pathlib import Path
root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('guard', root / 'd365-email-studio/scripts/validate_email.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
source = (root / 'example/example2.html').read_bytes().decode()
cases = [('unchanged', source, True)]
def change(name, old, new, accept):
    assert old in source, f'{name}: fixture target missing'
    updated = source.replace(old, new)
    assert updated != source
    cases.append((name, updated, accept))
change('designer setting', 'value="marketing-designer-content-editor-document"', 'value="other"', False)
change('CSS marker', '/* @layout-max-width */', '/* changed */', False)
change('subject/title', '<title>My Email Subject</title>', '<title>Sujet</title>', False)
for attr in ['data-editorblocktype', 'data-image-file-id']:
    match = re.search(rf'{attr}="[^"]+"', source)
    assert match, f'{attr}: fixture target missing'
    change(attr, match.group(), f'{attr}="changed"', False)
for name, updated, expected in cases:
    try:
        guard.validate(source, updated)
        accepted = True
    except ValueError:
        accepted = False
    assert accepted == expected, name
    print('PASS:', name)

# Compact designer fixture retains coverage for metadata and tracking not present
# in every shipped example. Both before/after inputs remain under test control.
source = '<html lang="en-US"><body><a href="https://example.com#_msdynmkt_linkid=abc" data-lookup-name="Event" data-containerid="container1">Link</a><img src="https://example.com/a" data-image-file-id="asset1"></body></html>'
cases = []
change('language', 'lang="en-US"', 'lang="fr-FR"', True)
change('label', '>Link<', '>Lien<', True)
change('destination retaining tracking', 'https://example.com#', 'https://other.example#', True)
change('tracking removed', '#_msdynmkt_linkid=abc', '', False)
change('tracking changed', '_msdynmkt_linkid=abc', '_msdynmkt_linkid=other', False)
change('container ID', 'data-containerid="container1"', 'data-containerid="other"', False)
change('lookup metadata', 'data-lookup-name="Event"', 'data-lookup-name="Other"', False)
change('asset metadata', 'data-image-file-id="asset1"', 'data-image-file-id="other"', False)
change('image source', 'src="https://example.com/a"', 'src="https://example.com/b"', True)
change('missing alt added', '<img src=', '<img alt="Logo" src=', False)
for name, updated, expected in cases:
    try:
        guard.validate(source, updated)
        accepted = True
    except ValueError:
        accepted = False
    assert accepted == expected, name
    print('PASS:', name)
