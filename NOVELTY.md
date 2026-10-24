# Novelty check: whyenv

Done 2026-10-24 before building. Wording is deliberately modest: **no existing tool found as of October 2026** that, for
one named variable, lists every source that can define it (shell, `.env*` files, compose `environment:`/`env_file:`),
orders them by the *framework's* precedence, marks the winner and says which file you should change. This is not a claim
that none exists anywhere.

## GitHub repository search queries (API, total results)

| query | total |
|---|---|
| `which .env file wins` | 3 |
| `dotenv precedence` | 4 |
| `env precedence explain` | 0 |
| `dotenv override shell variable` | 0 |
| `env var shadowed .env` | 11 |
| `why is my env variable not updating` | 3 |
| `dotenv debug which value` | 0 |
| `env file precedence vite next` | 0 |
| `docker compose env precedence` | 1 |
| `env var wrong value diagnose` | 0 |
| `whyenv` | 0 |
| `envwhy` | 0 |
| `dotenv conflict detect shell` | 0 |
| `effective environment variable value source` | 2 |

Search is AND-of-terms and noisy; several non-zero totals were unrelated repositories (config dumps, saved web pages).
Also checked on the web (two searches): results were framework documentation, guides and the tools below. Name `whyenv` is
free on GitHub (for this account), PyPI and npm at the time of checking.

## Closest existing work (all different in kind)

| project | what it is | difference |
|---|---|---|
| framework docs (Vite, Next.js, CRA, dotenv, Docker Compose) | state the precedence rules in prose | you must apply them by hand to your files and shell; whyenv applies them and shows the result |
| dotenv `debug: true` | logs that a key already existed and was not overwritten | inside one loader, at runtime, no cross-file or shell-origin explanation |
| nextenv-cli (samuliasmala) | drop-in dotenv-cli that loads `.env*` the Next.js way | *loads* files for a command; does not explain a variable |
| dotenv-precedence-drill (jg-noncelogic) | traces interpolation and merge before trusting a precedence flag | a different problem (a configuration pipeline) |
| typespun, priority-config | generate loaders with explicit precedence | you design precedence up front; they do not diagnose an existing project |
| ghsecret (barisdemirhan) | pushes `.env` to GitHub Secrets with a precedence warning | about secrets sync, not local resolution |
| direnv | loads `.envrc` into the shell | one of the *sources* whyenv looks for |

## Verdict

The individual facts are all documented. What does not appear to exist is a tool that applies them to a real project and answers the
question people actually ask ("I changed it, why is the old value still used?") for one variable, including the shell/registry origin.
If you know of one, please open an issue.

## Rejected during the same brainstorm (for the record)

- Jalali date library disagreement checker (jdatetime and persiantools agree 100 % with ICU for 1900-2100).
- Database connection staged diagnoser (`holdon` exists).
- Rounding-policy fit for invoices (`invoice-rounding-witness`, `invoice-rounding-ledger` exist).
- Flaky-test statistics, GRIM checks, McNemar CLIs, SMS segment calculators, Windows to Linux compatibility checkers: close tools exist.
