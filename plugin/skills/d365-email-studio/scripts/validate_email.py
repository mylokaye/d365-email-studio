#!/usr/bin/env python3
"""Conservative source-preservation guard; no DOM serialization or dependencies."""
import html
import re
import sys
import unicodedata
from pathlib import Path

TOKEN = re.compile(r'<!-->|<!--\[if\b[^>]*>|<!\[endif\]-->|<!--\[endif\]---->|<!--.*?-->|<![^>]*>|</?[A-Za-z][^>"\']*(?:(?:"[^"]*"|\'[^\']*\')[^>"\']*)*>', re.S | re.I)
ATTR = re.compile(r'([^\s=<>/]+)(\s*=\s*)(["\'])(.*?)\3', re.S)
EXPR = re.compile(r'{{.*?}}|{%.*?%}|\$\{.*?}', re.S)
SPACER = re.compile(r'(?:&(?:nbsp|#160|#x[aA]0);|[\u00a0\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff])')
TEXT_TAGS = {'p', 'span', 'a', 'center', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'div', 'strong', 'em', 'b', 'i', 'u', 's', 'v:textbox'}


def protected_url(value):
    value = html.unescape(value)
    return bool(EXPR.search(value) or re.search(r'mkt\.dynamics\.com|preferencecenter|unsubscribe|eventmanagement', value, re.I))


def text_shape(value):
    if '<' in value:
        raise ValueError('Unrecognized markup in text')
    if not html.unescape(value).strip():
        return ('fixed-text', value)
    # Keep edge whitespace, expressions, padding entities and invisible chars exact.
    leading = value[:len(value) - len(value.lstrip())]
    trailing = value[len(value.rstrip()):]
    fixed_pattern = re.compile(EXPR.pattern + '|' + SPACER.pattern, re.S)
    parts = fixed_pattern.split(value)
    # Preserve a meaningful run on each side of protected tokens and padding.
    def visible(run):
        return any(not c.isspace() and unicodedata.category(c)[0] not in {'C', 'Z'} for c in html.unescape(run))
    fixed = tuple(m.group() for m in fixed_pattern.finditer(value))
    runs = tuple(visible(run) for run in parts)
    if not visible(value) and not fixed:
        return ('fixed-text', value)
    return ('text', leading, trailing, fixed, runs)



def signature(source):
    result = []
    stack = []
    position = 0
    def data(value):
        editable = bool(stack and any(t in TEXT_TAGS for t in stack) and not any(t in {'head', 'style', 'script', 'title'} for t in stack))
        result.append(text_shape(value) if editable else ('fixed-text', value))
    for match in TOKEN.finditer(source):
        data(source[position:match.start()])
        token = match.group()
        position = match.end()
        if token.startswith('<!'):
            result.append(('fixed', token))
            continue
        name_match = re.match(r'</?([^\s/>]+)', token)
        tag = name_match.group(1).lower()
        closing = token.startswith('</')
        if closing:
            result.append(('fixed', token))
            if tag in stack:
                stack = stack[:len(stack) - 1 - stack[::-1].index(tag)]
            continue
        pieces = []
        end = 0
        for attr in ATTR.finditer(token, name_match.end()):
            name, value = attr.group(1).lower(), attr.group(4)
            allowed = ((tag == 'img' and name in {'src', 'alt'}) or (tag in {'a', 'v:shape', 'v:roundrect'} and name == 'href') or (tag == 'html' and name == 'lang'))
            if EXPR.search(value) or (name == 'href' and protected_url(value)):
                allowed = False
            if allowed:
                if name in {'href', 'src'}:
                    decoded = html.unescape(value).strip()
                    if not re.match(r'^(?:https?://|mailto:|tel:|/|#)', decoded, re.I):
                        raise ValueError('Unsupported replacement URL scheme')
                if name == 'lang' and not re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*', value):
                    raise ValueError('Invalid language tag')
                if '<' in value or '>' in value:
                    raise ValueError('Markup in editable attribute')
                # Dynamics stores tracking fields in the URL fragment, not just attributes.
                # Keep the entire original fragment verbatim when it contains them.
                fragment = value[value.index('#'):] if '#' in value else ''
                tracking = fragment if re.search(r'_msdynmkt_', html.unescape(fragment), re.I) else ''
                pieces.extend([token[end:attr.start(4)], ('editable', name, tracking)])
                end = attr.end(4)
        pieces.append(token[end:])
        result.append(('tag', tuple(pieces)))
        if tag not in {'img', 'br', 'hr', 'meta', 'link', 'input', 'w:anchorlock', 'o:allowpng'} and not token.endswith('/>'):
            stack.append(tag)
    data(source[position:])
    return result


def attribute(tag, name):
    for match in ATTR.finditer(tag):
        if match.group(1).lower() == name:
            return match.group(4)
    return None


def counterpart_values(source):
    """Recognize source-specific adjacent image fallbacks and tracking-linked buttons.

    Other fallback patterns still require manual review.
    """
    pairs = []
    for wrapper in re.finditer(r'<div\b[^>]*class=["\'][^"\']*imageWrapper[^"\']*["\'][^>]*>(.*?)</div>', source, re.S | re.I):
        images = re.findall(r'<img\b[^>]*>', wrapper.group(1), re.S | re.I)
        if len(images) == 2:
            for name in ('src', 'alt'):
                pairs.append(tuple(attribute(image, name) for image in images))
    buttons = {}
    for match in re.finditer(r'<(v:shape|a)\b([^>]*data-msdyn-tracking-id[^>]*)>(.*?)</\1>', source, re.S | re.I):
        tag = '<' + match.group(1) + match.group(2) + '>'
        identity = attribute(tag, 'data-msdyn-tracking-id')
        label = re.sub(r'<[^>]*>', '', match.group(3))
        buttons.setdefault(identity, []).append((attribute(tag, 'href'), label))
    for values in buttons.values():
        if len(values) == 2:
            pairs.extend(zip(*values))
    return pairs


def check_counterparts(original, updated):
    before, after = counterpart_values(original), counterpart_values(updated)
    if len(before) != len(after):
        raise ValueError('Recognized Outlook counterpart grouping changed')
    for old, new in zip(before, after):
        if old[0] == old[1] and new[0] != new[1]:
            raise ValueError('Matching Outlook and standard content diverged')


def validate(original, updated):
    before, after = signature(original), signature(updated)
    check_counterparts(original, updated)
    if before != after:
        for index, (a, b) in enumerate(zip(before, after)):
            if a != b:
                raise ValueError(f'Protected source changed near token {index}; inspect the local diff')
        raise ValueError('Content or markup was added or removed')


def main():
    if len(sys.argv) != 3:
        print('Usage: validate_email.py ORIGINAL.html UPDATED.html', file=sys.stderr)
        return 2
    try:
        original, updated = [Path(p).read_bytes().decode('utf-8') for p in sys.argv[1:]]
        validate(original, updated)
    except (ValueError, OSError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    print('PASS: source-preservation allowlist; semantic and Outlook counterpart review still required')
    return 0

if __name__ == '__main__':
    sys.exit(main())
