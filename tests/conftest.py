import pytest


@pytest.fixture
def proj(tmp_path):
    def make(files, home=None):
        for name, text in files.items():
            p = tmp_path / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(text.encode("utf-8"))
        h = tmp_path / "_home"
        h.mkdir(exist_ok=True)
        for name, text in (home or {}).items():
            (h / name).write_text(text, encoding="utf-8")
        return str(tmp_path), str(h)
    return make
