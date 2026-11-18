# Catalyst deploy (run on the SHAHIL machine — India network + your Catalyst login)

The cloud session can't deploy code (its network can't reach Catalyst's deploy
endpoints and it has no Catalyst login). Code upload is the only step that must
run on your machine. Everything else — setting env vars, scheduling, running and
checking the function — the cloud session does via the Zoho MCP.

## Spike: prove GeM is reachable from Catalyst India (no proxy)

Org: `60096734987`  ·  Project: `Project-Rainfall` (`95882000000013024`)  ·  Env: Development

From the repo root on SHAHIL:

```bash
npm install -g zcatalyst-cli
```

```bash
catalyst login
```

```bash
catalyst init --org 60096734987 -p 95882000000013024 -ni
```

```bash
catalyst functions:add --name gem_reachability --type aio --stack node20 -ni
```

That last command scaffolds `functions/gem_reachability/` with a correct
`catalyst-config.json` + `catalyst.json`. Overwrite the generated handler with
the one in this repo, then deploy:

```bash
cp catalyst/functions/gem_reachability/index.js functions/gem_reachability/index.js
```

```bash
catalyst deploy --only functions:gem_reachability
```

Paste the deploy output back (it prints the FUNCTION URL). The cloud session will
then invoke it via MCP and read the verdict — no need to curl it yourself.

Expected result: `"verdict": "REACHABLE — GeM answered, no proxy needed"` with an
egress `country` of India. If so, we port the full pipeline the same way.

---

## Full pipeline: `gem_sync` Job function

Runs the whole daily sync (DC + cyber domains) from Catalyst India — no proxy.
Authoritative code: `catalyst/functions/gem_sync/{main.py,requirements.txt}`;
the rest is vendored in by the build script. On SHAHIL, from the repo root:

```bash
git pull
```

```bash
catalyst functions:add --name gem_sync --type job --stack python_3_11 -ni
```

That scaffolds `functions/gem_sync/` with a correct `catalyst-config.json`.
Assemble the deployable into it (copies main.py, requirements.txt, and vendors
`gem_sheets_sync.py` + the needed `src/` modules):

```bash
bash catalyst/build-gem-sync.sh
```

```bash
catalyst deploy --only functions:gem_sync
```

Paste the deploy result back. Then the cloud session (via MCP) will:
1. set the `GOOGLE_SHEETS_CREDENTIALS` env var on the function,
2. run the job once and read the logs (confirm bids discovered + both sheets updated),
3. create the daily 08:45 IST schedule via Job Scheduling.

Note: do **not** set `PROXY_URL` — from India the pipeline connects to GeM directly.

