# AGENTS.md

Personal site of Christopher Patton, <https://cjpatton.net>, served by a
Cloudflare Worker with static assets.

## Build and verify

Run `make` after any change; it must succeed. It assembles `public/` from
`static/` (copied as-is), `resume.toml` (main page and CV PDF, via
`gen_resume.py` and LaTeX), and the Markdown posts in `blog/` (via
`gen_blog.py`). `make clean` removes all of `public/`.

Requires Python 3.9+ (`pip install -r requirements.txt`) and LaTeX
(`moderncv`); Node.js (`npm install`) is only needed for `npx wrangler`.

To preview, run `npx wrangler dev` and spot-check `http://localhost:8787/`,
`/blog`, a post URL (e.g. `/blog/2026-09-20-hello-world`), and `/style.css`.

## Conventions

- The site is plain HTML/CSS with **no JavaScript**. LaTeX math is rendered to
  MathML at build time, not on the client. Do not add client-side JS.
- `public/` is generated and git-ignored. Never commit or hand-edit it;
  re-run `make` instead.
- Templates `t.*.html` are Jinja with custom delimiters (`<& &>`, `<< >>`,
  `<# #>`), so they can hold raw HTML, CSS, and LaTeX. Shared styles are in
  `static/style.css`.
- Use f-strings for string formatting in Python.
- Blog posts are `blog/YYYY-MM-DD-short-title.md` (publication date and slug
  come from the file name), with optional `title:` and `description:` front
  matter. Posts support `$x^2$` / `$$x^2$$` math, images with paths relative
  to `blog/` (e.g. `img/foo.png`), and citations `[BR93]` or `[BR93,Mer87]`
  that link to a trailing `## References` section.
  `blog/2026-09-20-hello-world.md` is a living example of the syntax.

## Deploying

CI (`.github/workflows/deploy.yml`) runs `make` and then
`npx wrangler deploy` on every push to `main`. Manual deploys are rarely
needed.
