import re
import sys

from jinja2 import Environment, FileSystemLoader

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def load_cv(fn):
    with open(fn, "rb") as f:
        cv = tomllib.load(f)
    _strip_newlines(cv)
    return cv


def _strip_newlines(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = _strip_newlines(v)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = _strip_newlines(item)
    elif isinstance(obj, str):
        return obj.strip().replace('\n', ' ')
    return obj


def ordered(val):
    if isinstance(val, str):
        return val
    if len(val) == 0:
        return ''
    elif len(val) == 1:
        return val[0]
    elif len(val) == 2:
        return '%s and %s' % (val[0], val[1])
    else:
        expanded = ''
        for it in val[:-1]:
            expanded += '%s, ' % it
        expanded += 'and %s' % val[-1]
        return expanded


def conference(venue, year):
    return "%s %s" % (venue, year)


MDLINK_RE = re.compile(r'\[([^\]]*)\]\(([^)]*)\)')


def expand_md_links(s, target):
    if target == 'tex':
        return MDLINK_RE.sub(r'\\href{\2}{\1}', s)
    else:
        return MDLINK_RE.sub(r'<a href="\2" target="_blank">\1</a>', s)


def resolve_references(node, root=None):
    """Resolve EVENT(...) and ITEM... references in all string values."""
    if root is None:
        root = node
    if isinstance(node, dict):
        return {k: resolve_references(v, root) for k, v in node.items()}
    elif isinstance(node, list):
        return [resolve_references(item, root) for item in node]
    elif isinstance(node, str):
        return _resolve_in_str(node, root)
    return node


def _resolve_in_str(s, root):
    """Resolve ITEM... and EVENT(...) macros within a single string."""
    # First pass: ITEM.key.path
    while True:
        m = re.search(r'ITEM\.([a-z0-9_]+(?:\.[a-z0-9_]+)*)', s)
        if not m:
            break
        key = m.group(1).split('.')
        val = root
        for k in key:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                val = None
                break
        if isinstance(val, str):
            s = s[:m.start()] + val + s[m.end():]
        else:
            break
    # Second pass: EVENT(venue, year)
    while True:
        m = re.search(r'EVENT\((.+?),(\d{4})\)', s)
        if not m:
            break
        venue_raw = m.group(1).strip()
        year = m.group(2)
        venue_raw = _resolve_in_str(venue_raw, root)
        resolved = conference(venue_raw, year)
        s = s[:m.start()] + resolved + s[m.end():]
    return s


# Jinja2 environment (module-level so filters/decorators work)
_env = Environment(
    loader=FileSystemLoader('.'),
    block_start_string='<&',
    block_end_string='&>',
    variable_start_string='<<',
    variable_end_string='>>',
    comment_start_string='<#',
    comment_end_string='#>',
    autoescape=False,
)
_env.filters['ordered'] = ordered


def main():
    target = sys.argv[1]
    cv_fn = sys.argv[2]
    template_fn = sys.argv[3]
    out_fn = sys.argv[4]

    cv = load_cv(cv_fn)
    cv = resolve_references(cv)

    template = _env.get_template(template_fn)
    output = template.render(cv=cv, target=target)

    # Expand markdown links in the final output
    output = expand_md_links(output, target)

    if target == 'html':
        output = re.sub(r' \(\)', '', output)
        output = re.sub(r'\.\.', '.', output)

    with open(out_fn, 'w') as f:
        f.write(output)
        if not output.endswith('\n'):
            f.write('\n')


if __name__ == '__main__':
    main()
