"""A small, forgiving .env parser that also reports the traps (BOM, CRLF, spaces, `$`, duplicates)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")


@dataclass
class Entry:
    key: str
    value: str
    line: int
    issues: List[str] = field(default_factory=list)


def parse(text: str) -> List[Entry]:
    """Return every assignment, in file order (duplicates included). `text` must be read with newline=''."""
    out: List[Entry] = []
    bom = text.startswith("\ufeff")
    if bom:
        text = text[1:]
    lines = text.split("\n")
    first = True
    for n, raw in enumerate(lines, 1):
        crlf = raw.endswith("\r")
        line = raw.rstrip("\r")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            first = False
            continue
        body = stripped
        if body.startswith("export "):
            body = body[7:].lstrip()
        if "=" not in body:
            continue
        k, v = body.split("=", 1)
        spaced = k.endswith((" ", "\t")) or v.startswith((" ", "\t"))
        k = k.strip()
        if not KEY_RE.match(k):
            continue
        issues: List[str] = []
        if bom and first:
            issues.append("UTF-8 BOM at the start of the file: some loaders read this key as '\\ufeff" + k + "'")
        first = False
        v = v.strip()
        if v[:1] in "\"'" and v:
            q = v[0]
            end = -1
            i = 1
            while i < len(v):
                if v[i] == "\\" and q == '"':
                    i += 2
                    continue
                if v[i] == q:
                    end = i
                    break
                i += 1
            if end == -1:
                val = v[1:]
                issues.append("unterminated quote (multi-line values are not analysed)")
            else:
                val = v[1:end]
                if q == '"':
                    val = val.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        else:
            m = re.search(r"\s#", v)
            if m:
                issues.append("text after ' #' is treated as a comment by dotenv loaders (quote the value if the # is part of it)")
                v = v[: m.start()].rstrip()
            val = v
        if crlf:
            issues.append("CRLF line ending (Windows): most dotenv loaders strip it, but bash `source` and some other tools keep a trailing \\r in the value")
        if spaced:
            issues.append("spaces around '=': works in dotenv loaders, breaks if the file is also sourced by bash")
        if "$" in val and v[:1] != "'":
            issues.append("contains '$': Vite, Next.js, CRA and Docker Compose expand $VAR here; a password with $ is silently altered (write \\$)")
        out.append(Entry(k, val, n, issues))
    return out


def load(path: str) -> List[Entry]:
    with open(path, encoding="utf-8", newline="") as fh:
        return parse(fh.read())


def last_wins(entries: List[Entry]) -> Dict[str, Entry]:
    d: Dict[str, Entry] = {}
    for e in entries:
        d[e.key] = e
    return d
