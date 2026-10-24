<!-- Paste into AGENTS.md, CLAUDE.md, .cursorrules or your agent's rules file. Requires `pipx install git+https://github.com/mrzroot/whyenv` (or `uvx --from git+https://github.com/mrzroot/whyenv whyenv`). -->

## Environment variables that "do not change"

When you edit `.env`, `.env.local`, `docker-compose.yml` or similar and the app still behaves with the old value, do not edit the file again and do not guess. Run:

```sh
whyenv NAME_OF_THE_VARIABLE            # which source wins, which edit is being ignored, and why
whyenv NAME -f next -m production      # force the framework / mode
```

- A variable already exported in the shell (or set in the Windows registry) beats `.env*` files in Vite, Next.js, CRA and dotenv.
- `NEXT_PUBLIC_*`, `VITE_*` and `REACT_APP_*` values are baked into the build: rebuild after changing them.
- A running Docker container keeps the environment it was created with: `docker compose up -d --force-recreate SERVICE`.
- `whyenv` masks secret-looking values; never pass `--show-values` in a shared log.
