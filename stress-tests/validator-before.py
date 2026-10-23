#!/usr/bin/env python3
"""Conservative source-preservation guard; no DOM serialization or dependencies."""
import html
import re
import sys
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
    fixed = [(m.start(), m.end(), m.group()) for pattern in (EXPR, SPACER) for m in pattern.finditer(value)]
    fixed.sort()
    return ('text', leading, trailing, tuple(x[2] for x in fixed))


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
                pieces.extend([token[end:attr.start(4)], ('editable', name)])
                end = attr.end(4)
        pieces.append(token[end:])
        result.append(('tag', tuple(pieces)))
        if tag not in {'img', 'br', 'hr', 'meta', 'link', 'input', 'w:anchorlock', 'o:allowpng'} and not token.endswith('/>'):
            stack.append(tag)
    data(source[position:])
    return result


def validate(original, updated):
    before, after = signature(original), signature(updated)
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
