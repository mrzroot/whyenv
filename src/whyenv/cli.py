from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__, render, resolve


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="whyenv", description=(
        "Which source wins for an environment variable? Lists every place that can define it, in the order your "
        "framework reads them, marks the winner and says why your edit is ignored."))
    ap.add_argument("name", nargs="?", help="variable name, e.g. API_URL")
    ap.add_argument("-d", "--dir", default=".", help="project directory (default: current)")
    ap.add_argument("-f", "--framework", choices=list(resolve.FRAMEWORKS), help="force a framework (default: auto-detect)")
    ap.add_argument("-m", "--mode", help="Vite mode / NODE_ENV (default: development)")
    ap.add_argument("--show-values", action="store_true", help="also show values of secret-looking variables (KEY, TOKEN, PASSWORD...)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--demo", action="store_true", help="offline: three broken projects in a temp dir")
    ap.add_argument("--version", action="version", version=f"whyenv {__version__}")
    a = ap.parse_args(argv)
    if a.demo:
        from . import demo
        sys.stdout.write(demo.run())
        return 0
    if not a.name:
        ap.error("give a variable name (or use --demo)")
    rep = resolve.resolve(a.name, a.dir, a.framework, a.mode, reveal=a.show_values)
    sys.stdout.write((render.as_json(rep) + "\n") if a.json else render.text(rep, color=sys.stdout.isatty() and not a.no_color))
    return rep.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
