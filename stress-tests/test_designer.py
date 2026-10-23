"""Regression checks against current designer source; no-op mutations fail tests."""
import importlib.util
import json
from pathlib import Path
spec=importlib.util.spec_from_file_location('guard','/Users/mylo/.codex/skills/d365-email-studio/scripts/validate_email.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
source=Path(__file__).parents[1].joinpath('example/example.html').read_bytes().decode()
cases=[]
def change(name,old,new,accept):
    assert old in source, f'{name}: fixture target missing'
    updated=source.replace(old,new,1)
    assert updated!=source
    cases.append((name,updated,accept))
cases.append(('unchanged',source,True))
change('language','lang="en-US"','lang="fr-FR"',True)
change('label','>Link<','>Lien<',True)
change('destination retaining tracking','https://google.com#','https://example.com#',True)
change('removed tracking', '#_msdynmkt_donottrack=0,_msdynmkt_linkid=473e3671-e12e-4d35-930b-5d92c5120fe2','',False)
change('altered tracking ID','473e3671-e12e-4d35-930b-5d92c5120fe2','replacement',False)
change('tracking disabled','_msdynmkt_donottrack=0','_msdynmkt_donottrack=1',False)
change('designer setting','value="marketing-designer-content-editor-document"','value="other"',False)
change('CSS marker','/* @layout-max-width */','/* changed */',False)
change('editor block type','data-editorblocktype="Text"','data-editorblocktype="Image"',False)
change('container ID','container4009e107d1ec71792736061457','replacement',False)
change('asset metadata','data-image-file-id="a10c8e0a-492b-f111-88b4-7c1e5265a4b8"','data-image-file-id="other"',False)
change('image source only','src="https://assets-gbr.mkt.dynamics.com/','src="https://example.com/',True)
change('missing alt added','<img src=','<img alt="Logo" src=',False)
change('lookup metadata','data-lookup-name="New event 1"','data-lookup-name="Translated event"',False)
change('functional URL','New_event_12303416225','other',False)
change('subject/title','<title>My Email Subject</title>','<title>Sujet</title>',False)
results=[]
for name,updated,expected in cases:
    try: guard.validate(source,updated);accepted=True
    except ValueError:accepted=False
    results.append(dict(test=name,passed=accepted==expected,accepted=accepted))
print(json.dumps(results,indent=2))
assert all(r['passed'] for r in results)
