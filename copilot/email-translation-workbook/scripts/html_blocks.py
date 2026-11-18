"""Source-bound translation units built on the existing Email Studio guard."""
import hashlib
import html
import importlib.util
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


def load_guard():
    # Release builds put the shared guard beside this module, unchanged.
    path = Path(__file__).with_name('source_guard.py')
    if not path.exists():
        path = Path(__file__).resolve().parents[3] / 'plugin/skills/d365-email-studio/scripts/validate_email.py'
    spec = importlib.util.spec_from_file_location('email_source_guard', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = load_guard()
EXPRESSIONS = re.compile(r'{{.*?}}|{%.*?%}|\$\{.*?}|\[\[.*?\]\]', re.S)
DELIMITERS = re.compile(r'{{|}}|{%|%}|\$\{|\[\[|\]\]')
EXCLUDED = {'head', 'template', 'noscript', 'svg', 'math', 'object', 'select', 'option', 'button'}
LANGUAGE = re.compile(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*')
RTL = {'ar', 'arc', 'ckb', 'dv', 'fa', 'he', 'ku', 'nqo', 'ps', 'sd', 'syr', 'ug', 'ur', 'yi'}


def fingerprint(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def language_tag(value):
    if not isinstance(value, str) or not LANGUAGE.fullmatch(value):
        raise ValueError(f'Invalid language code: {value!r}. Use a code such as en-GB or de-DE.')
    pieces = value.split('-')
    return '-'.join([pieces[0].lower()] + [p.upper() if len(p) == 2 else p.title() if len(p) == 4 else p.lower() for p in pieces[1:]])


def language_selection(source, targets):
    source = language_tag(source)
    targets = [language_tag(t) for t in targets]
    if not targets or len(targets) > 25:
        raise ValueError('Choose between 1 and 25 target languages.')
    if len(set(t.lower() for t in targets)) != len(targets):
        raise ValueError('Each target language must be unique.')
    if any(t.split('-')[0] in RTL for t in [source] + targets):
        raise ValueError('Right-to-left language workflows need a separate layout review and are not supported in this version.')
    return source, targets


@dataclass
class Block:
    id: str
    kind: str
    context: str
    source: str
    ranges: list = field(default_factory=list)

    def manifest(self):
        return dict(id=self.id, kind=self.kind, context=self.context, source=self.source,
                    ranges=self.ranges)


def editable_spans(raw):
    """Keep tokens, fixed entities, invisible characters and edge whitespace in situ."""
    residual = EXPRESSIONS.sub('', raw)
    if DELIMITERS.search(html.unescape(residual)):
        raise ValueError('Incomplete, encoded or unsupported template expression in editable wording.')
    fixed = guard.fixed_text_parts(raw) + [m.span() for m in EXPRESSIONS.finditer(raw)]
    merged = []
    for start, end in sorted(fixed):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    position = 0
    for start, end in merged + [(len(raw), len(raw))]:
        chunk = raw[position:start]
        left = len(chunk) - len(chunk.lstrip(' \t\r\n'))
        right = len(chunk.rstrip(' \t\r\n'))
        if right > left and html.unescape(chunk[left:right]).strip():
            yield position + left, position + right
        position = end


def describe(document, item):
    nodes = document['nodes']
    ancestors = [nodes[n] for n in reversed(item['nodes'])]
    if item['kind'] == 'alt':
        return 'Image description', 'Existing image description'
    owner = next((n for n in ancestors if n['tag'] in guard.LINK_TAGS), None)
    kind = 'Link / button' if owner else 'Body text'
    if not owner:
        heading = next((n for n in ancestors if re.fullmatch(r'h[1-6]', n['tag'])), None)
        kind = 'Heading' if heading else 'List item' if any(n['tag'] == 'li' for n in ancestors) else kind
    container = next((n for n in ancestors if n['tag'] in {'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}), owner)
    context = ' '.join(html.unescape(''.join(container['text'])).split()) if container else kind
    return kind, context[:240]


class EmailDocument:
    def __init__(self, source):
        if len(source.encode('utf-8')) > 5 * 1024 * 1024:
            raise ValueError('Use a complete UTF-8 HTML email smaller than 5 MB.')
        self.source = source
        self.sha256 = fingerprint(source)
        self.document = guard.analyse(source)
        nodes = self.document['nodes']
        roots = [n for n in nodes.values() if n['tag'] == 'html' and not n['parents']]
        bodies = [n for n in nodes.values() if n['tag'] == 'body']
        if len(roots) != 1 or len(bodies) != 1 or not re.search(r'</body\s*>', source, re.I) or not re.search(r'</html\s*>\s*$', source, re.I):
            raise ValueError('Supply one complete HTML email including html and body opening and closing tags.')
        self.groups = guard.counterpart_groups(self.document)
        mapped = {n: index for index, group in enumerate(self.groups) for n in group}
        for group in self.groups:
            values = [guard.node_values(nodes[n]) for n in group]
            if any(value != values[0] for value in values[1:]):
                raise ValueError('Existing Outlook counterparts differ. Resolve their wording/URLs before preparing a workbook.')
        unknown = [n for n in nodes.values() if n['tag'] in guard.LINK_TAGS | {'img'}
                   and not n['protected'] and (n['conditional'] or n['tag'].startswith('v:')) and n['id'] not in mapped]
        if unknown:
            raise ValueError('Unpaired Outlook link/image. Add matching wrapper/tracking metadata or review this email separately.')
        self.decisions = [dict(type='standalone', members=[n['id']], reason='No unpaired conditional link/image remains; this occurrence is outside recognised counterpart groups.')
                          for n in nodes.values() if n['tag'] in guard.LINK_TAGS | {'img'} and not n['protected'] and n['id'] not in mapped]
        self.blocks, self.notices = [], []
        self.lang_field = next((f for f in self.document['fields'] if f['kind'] == 'lang'), None)
        if self.lang_field is None:
            self.notices.append('No editable root html lang value. Language metadata will remain unchanged.')
        candidates, group_units = [], {}
        for item in self.document['fields']:
            if item['kind'] not in {'text', 'alt'}:
                continue
            ancestors = [nodes[n] for n in item['nodes']]
            if any(n['tag'] in EXCLUDED for n in ancestors):
                continue
            owner = next((n['id'] for n in reversed(ancestors) if n['tag'] in guard.LINK_TAGS | {'img'}), None)
            kind, context = describe(self.document, item)
            for start, end in editable_spans(item['before']):
                raw = item['before'][start:end]
                unit = dict(start=item['start'] + start, end=item['start'] + end, raw=raw, field_id=item['id'])
                candidate = Block('', kind, context, html.unescape(raw), [unit])
                if owner in mapped:
                    group_units.setdefault((mapped[owner], owner), []).append(candidate)
                else:
                    candidates.append(candidate)
        for index, members in enumerate(self.groups):
            sequences = [group_units.get((index, member), []) for member in members]
            if any([b.source for b in seq] != [b.source for b in sequences[0]] for seq in sequences[1:]):
                raise ValueError('Outlook counterparts have different inline text segmentation. Review this email separately.')
            for position, first in enumerate(sequences[0]):
                first.ranges = [r for seq in sequences for r in seq[position].ranges]
                candidates.append(first)
        for index, block in enumerate(sorted(candidates, key=lambda b: min(r['start'] for r in b.ranges)), 1):
            if len(block.source) > 30000:
                raise ValueError('An editable text run exceeds the supported Excel cell length. Review this email separately.')
            block.id = f'B{index:04d}'
            self.blocks.append(block)
        if not self.blocks:
            raise ValueError('No editable translation blocks were found.')
        if len(self.blocks) > 10000:
            raise ValueError('This version supports at most 10,000 translation blocks per email.')
        self.inventory_sha256 = fingerprint(json_text([b.manifest() for b in self.blocks]))

    def render(self, translations, target, update_lang=True):
        expected = {block.id for block in self.blocks}
        if set(translations) != expected:
            raise ValueError('Translation block IDs do not match the source.')
        by_field = {}
        for block in self.blocks:
            value = translations[block.id]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{block.id}: translation is missing.')
            if value != value.strip(' \t\r\n'):
                raise ValueError(f'{block.id}: remove leading/trailing spaces or line breaks.')
            if value == block.source:
                continue  # Retain original entities and internal line endings on an unchanged run.
            if DELIMITERS.search(value) or any(guard.invisible(c) for c in value):
                raise ValueError(f'{block.id}: translation contains template syntax or protected invisible characters.')
            # Fixed whitespace belongs to the source ranges between these runs.
            if '\n' in value or '\r' in value or '\t' in value:
                raise ValueError(f'{block.id}: keep this text run on one line.')
            for span in block.ranges:
                by_field.setdefault(span['field_id'], []).append((span, html.escape(value, quote=True)))
        fields = {f['id']: f for f in self.document['fields']}
        edits = []
        for identity, replacements in by_field.items():
            item = fields[identity]
            after = item['before']
            for span, replacement in sorted(replacements, key=lambda p: p[0]['start'], reverse=True):
                start, end = span['start'] - item['start'], span['end'] - item['start']
                if after[start:end] != span['raw']:
                    raise ValueError('Source range mismatch. Reload the original HTML.')
                after = after[:start] + replacement + after[end:]
            edits.append(dict(id=identity, before=item['before'], after=after, reason=f'Workbook translation into {target}.'))
        if update_lang and self.lang_field and self.lang_field['before'] != target:
            edits.append(dict(id=self.lang_field['id'], before=self.lang_field['before'], after=language_tag(target), reason='Set the existing root language value to the requested target.'))
        plan = dict(version=1, source_sha256=self.sha256, mode='translation',
                    request=f'Apply the completed workbook translations into {target}; preserve destinations, images, markup and protected expressions.',
                    edits=edits, counterpart_decisions=self.decisions)
        updated = guard.planned_output(self.source, plan)
        guard.validate(self.source, updated, plan)
        return updated
