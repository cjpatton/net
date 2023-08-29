import json
import re
import sys

LPAR = '('
RPAR = ')'
PARSEP = ','
KEYSEP = '.'

## Regular expressions
RUNE_re = "([a-z0-9_]+)"
KEY_re = "(\%s%s)+" % (KEYSEP, RUNE_re)

ITEM_prog = re.compile("ITEM%s" % KEY_re)
KEY_prog = re.compile(KEY_re)
LIST_prog = re.compile("LIST%s" % KEY_re)
LIT_prog = re.compile("LIT%s" % KEY_re)
LOR_prog = re.compile("LOR%s" % KEY_re)
ORDERED_prog = re.compile("ORDERED%s" % KEY_re)

## Parsers
class Err(BaseException):
    def __init__(self, S):
        self.S = S
    def __str__(self):
        return self.S

def err(S):
    raise Err(S)

def parseKey(S):
    # Seek to beginning of key.
    off = 0
    while S[off] != KEYSEP:
        off += 1
    m = KEY_prog.match(S[off:])
    key = []
    if m:
        idx = off
        prev = off
        for c in S[off+1:off+m.end()]+KEYSEP:
            idx += 1
            if c == KEYSEP:
                key.append(S[prev+1:idx])
                prev = idx
        return key
    err("syntax: couldn't parse key")

def parseArgs(S, expectedCount):
    if S[0] != LPAR:
        err("syntax: missing left paranthesis")
    lv = 0
    idx = 0
    arg_ends = [1]
    for c in S:
        idx += 1
        if c == LPAR:
            lv += 1
        elif c == RPAR:
            lv -= 1
        elif c == PARSEP and lv == 1:
            arg_ends.append(idx)
        if lv == 0:
            arg_ends.append(idx)
            args = []
            for i in range(len(arg_ends)-1):
                args.append(S[arg_ends[i]:arg_ends[i+1]-1])
            if len(args) != expectedCount:
                err("expected %s arguments, got %s" % (
                    expectedCount, len(args)))
            return args, idx
    err("syntax: missing right paranthesis")

## Expanders
def ordered(val):
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

def get(D, K):
    if len(K) == 0:
        return D
    return get(D.get(K[0]), K[1:])

def processListItemArg(D, arg):
    # Process list items.
    for m in reversed(list(LIT_prog.finditer(arg))):
        key = parseKey(m.group(0))
        val = get(D, key)
        if val == None:
            val = ""
        arg = arg[:m.start()] + val + arg[m.end():]

    # Process list ordered lists.
    for m in reversed(list(LOR_prog.finditer(arg))):
        key = parseKey(m.group(0))
        val = get(D, key)
        if val == None:
            val = ""
        arg = arg[:m.start()] + ordered(val) + arg[m.end():]

    return arg



# Expander for LaTeX documents. This assumes the following macro is defined:
# \newcommand{\cvitem}[6]{ ... }
class TexExpander:
    def Conference(self, args):
        if len(args[1]) != 4: # year
            err("unexpected year length")
        return "%s %s" % (args[0], args[1])

    def List(self, args, key, D):
        expanded = ""
        for val in get(D, key):
            expanded += "%s\n" % self.ListItem(args, val)
        return expanded

    def ListItem(self, args, D):
        expanded = '\\cventry'
        for arg in args:
            expanded += "{%s}" % processListItemArg(D, arg)
        return expanded

    def Link(self, text, url):
        return '\\href{%s}{%s}' % (url, text)

    def Ordered(self, key, D):
        val = get(D, key)
        return ordered(val)

    def Post(self, I):
        return I

# Expander for HTML documents.
class HtmlExpander:
    def Conference(self, args):
        if len(args[1]) != 4: # year
            err("unexpected year length")
        return "%s %s" % (args[0], args[1])

    def List(self, args, key, D):
        # The first argument is interpreted as the tabbing.
        expanded = "%s<ul>\n" % args[0]
        for val in get(D, key):
            expanded += "%s  <li>%s</li>\n" % (
                args[0], self.ListItem(args[1:], val))
        expanded += "%s</ul>" % args[0]
        return expanded

    def ListItem(self, args, D):
        x = []
        for arg in args:
            x.append(processListItemArg(D, arg))
        expanded = '' if len(x[0]) == 0 else '<b>%s</b> ' % x[0]
        expanded += '' if len(x[1]) == 0  else '%s. ' % x[1]
        expanded += '' if len(x[2]) == 0 else '%s. ' % x[2]
        expanded += '' if len(x[3]) == 0 else '%s.' % x[3]
        return expanded

    def Link(self, text, url):
        return '<a href="%s" target="_blank">%s</a>' % (url, text)

    def Ordered(self, key, D):
        val = get(D, key)
        return ordered(val)

    def Post(self, I):
        # Remove undefined links.
        I = re.sub(' \(\)', '', I)
        # Remove double periods.
        I = re.sub('\.\.', '.', I)
        return I

expanders = {
    "tex": TexExpander(),
    "html": HtmlExpander()
}

## Main
target = sys.argv[1]      # e.g., tex
cv_fn = sys.argv[2]       # e.g., resume.json
template_fn = sys.argv[3] # e.g., t.patton.tex
out_fn = sys.argv[4]      # e.g., build/patton.tex

cv = json.load(open(cv_fn))
I = open(template_fn).read()
e = expanders[target]

# Expand macros. Because we're not parsing a real grammar and just matching
# regular expressions, the order of operations is very important. The following
# items are done first.
#
# LIST
for m in reversed(list(LIST_prog.finditer(I))):
    key = parseKey(m.group(0))
    args, n = parseArgs(I[m.end(0):], 6)
    expanded = e.List(args, key, cv)
    I = I[:m.start()] + expanded + I[m.end()+n:]

# ORDERED
for m in reversed(list(ORDERED_prog.finditer(I))):
    key = parseKey(m.group(0))
    expanded = e.Ordered(key, cv)
    I = I[:m.start()] + expanded + I[m.end():]

# Done second.
#
# ITEM
for m in reversed(list(ITEM_prog.finditer(I))):
    key = parseKey(m.group(0))
    expanded = get(cv, key)
    I = I[:m.start()] + expanded + I[m.end():]

# Done third.
#
# EVENT
for m in reversed(list(re.finditer('EVENT', I))):
    args, n = parseArgs(I[m.end(0):], 2)
    expanded = e.Conference(args)
    I = I[:m.start()] + expanded + I[m.end()+n:]

# Markdown-style links
MDLINK_prog = re.compile("\[([^\]]*)\]\(([^\)]*)\)")
for m in reversed(list(MDLINK_prog.finditer(I))):
    expanded = e.Link(m.group(1), m.group(2))
    I = I[:m.start()] + expanded + I[m.end():]

# Post processing
I = e.Post(I)

open(out_fn, 'w').write(I)
