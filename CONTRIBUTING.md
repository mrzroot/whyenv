# Contributing

Thanks for helping! whyenv is small on purpose: standard library only, no telemetry.

```sh
git clone https://github.com/mrzroot/whyenv && cd whyenv
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
pytest
python -m whyenv --demo
```

Ground rules

- **No new runtime dependencies**, and Python 3.9 must keep working.
- **Only confirmed facts are SHADOWED.** A finding that is a guess goes to `CHECK` or `NOTE`. Precedence rules must cite the framework's own documentation in `resolve.py` comments or the PR.
- **Never print secret values by default.** Names that look secret (KEY, SECRET, TOKEN, PASS...) stay masked unless `--show-values` is passed. Tests must cover any new output path.
- whyenv reads files and the Windows registry only; it never executes the project, never reads other processes' memory, and never sends anything over the network.
- Adding a framework: one function in `resolve.py` that returns the ordered source list, plus a test using the `proj` fixture.
- Add your change to `CHANGELOG.md`.
- Found a tool that already does this? Open an issue; it will be linked in the README and NOVELTY.md.
