# penyal-ifac-3d

A free web 3D walk along the Ruta Roja of the Parc Natural del Penyal d'Ifac (Calp). Everything needed to work on it (commands, architecture, conventions) is in [`CLAUDE.md`](CLAUDE.md); decisions are in [`docs/adr/`](docs/adr/), specs in [`docs/specs/`](docs/specs/).

## Private preview

A test URL for the reference phones and a few neighbours, hosted on Cloudflare Pages ([ADR 0012](docs/adr/0012-private-preview-on-cloudflare-pages.md)). It is not indexed (`X-Robots-Tag: noindex`, `robots.txt`) and the app makes no third-party requests. Cloudflare, as the host, still sees request IP addresses.

### One-time setup (you)
1. Create a free Cloudflare account at https://dash.cloudflare.com/sign-up.
2. Log in with Wrangler (opens the browser): `pnpm exec wrangler login`.
3. Create the Pages project once, with `main` as its production branch (nothing is ever deployed there): `pnpm exec wrangler pages project create penyal-ifac-3d --production-branch main`. A different name: set `PENYAL_PAGES_PROJECT` for every deploy.
4. Leave Web Analytics off in the project settings.
5. Optional, to restrict viewers by email: dashboard, Workers & Pages, the project, Settings, General, **Enable access policy**; then, in Zero Trust, Access, allow the email addresses of the testers. It protects preview deployments only, which is where this script deploys.

### Deploy
From a clean checkout of `main`:

```sh
pnpm deploy:preview          # verifies, builds, checks Pages limits, prints the plan; deploys nothing
pnpm deploy:preview --yes    # the same, then deploys
```

The script runs `penyal verify-generated` and refuses to continue if it fails, builds without the test hooks, checks the file count (20,000) and size per file (25 MiB), and deploys to the `preview` branch: `https://preview.<project>.pages.dev` (override with `PENYAL_PAGES_BRANCH`; production branches are refused). It needs the generated assets and `tools/bin/ktx` in place, as for any local build.

### Roll back or take down
Re-deploy an earlier commit with `pnpm deploy:preview --yes`, or list and delete deployments with `pnpm exec wrangler pages deployment list --project-name penyal-ifac-3d`. To remove the preview completely, delete the Pages project in the dashboard.
