# Resume

Personal site and CV, deployed at <https://cjpatton.net>.

## Building

Requires Python 3 (`pip install -r requirements.txt`), LaTeX (`moderncv`), and
Node.js (`npm install`). Run `make` to assemble the site in `public/` from
`resume.toml`, the Markdown posts in `blog/`, and the static assets in
`static/` (images, PDFs, etc.). The contents of `public/` are generated, so
they are not tracked in git.

## Blog

A post is a Markdown file in `blog/` named like `2026-09-20-short-title.md`,
where the publication date comes from the file name and the short title from
the `title` field of the front matter (falling back to the file name):

    ---
    title: Short Title
    ---

    Body in Markdown...

The post above would be published at `/blog/2026-09-20-short-title` and
listed, newest first, at `/blog`.

LaTeX math is rendered to HTML (MathML) at build time, so no JavaScript is
needed on the client: `$x^2$` for inline math and `$$x^2$$` for display math
(on its own lines). Images and other non-Markdown files in `blog/` are
copied to the site as-is; refer to them with paths relative to `blog/`,
e.g. `![alt](img/foo.png)`.

## Deploying

The site is served by a Cloudflare Worker with
[Static Assets](https://developers.cloudflare.com/workers/static-assets/).
Build the site and deploy `public/` with:

    make
    npx wrangler deploy

Pushes to `main` are deployed automatically by
[.github/workflows/deploy.yml](.github/workflows/deploy.yml). This requires a
`CLOUDFLARE_API_TOKEN` secret with permission to edit Workers scripts and
Workers routes on the `cjpatton.net` zone.
