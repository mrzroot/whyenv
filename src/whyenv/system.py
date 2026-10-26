"""Where could the *shell's* value of a variable come from? (startup files, direnv, Windows registry)"""
from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class Where:
    where: str       # e.g. ~/.bashrc:12
    text: str        # the line (value may be masked by the caller)
    value: Optional[str] = None


POSIX_FILES = ["~/.bashrc", "~/.bash_profile", "~/.bash_login", "~/.profile", "~/.zshenv", "~/.zprofile", "~/.zshrc",
               "~/.config/fish/config.fish", "/etc/environment", "/etc/profile", "/etc/bash.bashrc"]


def _short(path: str, home: str) -> str:
    return "~" + path[len(home):] if home and path.startswith(home) else path


def _unq(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def scan_posix(name: str, home: str, project_dir: str, extra_files: Optional[List[str]] = None) -> List[Where]:
    pat = re.compile(r"^\s*(?:export\s+|declare\s+-x\s+|typeset\s+-x\s+)?" + re.escape(name) + r"=(.*)$")
    fish = re.compile(r"^\s*set\s+(?:-gx|-x|-Ux|-xg|-gx)\s+" + re.escape(name) + r"\s+(.*)$")
    files = [os.path.expanduser(f.replace("~", home, 1)) if f.startswith("~") else f for f in POSIX_FILES]
    files += sorted(glob.glob("/etc/profile.d/*.sh"))
    # direnv: .envrc in the project and every parent
    d = os.path.abspath(project_dir)
    while True:
        p = os.path.join(d, ".envrc")
        if os.path.isfile(p):
            files.append(p)
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    files += extra_files or []
    out: List[Where] = []
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    if line.lstrip().startswith("#"):
                        continue
                    m = pat.match(line.rstrip("\n")) or fish.match(line.rstrip("\n"))
                    if m:
                        raw = m.group(1)
                        raw = re.sub(r"\s+#.*$", "", raw) if raw[:1] not in "\"'" else raw
                        out.append(Where(f"{_short(f, home)}:{n}", line.strip(), _unq(raw)))
        except OSError:
            continue
    return out


def registry_windows(name: str) -> List[Where]:
    out: List[Where] = []
    try:
        import winreg  # type: ignore
    except ImportError:
        return out
    for label, root, sub in (("User (HKCU\\Environment)", winreg.HKEY_CURRENT_USER, "Environment"),
                             ("Machine (HKLM\\...\\Environment)", winreg.HKEY_LOCAL_MACHINE,
                              r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
        try:
            with winreg.OpenKey(root, sub) as k:
                v, _ = winreg.QueryValueEx(k, name)
                out.append(Where(label, f"{name}=…", str(v)))
        except OSError:
            continue
    return out


def scan(name: str, home: str, project_dir: str, windows: Optional[bool] = None,
         registry: Optional[Callable[[str], List[Where]]] = None) -> List[Where]:
    win = (os.name == "nt") if windows is None else windows
    if win:
        return (registry or registry_windows)(name)
    return scan_posix(name, home, project_dir)
