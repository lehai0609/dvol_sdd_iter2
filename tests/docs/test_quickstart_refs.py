from pathlib import Path


def test_quickstart_doc_exists_and_has_sections():
    p = Path("specs/001-dvol-forecasting-volatility/quickstart.md")
    assert p.exists(), "quickstart.md should exist"
    txt = p.read_text(encoding="utf-8")
    # Check a few expected section keywords
    assert "Quickstart" in txt
    assert "Environment" in txt or "Repo Layout" in txt
