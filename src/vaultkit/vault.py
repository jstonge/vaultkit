"""Shared reading of a vault, so commands don't drift in how they parse notes.

A vault is the directory holding `vault.toml`, found by walking up from the
current directory — the tool lives in one place and serves any vault. The OKF
bundle is a directory inside it (`bundle =` in the config), so the project
files around it — AGENTS.md, templates, .obsidian — never have to pass as
concepts.
"""

import io
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from . import __version__

RESERVED = {"index.md", "log.md"}  # OKF §8, §9: never concepts
WIKILINK = re.compile(r"\[\[([^\]|#]+)")
MDLINK = re.compile(r"\]\(<?([^)<>]+?\.md)>?(?:#[^)]*)?\)")


def _yaml():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096  # never wrap a long description onto a second line
    y.indent(mapping=2, sequence=4, offset=2)  # `  - item`, as Obsidian writes it
    return y


YAML_RT = _yaml()


# ---------------------------------------------------------------- config

@dataclass
class Template:
    name: str
    folder: str = ""          # relative to the bundle; "" is the bundle root
    authored: bool = False    # gets an `### <author>` heading per person
    archive: bool = False     # fetches the URL into sources/
    index_by: str = ""        # field that groups this folder's index.md
    description: str = ""     # one line for the bundle's root index.md


@dataclass
class Vault:
    root: Path
    name: str
    bundle: Path
    templates_dir: Path
    group_by: str
    group_label: str
    okf_version: str
    templates: dict = field(default_factory=dict)
    exclude: tuple = ()
    synth_columns: tuple = ("What it is", "The distinctive move")

    @property
    def sources(self):
        return self.bundle / "sources"

    def folder(self, template):
        t = self.templates.get(template)
        return self.bundle / (t.folder if t else "")

    def concept_id(self, path):
        """OKF §3: the path within the bundle, minus `.md`."""
        return Path(path).resolve().relative_to(self.bundle.resolve()).with_suffix("").as_posix()

    def excluded(self, path):
        rel = Path(path).relative_to(self.bundle)
        if any(p.startswith(".") for p in rel.parts):
            return True
        return any(rel.as_posix() == e or rel.as_posix().startswith(e.rstrip("/") + "/")
                   for e in self.exclude)


def find_root(start=None):
    start = Path(start or os.environ.get("VAULTKIT_VAULT") or Path.cwd()).resolve()
    for d in (start, *start.parents):
        if (d / "vault.toml").exists():
            return d
    sys.exit(f"no vault.toml in {start} or above — run from inside a vault, "
             "or make one with `vaultkit init <dir>`")


def load(start=None):
    root = find_root(start)
    cfg = tomllib.loads((root / "vault.toml").read_text(encoding="utf-8"))
    templates = {name: Template(name=name, **t) for name, t in cfg.get("templates", {}).items()}
    synth = cfg.get("synth", {})
    return Vault(
        root=root,
        name=cfg.get("name", root.name),
        bundle=root / cfg.get("bundle", "."),
        templates_dir=root / cfg.get("templates_dir", "my-templates"),
        group_by=cfg.get("group_by", "topic"),
        group_label=cfg.get("group_label", cfg.get("group_by", "topic").capitalize()),
        okf_version=str(cfg.get("okf_version", "0.2")),
        templates=templates,
        exclude=tuple(cfg.get("exclude", ())),
        synth_columns=tuple(synth.get("columns", Vault.synth_columns)),
    )


# ---------------------------------------------------------------- frontmatter

FM = re.compile(r"\A---\n(.*?)^---[ \t]*\n?", re.S | re.M)


def split(text):
    """(frontmatter text or None, body)."""
    m = FM.match(text)
    return (m[1], text[m.end():]) if m else (None, text)


def parse(text):
    """(mapping, body). Raises on YAML the parser can't read — `check` reports
    that; everything else treats an unreadable block as empty."""
    fm, body = split(text)
    if fm is None:
        return None, body
    data = YAML_RT.load(fm) if fm.strip() else CommentedMap()
    return (data if data is not None else CommentedMap()), body


def read(path):
    try:
        data, body = parse(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return CommentedMap(), Path(path).read_text(encoding="utf-8")
    return (data if isinstance(data, dict) else CommentedMap()), body


def dump(data, body):
    out = io.StringIO()
    YAML_RT.dump(data, out)
    return f"---\n{out.getvalue()}---\n{body}"


def listed(fields, key):
    v = fields.get(key)
    if v is None or v == "":
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


def linked(fields, key):
    """A list field whose values are wikilinks, as plain names."""
    return [raw.strip('"').strip("[]").split("|")[0].split("/")[-1]
            for raw in listed(fields, key)]


def seq(items):
    return CommentedSeq(list(items))


# ---------------------------------------------------------------- time and people

def now():
    """OKF §5: ISO 8601 with an explicit offset."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def today():
    return date.today().isoformat()


def identity():
    """Who's writing. The git name is what a collaborator sees in the history
    anyway; whoami is the fallback when git isn't configured."""
    for cmd in (["git", "config", "user.name"], ["whoami"]):
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    return "unknown"


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def human_actor(name=None):
    """OKF §6 actor for a person: `human:<id>`."""
    if who := os.environ.get("VAULT_HUMAN"):
        return who if who.startswith("human:") else f"human:{who}"
    return f"human:{slugify(name or identity())}"


def agent_name():
    return os.environ.get("VAULT_AGENT", "Claude")


def agent_actor(model=None):
    """OKF §6 actor for an agent: `<producer>/<version>`."""
    model = model or os.environ.get("VAULT_MODEL", "")
    producer = slugify(agent_name())
    return f"{producer}/{model}" if model else producer


TOOL_ACTOR = f"vaultkit/{__version__}"


# ---------------------------------------------------------------- notes

def gist(body, limit=110):
    """The note's first sentence — the agent's summary, else the author's own text."""
    m = re.search(r"(?ms)^# .*?\n(.*?)(?:^## |\Z)", body)
    text = m[1].strip() if m else ""
    text = re.sub(r"^> \[!(?:agent|claude)\][^\n]*\n", "", text)
    if not text:
        m = re.search(r"(?ms)^## Why do I bring this up\?\n(.*)\Z", body)
        text = m[1].strip() if m else ""
        text = re.sub(r"(?m)^### .*\n?", "", text).strip()
        text = re.sub(r"^\*\*[\d-]+\*\* — ", "", text)
    text = re.sub(r"^>\s*", "", text, flags=re.M).replace("\n", " ").strip()
    return (text[:limit].rsplit(" ", 1)[0] + "…") if len(text) > limit else text


def first_sentence(text):
    text = " ".join(text.split())
    m = re.match(r"(.+?[.!?])(?:\s|$)", text)
    return m[1] if m else text


@dataclass
class Note:
    path: Path
    id: str
    fields: dict
    body: str

    @property
    def slug(self):
        return self.path.stem

    @property
    def title(self):
        return str(self.fields.get("title") or self.slug)

    @property
    def description(self):
        return str(self.fields.get("description") or "") or gist(self.body)


def concepts(v):
    """Every non-reserved .md in the bundle."""
    out = []
    for f in sorted(v.bundle.rglob("*.md")):
        if f.name in RESERVED or v.excluded(f):
            continue
        fields, body = read(f)
        out.append(Note(f, v.concept_id(f), fields, body))
    return out


def notes_in(v, template):
    d = v.folder(template)
    out = []
    for f in sorted(d.glob("*.md")):
        if f.name in RESERVED or v.excluded(f):
            continue
        fields, body = read(f)
        out.append(Note(f, v.concept_id(f), fields, body))
    return out


def links(v, path, body):
    """Concept ids a body links to. Markdown links resolve against the file's
    folder; wikilinks resolve by filename, as Obsidian does."""
    by_name = {}
    for f in v.bundle.rglob("*.md"):
        by_name.setdefault(f.stem, f)
    out = set()
    for target in MDLINK.findall(body):
        if re.match(r"^[a-z]+://", target):
            continue
        target = unquote(target)
        base = v.bundle if target.startswith("/") else Path(path).parent
        p = (base / target.lstrip("/")).resolve()
        try:
            out.add(v.concept_id(p))
        except ValueError:
            pass
    for name in WIKILINK.findall(body):
        name = name.strip().split("/")[-1]
        if name in by_name:
            out.add(v.concept_id(by_name[name]))
        else:
            out.add(name)
    return out


def groups(notes, key):
    """value -> [Note], most-covered first."""
    out = {}
    for n in notes:
        for g in listed(n.fields, key):
            out.setdefault(g, []).append(n)
    return dict(sorted(out.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def by_author(notes):
    out = {}
    for n in notes:
        for b in linked(n.fields, "by"):
            out.setdefault(b, []).append(n)
    return dict(sorted(out.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def as_list(v):
    """OKF §5: a bare `verified` mapping is a one-element list."""
    if v is None:
        return []
    return list(v) if isinstance(v, list) else [v]


def when(value):
    """A timestamp field as an aware datetime, or None if it isn't one."""
    if isinstance(value, datetime):
        return value if value.tzinfo else None
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return dt if dt.tzinfo else None


def needs_review(fields):
    """An agent wrote it and no human has verified it since."""
    gen = fields.get("generated")
    if not isinstance(gen, dict) or not gen.get("by"):
        return False
    if str(gen["by"]).startswith(TOOL_ACTOR.split("/")[0] + "/"):
        return False  # fetched verbatim by the tool, not written by an agent
    at = when(gen.get("at"))
    humans = [when(e.get("at")) for e in as_list(fields.get("verified"))
              if isinstance(e, dict) and str(e.get("by", "")).startswith("human:")]
    return not any(h and (at is None or h >= at) for h in humans)
