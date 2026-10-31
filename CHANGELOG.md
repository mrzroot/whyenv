# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-10-31

### Fixed
- The repository had no `pyproject.toml`, so the install commands in the README (`pipx install git+…`, `uvx --from git+…`, `pip install -e .`) failed. It now ships one (setuptools, no dependencies, `whyenv` console script), and those commands work.

### Changed
- Internal clean-up only: unused imports removed and two tests made easier to read. No change in output.

## [0.1.0] - 2026-10-24

First release.

### Added
- `whyenv NAME`: lists every place that can define an environment variable in the order the framework reads them (Vite, Next.js, Create React App, plain dotenv, Docker Compose), marks the winner and explains why your edit is ignored.
- Finds the shell startup file (`~/.bashrc`, `/etc/profile.d`, `.envrc`) or Windows registry entry that probably exports the shadowing value.
- Notes for the traps around it: missing client prefix, build older than the `.env` file, empty value winning, CRLF/BOM, spaces around `=`, `$` expansion, duplicates, container not recreated.
- Secret-looking names are masked unless `--show-values`; `--json`; `--demo` (offline, three broken projects).
