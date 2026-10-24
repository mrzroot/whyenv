"""Offline demo: three projects that behave the way real ones do."""
from __future__ import annotations

import os
import tempfile
import time

from . import render, resolve


def _w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def run() -> str:
    out = []
    with tempfile.TemporaryDirectory() as root:
        home = os.path.join(root, "home")
        _w(os.path.join(home, ".bashrc"), "# my shell\nexport PATH=$PATH:~/bin\nexport API_URL=http://old.example.test\n")

        # 1. Vite: edited .env.local, shell still exports the old value
        p1 = os.path.join(root, "shop-vite")
        _w(os.path.join(p1, "package.json"), '{"devDependencies": {"vite": "^5.0.0"}}')
        _w(os.path.join(p1, ".env"), "VITE_API_URL=https://api.example.test\nAPI_URL=https://prod.example.test\n")
        _w(os.path.join(p1, ".env.local"), "API_URL=http://localhost:3000\n")
        out.append("### 1. 'I changed API_URL in .env.local but the app still calls the old server' (Vite)\n")
        out.append(render.text(resolve.resolve("API_URL", p1, env={"API_URL": "http://old.example.test"}, home=home, windows=False)))

        # 2. Next: baked at build time, plus a CRLF .env and a $ in the value
        p2 = os.path.join(root, "blog-next")
        _w(os.path.join(p2, "package.json"), '{"dependencies": {"next": "14.0.0"}}')
        os.makedirs(os.path.join(p2, ".next"))
        time.sleep(0.05)
        _w(os.path.join(p2, ".env.production"), "NEXT_PUBLIC_API_URL=https://api.example.test\r\n")
        out.append("\n### 2. 'next build was fine, but the site shows the old API URL' (Next.js, mode=production)\n")
        out.append(render.text(resolve.resolve("NEXT_PUBLIC_API_URL", p2, mode="production", env={}, home=home, windows=False)))

        # 3. Docker Compose: environment beats env_file
        p3 = os.path.join(root, "stack")
        _w(os.path.join(p3, "docker-compose.yml"),
           "services:\n  web:\n    image: web:1\n    env_file:\n      - web.env\n    environment:\n      LOG_LEVEL: debug\n")
        _w(os.path.join(p3, "web.env"), "LOG_LEVEL=warn\n")
        out.append("\n### 3. 'I set LOG_LEVEL=warn in web.env and nothing changed' (Docker Compose)\n")
        out.append(render.text(resolve.resolve("LOG_LEVEL", p3, env={}, home=home, windows=False)))
    return "\n".join(out)
