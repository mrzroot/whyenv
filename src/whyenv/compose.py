"""Minimal reader for docker-compose files: only `environment:` and `env_file:` per service (no YAML dependency)."""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


def _clean(line: str) -> str:
    out, q = [], ""
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = ""
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _unq(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse(text: str) -> Dict[str, Dict[str, object]]:
    """-> {service: {"environment": {KEY: value-or-None}, "env_file": [path...]}}"""
    services: Dict[str, Dict[str, object]] = {}
    lines = [(len(l) - len(l.lstrip(" ")), _clean(l).strip()) for l in text.replace("\r", "").split("\n")]
    lines = [(i, s) for i, s in lines if s]
    in_services = False
    svc_indent = None
    cur = None
    j = 0
    while j < len(lines):
        ind, s = lines[j]
        if ind == 0:
            in_services = s == "services:"
            cur = None
            j += 1
            continue
        if not in_services:
            j += 1
            continue
        if svc_indent is None:
            svc_indent = ind
        if ind == svc_indent and s.endswith(":"):
            cur = s[:-1].strip()
            services[cur] = {"environment": {}, "env_file": []}
            j += 1
            continue
        if cur and ind > svc_indent and s.split(":")[0] in ("environment", "env_file"):
            key = s.split(":")[0]
            rest = s[len(key) + 1:].strip()
            block: List[str] = []
            k = j + 1
            while k < len(lines) and lines[k][0] > ind:
                block.append(lines[k][1])
                k += 1
            if key == "env_file":
                if rest:
                    items = [_unq(x) for x in re.split(r"\s*,\s*", rest.strip("[]")) if x] if rest.startswith("[") else [_unq(rest)]
                else:
                    items = []
                    for b in block:
                        if b.startswith("- path:"):
                            items.append(_unq(b[7:]))
                        elif b.startswith("- ") and ":" not in b:
                            items.append(_unq(b[2:]))
                services[cur]["env_file"] = items  # type: ignore[assignment]
            else:
                env: Dict[str, Optional[str]] = {}
                for b in block:
                    if b.startswith("- "):
                        item = _unq(b[2:])
                        if "=" in item:
                            a, v = item.split("=", 1)
                            env[a.strip()] = v
                        else:
                            env[item.strip()] = None
                    elif ":" in b:
                        a, v = b.split(":", 1)
                        v = v.strip()
                        env[_unq(a)] = _unq(v) if v else None
                services[cur]["environment"] = env  # type: ignore[assignment]
            j = k
            continue
        j += 1
    return services


COMPOSE_NAMES = ("compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml")
