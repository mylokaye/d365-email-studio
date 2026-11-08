#!/usr/bin/env python3
"""Local source-preservation and request-scoped edit guard. No DOM serialization."""
import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

TOKEN = re.compile(r'<!-->|<!--\[if\b[^>]*>|<!\[endif\]-->|<!--\[endif\]---->|<!--.*?-->|<![^>]*>|</?[A-Za-z][^>"\']*(?:(?:"[^"]*"|\'[^\']*\')[^>"\']*)*>', re.S | re.I)
ATTR = re.compile(r'([^\s=<>/]+)(\s*=\s*)(["\'])(.*?)\3', re.S)
ATTRIBUTE_TOKEN = re.compile(r'''\s+([^\s=<>/"']+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s"'=<>`]+))?''', re.S)
EXPR = re.compile(r'{{.*?}}|{%.*?%}|\$\{.*?}', re.S)
ENTITY = re.compile(r'&(?:#[xX][0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]+);?')
TEXT_TAGS = {'p', 'span', 'a', 'center', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'div', 'strong', 'em', 'b', 'i', 'u', 's', 'v:textbox'}
RAW_TAGS = {'script', 'style', 'title', 'textarea', 'xmp', 'iframe', 'noembed', 'noframes'}
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr', 'w:anchorlock', 'o:allowpng'}
LINK_TAGS = {'a', 'v:shape', 'v:roundrect'}
FUNCTIONAL = re.compile(r'mkt\.dynamics\.com|preference[\s_/-]*cent(?:er|re)|unsubscribe|opt[\s_/-]*out|eventmanagement|calendar|\.ics(?:\b|$)|event[\s_/-]*registration|register|registration', re.I)


def digest(source):
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def protected_url(value):
    value = unquote(html.unescape(value))
    return bool(EXPR.search(value) or FUNCTIONAL.search(value))


def invisible(char):
    return unicodedata.category(char) in {'Cf', 'Cc', 'Zs', 'Zl', 'Zp'} and char not in ' \t\r\n'


def fixed_text_parts(value):
    """Classify decoded characters, but compare their exact source spellings."""
    fixed = []
    position = 0
    pattern = re.compile(EXPR.pattern + '|' + ENTITY.pattern, re.S)
    for match in pattern.finditer(value):
        for offset in range(position, match.start()):
            if invisible(value[offset]):
                fixed.append((offset, offset + 1))
        raw = match.group()
        if EXPR.fullmatch(raw) or any(invisible(c) or c.isspace() for c in html.unescape(raw)):
            fixed.append(match.span())
        position = match.end()
    for offset in range(position, len(value)):
        if invisible(value[offset]):
            fixed.append((offset, offset + 1))
    return fixed


def text_shape(value):
    if '<' in value:
        raise ValueError('Unrecognized markup in text')
    if not html.unescape(value).strip():
        return ('fixed-text', value)
    leading = value[:len(value) - len(value.lstrip())]
    trailing = value[len(value.rstrip()):]
    def visible(run):
        return any(not c.isspace() and unicodedata.category(c)[0] not in {'C', 'Z'} for c in html.unescape(run))
    fixed, runs, position = [], [], 0
    for start, end in fixed_text_parts(value):
        runs.append(visible(value[position:start]))
        fixed.append(value[start:end])
        position = end
    runs.append(visible(value[position:]))
    if not visible(value) and not fixed:
        return ('fixed-text', value)
    return ('text', leading, trailing, tuple(fixed), tuple(runs))


def source_tokens(source):
    """Yield exact ranges; raw-text elements are opaque, including their tags."""
    position = 0
    while position < len(source):
        if source[position] != '<':
            end = source.find('<', position)
            end = len(source) if end < 0 else end
            yield ('text', position, end)
        else:
            match = TOKEN.match(source, position)
            if not match:
                raise ValueError(f'Unsupported markup at character {position}')
            end = match.end()
            name = re.match(r'<([A-Za-z][^\s/>]*)', match.group())
            if name and name.group(1).lower() in RAW_TAGS:
                tag = name.group(1)
                close = re.search(r'</' + re.escape(tag) + r'\s*>', source[end:], re.I)
                if not close:
                    raise ValueError(f'Unclosed protected {tag} element')
                end += close.end()
                yield ('opaque', position, end)
            else:
                yield ('tag', position, end)
        position = end


def parse_attributes(raw, position):
    """Parse every attribute boundary; only existing quoted values are editable."""
    values, quoted = {}, []
    while raw[position:].strip() not in {'>', '/>'}:
        match = ATTRIBUTE_TOKEN.match(raw, position)
        if not match:
            raise ValueError('Unsupported or ambiguous attribute syntax')
        name, value = match.group(1).lower(), match.group(2)
        if name in values:
            raise ValueError('Duplicate attributes')
        is_quoted = value is not None and value[0] in {'"', "'"}
        values[name] = value[1:-1] if is_quoted else value or ''
        if is_quoted:
            quoted.append(ATTR.search(raw, match.start(), match.end()))
        position = match.end()
    return values, quoted


def inspect_source(source):
    tokens, nodes, stack, conditions = [], {}, [], []
    for index, (kind, start, end) in enumerate(source_tokens(source)):
        raw = source[start:end]
        item = dict(kind=kind, start=start, end=end, raw=raw, parents=list(stack))
        tokens.append(item)
        if kind == 'text':
            for parent in stack:
                nodes[parent]['text'].append(raw)
            continue
        if kind == 'opaque':
            continue
        if raw.startswith('<!'):
            if re.match(r'<!--\[if\b', raw, re.I):
                conditions.append(raw)
            elif re.match(r'(?:<!\[endif\]|<!--\[endif\])', raw, re.I):
                if not conditions:
                    raise ValueError('Unmatched conditional closing marker')
                conditions.pop()
            continue
        name_match = re.match(r'</?([^\s/>]+)', raw)
        tag = name_match.group(1).lower()
        item['tag'] = tag
        if raw.startswith('</'):
            matching = [i for i, identity in enumerate(stack) if nodes[identity]['tag'] == tag]
            if matching:
                cut = matching[-1]
                for identity in stack[cut:]:
                    nodes[identity]['end'] = end
                stack = stack[:cut]
            continue
        values, attrs = parse_attributes(raw, name_match.end())
        identity = f'node:{index}'
        item['node'] = identity
        nodes[identity] = dict(id=identity, tag=tag, start=start, end=end,
                               attrs=values,
                               text=[], parents=list(stack), conditional=bool(conditions),
                               protected=any(nodes[p]['tag'] in {'head', 'template', 'noscript'} for p in stack))
        item['attributes'] = attrs
        if tag not in VOID_TAGS and not raw.endswith('/>'):
            stack.append(identity)
    if conditions:
        raise ValueError('Unclosed conditional marker')
    return tokens, nodes


def functional_reason(node, nodes):
    href = node['attrs'].get('href', '')
    if protected_url(href):
        return 'dynamic expression or functional URL'
    context = html.unescape(' '.join(node['text']) + ' ' + ' '.join(
        value for owner in [node] + [nodes[p] for p in node['parents']]
        for key, value in owner['attrs'].items()
        if key.startswith('data-') or key in {'title', 'aria-label'}))
    if FUNCTIONAL.search(context) or re.search(r'\bevent\b', context, re.I):
        return 'functional label or metadata'
    return None


def analyse(source, protected_links=None):
    tokens, nodes = inspect_source(source)
    if protected_links is None:
        protected_links = {identity for identity, node in nodes.items()
                           if node['tag'] in LINK_TAGS and functional_reason(node, nodes)}
    result, fields = [], []
    for index, token in enumerate(tokens):
        raw = token['raw']
        if token['kind'] == 'text':
            ancestors = [nodes[p]['tag'] for p in token['parents']]
            editable = any(t in TEXT_TAGS for t in ancestors) and not any(t in {'head', 'template', 'noscript'} for t in ancestors)
            shape = text_shape(raw) if editable else ('fixed-text', raw)
            result.append(shape)
            if shape[0] == 'text':
                fields.append(dict(id=f'text:{index}', kind='text', before=raw,
                                   start=token['start'], end=token['end'], nodes=token['parents']))
            continue
        if 'node' not in token:
            result.append(('fixed', raw))
            continue
        node = nodes[token['node']]
        tag, pieces, end = node['tag'], [], 0
        for attr in token['attributes']:
            name, value = attr.group(1).lower(), attr.group(4)
            allowed = not node['protected'] and ((tag == 'img' and name in {'src', 'alt'}) or (tag in LINK_TAGS and name == 'href') or (tag == 'html' and not node['parents'] and name == 'lang'))
            if EXPR.search(html.unescape(value)) or name == 'href' and node['id'] in protected_links:
                allowed = False
            if not allowed:
                continue
            if name in {'href', 'src'} and not re.match(r'^(?:https?://|mailto:|tel:|/|#)', html.unescape(value).strip(), re.I):
                raise ValueError('Unsupported URL scheme in editable field')
            if name == 'lang' and not re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*', value):
                raise ValueError('Invalid language tag')
            if '<' in value or '>' in value:
                raise ValueError('Markup in editable attribute')
            fragment = value[value.index('#'):] if '#' in value else ''
            tracking = fragment if re.search(r'_msdynmkt_', html.unescape(fragment), re.I) else ''
            pieces.extend([raw[end:attr.start(4)], ('editable', name, tracking)])
            end = attr.end(4)
            fields.append(dict(id=f'attr:{index}:{name}', kind=name, before=value,
                               start=token['start'] + attr.start(4), end=token['start'] + attr.end(4),
                               nodes=node['parents'] + [node['id']]))
        pieces.append(raw[end:])
        result.append(('tag', tuple(pieces)))
    return dict(signature=result, fields=fields, nodes=nodes, protected_links=protected_links)


def counterpart_groups(document):
    """Use local wrapper boundaries before tracking IDs; never pair by URL alone."""
    nodes, groups = document['nodes'], []
    wrappers = {identity for identity, node in nodes.items()
                if set(node['attrs'].get('class', '').split()) & {'imageWrapper', 'buttonWrapper'}}
    buckets = {}
    for identity, node in nodes.items():
        if node['protected'] or node['tag'] not in LINK_TAGS | {'img'}:
            continue
        wrapper = next((p for p in reversed(node['parents']) if p in wrappers), None)
        tracking = node['attrs'].get('data-msdyn-tracking-id')
        if node['tag'] == 'img' and wrapper:
            key = ('image', wrapper)
        elif node['tag'] in LINK_TAGS and (wrapper or tracking):
            key = ('link', wrapper, tracking)
        else:
            continue
        buckets.setdefault(key, []).append(identity)
    for members in buckets.values():
        if len(members) > 1 and any(nodes[m]['conditional'] or nodes[m]['tag'].startswith('v:') for m in members):
            groups.append(members)
    return groups


def node_values(node):
    if node['tag'] == 'img':
        return {'src': node['attrs'].get('src'), 'alt': node['attrs'].get('alt')}
    return {'href': node['attrs'].get('href'),
            'label': ' '.join(html.unescape(''.join(node['text'])).split())}


def check_counterparts(before, after, extra_groups=()):
    groups = counterpart_groups(before) + list(extra_groups)
    for members in groups:
        old = [node_values(before['nodes'][m]) for m in members]
        new = [node_values(after['nodes'][m]) for m in members]
        for key in old[0]:
            if any(a[key] != b[key] for a, b in zip(old, new)):
                if len({v[key] for v in old}) != 1:
                    raise ValueError(f'Ambiguous Outlook counterparts ({key}): {members}')
                if len({v[key] for v in new}) != 1:
                    raise ValueError(f'Matching Outlook and standard content diverged ({key}): {members}')
    return groups


def structural_check(original, updated):
    before = analyse(original)
    after = analyse(updated, before['protected_links'])
    if before['signature'] != after['signature']:
        for index, (a, b) in enumerate(zip(before['signature'], after['signature'])):
            if a != b:
                raise ValueError(f'Protected source changed near token {index}; inspect the local diff')
        raise ValueError('Content or markup was added or removed')
    check_counterparts(before, after)
    return before, after


def inventory(original):
    document = analyse(original)
    nodes = document['nodes']
    return dict(version=1, source_sha256=digest(original), fields=document['fields'],
                links=[dict(id=n['id'], href=n['attrs'].get('href'),
                            label=''.join(n['text']), protected_reason=functional_reason(n, nodes),
                            metadata={k: v for k, v in n['attrs'].items() if k.startswith('data-')})
                       for n in nodes.values() if n['tag'] in LINK_TAGS and 'href' in n['attrs']],
                counterparts=counterpart_groups(document),
                conditional_nodes=[dict(id=n['id'], tag=n['tag'], values=node_values(n))
                                   for n in nodes.values() if n['tag'] in LINK_TAGS | {'img'}
                                   and (n['conditional'] or n['tag'].startswith('v:')) and not n['protected']])


def require_reason(record):
    if not isinstance(record.get('reason'), str) or not record['reason'].strip():
        raise ValueError('Every planned edit or counterpart decision needs a reason')


def planned_output(original, plan):
    if not isinstance(plan, dict) or plan.get('version') != 1 or plan.get('source_sha256') != digest(original):
        raise ValueError('Edit plan version or original source hash does not match')
    if plan.get('mode') not in {'translation', 'edit'} or not isinstance(plan.get('request'), str) or not plan['request'].strip():
        raise ValueError('Edit plan needs mode (translation/edit) and the user request')
    edits = plan.get('edits')
    if not isinstance(edits, list):
        raise ValueError('Edit plan needs an edits list')
    fields = {field['id']: field for field in analyse(original)['fields']}
    replacements, seen = [], set()
    for edit in edits:
        if not isinstance(edit, dict) or not isinstance(edit.get('id'), str):
            raise ValueError('Invalid edit record')
        require_reason(edit)
        identity = edit['id']
        if identity not in fields or identity in seen:
            raise ValueError(f'Unknown, protected or duplicate edit occurrence: {identity}')
        seen.add(identity)
        field = fields[identity]
        if edit.get('before') != field['before'] or not isinstance(edit.get('after'), str):
            raise ValueError(f'Original value or replacement missing for {identity}')
        if plan['mode'] == 'translation' and field['kind'] in {'href', 'src'}:
            raise ValueError('Translation plans cannot change destinations or image sources')
        if field['kind'] == 'href' and edit.get('purpose') != 'ordinary':
            raise ValueError('Destination edits require an explicit ordinary-link classification')
        replacements.append((field['start'], field['end'], edit['after']))
    updated = original
    for start, end, replacement in sorted(replacements, reverse=True):
        updated = updated[:start] + replacement + updated[end:]
    return updated


def review_counterparts(before, after, plan):
    extra, reviewed = [], set()
    decisions = plan.get('counterpart_decisions', [])
    if not isinstance(decisions, list):
        raise ValueError('counterpart_decisions must be a list')
    nodes = before['nodes']
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError('Invalid counterpart decision')
        require_reason(decision)
        members = decision.get('members')
        if not isinstance(members, list) or not members or any(not isinstance(m, str) or m not in nodes for m in members):
            raise ValueError('Counterpart decision needs valid node IDs')
        if len(set(members)) != len(members) or reviewed.intersection(members):
            raise ValueError('Duplicate counterpart decision')
        kinds = {nodes[m]['tag'] == 'img' for m in members}
        if len(kinds) != 1 or any(nodes[m]['tag'] not in LINK_TAGS | {'img'} or nodes[m]['protected'] for m in members):
            raise ValueError('Counterpart members must be comparable image or link nodes')
        if decision.get('type') == 'group' and len(members) > 1:
            extra.append(members)
        elif decision.get('type') != 'standalone' or len(members) != 1:
            raise ValueError('Use group for counterparts or standalone for one reviewed occurrence')
        reviewed.update(members)
    groups = check_counterparts(before, after, extra)
    covered = {m for group in groups for m in group}
    for identity, node in nodes.items():
        if node['tag'] not in LINK_TAGS | {'img'} or node['protected']:
            continue
        if node_values(node) == node_values(after['nodes'][identity]):
            continue
        # Every changed image/link must be mapped or explicitly reviewed as standalone.
        if identity not in covered | reviewed:
            raise ValueError(f'Unresolved counterpart for changed occurrence {identity}; inspect and record a decision')


def validate(original, updated, plan=None):
    """Without a plan this API performs structural checks ONLY (legacy test callers)."""
    before, after = structural_check(original, updated)
    if plan is not None:
        if planned_output(original, plan) != updated:
            raise ValueError('Output differs from the exact request-scoped edit plan')
        review_counterparts(before, after, plan)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('updated', nargs='?', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--inventory', action='store_true')
    mode.add_argument('--structural-only', action='store_true')
    mode.add_argument('--plan', type=Path)
    mode.add_argument('--apply-plan', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        original = args.original.read_bytes().decode('utf-8')
        if args.inventory:
            if args.updated or args.output:
                raise ValueError('--inventory only takes the original file')
            print(json.dumps(inventory(original), ensure_ascii=False, indent=2))
            return 0
        plan_path = args.plan or args.apply_plan
        if not plan_path and not args.structural_only:
            raise ValueError('Use --plan EDITS.json; --structural-only is diagnostic and does not verify request scope')
        plan = json.loads(plan_path.read_text(encoding='utf-8')) if plan_path else None
        if plan_path and not isinstance(plan, dict):
            raise ValueError('Edit plan must be a JSON object')
        if args.apply_plan:
            if not args.output or args.updated:
                raise ValueError('--apply-plan requires --output NEW.html and no updated positional file')
            updated = planned_output(original, plan)
        else:
            if not args.updated or args.output:
                raise ValueError('Validation requires original and updated files, without --output')
            updated = args.updated.read_bytes().decode('utf-8')
        validate(original, updated, plan)
        if args.apply_plan:
            # Exclusive creation prevents accidental overwrite of the original or prior output.
            with args.output.open('xb') as output:
                output.write(updated.encode('utf-8'))
    except (ValueError, OSError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    if args.structural_only:
        print('STRUCTURAL ONLY: source-preservation checks passed; request scope and unresolved counterparts NOT verified')
    else:
        print('PASS: exact edit plan, protected source and counterpart checks; meaning, request interpretation and rendering still require review')
    return 0


if __name__ == '__main__':
    sys.exit(main())
