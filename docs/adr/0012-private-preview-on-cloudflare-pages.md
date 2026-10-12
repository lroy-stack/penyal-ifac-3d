# 0012. Host the private test preview on Cloudflare Pages

- Status: accepted (covers the H1 preview only; the final hosting is decided in H5)
- Date: 2026-10-12
- Deciders: lr0y (product owner), tech lead

## Context
Milestone H1 (`docs/specs/006-h1-paseo-con-sentido/plan.md`, task F1) needs a URL that the product owner's reference phones and five neighbours can open outside the local network. Tasks E4 (phone budget) and E5 (neighbour test) depend on it. The app is a static Vite build (`app/dist`): no backend, no accounts, no cookies, no analytics.

Facts that constrain the choice:
- The build is about 33 MiB in 97 files; the largest file is 5.1 MiB (a KTX2 texture).
- The app needs response headers: a CSP that allows blob workers and `unsafe-eval` (the Basis transcoder), `X-Robots-Tag`, long caching for hashed bundles.
- The URL must stay out of search engines and be easy to take down.
- The final hosting (the Ajuntament's domain, PWA, security headers, maintenance guide) is a separate decision in roadmap H5 (`docs/roadmap.md`). This ADR must not pre-empt it.

Limits of Cloudflare Pages that apply (https://developers.cloudflare.com/pages/platform/limits/, read 2026-10-12): 20,000 files per site on the Free plan, 25 MiB per file, 100 `_headers` rules, 2,000 characters per header line.

## Options considered
1. **Cloudflare Pages.** Static hosting with a free tier, per-branch preview URLs, a `_headers` file, a CLI (`wrangler pages deploy`) that deploys a built directory from a laptop, and an Access policy that can restrict preview deployments. Cost to reverse: low (delete the project, stop using the URL).
2. **Netlify.** Equivalent features (`_headers`, deploy previews, CLI). To our knowledge its free tier is metered and viewer restriction (password protection) is a paid feature; plans were not re-checked for this ADR. No advantage here over option 1. Cost to reverse: low.
3. **GitHub Pages.** The repository is private, and to our knowledge Pages for private repositories needs a paid plan (not re-checked). GitHub Pages cannot set custom response headers (no `X-Robots-Tag`, no CSP, no cache control). It also serves from a public URL with no viewer restriction. Cost to reverse: low, but it cannot meet the header requirement.

## Decision
Option 1, chosen by the product owner on 2026-10-12. Cloudflare Pages is the only one of the three that sets the required headers, deploys from the command line without CI (GitHub Actions billing is an open item in plan §5), and can restrict viewers.

How it works:
- One Pages project (default name `penyal-ifac-3d`, overridable with `PENYAL_PAGES_PROJECT`).
- Deployments always go to the non-production branch `preview` (`PENYAL_PAGES_BRANCH`; the script refuses `main`, `master` and `trunk`). The URL is `https://preview.<project>.pages.dev`, plus a hash URL per deployment. The production URL `<project>.pages.dev` never receives a deployment.
- `pnpm deploy:preview` (`scripts/deploy-preview.mjs`) runs `penyal verify-generated`, a plain `pnpm --filter @penyal/app build` (no `VITE_E2E`; it fails if `__appState` is in the bundle), checks the Pages limits on `app/dist`, prints the plan and stops. Only `--yes` runs `wrangler pages deploy`. Wrangler is a pinned devDependency (`wrangler` 4.149.0, npm `latest` on 2026-10-12; CLI flags checked against https://developers.cloudflare.com/workers/wrangler/commands/pages/ and `wrangler pages deploy --help`).
- The project is created once by the product owner (`wrangler pages project create`), and login is done by the product owner. Neither the agents nor the script create resources or read credentials.

## Privacy posture
What the app does (unchanged by this ADR):
- No analytics, no cookies, no accounts. The notebook keeps card ids and dates in `localStorage` only, on the visitor's device.
- No third-party requests: the CSP is `default-src 'none'` with `'self'` (plus `blob:` and `data:` where the loaders need them), so the browser blocks any other origin.

What this ADR adds (`app/public/_headers`, `app/public/robots.txt`):
- `X-Robots-Tag: noindex, nofollow` on every response and `robots.txt` with `Disallow: /`. The header is the primary control; the `<meta name="robots">` tag was deliberately not added to `app/index.html` to avoid conflicting edits there, and the header makes it redundant.
- `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `Cross-Origin-Opener-Policy: same-origin`, `frame-ancestors 'none'`, and a `Permissions-Policy` that denies sensors, camera, microphone, geolocation, payment and USB (autoplay stays allowed for the soundscape).
- The CSP needs `'unsafe-eval'` in `script-src` because the Basis transcoder (emscripten embind) calls `new Function` inside the KTX2 worker; without it the worker fails with a CSP error. With `script-src 'self'` and no third-party origins, eval can only run our own bundle. Revisit when three.js ships a transcoder without it.
- Leave Cloudflare Web Analytics off in the project settings; enabling it injects a third-party script and breaks the "no analytics" promise.

What Cloudflare itself does: it serves the files, so it processes request data. Its privacy policy (https://www.cloudflare.com/privacypolicy/, read 2026-10-12) says it acts as a data processor of "Customer Logs" on behalf of its customers; the data about end users "may include but is not limited to IP addresses, traffic routing data", and log files may include IP addresses and referring URLs. The policy gives no retention period for Customer Logs. We therefore cannot promise "no logs": for the test group the honest statement is "the host sees IP addresses and requests, as any web host does; the app adds nothing". The privacy declaration for the Ajuntament (H5) must be written against the final host, not this one.

## Restricting viewers (optional, done by the product owner)
Preview deployments are public by default (https://developers.cloudflare.com/pages/configuration/preview-deployments/). The URL is unguessable only in the weak sense of being unlisted. To limit it:
1. Dashboard, Workers & Pages, the project, Settings, General, **Enable access policy**. This puts Cloudflare Access in front of preview deployments (hash URLs and the `preview` alias) and protects only previews, which is why we deploy to the `preview` branch.
2. In Zero Trust, Access, edit the policy that was created and allow the neighbours' and testers' email addresses (the one-time PIN login method needs no account on their side; the Pages docs only describe the default policy, which admits members of your Cloudflare account, so this step was not verified against the docs and the product owner should confirm it in the dashboard).

The trade-off: each viewer receives a code by email and the session expires, which is friction for a neighbour test. Skip it when the URL is shared only in person and the content is not sensitive; enable it before sharing the link in a group chat.

## Rollback
- Preview deployments are not valid rollback targets for the dashboard's "Rollback to this deployment" (https://developers.cloudflare.com/pages/configuration/rollbacks/); that feature covers production only.
- To go back to an earlier build: check out that commit and run `pnpm deploy:preview --yes` again. Every deploy records the commit hash.
- To list and remove deployments: `pnpm exec wrangler pages deployment list --project-name <name>` and `pnpm exec wrangler pages deployment delete <id> --project-name <name>` (the latest deployment of a branch cannot be deleted).
- To take the preview down entirely: delete the Pages project in the dashboard. Nothing else depends on it.

## Consequences
- Easier: a phone-reachable URL in one command, with the same verification gates as local work, and no CI needed.
- Harder: the preview is deployed by hand from a clean checkout; nothing publishes automatically. The script refuses a dirty tree unless `--allow-dirty` is passed.
- Watch: the 25 MiB per-file limit (the largest file is 5.1 MiB; the H1 rocks, boats and walls must stay far below it), the 20,000-file limit, and the 100 header rules. `deploy-preview.mjs` checks all three.
- `pnpm-workspace.yaml` now sets `allowBuilds: { esbuild: false, workerd: false }`. Wrangler depends on both; neither install script is needed to deploy static files, and pnpm 12 fails `pnpm install` when a dependency's build script is neither allowed nor denied.

## What changes for H5
- The hosting is decided again with the Ajuntament's constraints (domain, who pays, who maintains, data protection). Cloudflare Pages remains a candidate, not a choice.
- `app/public/_headers` becomes the base of the final security headers (HSTS, a CSP without `unsafe-eval` if possible, no `noindex`). Remove `X-Robots-Tag` and `robots.txt` when the site is meant to be found.
- The privacy and accessibility declarations are written for the final host.
- CI deployment, with a scoped API token in the platform's secret store, replaces the manual command; this ADR's script is the starting point.
- Delete the preview project when the final URL is live.
