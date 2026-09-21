"""Build the blog.

Each post is a Markdown file in blog/ named YYYY-MM-DD-short-title.md, where
the publication date is taken from the file name and the short title from the
"title" field of the front matter (falling back to the file name). For
example, blog/2026-09-20-hello-world.md is published at
/blog/2026-09-20-hello-world and linked from the index at /blog.

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


_md = MarkdownIt("commonmark").use(dollarmath_plugin)
_md.enable(["table", "strikethrough"])
_md.add_render_rule("math_inline", _math_inline)
_md.add_render_rule("math_block", _math_block)


def _render_markdown(text):
    """Render Markdown to HTML, including LaTeX math.

    Relative links and images are rewritten relative to /blog/, so that
    they resolve no matter how the URL of the page is written.
    """
    html = _md.render(text)
    return RELATIVE_URL_RE.sub(r'\1="/blog/\2"', html)


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
            slug = m.group(4)
            url = f"/blog/{pub.isoformat()}-{slug}"
            posts.append({
                "slug": slug,
                "url": url,
                "og_url": SITE + url,
                "title": meta.get("title", slug.replace("-", " ").title()),
                "date_iso": pub.isoformat(),
                "date_pretty": f"{pub.day} {pub.strftime('%B')} {pub.year}",
                "excerpt": meta.get("description") or _excerpt(body),
                "html": _render_markdown(body),
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
        fn = f"{p['date_iso']}-{p['slug']}.html"
        write_page("t.post.html", os.path.join(OUT_DIR, fn), post=p, site=SITE)
        print(f"blog: {p['date_iso']}-{p['slug']}.md -> {fn}")

    write_page("t.blog.html", os.path.join(OUT_DIR, "index.html"), posts=posts, site=SITE)
    print(f"blog: {len(posts)} post(s), index at {os.path.join(OUT_DIR, 'index.html')}")

    copy_assets()


if __name__ == "__main__":
    main()
