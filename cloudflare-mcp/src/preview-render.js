import DOMPurify from 'dompurify';
import { IMAGE_ORIGINS } from './image-policy.js';

// These transformations affect only the display copy. The original output
// bytes are kept separately and are the only bytes offered for download.
const properties = /^(?:color|background-color|font(?:-family|-size|-style|-weight|-variant)?|line-height|letter-spacing|word-spacing|text-(?:align|decoration(?:-color|-line|-style)?|transform|indent|overflow)|white-space|word-break|overflow-wrap|display|width|height|min-width|max-width|min-height|max-height|margin(?:-top|-right|-bottom|-left)?|padding(?:-top|-right|-bottom|-left)?|border(?:-collapse|-spacing|-radius|-(?:top|right|bottom|left)(?:-width|-style|-color)?|-width|-style|-color)?|box-sizing|vertical-align|table-layout|overflow(?:-x|-y)?|opacity|direction|list-style-type)$/;
export function safeImageUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : '';
  } catch { return ''; }
}
function permittedImage(value, blockedOrigins) {
  const url = safeImageUrl(value);
  if (!url) return '';
  const origin = new URL(url).origin;
  if (IMAGE_ORIGINS.includes(origin)) return url;
  blockedOrigins.add(origin);
  return '';
}
export function safeDeclarations(style, blockedOrigins = new Set()) {
  const declarations = [];
  for (const property of Array.from(style)) {
    const value = style.getPropertyValue(property);
    if (property === 'background-image') {
      const match = /^url\(["']?(https:\/\/[^"'()\\\s]+)["']?\)$/i.exec(value);
      const url = match && permittedImage(match[1], blockedOrigins);
      if (url) declarations.push(`background-image:url("${url}")`);
    } else if (/^background-(?:size|position|repeat|origin|clip|attachment)$/.test(property) && !/[\\@]|\/\*|(?:url|image-set|expression|var|attr)\s*\(/i.test(value)) {
      declarations.push(`${property}:${value}`);
    } else if (properties.test(property) && !/[\\@]|\/\*|(?:url|image-set|expression|var|attr)\s*\(/i.test(value)) {
      declarations.push(`${property}:${value}${style.getPropertyPriority(property) ? ' !important' : ''}`);
    }
  }
  return declarations.join(';');
}
function safeRules(rules, blockedOrigins) {
  let css = '';
  for (const rule of Array.from(rules)) {
    if (rule.type === 1) css += `${rule.selectorText}{${safeDeclarations(rule.style, blockedOrigins)}}`;
    else if (rule.type === 4) css += `@media ${rule.conditionText}{${safeRules(rule.cssRules, blockedOrigins)}}`;
  }
  return css;
}

export function renderEmail(root, html, onImageError = () => {}) {
  const blockedOrigins = new Set();
  const sanitized = DOMPurify.sanitize(html, {
    WHOLE_DOCUMENT: true,
    RETURN_DOM: true,
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'select', 'textarea', 'link', 'meta', 'base', 'svg', 'math', 'video', 'audio', 'source'],
    FORBID_ATTR: ['srcset', 'href', 'xlink:href', 'poster', 'background', 'action', 'formaction', 'ping', 'autofocus', 'contenteditable', 'is', 'attributionsrc'],
  });
  for (const element of sanitized.querySelectorAll('[src]')) {
    const url = element.localName === 'img' && permittedImage(element.getAttribute('src'), blockedOrigins);
    if (url) {
      element.setAttribute('referrerpolicy', 'no-referrer');
      element.setAttribute('src', url);
      element.addEventListener('error', () => { if (root.contains(element)) onImageError(); }, { once: true });
    } else element.removeAttribute('src');
  }
  const styles = [];
  for (const element of sanitized.querySelectorAll('style')) {
    // Constructed sheets parse without fetching imported sheets. Only ordinary
    // style rules and media groups survive; only HTTPS background images survive.
    if (typeof CSSStyleSheet !== 'undefined' && CSSStyleSheet.prototype.replaceSync) {
      const sheet = new CSSStyleSheet();
      sheet.replaceSync(element.textContent);
      const style = document.createElement('style');
      style.textContent = safeRules(sheet.cssRules, blockedOrigins);
      styles.push(style);
    }
    element.remove();
  }
  for (const element of sanitized.querySelectorAll('[style]')) {
    const css = safeDeclarations(element.style, blockedOrigins);
    if (css) element.setAttribute('style', css);
    else element.removeAttribute('style');
  }
  const reset = document.createElement('style');
  reset.textContent = ':host{display:block;color:#111;background:white;font:16px Arial,sans-serif}body{display:block;margin:8px}img{max-width:100%}a{cursor:default}';
  const body = sanitized.querySelector('body') || sanitized;
  root.replaceChildren(reset, ...styles, body);
  return { blockedOrigins: [...blockedOrigins] };
}
