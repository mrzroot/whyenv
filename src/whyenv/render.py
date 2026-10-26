from __future__ import annotations

import json
from typing import List

from . import __version__
from .resolve import Report


def _c(t: str, code: str, on: bool) -> str:
    return f"\033[{code}m{t}\033[0m" if on else t


def text(rep: Report, color: bool = False) -> str:
    out: List[str] = [f"whyenv {__version__} · {rep.name} · {rep.directory}"]
    if not rep.sections:
        out.append("nothing to analyse")
    for sec in rep.sections:
        out.append("")
        out.append(_c(f"== {sec.title}", "1", color))
        eff = sec.effective
        if eff:
            out.append(f"effective value: {rep.show(eff.value)!r}   <- from: {eff.label}" + (f":{eff.line}" if eff.line else ""))
        else:
            out.append("effective value: (not defined anywhere)")
        out.append("priority, highest first:")
        for i, s in enumerate(sec.sources, 1):
            if not s.exists:
                out.append(f"  {i}. {s.label:<44} (no such file)")
                continue
            if s.value is None:
                out.append(f"  {i}. {s.label:<44} -")
                continue
            loc = f"{s.label}" + (f":{s.line}" if s.line else "")
            tag = _c("WINS", "32", color) if s.state == "WINS" else _c("shadowed", "31", color)
            out.append(f"  {i}. {loc:<44} {rep.show(s.value)!r:<28} {tag}")
            if s.where:
                for w in s.where[:4]:
                    shown = w.text
                    if w.value is not None and not rep.reveal and rep.show(w.value) != w.value:
                        shown = shown.replace(w.value, rep.show(w.value)) if w.value else shown
                    out.append(f"       probably set at: {w.where}   {shown}")
                out.append("       (whyenv can only see files, not the process that exported it)")
            elif s.state == "WINS" and s.path is None and s.label.startswith("process"):
                out.append("       no startup file or registry entry found for it: it was exported by hand, by your IDE, or by a parent process")
        for f in sec.findings:
            out.append("")
            mark = {"SHADOWED": "✗", "CHECK": "?", "NOTE": "·"}[f.level]
            out.append(f"{mark} {f.level}: {f.title}")
            if f.detail:
                out.append(f"    why:  {f.detail}")
            if f.fix:
                out.append(f"    fix:  {f.fix}")
    out.append("")
    n = sum(1 for s in rep.sections for f in s.findings if f.level == "SHADOWED")
    out.append(f"{n} confirmed shadowed value(s)." if n else ("no shadowed values." if rep.found else f"{rep.name} is not defined anywhere whyenv looked."))
    return "\n".join(out) + "\n"


def as_json(rep: Report) -> str:
    def src(s):
        return {"label": s.label, "path": s.path, "line": s.line, "defines": s.value is not None, "exists": s.exists,
                "value": rep.show(s.value) if s.value is not None else None, "state": s.state,
                "issues": s.issues, "where": [w.where for w in s.where]}
    return json.dumps({"tool": "whyenv", "version": __version__, "name": rep.name, "directory": rep.directory, "mode": rep.mode,
                       "sections": [{"framework": s.framework, "title": s.title,
                                     "effective": src(s.effective) if s.effective else None,
                                     "sources": [src(x) for x in s.sources],
                                     "findings": [f.__dict__ for f in s.findings]} for s in rep.sections]},
                      indent=2, ensure_ascii=False)
