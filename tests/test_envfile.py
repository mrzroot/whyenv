from whyenv import envfile


def d(text):
    return {e.key: e for e in envfile.parse(text)}


def test_basic_quotes_comments_export():
    e = d('A=1\nexport B="two words"\nC=\'x # y\'\nD=val # comment\n# E=no\n\nF=\n')
    assert e["A"].value == "1"
    assert e["B"].value == "two words"
    assert e["C"].value == "x # y"
    assert e["D"].value == "val" and any("comment" in i for i in e["D"].issues)
    assert "E" not in e and e["F"].value == ""


def test_crlf_and_bom():
    e = d("\ufeffA=1\r\nB=2\r\n")
    assert e["A"].value == "1" and e["B"].value == "2"
    assert any("BOM" in i for i in e["A"].issues)
    assert any("CRLF" in i for i in e["B"].issues)
    assert not any("BOM" in i for i in e["B"].issues)


def test_spaces_and_dollar():
    e = d("A = 1\nB=pa$word\nC='pa$word'\n")
    assert any("spaces" in i for i in e["A"].issues)
    assert any("'$'" in i for i in e["B"].issues)
    assert not e["C"].issues


def test_duplicates_last_wins():
    entries = envfile.parse("A=1\nA=2\n")
    assert len(entries) == 2 and envfile.last_wins(entries)["A"].value == "2"


def test_double_quote_escapes_and_unterminated():
    assert d('A="x\\ny"')["A"].value == "x\ny"
    assert any("unterminated" in i for i in d('A="oops')["A"].issues)


def test_invalid_keys_skipped():
    assert d("1A=x\nA B=y\n=z\n") == {}
