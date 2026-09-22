"""Build the blog.

Each post is a Markdown file in blog/ named YYYY-MM-DD-short-title.md, where
the publication date is taken from the file name and the short title from the
"title" field of the front matter (falling back to the file name). For
example, blog/2026-09-20-hello-world.md is published at
/blog/2026-09-20-hello-world and linked from the index at /blog. A post with
a "staging" field in its front matter (a hex string encoding 16 random
bytes) is instead published at /blog/<staging>-<short-title>, with the date
replaced by the token, and is left out of the index.

LaTeX math is rendered to MathML at build time: $x^2$ for inline math and
$$x^2$$ for display math. Non-Markdown files in blog/ (images, etc.) are
copied to public/blog/ as-is; refer to them from posts with paths relative
to blog/ (e.g. ![alt](img/foo.png)).
"""

import os
import re
import shutil
from datetime import date

from latex2mathml.converter import convert as latex2mathml
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

from gen_resume import _env

BLOG_DIR = "blog"
OUT_DIR = os.path.join("public", "blog")
SITE = "https://cjpatton.net"

POST_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
RELATIVE_URL_RE = re.compile(r'(src|href)="(?!/|#|[a-z][a-z0-9+.-]*:)([^"]*)"')

# References. A post may end with a "## References" section listing entries
# like "- [BR93] M. Bellare and P. Rogaway. Random Oracles Are Practical.
# CCS 1993." Cite them in the body with "[BR93]" (or a comma-separated list
# like "[BR93,BR24]", in the spirit of LaTeX's \cite{}), which renders as
# link(s) to the reference(s) at the bottom of the page.
REFS_HEADING_RE = re.compile(r"^##\s+References\s*$", re.MULTILINE)
REFS_ENTRY_RE = re.compile(r"^[-*] \[([A-Za-z0-9._+-]+)\] (.*)$")
CITE_RE = re.compile(r"\[([A-Za-z0-9._+-]+(?:,\s*[A-Za-z0-9._+-]+)*)\]")


def _excerpt(body):
    """Plain-text excerpt from the first paragraph, for meta tags."""
    para = ""
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if chunk:
            para = chunk
            break
    para = re.sub(r"^#+\s*", "", para)                       # headings
    para = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", para)    # images
    para = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", para)     # links
    para = re.sub(r"[*`_]", "", para)                        # emphasis, code
    para = re.sub(r"\s+", " ", para).strip()
    if len(para) > 160:
        para = para[:160].rsplit(" ", 1)[0] + "..."
    return para


def _load_post(path):
    with open(path) as f:
        raw = f.read()

    meta, body = {}, raw
    m = FRONT_MATTER_RE.match(raw)
    if m:
        body = raw[m.end():]
        for line in m.group(1).split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip().lower()] = val.strip()

    return meta, body


def _math_inline(self, tokens, idx, options, env):
    return latex2mathml(tokens[idx].content, display="inline")


def _math_block(self, tokens, idx, options, env):
    return latex2mathml(tokens[idx].content, display="block")


def _ref_link(state, silent):
    """Inline rule for citations: [BR93] or [BR93,BR24]."""
    m = CITE_RE.match(state.src, state.pos)
    if not m:
        return False
    refs = (state.env or {}).get("refs", ())
    labels = [label.strip() for label in m.group(1).split(",")]
    if any(label not in refs for label in labels):
        return False
    if not silent:
        token = state.push("ref_link", "", 0)
        token.content = ",".join(labels)
    state.pos = m.end()
    return True


def _ref_link_html(self, tokens, idx, options, env):
    parts = ",".join(
        f'<a class="ref" href="#ref-{label}">{label}</a>'
        for label in tokens[idx].content.split(",")
    )
    return f"[{parts}]"


_md = MarkdownIt("commonmark").use(dollarmath_plugin)
_md.enable(["table", "strikethrough"])
_md.inline.ruler.after("link", "ref_link", _ref_link)
_md.add_render_rule("math_inline", _math_inline)
_md.add_render_rule("math_block", _math_block)
_md.add_render_rule("ref_link", _ref_link_html)


def _split_refs(body):
    """Split a trailing "## References" section off of the post body.

    Returns (body, entries), where entries is a list of (label, text). If
    there is no References section with entries, returns (body, []).
    """
    m = None
    for m in REFS_HEADING_RE.finditer(body):
        pass
    if m is None:
        return body, []

    entries = []
    label, text = None, ""
    for line in body[m.end():].split("\n"):
        em = REFS_ENTRY_RE.match(line)
        if em:
            if label:
                entries.append((label, text))
            label, text = em.group(1), em.group(2)
        elif label is not None and line[:1] in (" ", "\t") and line.strip():
            text += " " + line.strip()    # indented continuation line
    if label:
        entries.append((label, text))

    if not entries:
        return body, []
    return body[:m.start()], entries


def _render_refs(entries):
    """Render the References section, one anchor per entry."""
    items = []
    for label, text in entries:
        # Rendered without "refs" in env, so labels stay literal here.
        desc = _md.renderInline(text, {})
        items.append(f'<li id="ref-{label}"><span class="ref-label">[{label}]</span> {desc}</li>')
    return '<h2>References</h2>\n<ul class="refs">\n' + "\n".join(items) + "\n</ul>"


def _rewrite_urls(html):
    return RELATIVE_URL_RE.sub(r'\1="/blog/\2"', html)


def _render_markdown(text, refs=()):
    """Render Markdown to HTML, including LaTeX math.

    Relative links and images are rewritten relative to /blog/, so that
    they resolve no matter how the URL of the page is written. Citations of
    "refs" labels render as links to the References section.
    """
    return _rewrite_urls(_md.render(text, {"refs": set(refs)}))


def load_posts():
    posts = []
    if os.path.isdir(BLOG_DIR):
        for fn in sorted(os.listdir(BLOG_DIR)):
            m = POST_RE.match(fn)
            if not m or not os.path.isfile(os.path.join(BLOG_DIR, fn)):
                continue
            try:
                pub = date(*map(int, m.group(1, 2, 3)))
            except ValueError as e:
                raise SystemExit(f"{fn}: bad publication date: {e}")
            meta, body = _load_post(os.path.join(BLOG_DIR, fn))
            body, refs = _split_refs(body)
            slug = m.group(4)

            # A staging post is published at an unpredictable URL (the date
            # replaced by a random token) and left out of the blog index.
            staging = meta.get("staging")
            if staging is not None:
                if not re.fullmatch(r"[0-9a-f]{32}", staging):
                    raise SystemExit(
                        f"{fn}: staging must be 32 lowercase hex characters "
                        "(16 bytes), e.g. openssl rand -hex 16")
            stem = staging if staging else pub.isoformat()

            url = f"/blog/{stem}-{slug}"
            html = _render_markdown(body, (label for label, _ in refs))
            if refs:
                html += "\n" + _rewrite_urls(_render_refs(refs))
            posts.append({
                "slug": slug,
                "stem": stem,
                "staging": staging,
                "url": url,
                "og_url": SITE + url,
                "title": meta.get("title", slug.replace("-", " ").title()),
                "date_iso": pub.isoformat(),
                "date_pretty": f"{pub.day} {pub.strftime('%B')} {pub.year}",
                "excerpt": meta.get("description") or _excerpt(body),
                "html": html,
            })
    posts.sort(key=lambda p: (p["date_iso"], p["slug"]), reverse=True)
    return posts


def copy_assets():
    for root, dirs, files in os.walk(BLOG_DIR):
        for fn in files:
            if fn.endswith(".md"):
                continue
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, BLOG_DIR)
            dst = os.path.join(OUT_DIR, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


def write_page(template, out_fn, **ctx):
    out = _env.get_template(template).render(**ctx)
    with open(out_fn, "w") as f:
        f.write(out)
        if not out.endswith("\n"):
            f.write("\n")


def main():
    posts = load_posts()

    shutil.rmtree(OUT_DIR, ignore_errors=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    for p in posts:
        fn = f"{p['stem']}-{p['slug']}.html"
        write_page("t.post.html", os.path.join(OUT_DIR, fn), post=p, site=SITE)
        note = " (staging)" if p["staging"] else ""
        print(f"blog: {p['date_iso']}-{p['slug']}.md -> {fn}{note}")

    published = [p for p in posts if not p["staging"]]
    write_page("t.blog.html", os.path.join(OUT_DIR, "index.html"), posts=published, site=SITE)
    print(f"blog: {len(published)} post(s) in index, {len(posts) - len(published)} staging, "
          f"index at {os.path.join(OUT_DIR, 'index.html')}")

    copy_assets()


if __name__ == "__main__":
    main()
