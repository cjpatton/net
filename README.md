# Resume

Personal site and CV, deployed at <https://cjpatton.net>.

## Building

Requires Python 3 (`pip install -r requirements.txt`), LaTeX (`moderncv`), and
Node.js (`npm install`). Run `make` to generate `public/index.html` and
`public/cv.pdf` from `resume.toml`.

## Deploying

The site is served by a Cloudflare Worker with
[Static Assets](https://developers.cloudflare.com/workers/static-assets/).
Deploy the current contents of `public/` with:

    npx wrangler deploy

Pushes to `main` are deployed automatically by
[.github/workflows/deploy.yml](.github/workflows/deploy.yml). This requires a
`CLOUDFLARE_API_TOKEN` secret with permission to edit Workers scripts and
Workers routes on the `cjpatton.net` zone.
