import io
import sys

import pytest

from vaultkit import cli, okf
from vaultkit import note as note_mod
from vaultkit import vault as V


@pytest.fixture
def vlt(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_HUMAN", "tester")
    monkeypatch.setenv("VAULT_AGENT", "Claude")
    monkeypatch.delenv("VAULT_MODEL", raising=False)
    monkeypatch.setattr(V, "identity", lambda: "Test Person")
    monkeypatch.setattr(note_mod, "fetch", lambda url: ("Archived body text.", "fake fetch", "2025-10-15"))
    cli.main(["init", str(tmp_path / "v"), "--group-by", "harness"])
    monkeypatch.chdir(tmp_path / "v")
    return V.load()


def run(argv, stdin=""):
    old = sys.stdin
    sys.stdin = io.StringIO(stdin)
    try:
        cli.main(argv)
    finally:
        sys.stdin = old


def conforms(v):
    errors = [p for p in okf.check(v) if p[0] == "error"]
    assert not errors, errors


def test_init_makes_a_conformant_empty_bundle(vlt):
    assert (vlt.bundle / "index.md").read_text().startswith('---\nokf_version: "0.2"\n---')
    assert (vlt.root / ".claude/skills/vault-note/SKILL.md").exists()
    assert "--harness" in (vlt.root / ".claude/skills/vault-note/SKILL.md").read_text()
    assert "__" not in (vlt.root / "vault.toml").read_text()
    conforms(vlt)


def test_reading_note_carries_okf_fields(vlt):
    run(["note", "https://github.com/a/b", "--slug", "a-b", "--harness", "pi,claude-code",
         "--by", "Some One", "--tags", "x"])
    run(["note", "https://github.com/a/b", "--slug", "a-b", "--force", "--no-archive",
         "--model", "claude-opus-5-5"], stdin="It claims one thing. Then more.")
    f, body = V.read(vlt.bundle / "reading/a-b.md")
    assert f["type"] == "reading"
    assert f["title"] == "a-b"
    assert f["kind"] == "repo"
    assert f["resource"] == "https://github.com/a/b"
    assert f["sources"][0]["resource"] == "/sources/a-b.md"
    assert f["description"] == "It claims one thing."
    assert f["generated"]["by"] == "claude/claude-opus-5-5"
    assert V.when(f["generated"]["at"]) is not None
    assert list(f["harness"]) == ["pi", "claude-code"]
    assert list(f["by"]) == ["[[Some One]]"]
    assert f["readStatus"] == "unread" and "status" not in f
    assert "> [!agent] Claude summary\n> It claims one thing." in body
    assert "### Test Person" in body
    src, _ = V.read(vlt.sources / "a-b.md")
    assert src["type"] == "source" and src["resource"] == "https://github.com/a/b"
    assert src["published"] == "2025-10-15" and f["published"] == "2025-10-15"
    conforms(vlt)


def test_a_published_date_already_on_the_note_wins(vlt):
    run(["note", "https://x.org/p", "--slug", "p", "--set", "published=2024-01-02"])
    run(["note", "https://x.org/p", "--slug", "p", "--force"])
    f, _ = V.read(vlt.bundle / "reading/p.md")
    assert f["published"] == "2024-01-02"


def test_metadata_dates_are_normalised_and_stripped():
    from vaultkit.archive import iso_date, split_metadata
    assert iso_date("20260810") == "2026-08-10"
    assert iso_date("not a date") is None
    text, date = split_metadata('---\ntitle: "T"\ndate: "2025-10-15"\n---\n# T\n\nBody')
    assert (text, date) == ("# T\n\nBody", "2025-10-15")
    assert split_metadata("# T\n\nBody") == ("# T\n\nBody", None)


def test_rerun_keeps_the_users_section_and_replaces_the_summary(vlt):
    run(["note", "https://x.org/p", "--slug", "p"])
    path = vlt.bundle / "reading/p.md"
    path.write_text(path.read_text().replace("### Test Person\n",
                                             "### Test Person\n\n**2026-10-01** — mine\n"))
    text = path.read_text().replace("tags:", "myKey: kept\ntags:")
    path.write_text(text + "\n> a quote of my own\n")
    run(["note", "https://x.org/p", "--slug", "p", "--force", "--no-archive"], stdin="First.")
    run(["note", "https://x.org/p", "--slug", "p", "--force", "--no-archive"], stdin="Second.")
    f, body = V.read(path)
    assert body.count("[!agent]") == 1 and "> Second." in body
    assert "**2026-10-01** — mine" in body
    assert "> a quote of my own" in body
    assert f["myKey"] == "kept"
    assert f["description"] == "First."  # an existing description isn't clobbered


def test_log_is_newest_first_with_one_heading_per_day(vlt):
    log = vlt.bundle / "log.md"
    log.write_text(log.read_text().replace(V.today(), "2020-01-01"))
    run(["note", "--slug", "idea", "--template", "atomic"])
    run(["note", "--slug", "idea2", "--template", "atomic"])
    text = log.read_text()
    assert text.index(f"## {V.today()}") < text.index("## 2020-01-01")
    assert text.count(f"## {V.today()}") == 1
    assert "[idea](idea.md)" in text and "[idea2](idea2.md)" in text
    conforms(vlt)


def test_indexes_list_descriptions_grouped(vlt):
    run(["note", "https://x.org/p", "--slug", "p", "--harness", "pi", "--no-archive",
         "--description", "Says a thing."])
    idx = (vlt.bundle / "reading/index.md").read_text()
    assert "## pi" in idx and "- [p](p.md) — Says a thing." in idx
    root = (vlt.bundle / "index.md").read_text()
    assert "[Reading](reading/index.md)" in root


def test_verify_clears_needs_review_until_regenerated(vlt):
    run(["note", "https://x.org/p", "--slug", "p", "--no-archive"], stdin="Summary.")
    f, _ = V.read(vlt.bundle / "reading/p.md")
    assert V.needs_review(f)
    run(["verify", "reading/p"])
    f, _ = V.read(vlt.bundle / "reading/p.md")
    assert f["verified"][0]["by"] == "human:tester"
    assert not V.needs_review(f)
    assert "**Verification**" in (vlt.bundle / "log.md").read_text()


def test_synth_builds_a_table_and_reruns_without_stacking(vlt):
    for s, h in [("a", "pi"), ("b", "pi"), ("c", "codex")]:
        run(["note", f"https://x.org/{s}", "--slug", s, "--harness", h, "--no-archive"])
    run(["synth", "--slug", "landscape"])
    run(["synth", "--slug", "landscape", "--force"])
    body = (vlt.bundle / "synthesis/landscape.md").read_text()
    assert body.count("## By harness") == 1
    assert "| **pi** |" in body and "[a](../reading/a.md)" in body
    assert body.index("## By harness") < body.index("## Thinking")
    conforms(vlt)


def test_check_catches_what_breaks_conformance(vlt):
    (vlt.bundle / "no-fm.md").write_text("# hi\n")
    (vlt.bundle / "no-type.md").write_text("---\ntitle: x\n---\n")
    (vlt.bundle / "bad.md").write_text("---\ntype: [unclosed\n---\n")
    (vlt.bundle / "reading/index.md").write_text("---\nokf_version: '0.2'\n---\n# R\n")
    log = vlt.bundle / "log.md"
    log.write_text(log.read_text() + "\n## 2099-01-01\n\n- **Creation** x\n")
    msgs = {(p.name, m.split(":")[0]) for lvl, p, m in okf.check(vlt) if lvl == "error"}
    names = {n for n, _ in msgs}
    assert {"no-fm.md", "no-type.md", "bad.md", "index.md", "log.md"} <= names


def test_reserved_slug_is_refused(vlt):
    with pytest.raises(SystemExit):
        run(["note", "--slug", "index", "--template", "atomic"])


def test_links_resolve_markdown_and_wikilinks(vlt):
    run(["note", "https://x.org/p", "--slug", "p", "--no-archive"])
    (vlt.bundle / "mine.md").write_text(
        "---\ntype: atomic\n---\n# mine\n[p](reading/p.md) and [[p]] and [w](https://a.b/c.md)\n")
    ids = V.links(vlt, vlt.bundle / "mine.md", (vlt.bundle / "mine.md").read_text())
    assert ids == {"reading/p"}


def test_verify_by_slug_skips_the_archive_and_archives_need_no_review(vlt):
    run(["note", "https://x.org/p", "--slug", "p"], stdin="Summary.")
    src, _ = V.read(vlt.sources / "p.md")
    assert not V.needs_review(src)
    run(["verify", "p"])
    f, _ = V.read(vlt.bundle / "reading/p.md")
    assert f["verified"][0]["by"] == "human:tester"


def _requires(v, slug, *targets):
    """Put a `requires` list on an existing reading note."""
    path = v.bundle / f"reading/{slug}.md"
    text = path.read_text()
    lines = "".join(f'  - "[[{t}]]"\n' for t in targets)
    path.write_text(text.replace("requires:\n", f"requires:\n{lines}", 1))


def _three(vlt):
    for s in "abc":
        run(["note", f"https://x.org/{s}", "--slug", s])


def test_requires_that_resolve_and_do_not_loop_conform(vlt):
    _three(vlt)
    _requires(vlt, "b", "reading/a")
    _requires(vlt, "c", "reading/a", "b")  # by path, and by bare filename
    conforms(vlt)


def test_requires_pointing_nowhere_is_an_error(vlt):
    _three(vlt)
    _requires(vlt, "b", "reading/missing")
    errors = [m for lvl, _, m in okf.check(vlt) if lvl == "error"]
    assert any("missing" in m for m in errors)


def test_requires_that_loop_are_an_error(vlt):
    _three(vlt)
    _requires(vlt, "a", "reading/c")
    _requires(vlt, "b", "reading/a")
    _requires(vlt, "c", "reading/b")
    errors = [m for lvl, _, m in okf.check(vlt) if lvl == "error"]
    assert any("loops" in m for m in errors)


def test_a_note_cannot_require_itself(vlt):
    _three(vlt)
    _requires(vlt, "a", "reading/a")
    assert any("loops" in m for lvl, _, m in okf.check(vlt) if lvl == "error")


def test_key_is_a_boolean(vlt):
    _three(vlt)
    path = vlt.bundle / "reading/a.md"
    path.write_text(path.read_text().replace("key:\n", "key: maybe\n", 1))
    assert any("`key" in m for lvl, _, m in okf.check(vlt) if lvl == "warning")
    path.write_text(path.read_text().replace("key: maybe", "key: true", 1))
    assert not any("`key" in m for _, _, m in okf.check(vlt))


def test_graph_levels_edges_and_key(vlt, capsys):
    import json
    _three(vlt)
    _requires(vlt, "b", "reading/a")
    _requires(vlt, "c", "reading/a", "b")
    p = vlt.bundle / "reading/a.md"
    p.write_text(p.read_text().replace("key:\n", "key: true\n", 1))
    capsys.readouterr()
    run(["graph"])
    g = json.loads(capsys.readouterr().out)
    level = {n["id"]: n["level"] for n in g["nodes"]}
    assert level == {"reading/a": 0, "reading/b": 1, "reading/c": 2}
    assert {"from": "reading/a", "to": "reading/c"} in g["edges"]
    assert [n["key"] for n in g["nodes"]] == [True, False, False]


def test_graph_refuses_a_loop(vlt):
    _three(vlt)
    _requires(vlt, "a", "reading/b")
    _requires(vlt, "b", "reading/a")
    with pytest.raises(SystemExit):
        run(["graph"])
