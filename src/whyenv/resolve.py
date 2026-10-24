"""Work out, for one variable, every place that can define it, in the order the framework reads them."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import compose as composemod
from . import envfile, system

FRAMEWORKS = ("vite", "next", "cra", "dotenv", "compose")
SECRET_RE = re.compile(r"(KEY|SECRET|TOKEN|PASS|PWD|CREDENTIAL|PRIVATE|AUTH|COOKIE|DSN|CONNECTION_STRING|DATABASE_URL)", re.I)
PREFIX = {"vite": "VITE_", "next": "NEXT_PUBLIC_", "cra": "REACT_APP_"}
BUILD_DIR = {"vite": "dist", "next": ".next", "cra": "build"}


@dataclass
class Source:
    label: str
    path: Optional[str] = None
    line: Optional[int] = None
    value: Optional[str] = None      # None = does not define it
    exists: bool = True
    state: str = ""                  # WINS | shadowed | (empty = absent)
    by: str = ""                     # who shadows it
    issues: List[str] = field(default_factory=list)
    where: List[system.Where] = field(default_factory=list)   # provenance of a process value


@dataclass
class Finding:
    level: str       # SHADOWED | CHECK | NOTE
    title: str
    detail: str = ""
    fix: str = ""


@dataclass
class Section:
    framework: str
    title: str
    sources: List[Source] = field(default_factory=list)
    effective: Optional[Source] = None
    findings: List[Finding] = field(default_factory=list)


@dataclass
class Report:
    name: str
    directory: str
    mode: str
    sections: List[Section] = field(default_factory=list)
    reveal: bool = False

    @property
    def found(self) -> bool:
        return any(s.effective for s in self.sections)

    @property
    def exit_code(self) -> int:
        if any(f.level == "SHADOWED" for s in self.sections for f in s.findings):
            return 1
        return 0 if self.found else 2

    def show(self, value: Optional[str]) -> str:
        if value is None:
            return ""
        if not self.reveal and SECRET_RE.search(self.name):
            return f"‹hidden, {len(value)} chars›"
        return value if len(value) <= 80 else value[:77] + "..."


def detect(directory: str) -> List[str]:
    found: List[str] = []
    pj = os.path.join(directory, "package.json")
    if os.path.isfile(pj):
        try:
            data = json.load(open(pj, encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "vite" in deps:
                found.append("vite")
            if "next" in deps:
                found.append("next")
            if "react-scripts" in deps:
                found.append("cra")
        except (OSError, ValueError):
            pass
    if any(os.path.isfile(os.path.join(directory, n)) for n in composemod.COMPOSE_NAMES):
        found.append("compose")
    if not found:
        found.append("dotenv")
    return found


def _files_for(framework: str, mode: str) -> List[str]:
    if framework == "vite":
        return [f".env.{mode}.local", f".env.{mode}", ".env.local", ".env"]
    if framework in ("next", "cra"):
        fs = [f".env.{mode}.local"]
        if mode != "test":
            fs.append(".env.local")
        return fs + [f".env.{mode}", ".env"]
    return [".env"]


def _norm_mode(framework: str, mode: Optional[str]) -> str:
    if mode:
        return mode
    return "development"


def _process_source(name: str, env: Dict[str, str], home: str, directory: str, windows, registry) -> Source:
    v = env.get(name)
    s = Source("process environment (your shell)", value=v, exists=True)
    if v is not None:
        s.where = system.scan(name, home, directory, windows, registry)
    return s


def _mark(sources: List[Source], report: Report, sec: Section, name: str) -> None:
    winner = next((s for s in sources if s.value is not None), None)
    sec.effective = winner
    for s in sources:
        if s.value is None:
            continue
        if s is winner:
            s.state = "WINS"
        else:
            s.state = "shadowed"
            s.by = winner.label  # type: ignore[union-attr]
    if not winner:
        return
    differing = [s for s in sources if s.state == "shadowed" and s.value != winner.value]
    if not differing:
        return
    names = ", ".join(s.label + (f" (line {s.line})" if s.line else "") for s in differing)
    plural = len(differing) > 1
    is_proc = winner.path is None and winner.label.startswith("process")
    if is_proc:
        origin = ""
        if winner.where:
            origin = " Probably set in: " + "; ".join(w.where for w in winner.where[:3]) + "."
        fix = ("remove it from this shell (bash/zsh: `unset %s`; PowerShell: `Remove-Item Env:%s`; cmd: `set %s=`) "
               "and restart the dev server; or change the shell value instead.%s" % (name, name, name, origin))
        sec.findings.append(Finding(
            "SHADOWED", f"{'edits to ' if plural else 'your edit to '}{', '.join(s.label for s in differing)} {'are' if plural else 'is'} ignored: the shell already exports {name}",
            f"{sec.framework} never overrides a variable that already exists in the process environment; different value(s) in: {names}.", fix))
    else:
        sec.findings.append(Finding(
            "SHADOWED", f"{', '.join(s.label for s in differing)} {'are' if plural else 'is'} ignored: {winner.label} wins",
            f"{winner.label}" + (f" (line {winner.line})" if winner.line else "") + f" is read first and has a different value than: {names}.",
            f"change the value in {winner.label}, or delete that line if you want the others to apply."))


def _file_source(directory: str, fname: str, name: str, report: Report) -> (Source, List[envfile.Entry]):
    path = os.path.join(directory, fname)
    s = Source(fname, path=path)
    if not os.path.isfile(path):
        s.exists = False
        return s, []
    try:
        entries = envfile.load(path)
    except (OSError, UnicodeDecodeError) as e:
        s.issues.append(f"unreadable: {e}")
        return s, []
    mine = [e for e in entries if e.key == name]
    if mine:
        e = mine[-1]
        s.value, s.line = e.value, e.line
        s.issues = list(e.issues)
        if len(mine) > 1:
            s.issues.append(f"defined {len(mine)} times in this file (lines {', '.join(str(m.line) for m in mine)}); the last one wins")
    return s, entries


def _similar(name: str, all_entries: Dict[str, List[envfile.Entry]]) -> List[str]:
    res = []
    for fname, entries in all_entries.items():
        for e in entries:
            k = e.key
            if k == name:
                continue
            if k.upper() == name.upper() or k.endswith("_" + name) or name.endswith("_" + k) or \
               k.replace("_", "").upper() == name.replace("_", "").upper():
                res.append(f"{k} in {fname}:{e.line}")
    return sorted(set(res))


def resolve_framework(framework: str, name: str, directory: str, mode: str, env: Dict[str, str], home: str,
                      windows=None, registry=None, reveal: bool = False, report: Optional[Report] = None) -> Section:
    report = report or Report(name, directory, mode, reveal=reveal)
    title = {"vite": f"Vite (mode={mode})", "next": f"Next.js (NODE_ENV={mode})", "cra": f"Create React App (NODE_ENV={mode})",
             "dotenv": "plain dotenv (.env + process environment)"}.get(framework, framework)
    sec = Section(framework, title)
    if framework == "compose":
        return _resolve_compose(name, directory, env, home, windows, registry, report)
    sources = [_process_source(name, env, home, directory, windows, registry)]
    all_entries: Dict[str, List[envfile.Entry]] = {}
    for f in _files_for(framework, mode):
        s, entries = _file_source(directory, f, name, report)
        all_entries[f] = entries
        sources.append(s)
    sec.sources = sources
    _mark(sources, report, sec, name)
    # per-line traps of the winning file
    w = sec.effective
    if w is not None:
        for msg in w.issues:
            lvl = "NOTE"
            sec.findings.append(Finding(lvl, f"{w.label}:{w.line}: {msg}"))
        # empty value
        if w.value == "" and any(s.state == "shadowed" and s.value for s in sources):
            sec.findings.append(Finding("NOTE", f"{name} is set but EMPTY in {w.label}, and an empty value still wins",
                                        "an empty assignment hides the real value from lower-priority files", f"delete the empty `{name}=` line in {w.label}"))
        # client exposure
        pre = PREFIX.get(framework)
        if pre and not name.startswith(pre):
            sec.findings.append(Finding("NOTE", f"{name} does not start with {pre}",
                                        f"{framework} only exposes {pre}* variables to browser code; reading it there gives undefined (server code and config files can read it)",
                                        f"rename to {pre}{name} if the browser needs it. Never put secrets in {pre}* variables: they end up in the public bundle."))
        # baked at build time
        if pre and name.startswith(pre):
            bdir = os.path.join(directory, BUILD_DIR[framework])
            envfiles = [s.path for s in sources if s.path and s.value is not None]
            if os.path.isdir(bdir) and envfiles:
                newest = max(os.path.getmtime(p) for p in envfiles)
                if newest > os.path.getmtime(bdir):
                    sec.findings.append(Finding("CHECK", f"{BUILD_DIR[framework]}/ is older than the .env file that defines {name}",
                                                f"{pre}* values are inlined into the bundle when you build; the existing build still contains the old value",
                                                "rebuild (and restart `next start` / re-deploy); editing .env after a build changes nothing"))
    if not sec.effective:
        sim = _similar(name, all_entries)
        sec.findings.append(Finding("NOTE", f"{name} is not defined in the process environment or any {framework} .env file",
                                    ("similar names exist: " + "; ".join(sim)) if sim else "check spelling and the directory (frameworks read .env files from the project root only)"))
    return sec


def _resolve_compose(name, directory, env, home, windows, registry, report) -> Section:
    sec = Section("compose", "Docker Compose")
    cpath = next((os.path.join(directory, n) for n in composemod.COMPOSE_NAMES if os.path.isfile(os.path.join(directory, n))), None)
    if not cpath:
        return sec
    services = composemod.parse(open(cpath, encoding="utf-8").read())
    # interpolation: ${NAME} in the compose file itself
    text = open(cpath, encoding="utf-8").read()
    uses_interp = re.search(r"\$\{?" + re.escape(name) + r"\b", text) is not None
    dotenv_src, _ = _file_source(directory, ".env", name, report)
    proc = _process_source(name, env, home, directory, windows, registry)
    if uses_interp:
        isec = Section("compose", "Docker Compose: ${%s} interpolation in %s" % (name, os.path.basename(cpath)))
        isec.sources = [proc, dotenv_src]
        _mark(isec.sources, report, isec, name)
        report.sections.append(isec)
    for svc, cfg in services.items():
        envmap = cfg["environment"]
        files = cfg["env_file"]
        defines_env = name in envmap  # type: ignore[operator]
        file_srcs: List[Source] = []
        for f in files:  # type: ignore[union-attr]
            s, _ = _file_source(directory, f, name, report)
            file_srcs.append(s)
        if not defines_env and not any(s.value is not None for s in file_srcs):
            continue
        ssec = Section("compose", f"Docker Compose: service '{svc}' container environment")
        srcs: List[Source] = []
        if defines_env:
            v = envmap[name]  # type: ignore[index]
            if v is None:
                pv = env.get(name)
                src = Source(f"environment: {name} (pass-through from the shell)", path=cpath, value=pv if pv is not None else None)
                if pv is None:
                    src.issues.append(f"{name} has no value in the shell, so compose passes nothing and falls back to env_file")
            else:
                src = Source(f"environment: {name} in {os.path.basename(cpath)}", path=cpath, value=v)
            srcs.append(src)
        # later env_file entries win over earlier ones
        srcs.extend(reversed(file_srcs))
        ssec.sources = srcs
        _mark(srcs, report, ssec, name)
        ssec.findings.append(Finding("NOTE", "a container keeps the environment it was created with",
                                     "after editing any of these sources, run `docker compose up -d --force-recreate " + svc + "` (a running container does not re-read them)"))
        report.sections.append(ssec)
    if not report.sections:
        sec.findings.append(Finding("NOTE", f"{name} is not referenced by {os.path.basename(cpath)} (environment, env_file or ${{{name}}})"))
        return sec
    return Section("compose", "")   # sentinel: sections were appended directly


def resolve(name: str, directory: str = ".", framework: Optional[str] = None, mode: Optional[str] = None,
            env: Optional[Dict[str, str]] = None, home: Optional[str] = None, windows=None, registry=None,
            reveal: bool = False) -> Report:
    directory = os.path.abspath(directory)
    env = dict(os.environ) if env is None else env
    home = home if home is not None else os.path.expanduser("~")
    fws = [framework] if framework else detect(directory)
    mode = mode or "development"
    rep = Report(name, directory, mode, reveal=reveal)
    for fw in fws:
        sec = resolve_framework(fw, name, directory, mode, env, home, windows, registry, reveal, rep)
        if fw == "compose":
            if sec.title:                      # not referenced anywhere
                rep.sections.append(sec)
            continue
        rep.sections.append(sec)
    return rep
