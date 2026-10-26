import os
import time

from whyenv import cli, render, resolve, system, compose

VITE = '{"devDependencies": {"vite": "5"}}'
NEXT = '{"dependencies": {"next": "14"}}'


def sec(rep, i=0):
    return rep.sections[i]


def test_process_env_beats_files_in_vite(proj):
    d, h = proj({"package.json": VITE, ".env": "A=file\n", ".env.local": "A=local\n"}, {".bashrc": "export A=shell\n"})
    r = resolve.resolve("A", d, env={"A": "shell"}, home=h, windows=False)
    s = sec(r)
    assert s.effective.label.startswith("process")
    assert [x.state for x in s.sources if x.value is not None] == ["WINS", "shadowed", "shadowed"]
    f = [x for x in s.findings if x.level == "SHADOWED"]
    assert len(f) == 1 and ".env.local" in f[0].title and ".bashrc:1" in f[0].fix
    assert r.exit_code == 1


def test_vite_file_order_and_mode(proj):
    d, h = proj({"package.json": VITE, ".env": "A=1\n", ".env.local": "A=2\n", ".env.production": "A=3\n", ".env.development.local": "A=4\n"})
    assert sec(resolve.resolve("A", d, env={}, home=h)).effective.value == "4"
    assert sec(resolve.resolve("A", d, mode="production", env={}, home=h)).effective.value == "3"
    assert sec(resolve.resolve("A", d, mode="staging", env={}, home=h)).effective.value == "2"


def test_next_skips_env_local_in_test_mode(proj):
    d, h = proj({"package.json": NEXT, ".env": "A=1\n", ".env.local": "A=2\n"})
    assert sec(resolve.resolve("A", d, mode="test", env={}, home=h)).effective.value == "1"
    assert sec(resolve.resolve("A", d, mode="development", env={}, home=h)).effective.value == "2"


def test_same_value_is_not_a_finding(proj):
    d, h = proj({"package.json": VITE, ".env": "VITE_A=1\n", ".env.local": "VITE_A=1\n"})
    r = resolve.resolve("VITE_A", d, env={}, home=h)
    assert not [f for f in sec(r).findings if f.level == "SHADOWED"]
    assert r.exit_code == 0


def test_prefix_note_only_without_prefix(proj):
    d, h = proj({"package.json": VITE, ".env": "A=1\nVITE_B=2\n"})
    assert any("VITE_" in f.title for f in sec(resolve.resolve("A", d, env={}, home=h)).findings)
    assert not any("does not start" in f.title for f in sec(resolve.resolve("VITE_B", d, env={}, home=h)).findings)


def test_stale_build_detected(proj):
    d, h = proj({"package.json": NEXT, ".env": "NEXT_PUBLIC_X=1\n"})
    os.makedirs(os.path.join(d, ".next"))
    old = time.time() - 3600
    os.utime(os.path.join(d, ".next"), (old, old))
    assert any(".next/ is older" in f.title for f in sec(resolve.resolve("NEXT_PUBLIC_X", d, env={}, home=h)).findings)
    now = time.time() + 10
    os.utime(os.path.join(d, ".next"), (now, now))
    assert not any(".next/ is older" in f.title for f in sec(resolve.resolve("NEXT_PUBLIC_X", d, env={}, home=h)).findings)


def test_empty_value_wins_and_is_flagged(proj):
    d, h = proj({"package.json": VITE, ".env": "A=real\n", ".env.local": "A=\n"})
    s = sec(resolve.resolve("A", d, env={}, home=h))
    assert s.effective.value == "" and any("EMPTY" in f.title for f in s.findings)


def test_not_found_suggests_similar_names(proj):
    d, h = proj({"package.json": VITE, ".env": "VITE_API_URL=1\nApi_Url=2\n"})
    r = resolve.resolve("API_URL", d, env={}, home=h)
    assert r.exit_code == 2
    t = " ".join(f.detail for f in sec(r).findings)
    assert "VITE_API_URL" in t and "Api_Url" in t


def test_secrets_are_hidden_by_default(proj):
    d, h = proj({"package.json": VITE, ".env": "SECRET_TOKEN=supersecretvalue\n"})
    r = resolve.resolve("SECRET_TOKEN", d, env={}, home=h)
    out = render.text(r) + render.as_json(r)
    assert "supersecretvalue" not in out and "hidden, 16 chars" in out
    r2 = resolve.resolve("SECRET_TOKEN", d, env={}, home=h, reveal=True)
    assert "supersecretvalue" in render.text(r2)


def test_secret_value_not_leaked_through_startup_file_line(proj):
    d, h = proj({"package.json": VITE}, {".bashrc": "export API_KEY=abcdef123456\n"})
    r = resolve.resolve("API_KEY", d, env={"API_KEY": "abcdef123456"}, home=h, windows=False)
    assert "abcdef123456" not in render.text(r)


def test_dotenv_default_and_autodetect(proj):
    d, h = proj({".env": "A=1\n"})
    assert resolve.detect(d) == ["dotenv"]
    assert sec(resolve.resolve("A", d, env={"A": "9"}, home=h)).effective.value == "9"


def test_compose_environment_beats_env_file_and_later_file_wins(proj):
    yml = "services:\n  web:\n    env_file:\n      - a.env\n      - b.env\n    environment:\n      X: fromenv\n      Y:\n"
    d, h = proj({"docker-compose.yml": yml, "a.env": "X=a\nZ=a\nY=a\n", "b.env": "Z=b\n"})
    r = resolve.resolve("X", d, env={}, home=h)
    assert r.sections[-1].effective.value == "fromenv" and r.exit_code == 1
    r = resolve.resolve("Z", d, env={}, home=h)
    assert r.sections[-1].effective.value == "b"
    # pass-through with no shell value falls back to env_file
    r = resolve.resolve("Y", d, env={}, home=h)
    assert r.sections[-1].effective.value == "a"
    r = resolve.resolve("Y", d, env={"Y": "shell"}, home=h)
    assert r.sections[-1].effective.value == "shell"


def test_compose_interpolation_uses_shell_then_dotenv(proj):
    yml = "services:\n  web:\n    image: x:${TAG}\n"
    d, h = proj({"docker-compose.yml": yml, ".env": "TAG=1\n"})
    r = resolve.resolve("TAG", d, env={"TAG": "2"}, home=h)
    assert r.sections[0].effective.value == "2" and r.exit_code == 1
    r = resolve.resolve("TAG", d, env={}, home=h)
    assert r.sections[0].effective.value == "1"


def test_compose_not_referenced(proj):
    d, h = proj({"docker-compose.yml": "services:\n  web:\n    image: x\n"})
    r = resolve.resolve("NOPE", d, env={}, home=h)
    assert r.exit_code == 2


def test_windows_registry_provenance(proj):
    d, h = proj({"package.json": VITE, ".env": "A=file\n"})
    reg = lambda n: [system.Where("User (HKCU\\Environment)", n + "=…", "setx")]
    r = resolve.resolve("A", d, env={"A": "setx"}, home=h, windows=True, registry=reg)
    s = sec(r)
    assert s.sources[0].where[0].where.startswith("User")
    assert "User (HKCU" in next(f for f in s.findings if f.level == "SHADOWED").fix


def test_direnv_envrc_found_in_parent(proj):
    d, h = proj({"package.json": VITE, "sub/x": ""})
    with open(os.path.join(d, ".envrc"), "w") as f:
        f.write("export A=fromdirenv\n")
    w = system.scan_posix("A", h, os.path.join(d, "sub"))
    assert any(x.where.endswith(".envrc:1") for x in w)


def test_compose_parser_shapes():
    c = compose.parse("services:\n  a:\n    env_file: one.env\n    environment:\n      - K=v\n      - P\n  b:\n    env_file: [x.env, y.env]\n")
    assert c["a"]["env_file"] == ["one.env"] and c["a"]["environment"] == {"K": "v", "P": None}
    assert c["b"]["env_file"] == ["x.env", "y.env"]


def test_cli_and_json_and_exit_codes(proj, capsys, monkeypatch):
    d, h = proj({"package.json": VITE, ".env": "A=1\n"})
    monkeypatch.delenv("A", raising=False)
    assert cli.main(["A", "-d", d]) == 0
    assert cli.main(["NOPE", "-d", d]) == 2
    monkeypatch.setenv("A", "2")
    assert cli.main(["A", "-d", d, "--json"]) == 1
    out = capsys.readouterr().out
    assert '"tool": "whyenv"' in out


def test_demo_runs(capsys):
    assert cli.main(["--demo"]) == 0
    out = capsys.readouterr().out
    assert "SHADOWED" in out and "older than" in out and "web.env" in out
