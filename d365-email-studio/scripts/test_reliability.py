"""Behavioral regressions for source guards and the request-scoped CLI workflow."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 and sys.argv[1].endswith('.py') else Path(__file__).with_name('validate_email.py')
spec = importlib.util.spec_from_file_location('guard', SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def page(content, head=''):
    return f'<html lang="en-US"><head>{head}</head><body>{content}</body></html>'


def plan_for(source, changes, mode='translation', standalone=False):
    inv = guard.inventory(source)
    plan = dict(version=1, source_sha256=inv['source_sha256'], mode=mode,
                request='Translate the selected copy to French.' if mode == 'translation' else 'Update the selected content and destinations.', edits=[])
    for before, after in changes:
        fields = [field for field in inv['fields'] if field['before'] == before]
        if not fields:
            raise AssertionError(f'Missing fixture field {before!r}')
        for field in fields:
            edit = dict(id=field['id'], before=before, after=after, reason='Requested occurrence in the source.')
            if field['kind'] == 'href':
                edit['purpose'] = 'ordinary'
            plan['edits'].append(edit)
    if standalone:
        plan['counterpart_decisions'] = [dict(type='standalone', members=[identity], reason='Inspected source; this occurrence has no fallback.')
                                         for identity, node in guard.analyse(source)['nodes'].items()
                                         if node['tag'] in guard.LINK_TAGS | {'img'} and not node['protected']]
    return plan


def button_pair(tag='v:roundrect', tracking=True, third=False, labels=('Buy', 'Buy')):
    identity = ' data-msdyn-tracking-id="cta"' if tracking else ''
    vml = f'<!--[if mso]><{tag} href="https://example.com/a"{identity}><center>{labels[0]}</center></{tag}><![endif]-->'
    normal = f'<a href="https://example.com/a"{identity}>{labels[1]}</a>'
    return page(vml + normal + (normal if third else ''))


class SourceTests(unittest.TestCase):
    def test_protected_raw_contexts(self):
        for tag in ('style', 'script', 'title', 'textarea', 'xmp', 'iframe'):
            with self.subTest(tag=tag):
                source = page(f'<{tag}>prefix \'<img src="https://example.com/a">\' suffix</{tag}><p>Hello</p>')
                guard.validate(source, source)
                with self.assertRaises(ValueError):
                    guard.validate(source, source.replace('/a"', '/b"'))
                guard.validate(source, source.replace('Hello', 'Bonjour'))
                self.assertFalse(any(f['kind'] == 'src' for f in guard.inventory(source)['fields']))

    def test_head_and_inert_contexts(self):
        for source in (page('<p>Hello</p>', '<a href="https://example.com/a">Text</a>'),
                       page('<template><img src="https://example.com/a"></template>'),
                       page('<noscript><img src="https://example.com/a"></noscript>')):
            with self.subTest(source=source), self.assertRaises(ValueError):
                guard.validate(source, source.replace('/a"', '/b"'))

    def test_unclosed_raw_context_and_ambiguous_attributes(self):
        for source in ('<style>unclosed', page('<img src="https://a" src="https://b">'),
                       page('<img src=https://a src="https://b">'),
                       page('<a data-value=href="https://example.com/a">Read</a>'),
                       '<!--[if mso]><p>Hello</p>'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                guard.validate(source, source)

    def test_encoded_padding_is_fixed_in_mixed_text(self):
        for spacer in ('&#8203;', '&#x200B;', '&ZeroWidthSpace;', '&#0160;', '&#x000A0;', '&nbsp;', '&lrm;', '&#8238;', '&ensp;', '&#32;', '&#13;', '\u200b', '\u00a0'):
            source = page('<div>Hello' + spacer + 'world</div>')
            with self.subTest(spacer=spacer):
                with self.assertRaises(ValueError):
                    guard.validate(source, source.replace(spacer, ''))
                with self.assertRaises(ValueError):
                    guard.validate(source, source.replace(spacer, '&#8204;'))
                guard.validate(source, source.replace('Hello', 'Bonjour').replace('world', 'monde'))

    def test_encoding_spelling_and_token_adjacency(self):
        source = page('<p>Hello&nbsp;{{Name}} welcome</p>')
        with self.assertRaises(ValueError):
            guard.validate(source, source.replace('&nbsp;', '&#160;'))
        with self.assertRaises(ValueError):
            guard.validate(source, source.replace('Hello&nbsp;', '&nbsp;'))

    def test_functional_links_from_url_label_and_metadata(self):
        cases = [
            ('https://events.example.com/calendar/event.ics', 'Add to calendar', ''),
            ('https://example.com/event%2Eics', 'Download', ''),
            ('https://events.example.com/register/42', 'Continue', ''),
            ('https://example.com/opaque', 'Add to calendar', ''),
            ('https://example.com/opaque', 'Continue', ' data-lookup-name="Event"'),
            ('https://example.com/opaque', 'Continue', ' aria-label="Unsubscribe"'),
        ]
        for href, label, attrs in cases:
            source = page(f'<a href="{href}"{attrs}>{label}</a>')
            with self.subTest(href=href, label=label, attrs=attrs):
                with self.assertRaises(ValueError):
                    guard.validate(source, source.replace(href, 'https://example.com/replaced'))
                guard.validate(source, source.replace('>' + label + '<', '>Texte traduit<'))
                self.assertTrue(guard.inventory(source)['links'][0]['protected_reason'])

    def test_ancestor_metadata_protects_link_after_label_translation(self):
        source = page('<div data-lookup-name="Event"><a href="https://example.com/opaque">Continue</a></div>')
        with self.assertRaises(ValueError):
            guard.validate(source, source.replace('/opaque', '/replacement').replace('Continue', 'Continuer'))
        guard.validate(source, source.replace('Continue', 'Continuer'),
                       plan_for(source, [('Continue', 'Continuer')], standalone=True))

    def test_unquoted_metadata_is_preserved_and_used_for_classification(self):
        source = page('<a data-lookup-name=Event href="https://example.com/a">Read</a>')
        guard.validate(source, source.replace('Read', 'Lire'))
        with self.assertRaises(ValueError):
            guard.validate(source, source.replace('/a"', '/b"'))
        with self.assertRaises(ValueError):
            guard.validate(source, source.replace('=Event', '=Product'))

    def test_roundrect_and_multiple_counterparts(self):
        for tag in ('v:shape', 'v:roundrect'):
            for third in (False, True):
                source = button_pair(tag=tag, third=third)
                with self.subTest(tag=tag, third=third):
                    with self.assertRaises(ValueError):
                        guard.validate(source, source.replace('>Buy<', '>Acheter<', 1))
                    updated = source.replace('>Buy<', '>Acheter<')
                    guard.validate(source, updated, plan_for(source, [('Buy', 'Acheter')]))

    def test_mismatched_existing_counterparts_stop_affected_edit(self):
        source = button_pair(labels=('Buy', 'Buy now'))
        guard.validate(source, source)
        with self.assertRaisesRegex(ValueError, 'Ambiguous Outlook'):
            guard.validate(source, source.replace('>Buy<', '>Acheter<'))

    def test_reused_tracking_id_does_not_cross_wrapper_boundaries(self):
        first = button_pair().split('<body>')[1].split('</body>')[0]
        second = first.replace('Buy', 'Read')
        source = page('<div class="buttonWrapper">' + first + '</div><div class="buttonWrapper">' + second + '</div>')
        guard.validate(source, source.replace('>Buy<', '>Acheter<'), plan_for(source, [('Buy', 'Acheter')]))

    def test_three_image_copies_and_nested_wrappers(self):
        image = '<img src="https://example.com/a" alt="Logo">'
        source = page('<div class="imageWrapper"><div><!--[if mso]>' + image + '<![endif]--></div>' + image * 2 + '</div>')
        with self.assertRaises(ValueError):
            guard.validate(source, source.replace('alt="Logo"', 'alt="Marque"', 1))
        guard.validate(source, source.replace('alt="Logo"', 'alt="Marque"'), plan_for(source, [('Logo', 'Marque')]))


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.source = page('<p>Hello</p><a href="https://example.com/a">Read</a><img src="https://example.com/a.png" alt="Logo">')
        self.plan = plan_for(self.source, [('Hello', 'Bonjour')])
        self.updated = self.source.replace('Hello', 'Bonjour')

    def test_exact_plan_passes_and_unrequested_edits_fail(self):
        guard.validate(self.source, self.updated, self.plan)
        for old, new in (('/a"', '/b"'), ('/a.png', '/b.png'), ('Read', 'Lire'), ('Logo', 'Marque')):
            with self.subTest(old=old), self.assertRaisesRegex(ValueError, 'exact request-scoped'):
                guard.validate(self.source, self.updated.replace(old, new), self.plan)

    def test_plan_bound_to_original_and_values(self):
        for key, value in (('source_sha256', 'bad'), ('version', 2), ('mode', 'anything'), ('request', '')):
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                guard.validate(self.source, self.updated, plan)
        for key, value in (('before', 'wrong'), ('id', 'unknown'), ('reason', ''), ('after', None)):
            plan = copy.deepcopy(self.plan)
            plan['edits'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                guard.validate(self.source, self.updated, plan)

    def test_duplicate_and_omitted_edits_rejected(self):
        for edits in ([self.plan['edits'][0]] * 2, []):
            plan = dict(self.plan, edits=edits)
            with self.assertRaises(ValueError):
                guard.validate(self.source, self.updated, plan)

    def test_translation_cannot_authorize_href_or_src(self):
        for value in ('https://example.com/a', 'https://example.com/a.png'):
            plan = plan_for(self.source, [(value, 'https://other.example/b')])
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'Translation plans'):
                guard.planned_output(self.source, plan)

    def test_destination_classification_required(self):
        plan = plan_for(self.source, [('https://example.com/a', 'https://other.example/b')], mode='edit', standalone=True)
        updated = guard.planned_output(self.source, plan)
        guard.validate(self.source, updated, plan)
        del plan['edits'][0]['purpose']
        with self.assertRaisesRegex(ValueError, 'classification'):
            guard.validate(self.source, updated, plan)

    def test_unresolved_fallback_requires_review_and_consistency(self):
        source = button_pair(tracking=False)
        plan = plan_for(source, [('Buy', 'Acheter')])
        updated = guard.planned_output(source, plan)
        with self.assertRaisesRegex(ValueError, 'Unresolved counterpart'):
            guard.validate(source, updated, plan)
        members = [identity for identity, node in guard.analyse(source)['nodes'].items() if node['tag'] in guard.LINK_TAGS]
        plan['counterpart_decisions'] = [dict(type='group', members=members, reason='Adjacent mutually exclusive versions of the same button.')]
        guard.validate(source, updated, plan)
        plan['edits'].pop()
        with self.assertRaisesRegex(ValueError, 'diverged'):
            guard.validate(source, guard.planned_output(source, plan), plan)

    def test_standalone_review_does_not_disable_detected_group(self):
        source = button_pair()
        plan = plan_for(source, [('Buy', 'Acheter')], standalone=True)
        plan['edits'].pop()
        with self.assertRaisesRegex(ValueError, 'diverged'):
            guard.validate(source, guard.planned_output(source, plan), plan)

    def test_repeated_copy_authorizes_one_occurrence(self):
        source = page('<p>Hello</p><p>Hello</p>')
        plan = plan_for(source, [('Hello', 'Bonjour')])
        plan['edits'].pop()
        guard.validate(source, source.replace('Hello', 'Bonjour', 1), plan)
        with self.assertRaisesRegex(ValueError, 'exact request-scoped'):
            guard.validate(source, source.replace('Hello', 'Bonjour'), plan)

    def test_attribute_injection_and_tracking_remain_protected(self):
        source = page('<img src="https://example.com/a" alt="Logo"><a href="https://example.com/a#_msdynmkt_linkid=abc">Read</a>')
        for old, new in [('Logo', 'Logo" onerror="run()'), ('https://example.com/a#_msdynmkt_linkid=abc', 'https://other.example/')]:
            plan = plan_for(source, [(old, new)], mode='edit', standalone=True)
            with self.subTest(old=old), self.assertRaises(ValueError):
                guard.validate(source, guard.planned_output(source, plan), plan)

    def test_authorized_tracking_destination_and_image_edits(self):
        source = page('<a href="https://example.com/a#_msdynmkt_linkid=abc">Read</a><img src="https://example.com/a.png" alt="Logo">')
        changes = [('https://example.com/a#_msdynmkt_linkid=abc', 'https://other.example/b#_msdynmkt_linkid=abc'),
                   ('https://example.com/a.png', 'https://other.example/b.png')]
        plan = plan_for(source, changes, mode='edit', standalone=True)
        guard.validate(source, guard.planned_output(source, plan), plan)

    def test_protected_destination_cannot_be_reclassified_in_plan(self):
        source = page('<a href="https://example.com/event.ics">Download</a>')
        plan = plan_for(source, [])
        node_id = guard.inventory(source)['links'][0]['id'].split(':')[1]
        plan['mode'] = 'edit'
        plan['edits'] = [dict(id=f'attr:{node_id}:href', before='https://example.com/event.ics', after='https://other.example/',
                             purpose='ordinary', reason='Incorrect attempted reclassification.')]
        with self.assertRaisesRegex(ValueError, 'protected'):
            guard.planned_output(source, plan)

    def test_exported_fixture_translation_with_outlook_copies(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / 'stress-tests/exported-original.html').read_bytes().decode('utf-8')
        plan = plan_for(source, [('Button', 'Continuer'), ('Link', 'Lien'), ('en-US', 'fr-FR')], standalone=True)
        updated = guard.planned_output(source, plan)
        expected = source.replace('>Button<', '>Continuer<').replace('>Link<', '>Lien<').replace('lang="en-US"', 'lang="fr-FR"')
        self.assertEqual(updated, expected)
        guard.validate(source, updated, plan)


class DistributionTests(unittest.TestCase):
    def test_packaged_skill_matches_canonical_sources(self):
        root = Path(__file__).resolve().parents[2]
        for relative in ('SKILL.md', 'scripts/validate_email.py', 'references/edit-plan.md'):
            with self.subTest(relative=relative):
                self.assertEqual((root / 'd365-email-studio' / relative).read_bytes(),
                                 (root / 'plugin/skills/d365-email-studio' / relative).read_bytes())

    def test_all_shipped_html_accepts_unchanged_plan(self):
        root = Path(__file__).resolve().parents[2]
        fixtures = list((root / 'example').glob('*.html')) + list((root / 'stress-tests').glob('*.html'))
        self.assertGreater(len(fixtures), 0)
        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                source = fixture.read_bytes().decode('utf-8')
                guard.validate(source, source, plan_for(source, []))


class CliTests(unittest.TestCase):
    def test_inventory_apply_validate_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original, output, manifest = [root / name for name in ('original.html', 'updated.html', 'edits.json')]
            source = '\ufeff' + page('<p>Héllo</p>\r\n<p>World</p>')
            original.write_bytes(source.encode('utf-8'))
            def run(*args):
                return subprocess.run([sys.executable, str(SCRIPT), str(original), *map(str, args)], capture_output=True, text=True)
            inv = run('--inventory')
            self.assertEqual(inv.returncode, 0, inv.stderr)
            self.assertEqual(json.loads(inv.stdout)['source_sha256'], guard.digest(source))
            plan = plan_for(source, [('Héllo', 'Bonjour')])
            manifest.write_text(json.dumps(plan), encoding='utf-8')
            applied = run('--apply-plan', manifest, '--output', output)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertEqual(output.read_bytes(), source.replace('Héllo', 'Bonjour').encode('utf-8'))
            self.assertEqual(original.read_bytes(), source.encode('utf-8'))
            self.assertEqual(run(output, '--plan', manifest).returncode, 0)
            self.assertNotEqual(run(output).returncode, 0)
            diagnostic = run(output, '--structural-only')
            self.assertEqual(diagnostic.returncode, 0, diagnostic.stderr)
            self.assertIn('NOT verified', diagnostic.stdout)
            self.assertNotEqual(run('--apply-plan', manifest, '--output', original).returncode, 0)
            self.assertEqual(original.read_bytes(), source.encode('utf-8'))
            invalid_output = root / 'rejected.html'
            invalid_plan = copy.deepcopy(plan)
            invalid_plan['edits'][0]['after'] = '<b>Injected markup</b>'
            manifest.write_text(json.dumps(invalid_plan), encoding='utf-8')
            self.assertNotEqual(run('--apply-plan', manifest, '--output', invalid_output).returncode, 0)
            self.assertFalse(invalid_output.exists())
            for invalid in ('null', '[]', '{}', '{bad json'):
                manifest.write_text(invalid)
                failure = run(output, '--plan', manifest)
                self.assertNotEqual(failure.returncode, 0)
                self.assertNotIn('Traceback', failure.stderr)


if __name__ == '__main__':
    unittest.main()
