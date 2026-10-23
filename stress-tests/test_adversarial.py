import importlib.util
import json
import sys
from pathlib import Path

validator = Path(sys.argv[1]) if len(sys.argv)>1 else Path('/Users/mylo/.codex/skills/d365-email-studio/scripts/validate_email.py')
spec=importlib.util.spec_from_file_location('guard',validator); guard=importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
base=Path(__file__).with_name('exported-original.html').read_bytes().decode()
fixture='<html lang="en-US"><body><p>Hello {{Name}} welcome</p><img src="https://example.com/a" alt="Logo"></body></html>'
cases=[
('baseline',base,base,True),
('French labels',base,base.replace('>Button<','>Continuer<').replace('>Link<','>Lien<').replace('>Unsubscribe<','>Se désabonner<').replace('lang="en-US"','lang="fr-FR"'),True),
('CSS changed',base,base.replace('font-size:14px','font-size:15px',1),False),
('added alt',base,base.replace('<img src=','<img alt="Logo" src=',1),False),
('removed button text',base,base.replace('>Button<','><'),False),
('button invisible numeric entities',base,base.replace('>Button<','>&#8203;<'),False),
('button invisible named entities',base,base.replace('>Button<','>&ZeroWidthSpace;<'),False),
('placeholder moved across wording',fixture,fixture.replace('Hello {{Name}} welcome','{{Name}} Hello welcome'),False),
('Outlook-only label changed',base,base.replace('>Button<','>Continuer<',1),False),
('single Outlook image changed',base,base.replace('src="https://assets-gbr.mkt.dynamics.com/','src="https://example.com/',1),False),
('protected URL',base,base.replace('href="{{PreferenceCenter}}"','href="https://example.com/preferences"'),False),
('tracking ID',base,base.replace('10ace54c12041785705071380','other'),False),
('conditional marker',base,base.replace('<!--[if gte mso 9]>','',1),False),
('encoded text literal',fixture,fixture.replace('Hello','&lt;Hello&gt;'),True),
('attribute injection',fixture,fixture.replace('alt="Logo"','alt="Logo" onerror="alert(1)"'),False),
('active URL',fixture,fixture.replace('https://example.com/a','javascript:alert(1)'),False),
('existing alt translated',fixture,fixture.replace('alt="Logo"','alt="Marque"'),True),
('new template inserted',fixture,fixture.replace('Hello','{{Injected}}Hello'),False),
]
results=[]
for name,original,updated,expected in cases:
 try: guard.validate(original,updated); accepted=True; reason='accepted'
 except ValueError as e: accepted=False; reason=str(e)
 results.append(dict(test=name,expected_accept=expected,accepted=accepted,passed=accepted==expected,reason=reason))
print(json.dumps(results,ensure_ascii=False,indent=2))
sys.exit(0 if all(r['passed'] for r in results) else 1)
