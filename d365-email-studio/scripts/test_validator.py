"""Run with python3 test_validator.py /path/to/example.html."""
import sys
from pathlib import Path
from validate_email import validate

original = Path(sys.argv[1]).read_bytes().decode('utf-8')
cases = [
    ('unchanged', original, True),
    ('translation and Outlook label', original.replace('Lorem ipsum dolor sit amet consectetur adipiscing elit.', 'Bonjour à tous.').replace('>Button<', '>Continuer<').replace('>Unsubscribe<', '>Se désabonner<').replace('lang="en-US"', 'lang="fr-FR"'), True),
    ('ordinary destination', original.replace('href="https://google.com"', 'href="https://example.com"'), True),
    ('image source', original.replace('src="https://assets-gbr.mkt.dynamics.com/', 'src="https://example.com/'), True),
    ('added alt', original.replace('<img src=', '<img alt="Logo" src=', 1), False),
    ('CSS', original.replace('font-size:14px', 'font-size:15px', 1), False),
    ('expression', original.replace('{{URL1}}', '{{URL2}}'), False),
    ('calendar destination', original.replace('New_event_12303416225', 'New_event_123'), False),
    ('preference destination', original.replace('href="{{PreferenceCenter}}"', 'href="https://example.com"'), False),
    ('removed text', original.replace('>Button<', '><'), False),
    ('added element', original.replace('>Button<', '><b>Button</b><'), False),
    ('removed conditional', original.replace('<!--[if gte mso 9]>', '', 1), False),
    ('padding', original.replace('&nbsp;', '', 1), False),
]
for name, updated, expected in cases:
    try:
        validate(original, updated)
        accepted = True
    except ValueError:
        accepted = False
    assert accepted == expected, name
    print('PASS:', name)
small = '<html lang="en-US"><body><p>Hello</p><img alt="" src="https://example.com/a.png"></body></html>'
validate(small, small.replace('alt=""', 'alt="Logo"'))
validate(small.replace('alt=""', 'alt="Logo"'), small.replace('alt=""', 'alt="Marque"'))
print('PASS: existing empty and nonempty alt edits')
