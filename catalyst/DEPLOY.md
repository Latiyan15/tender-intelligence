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
